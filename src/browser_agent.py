import json
from typing import Optional
from src.resume_tailor import compute_match_score, tailor_resume, load_base_resume
from src.llm_client import get_llm_client
from src.config_loader import load_all_configs, load_skills
from src.email_handler import send_blocked_summary
from src.db import AppliedJob, SearchResult, ResumeVersion
from src.linkedin_client import LinkedInClient
from agent_commons.db import get_session
from datetime import datetime, timezone


async def search_linkedin(
    role: str,
    location: str = "Ottawa",
    max_results: int = 100,
    headless: bool = True,
) -> list[dict]:
    client = LinkedInClient()
    try:
        jobs = client.search_jobs(role, location=location, max_results=max_results)
        return jobs or []
    finally:
        client.close()


async def apply_to_job(
    job: dict,
    profile: dict,
    resume: str,
    tailored_resume: str = None,
    skills: dict = None,
    headless: bool = True,
) -> dict:
    if job.get("apply_type") == "easy_apply":
        return {
            "status": "blocked",
            "job_id": job.get("url"),
            "title": job.get("title"),
            "company": job.get("company"),
            "block_reason": "Easy Apply requires browser automation - not yet implemented",
        }
    return {
        "status": "blocked",
        "job_id": job.get("url"),
        "title": job.get("title"),
        "company": job.get("company"),
        "block_reason": f"External apply - please apply manually at {job.get('apply_url', 'N/A')}",
    }


async def run_search_and_apply(
    target_roles: list[str] = None,
    location: str = "Ottawa",
    max_to_search: int = 100,
    max_to_apply: int = 10,
    min_match_score: float = None,
    headless: bool = True,
) -> dict:
    config = load_all_configs()
    filters = config.get("filters", {})
    profile = config.get("profile", {})

    target_roles = target_roles or filters.get("target_roles", ["Data Engineering Manager"])
    location = location or filters.get("location", "Ottawa")
    max_to_search = max_to_search or filters.get("max_to_search", 100)
    max_to_apply = max_to_apply or filters.get("max_to_apply", 10)
    min_match_score = min_match_score or filters.get("min_match_score", 80.0)

    skills = load_skills()
    base_resume = load_base_resume()
    session = get_session()
    try:
        already_applied = {r.job_id for r in session.query(AppliedJob).filter(AppliedJob.status.in_(["applied", "blocked", "failed"])).all()}

        all_results = []

        for role in target_roles:
            results = await search_linkedin(role, location=location, max_results=max_to_search, headless=headless)
            all_results.extend(results)

        from src.report import extract_skill_frequency
        all_skills_freq = extract_skill_frequency(all_results)

        scored_jobs = []
        blocked = []
        applied = 0

        for job in all_results:
            if job["url"] in already_applied:
                continue
            try:
                score = compute_match_score(job.get("jd", ""), base_resume)
            except Exception as e:
                entry = AppliedJob(
                    job_id=job["url"],
                    title=job.get("title"),
                    company=job.get("company"),
                    url=job["url"],
                    source="linkedin",
                    status="blocked",
                    block_reason=f"LLM scoring failed: {e}",
                    match_score=0.0,
                    jd_raw=job.get("jd"),
                )
                session.add(entry)
                blocked.append({"title": job.get("title"), "company": job.get("company"), "block_reason": f"LLM scoring failed: {e}"})
                already_applied.add(job["url"])
                continue

            if score >= min_match_score:
                scored_jobs.append((score, job))

        scored_jobs.sort(key=lambda x: x[0], reverse=True)
        top_jobs = scored_jobs[:max_to_apply]

        for score, job in top_jobs:
            try:
                tailored = tailor_resume(job.get("jd", ""), base_resume)
            except Exception as e:
                entry = AppliedJob(
                    job_id=job["url"],
                    title=job.get("title"),
                    company=job.get("company"),
                    url=job["url"],
                    source="linkedin",
                    status="blocked",
                    block_reason=f"LLM tailoring failed: {e}",
                    match_score=score,
                    jd_raw=job.get("jd"),
                )
                session.add(entry)
                blocked.append({"title": job.get("title"), "company": job.get("company"), "block_reason": f"LLM tailoring failed: {e}"})
                continue

            result = await apply_to_job(
                job=job,
                profile=profile,
                resume=base_resume,
                tailored_resume=tailored,
                skills=skills,
                headless=headless,
            )
            result.setdefault("company", job["company"])
            entry = AppliedJob(
                job_id=job["url"],
                title=job["title"],
                company=job["company"],
                url=job["url"],
                source="linkedin",
                status=result["status"],
                block_reason=result.get("block_reason"),
                match_score=score,
                jd_raw=job.get("jd"),
            )
            session.add(entry)
            if result["status"] == "blocked":
                blocked.append(result)
            else:
                applied += 1

            rv = ResumeVersion(
                version=f"tailored-{job['url'].split('/')[-1][:30]}",
                content_md=tailored,
                source_job_id=job["url"],
            )
            session.add(rv)

        sr = SearchResult(
            keywords=", ".join(target_roles),
            source="linkedin",
            results=all_results,
            skill_frequency=all_skills_freq,
            applied_count=applied,
        )
        session.add(sr)
        session.commit()
    finally:
        session.close()

    if blocked:
        send_blocked_summary(blocked)

    return {
        "total_searched": len(all_results),
        "scored": len(scored_jobs),
        "applied_count": applied,
        "blocked_count": len(blocked),
    }
