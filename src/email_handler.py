from agent_commons.email import EmailClient
from typing import Optional

def _get_client() -> EmailClient:
    return EmailClient()

def send_blocked_summary(blocked_jobs: list[dict], to: Optional[str] = None) -> None:
    if not blocked_jobs:
        return
    client = _get_client()
    lines = ["The following jobs were blocked during this run:\n"]
    for j in blocked_jobs:
        lines.append(f"- {j['title']} at {j['company']}: {j['block_reason']}")
    body = "\n".join(lines)
    client.send(to or client.username, subject="Job Agent: Blocked Jobs Summary", body=body)

def send_report_email(to: str, html_body: str) -> None:
    _get_client().send_report(to, subject="Weekly Job Application Report", html_body=html_body)
