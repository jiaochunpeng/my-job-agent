from fastmcp import FastMCP
from src.db import AppliedJob, SearchResult
from agent_commons.db import get_session
from src.browser_agent import run_search_and_apply
from types import SimpleNamespace
import asyncio


def create_server() -> FastMCP:
    mcp = FastMCP("my-job-agent")
    mcp._tool_manager = SimpleNamespace(_tools=[])

    @mcp.tool()
    def search_and_apply(roles: list[str] = None) -> dict:
        result = asyncio.run(run_search_and_apply(target_roles=roles))
        return result

    _tool_register(mcp, "search_and_apply")

    @mcp.tool()
    def get_history(limit: int = 20) -> list[dict]:
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

    _tool_register(mcp, "get_history")

    @mcp.tool()
    def get_status() -> dict:
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

    _tool_register(mcp, "get_status")

    @mcp.tool()
    def run_report() -> dict:
        from src.report import generate_weekly_report

        return asyncio.run(generate_weekly_report())

    _tool_register(mcp, "run_report")

    @mcp.tool()
    def get_skill_frequency(limit: int = 20) -> list[dict]:
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

    _tool_register(mcp, "get_skill_frequency")

    return mcp


def _tool_register(mcp: FastMCP, name: str) -> None:
    key = f"tool:{name}@"
    ft = mcp._local_provider._components.get(key)
    if ft:
        mcp._tool_manager._tools.append(ft)
        setattr(mcp, name, ft.fn)
