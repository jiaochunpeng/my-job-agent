import pytest
from unittest.mock import patch, MagicMock
from src.email_handler import send_blocked_summary, send_report_email

def test_send_blocked_summary():
    blocked_jobs = [
        {"title": "Data Eng Manager", "company": "Co A", "block_reason": "Missing years of Python"},
        {"title": "AI Builder", "company": "Co B", "block_reason": "Scrape failed"},
    ]
    with patch("src.email_handler.EmailClient") as MockClient:
        instance = MockClient.return_value
        send_blocked_summary(blocked_jobs, "test@test.com")
        instance.send.assert_called_once()

def test_send_report_email():
    with patch("src.email_handler.EmailClient") as MockClient:
        instance = MockClient.return_value
        send_report_email("test@test.com", "<h1>Report</h1><p>Content</p>")
        instance.send_report.assert_called_once_with(
            "test@test.com", subject="Weekly Job Application Report", html_body="<h1>Report</h1><p>Content</p>"
        )

def test_send_blocked_summary_empty_list():
    with patch("src.email_handler.EmailClient") as MockClient:
        instance = MockClient.return_value
        send_blocked_summary([], "test@test.com")
        instance.send.assert_not_called()
