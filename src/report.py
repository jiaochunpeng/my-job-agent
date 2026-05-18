from datetime import datetime, timedelta
from collections import Counter
import re
from src.db import AppliedJob, WeeklyReport, SearchResult
from agent_commons.db import get_session
from src.email_handler import send_report_email
from src.config_loader import load_all_configs

def extract_skill_frequency(results: list[dict]) -> dict[str, int]:
    all_text = " ".join(r.get("jd", "") for r in results)
    skills = re.findall(
        r"\b(Python|Azure|SQL|Spark|PySpark|Fabric|Synapse|ADF|Kubernetes|Docker|"
        r"Airflow|ML|AI|Data\s*(?:Engineering|Lake|Warehouse)|DevOps|CI\/CD|"
        r"Dynamics\s*365|Databricks|Snowflake|Power\s*BI|Tableau)\b",
        all_text, re.I
    )
    return dict(Counter(s.lower() for s in skills))

def build_report_html(data: dict) -> str:
    rows = ""
    for job in data.get("applied", []):
        rows += (
            f"<tr><td>{job['title']}</td><td>{job['company']}</td>"
            f"<td>{job.get('match_score', 'N/A')}</td>"
            f"<td>{str(job.get('applied_at', ''))[:10]}</td></tr>"
        )

    blocked_rows = ""
    for job in data.get("blocked", []):
        blocked_rows += (
            f"<tr><td>{job['title']}</td><td>{job['company']}</td>"
            f"<td>{job.get('match_score', 'N/A')}</td>"
            f"<td>{job.get('block_reason', '')}</td></tr>"
        )

    skill_rows = ""
    for s in data.get("skill_frequency", []):
        skill_rows += f"<tr><td>{s['skill']}</td><td>{s['count']}</td></tr>"

    blocked_section = ""
    if blocked_rows:
        blocked_section = f"""
    <h2>Blocked Jobs</h2>
    <table border="1"><tr><th>Title</th><th>Company</th><th>Match %</th><th>Reason</th></tr>{blocked_rows}</table>"""

    return f"""<html><body>
    <h1>Daily Job Report</h1>
    <p>{data['week_start']}</p>
    <h2>Summary</h2>
    <p>Searched: {data['total_searched']} | Applied: {data['total_applied']} | Blocked: {data['total_blocked']}</p>
    <h2>Applied Roles</h2>
    <table border="1"><tr><th>Title</th><th>Company</th><th>Match %</th><th>Date</th></tr>{rows}</table>
    {blocked_section}
    <h2>Top Skills in Market</h2>
    <table border="1"><tr><th>Skill</th><th>Frequency</th></tr>{skill_rows}</table>
    </body></html>"""

def generate_weekly_report() -> dict:
    config = load_all_configs()
    profile = config.get("profile", {})
    to_email = profile.get("email", "")

    session = get_session()
    week_ago = datetime.now() - timedelta(days=1)
    recent = session.query(AppliedJob).filter(
        AppliedJob.applied_at >= week_ago,
    ).all()

    applied_jobs = [j for j in recent if j.status == "applied"]
    blocked_jobs = [j for j in recent if j.status == "blocked"]

    search_results = session.query(SearchResult).order_by(
        SearchResult.searched_at.desc()
    ).limit(5).all()
    session.close()

    all_raw = []
    for sr in search_results:
        if sr.results:
            all_raw.extend(sr.results if isinstance(sr.results, list) else [])

    skill_freq = extract_skill_frequency(all_raw)
    sorted_skills = sorted(skill_freq.items(), key=lambda x: x[1], reverse=True)[:20]

    data = {
        "week_start": datetime.now().strftime("%Y-%m-%d"),
        "applied": [
            {
                "title": j.title,
                "company": j.company,
                "match_score": j.match_score,
                "applied_at": str(j.applied_at),
            }
            for j in applied_jobs
        ],
        "blocked": [
            {
                "title": j.title,
                "company": j.company,
                "match_score": j.match_score,
                "block_reason": j.block_reason,
            }
            for j in blocked_jobs
        ],
        "skill_frequency": [{"skill": s, "count": c} for s, c in sorted_skills],
        "total_searched": (
            sum(len(sr.results) for sr in search_results if sr.results)
            if search_results else 0
        ),
        "total_applied": len(applied_jobs),
        "total_blocked": len(blocked_jobs),
    }

    html = build_report_html(data)
    send_report_email(to_email or "user@example.com", subject="Daily Job Report", html_body=html)

    session = get_session()
    wr = WeeklyReport(week_start=week_ago.date(), report_data=data, sent_at=datetime.now())
    session.add(wr)
    session.commit()
    session.close()

    return {"sent": True, "report": data}
