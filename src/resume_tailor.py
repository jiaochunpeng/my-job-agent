from pathlib import Path
from src.llm_client import get_llm_client
import re

def load_base_resume(path: str = "resume/joseph-jiao.md") -> str:
    return Path(path).read_text()

def compute_match_score(jd: str, resume: str, llm_client=None) -> float:
    client = llm_client or get_llm_client()
    prompt = f"""Rate how well this resume matches the job description on a scale of 0-100.
Return ONLY the number, no other text.

JOB DESCRIPTION:
{jd}

RESUME:
{resume}"""
    result = client.query(prompt, temperature=0.1, max_tokens=10)
    cleaned = result.strip()
    if cleaned.isdigit():
        return float(cleaned)
    return 0.0

def tailor_resume(jd: str, resume: str, llm_client=None) -> str:
    client = llm_client or get_llm_client()
    prompt = f"""You are a professional resume writer. Given a job description and a resume,
rewrite the resume's experience section to emphasize the skills and experience most relevant
to this job. Keep ALL facts, dates, titles, and company names exactly as written.
Never fabricate or change facts. Reorder and rephrase bullet points only.

JOB DESCRIPTION:
{jd}

RESUME:
{resume}

Return only the tailored resume in markdown format."""
    return client.query(prompt, temperature=0.3)
