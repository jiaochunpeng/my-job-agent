import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock
from src.report import generate_weekly_report, build_report_html, extract_skill_frequency

def test_extract_skill_frequency():
    results = [
        {"title": "Job 1", "company": "Co", "jd": "Python, Azure, Python, Spark"},
        {"title": "Job 2", "company": "Co", "jd": "Azure, SQL, Python"},
    ]
    freq = extract_skill_frequency(results)
    assert freq["python"] == 3
    assert freq["azure"] == 2
    assert freq["spark"] == 1

def test_build_report_html_contains_sections():
    data = {
        "week_start": "2026-05-11",
        "applied": [
            {"title": "DE Manager", "company": "Co A", "match_score": 92, "applied_at": "2026-05-14"},
        ],
        "skill_frequency": [{"skill": "Python", "count": 45}, {"skill": "Azure", "count": 30}],
        "total_searched": 100,
        "total_applied": 5,
        "total_blocked": 2,
    }
    html = build_report_html(data)
    assert "DE Manager" in html
    assert "Co A" in html
    assert "Python" in html
    assert "45" in html
    assert "100" in html

def test_generate_weekly_report():
    mock_applied_jobs = [
        MagicMock(title="DE Manager", company="Co A", match_score=92, applied_at="2026-05-14 10:00:00"),
    ]
    mock_search_results = [
        MagicMock(results=[{"jd": "Python, Azure"}], skill_frequency=None),
    ]

    with patch("src.report.get_session") as mock_get_session, \
         patch("src.report.send_report_email") as mock_send:
        session = mock_get_session.return_value
        session.query.return_value.filter.return_value.all.side_effect = [mock_applied_jobs, []]
        session.query.return_value.order_by.return_value.limit.return_value.all.return_value = mock_search_results

        result = generate_weekly_report()
        assert result["sent"] is True
        assert "report" in result
        mock_send.assert_called_once()
