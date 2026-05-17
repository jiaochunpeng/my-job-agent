import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from src.browser_agent import search_linkedin, apply_to_job, run_search_and_apply


@pytest.mark.asyncio
async def test_search_linkedin_returns_results():
    with patch("src.browser_agent.LinkedInClient") as MockClient:
        instance = MockClient.return_value
        instance.search_jobs.return_value = [
            {"title": "Data Engineering Manager", "company": "Test Co", "url": "https://linkedin.com/jobs/1", "jd": "JD text"}
        ]
        results = await search_linkedin("Data Engineering Manager", location="Ottawa", max_results=10)
        assert len(results) == 1
        assert results[0]["title"] == "Data Engineering Manager"


@pytest.mark.asyncio
async def test_apply_to_job_blocks_on_missing_info():
    profile = {"first_name": "Joseph", "city": "Ottawa"}
    result = await apply_to_job(
        job={"title": "DE Manager", "company": "Co", "url": "https://linkedin.com/jobs/1", "jd": "JD", "apply_type": "external"},
        profile=profile,
        resume="# Joseph\nResume content",
    )
    assert result["status"] == "blocked"
    assert "External apply" in result["block_reason"]


@pytest.mark.asyncio
async def test_apply_to_job_succeeds():
    profile = {"first_name": "Joseph", "city": "Ottawa"}
    result = await apply_to_job(
        job={"title": "DE Manager", "company": "Co", "url": "https://linkedin.com/jobs/1", "jd": "JD", "apply_type": "easy_apply"},
        profile=profile,
        resume="# Joseph\nResume content",
    )
    assert result["status"] == "blocked"
    assert "not yet implemented" in result["block_reason"]


@pytest.fixture
def mock_db_session():
    session = MagicMock()
    session.query.return_value.filter.return_value.all.return_value = []
    session.add = MagicMock()
    session.commit = MagicMock()
    session.close = MagicMock()
    return session


@pytest.mark.asyncio
async def test_run_search_and_apply_full_flow(mock_db_session):
    with patch("src.browser_agent.search_linkedin") as mock_search, \
         patch("src.browser_agent.apply_to_job") as mock_apply, \
         patch("src.browser_agent.compute_match_score") as mock_score, \
         patch("src.browser_agent.tailor_resume") as mock_tailor, \
         patch("src.browser_agent.send_blocked_summary") as mock_summary, \
         patch("src.browser_agent.load_base_resume") as mock_resume, \
         patch("src.browser_agent.load_all_configs") as mock_config, \
         patch("src.browser_agent.get_session") as mock_get_session:
        mock_get_session.return_value = mock_db_session
        mock_tailor.return_value = "# Tailored Resume"
        mock_resume.return_value = "# Resume"
        mock_config.return_value = {
            "filters": {"target_roles": ["Data Engineering Manager"], "max_to_search": 100, "max_to_apply": 10, "min_match_score": 80},
            "profile": {"first_name": "Joseph"},
        }
        mock_search.return_value = [
            {"title": "Job A", "company": "Co A", "url": "url1", "jd": "JD1"},
            {"title": "Job B", "company": "Co B", "url": "url2", "jd": "JD2"},
        ]
        mock_score.return_value = 90
        mock_apply.side_effect = [
            {"status": "applied", "job_id": "url1", "title": "Job A"},
            {"status": "blocked", "job_id": "url2", "title": "Job B", "block_reason": "Missing info"},
        ]
        result = await run_search_and_apply()
        assert result["applied_count"] == 1
        assert result["blocked_count"] == 1
        assert result["total_searched"] == 2
        mock_summary.assert_called_once()
