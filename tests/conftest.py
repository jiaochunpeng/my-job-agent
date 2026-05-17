import pytest
import os
from unittest.mock import patch

@pytest.fixture
def mock_env_vars():
    env_patch = {
        "DATABASE_URL": "postgresql://localhost:5432/job_agent_test",
        "LLM_MODEL": "gpt-4o",
        "LLM_API_KEY": "test-key",
        "LLM_BASE_URL": "https://api.openai.com/v1",
        "EMAIL_USERNAME": "test@test.com",
        "EMAIL_PASSWORD": "pass",
        "SMTP_HOST": "smtp.test.com",
        "SMTP_PORT": "587",
        "IMAP_HOST": "imap.test.com",
        "IMAP_PORT": "993",
    }
    with patch.dict(os.environ, env_patch, clear=False):
        yield

@pytest.fixture
def sample_jd():
    return """
We are looking for a Data Engineering Manager to lead our data platform team.
Requirements:
- 10+ years experience in data engineering
- 5+ years managing teams
- Azure Synapse, Fabric, Data Lake expertise
- Python, PySpark, SQL
- Experience with CI/CD and DevOps
- AI/ML knowledge is a plus
"""

@pytest.fixture
def sample_resume():
    return """
# Joseph Jiao
Accomplished Data Leader with over 20 years of experience in end-to-end data lifecycle.
- Led data engineering team at OCS Ontario Cannabis Store
- Azure Synapse, Fabric, Data Lake, PySpark, ADF
- Python, SQL, .NET
- Dynamics 365 CRM, AI/ML integrations
- CI/CD pipelines with Azure DevOps
"""
