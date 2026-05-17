from fastmcp import FastMCP
from src.db import AppliedJob, SearchResult
from agent_commons.db import get_session
from src.browser_agent import run_search_and_apply
import asyncio


def create_server() -> FastMCP:
    mcp = FastMCP("my-job-agent")

    @mcp.tool()
    def search_and_apply(roles: list[str] = None) -> dict:
        """Run a job search and apply cycle for the given roles."""
        result = asyncio.run(run_search_and_apply(target_roles=roles))
        return result

    @mcp.tool()
    def get_history(limit: int = 20) -> list[dict]:
        """Get recently applied jobs."""
        session = get_session()
        jobs = (
            session.query(AppliedJob)
            .order_by(AppliedJob.applied_at.desc())
            .limit(limit)
            .all()
        )
        session.close()
        return [
            {
                "job_id": j.job_id,
                "title": j.title,
                "company": j.company,
                "status": j.status,
                "match_score": j.match_score,
                "applied_at": str(j.applied_at),
                "block_reason": j.block_reason,
            }
            for j in jobs
        ]

    @mcp.tool()
    def get_status() -> dict:
        """Get current status counts."""
        session = get_session()
        applied = (
            session.query(AppliedJob)
            .filter(AppliedJob.status == "applied")
            .count()
        )
        blocked = (
            session.query(AppliedJob)
            .filter(AppliedJob.status == "blocked")
            .count()
        )
        failed = (
            session.query(AppliedJob)
            .filter(AppliedJob.status == "failed")
            .count()
        )
        session.close()
        return {"applied": applied, "blocked": blocked, "failed": failed}

    @mcp.tool()
    def run_report() -> dict:
        """Generate and send the weekly report immediately."""
        from src.report import generate_weekly_report
        return asyncio.run(generate_weekly_report())

    @mcp.tool()
    def get_skill_frequency(limit: int = 20) -> list[dict]:
        """Get most common skills from recent search results."""
        session = get_session()
        results = (
            session.query(SearchResult)
            .order_by(SearchResult.searched_at.desc())
            .limit(5)
            .all()
        )
        session.close()
        freq = {}
        for r in results:
            if r.skill_frequency:
                for skill, count in r.skill_frequency.items():
                    freq[skill] = freq.get(skill, 0) + count
        sorted_skills = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:limit]
        return [{"skill": s, "count": c} for s, c in sorted_skills]

    return mcp
