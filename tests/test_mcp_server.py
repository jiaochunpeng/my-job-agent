import pytest
from unittest.mock import patch, MagicMock
from src.mcp_server import create_server

def test_server_has_correct_tools():
    server = create_server()
    tool_names = [t.name for t in server._tool_manager._tools]
    assert "search_and_apply" in tool_names
    assert "get_history" in tool_names
    assert "get_status" in tool_names
    assert "run_report" in tool_names
    assert "get_skill_frequency" in tool_names

def test_get_history_returns_applied_jobs():
    server = create_server()
    mock_job = MagicMock()
    mock_job.job_id = "url1"
    mock_job.title = "Job A"
    mock_job.company = "Co"
    mock_job.status = "applied"
    mock_job.match_score = 90.0
    mock_job.applied_at = "2026-05-16 12:00:00"
    mock_job.block_reason = None

    with patch("src.mcp_server.get_session") as mock_session:
        mock_query = MagicMock()
        mock_session.return_value.query.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_job]
        result = server.get_history(limit=10)
        assert len(result) == 1
        assert result[0]["job_id"] == "url1"
        assert result[0]["title"] == "Job A"

def test_get_status_returns_counts():
    server = create_server()
    with patch("src.mcp_server.get_session") as mock_session:
        session = mock_session.return_value
        session.query.return_value.filter.return_value.count.side_effect = [5, 2, 1]
        result = server.get_status()
        assert result["applied"] == 5
        assert result["blocked"] == 2
        assert result["failed"] == 1
