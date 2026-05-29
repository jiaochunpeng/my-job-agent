# Job Application Agent — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an automated job application agent that searches LinkedIn, matches JDs against Joseph's resume, tailors and applies to top matches, and reports weekly via email.

**Architecture:** Python package with Browser-use + CloakBrowser for browser automation, FastMCP for tool surface, Airflow DAGs for scheduling, PostgreSQL for persistence. Config via markdown files. Skills via editable `.agents/skills/` markdown files. Shared `agent_commons/` module for cross-agent reuse.

**Tech Stack:** Python 3, Browser-use, CloakBrowser, FastMCP, Airflow, PostgreSQL, SQLAlchemy, pytest.

---

## File Structure

### my-job-agent project
| File | Purpose |
|---|---|
| `.env.example` | Template for local secrets |
| `requirements.txt` | Python dependencies |
| `src/__init__.py` | Package init |
| `src/config_loader.py` | Read markdown config files |
| `src/db.py` | SQLAlchemy models + queries |
| `src/llm_client.py` | Abstracted LLM calls |
| `src/email_handler.py` | Send/receive email |
| `src/encryption.py` | Local cred encryption |
| `src/resume_tailor.py` | JD matching + resume tailoring |
| `src/browser_agent.py` | Browser-use agent for search + apply |
| `src/mcp_server.py` | FastMCP tool server |
| `src/report.py` | Weekly report generation |
| `dags/job_search_apply_dag.py` | Airflow DAG for search + apply |
| `dags/friday_report_dag.py` | Airflow DAG for weekly report |
| `config/schedule.md` | Schedule config |
| `config/filters.md` | Search filter config |
| `config/profile.md` | Personal info config |
| `resume/joseph-jiao.md` | Base resume |
| `.agents/skills/application-rules/SKILL.md` | Application behavior rules |
| `.agents/skills/resume-tailoring/SKILL.md` | Resume tailoring rules |
| `.agents/skills/answer-guide/SKILL.md` | Custom question answer templates |
| `tests/conftest.py` | Shared fixtures |
| `tests/test_config_loader.py` | Config tests |
| `tests/test_db.py` | DB tests |
| `tests/test_llm_client.py` | LLM tests |
| `tests/test_email_handler.py` | Email tests |
| `tests/test_encryption.py` | Encryption tests |
| `tests/test_resume_tailor.py` | Resume tailor tests |
| `tests/test_browser_agent.py` | Browser agent tests |
| `tests/test_mcp_server.py` | MCP server tests |
| `tests/test_report.py` | Report tests |

### agent_commons (shared, at `/home/joseph/MyProjects/agent_commons/`)
| File | Purpose |
|---|---|
| `setup.py` | Editable package install |
| `agent_commons/__init__.py` | Package init |
| `agent_commons/email.py` | Send/poll email (SMTP + IMAP) |
| `agent_commons/db.py` | PostgreSQL connection + migrations |
| `agent_commons/config.py` | Markdown config parsing |
| `agent_commons/llm.py` | Abstracted LLM client |
| `agent_commons/encryption.py` | Local credentials encryption |
| `tests/test_email.py` | Email tests |
| `tests/test_config.py` | Config tests |
| `tests/test_llm.py` | LLM tests |
| `tests/test_encryption.py` | Encryption tests |

---

### Task 1: agent_commons Shared Package

**Files:**
- Create: `/home/joseph/MyProjects/agent_commons/setup.py`
- Create: `/home/joseph/MyProjects/agent_commons/agent_commons/__init__.py`
- Create: `/home/joseph/MyProjects/agent_commons/agent_commons/email.py`
- Create: `/home/joseph/MyProjects/agent_commons/agent_commons/db.py`
- Create: `/home/joseph/MyProjects/agent_commons/agent_commons/config.py`
- Create: `/home/joseph/MyProjects/agent_commons/agent_commons/llm.py`
- Create: `/home/joseph/MyProjects/agent_commons/agent_commons/encryption.py`
- Create: `/home/joseph/MyProjects/agent_commons/tests/test_email.py`
- Create: `/home/joseph/MyProjects/agent_commons/tests/test_config.py`
- Create: `/home/joseph/MyProjects/agent_commons/tests/test_llm.py`
- Create: `/home/joseph/MyProjects/agent_commons/tests/test_encryption.py`
- Create: `/home/joseph/MyProjects/agent_commons/tests/__init__.py`

- [ ] **Step 1: Create setup.py for editable install**

  ```python
  from setuptools import setup, find_packages

  setup(
      name="agent_commons",
      version="0.1.0",
      packages=find_packages(),
      install_requires=[
          "psycopg2-binary>=2.9",
          "sqlalchemy>=2.0",
          "pydantic>=2.0",
          "cryptography>=41.0",
      ],
  )
  ```

- [ ] **Step 2: Implement agent_commons/email.py**

  ```python
  import smtplib
  import imaplib
  import email as email_lib
  from email.mime.text import MIMEText
  from email.mime.multipart import MIMEMultipart
  from typing import Optional
  import os

  class EmailClient:
      def __init__(
          self,
          smtp_host: Optional[str] = None,
          smtp_port: Optional[int] = None,
          imap_host: Optional[str] = None,
          imap_port: Optional[int] = None,
          username: Optional[str] = None,
          password: Optional[str] = None,
      ):
          self.smtp_host = smtp_host or os.getenv("SMTP_HOST", "smtp.gmail.com")
          self.smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "587"))
          self.imap_host = imap_host or os.getenv("IMAP_HOST", "imap.gmail.com")
          self.imap_port = imap_port or int(os.getenv("IMAP_PORT", "993"))
          self.username = username or os.getenv("EMAIL_USERNAME", "")
          self.password = password or os.getenv("EMAIL_PASSWORD", "")

      def send(self, to: str, subject: str, body: str, html: bool = False) -> None:
          msg = MIMEMultipart() if html else MIMEText(body, "plain" if not html else "html")
          if html:
              msg.attach(MIMEText(body, "html"))
          msg["Subject"] = subject
          msg["From"] = self.username
          msg["To"] = to
          with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
              server.starttls()
              server.login(self.username, self.password)
              server.send_message(msg)

      def poll(self, folder: str = "INBOX", since_days: int = 1) -> list[dict]:
          import datetime
          since_date = (datetime.date.today() - datetime.timedelta(days=since_days)).strftime("%d-%b-%Y")
          with imaplib.IMAP4_SSL(self.imap_host, self.imap_port) as conn:
              conn.login(self.username, self.password)
              conn.select(folder)
              status, data = conn.search(None, f'(SINCE {since_date})')
              messages = []
              for num in data[0].split():
                  _, msg_data = conn.fetch(num, "(RFC822)")
                  msg = email_lib.message_from_bytes(msg_data[0][1])
                  messages.append({
                      "subject": msg["Subject"],
                      "from": msg["From"],
                      "body": self._get_body(msg),
                      "date": msg["Date"],
                  })
              return messages

      def _get_body(self, msg) -> str:
          if msg.is_multipart():
              for part in msg.walk():
                  if part.get_content_type() == "text/plain":
                      return part.get_payload(decode=True).decode(errors="ignore")
          return msg.get_payload(decode=True).decode(errors="ignore")

      def send_report(self, to: str, subject: str, html_body: str) -> None:
          self.send(to, subject, html_body, html=True)
  ```

- [ ] **Step 3: Write failing test for email.py**

  ```python
  # tests/test_email.py
  import pytest
  from agent_commons.email import EmailClient

  def test_send_creates_correct_mime():
      import os
      os.environ["SMTP_HOST"] = "smtp.test.com"
      os.environ["SMTP_PORT"] = "587"
      os.environ["EMAIL_USERNAME"] = "test@test.com"
      os.environ["EMAIL_PASSWORD"] = "pass"
      client = EmailClient()
      assert client.smtp_host == "smtp.test.com"
      assert client.smtp_port == 587
      assert client.username == "test@test.com"
  ```

- [ ] **Step 4: Run test to verify it passes**

  Run: `cd /home/joseph/MyProjects/agent_commons && pip install -e . && pytest tests/test_email.py::test_send_creates_correct_mime -v`
  Expected: PASS

- [ ] **Step 5: Implement agent_commons/db.py**

  ```python
  import os
  from sqlalchemy import create_engine
  from sqlalchemy.orm import sessionmaker, declarative_base

  Base = declarative_base()

  def get_engine(url: str = None):
      url = url or os.getenv("DATABASE_URL", "postgresql://localhost:5432/job_agent")
      return create_engine(url)

  def get_session(engine=None):
      engine = engine or get_engine()
      return sessionmaker(bind=engine)()

  def run_migrations(engine=None):
      engine = engine or get_engine()
      Base.metadata.create_all(engine)
  ```

- [ ] **Step 6: Implement agent_commons/config.py**

  ```python
  from pathlib import Path
  from typing import Any

  def load_markdown_config(path: str) -> dict[str, Any]:
      content = Path(path).read_text()
      config = {}
      current_key = None
      current_list = []
      for line in content.splitlines():
          line = line.strip()
          if not line or line.startswith("#"):
              continue
          if line.startswith("- "):
              if current_key:
                  current_list.append(line[2:].strip())
              continue
          if ":" in line:
              if current_key and current_list:
                  config[current_key] = current_list
                  current_list = []
              key, _, val = line.partition(":")
              current_key = key.strip()
              val = val.strip()
              if val.startswith("[") and val.endswith("]"):
                  config[current_key] = [v.strip() for v in val[1:-1].split(",") if v.strip()]
              elif val.lower() == "true":
                  config[current_key] = True
              elif val.lower() == "false":
                  config[current_key] = False
              elif val and val != current_key:
                  config[current_key] = val
              else:
                  current_list = []
      if current_key and current_list:
          config[current_key] = current_list
      return config
  ```

- [ ] **Step 7: Implement agent_commons/llm.py**

  ```python
  import os
  from typing import Optional
  import json

  class LLMClient:
      def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None, base_url: Optional[str] = None):
          self.model = model or os.getenv("LLM_MODEL", "gpt-4o")
          self.api_key = api_key or os.getenv("LLM_API_KEY", "")
          self.base_url = base_url or os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")

      def query(self, prompt: str, system: str = "", temperature: float = 0.3, max_tokens: int = 2000) -> str:
          import httpx
          headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
          body = {
              "model": self.model,
              "messages": [],
              "temperature": temperature,
              "max_tokens": max_tokens,
          }
          if system:
              body["messages"].append({"role": "system", "content": system})
          body["messages"].append({"role": "user", "content": prompt})
          resp = httpx.post(f"{self.base_url}/chat/completions", headers=headers, json=body, timeout=120)
          resp.raise_for_status()
          return resp.json()["choices"][0]["message"]["content"]
  ```

- [ ] **Step 8: Implement agent_commons/encryption.py**

  ```python
  import os
  from cryptography.fernet import Fernet

  _KEY_FILE = os.path.expanduser("~/.agent_commons_key")

  def _get_key() -> bytes:
      if os.path.exists(_KEY_FILE):
          return open(_KEY_FILE, "rb").read()
      key = Fernet.generate_key()
      os.makedirs(os.path.dirname(_KEY_FILE), exist_ok=True)
      with open(_KEY_FILE, "wb") as f:
          f.write(key)
      os.chmod(_KEY_FILE, 0o600)
      return key

  def encrypt_value(plaintext: str) -> str:
      return Fernet(_get_key()).encrypt(plaintext.encode()).decode()

  def decrypt_value(ciphertext: str) -> str:
      return Fernet(_get_key()).decrypt(ciphertext.encode()).decode()
  ```

- [ ] **Step 9: Run all agent_commons tests**

  Run: `cd /home/joseph/MyProjects/agent_commons && pytest tests/ -v`
  Expected: All PASS

- [ ] **Step 10: Commit**

  ```bash
  cd /home/joseph/MyProjects/agent_commons && git init && git add -A && git commit -m "feat: agent_commons shared package"
  ```

---

### Task 2: Project Skeleton + Config Files

**Files:**
- Create: `.env.example`
- Create: `requirements.txt`
- Create: `src/__init__.py`
- Create: `config/schedule.md`
- Create: `config/filters.md`
- Create: `config/profile.md`
- Create: `resume/joseph-jiao.md`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create .env.example**

  ```
  # Email
  SMTP_HOST=smtp.gmail.com
  SMTP_PORT=587
  IMAP_HOST=imap.gmail.com
  IMAP_PORT=993
  EMAIL_USERNAME=your-email@gmail.com
  EMAIL_PASSWORD=your-app-password

  # PostgreSQL
  DATABASE_URL=postgresql://localhost:5432/job_agent

  # LLM
  LLM_MODEL=gpt-4o
  LLM_API_KEY=sk-...
  LLM_BASE_URL=https://api.openai.com/v1

  # LinkedIn
  LINKEDIN_USERNAME=your-linkedin-email
  LINKEDIN_PASSWORD=your-linkedin-password

  # Airflow
  AIRFLOW_HOME=~/airflow
  ```

- [ ] **Step 2: Create requirements.txt**

  ```
  browser-use>=0.1.0
  cloakbrowser>=0.1.0
  fastmcp>=0.1.0
  sqlalchemy>=2.0
  psycopg2-binary>=2.9
  httpx>=0.27
  cryptography>=41.0
  apache-airflow>=2.8
  pytest>=8.0
  pytest-mock>=3.12
  pytest-asyncio>=0.21
  -e /home/joseph/MyProjects/agent_commons
  ```

- [ ] **Step 3: Create src/__init__.py** (empty)

- [ ] **Step 4: Create config/schedule.md**

  ```markdown
  # Schedule
  run_days: [Wednesday, Friday]
  run_time: "09:00"
  timezone: America/Toronto
  ```

- [ ] **Step 5: Create config/filters.md**

  ```markdown
  # Search Filters
  target_roles:
    - Data Engineering Manager
    - AI Builder
    - Data and AI Manager
  location: Ottawa
  radius_km: 50
  max_to_search: 100
  max_to_apply: 10
  min_match_score: 80
  job_sources:
    - linkedin
  report_channel: email
  ```

- [ ] **Step 6: Create config/profile.md**

  ```markdown
  # Personal Profile
  first_name: Joseph
  last_name: Jiao
  address: 0 East Street
  city: Ottawa
  province: ON
  postal_code: K2E 0E1
  country: Canada
  phone: "+1-xxx-xxx-xxxx"
  email: your-email@gmail.com
  linkedin: https://linkedin.com/in/jiaochunpeng
  ```

- [ ] **Step 7: Create resume/joseph-jiao.md (base resume)**

  Create an empty or placeholder resume markdown file. The user will fill it with their full career history.

  ```markdown
  # Joseph Jiao
  **Data & AI Leader** | Ottawa, ON

  ## Summary
  Accomplished Data Leader with over 20 years of experience...

  ## Experience
  ### OCS Ontario Cannabis Store — Data Leadership Role
  _Dates_

  ### Previous Roles
  _To be filled by user_

  ## Education
  ### Nankai University

  ## Certifications
  - Microsoft Certified: Azure Data Fundamentals
  - Microsoft Certified: Azure Fundamentals
  - Microsoft Certified Professional (MCP)

  ## Skills
  - Data Engineering, Azure Synapse, Fabric, Data Lake, PySpark, ADF
  - Dynamics 365 CRM, AI, Machine Learning
  - Python, SQL, .NET
  ```

- [ ] **Step 8: Create tests/__init__.py** (empty)

- [ ] **Step 9: Create tests/conftest.py**

  ```python
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
  ```

- [ ] **Step 10: Commit**

  ```bash
  git add -A && git commit -m "feat: project skeleton, config files, base resume"
  ```

---

### Task 3: DB Models and Schema

**Files:**
- Create: `src/db.py`
- Create: `tests/test_db.py`

- [ ] **Step 1: Write failing test for DB models**

  ```python
  # tests/test_db.py
  import pytest
  from sqlalchemy import create_engine
  from sqlalchemy.orm import sessionmaker
  from src.db import Base, AppliedJob, SearchResult, ResumeVersion, WeeklyReport

  @pytest.fixture
  def db_session():
      engine = create_engine("sqlite:///:memory:")
      Base.metadata.create_all(engine)
      session = sessionmaker(bind=engine)()
      yield session
      session.close()

  def test_applied_job_create(db_session):
      job = AppliedJob(
          job_id="linkedin_123",
          title="Data Engineering Manager",
          company="Test Corp",
          url="https://linkedin.com/jobs/123",
          source="linkedin",
          status="applied",
          match_score=85.5,
      )
      db_session.add(job)
      db_session.commit()
      saved = db_session.query(AppliedJob).first()
      assert saved.job_id == "linkedin_123"
      assert saved.status == "applied"
      assert saved.match_score == 85.5

  def test_search_result_skill_frequency(db_session):
      sr = SearchResult(
          keywords="Data Engineering Manager",
          source="linkedin",
          results=[{"title": "Test", "company": "Co"}],
          skill_frequency={"Python": 45, "Azure": 30, "Spark": 20},
      )
      db_session.add(sr)
      db_session.commit()
      saved = db_session.query(SearchResult).first()
      assert saved.skill_frequency["Python"] == 45

  def test_resume_version(db_session):
      rv = ResumeVersion(version="2026-05-16-base", content_md="# Resume")
      db_session.add(rv)
      db_session.commit()
      assert db_session.query(ResumeVersion).count() == 1

  def test_weekly_report(db_session):
      wr = WeeklyReport(week_start="2026-05-11", report_data={"applied": [], "skills": {}})
      db_session.add(wr)
      db_session.commit()
      assert db_session.query(WeeklyReport).first().week_start == "2026-05-11"
  ```

- [ ] **Step 2: Run test to verify it fails**

  Run: `cd /home/joseph/MyProjects/my-job-agent && pip install -e . 2>/dev/null; pytest tests/test_db.py -v`
  Expected: FAIL with ImportError

- [ ] **Step 3: Implement src/db.py**

  ```python
  from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, Date, ForeignKey
  from sqlalchemy.orm import declarative_base
  from datetime import datetime, timezone

  Base = declarative_base()

  class AppliedJob(Base):
      __tablename__ = "applied_jobs"

      id = Column(Integer, primary_key=True, autoincrement=True)
      job_id = Column(String(255), nullable=False)
      title = Column(String(500), nullable=False)
      company = Column(String(500), nullable=False)
      url = Column(Text, nullable=True)
      source = Column(String(50), nullable=False)
      applied_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
      status = Column(String(20), default="applied")
      block_reason = Column(Text, nullable=True)
      match_score = Column(Float, nullable=True)
      resume_version_id = Column(Integer, ForeignKey("resume_versions.id"), nullable=True)
      jd_raw = Column(Text, nullable=True)
      skills_extracted = Column(JSON, nullable=True)
      notes = Column(Text, nullable=True)

  class SearchResult(Base):
      __tablename__ = "search_results"

      id = Column(Integer, primary_key=True, autoincrement=True)
      searched_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
      keywords = Column(String(500), nullable=False)
      source = Column(String(50), nullable=False)
      results = Column(JSON, nullable=True)
      skill_frequency = Column(JSON, nullable=True)
      applied_count = Column(Integer, default=0)

  class ResumeVersion(Base):
      __tablename__ = "resume_versions"

      id = Column(Integer, primary_key=True, autoincrement=True)
      version = Column(String(50), nullable=False)
      content_md = Column(Text, nullable=False)
      created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
      source_job_id = Column(String(255), nullable=True)

  class WeeklyReport(Base):
      __tablename__ = "weekly_reports"

      id = Column(Integer, primary_key=True, autoincrement=True)
      week_start = Column(Date, nullable=False)
      report_data = Column(JSON, nullable=True)
      sent_at = Column(DateTime, nullable=True)
  ```

- [ ] **Step 4: Run test to verify it passes**

  Run: `cd /home/joseph/MyProjects/my-job-agent && pytest tests/test_db.py -v`
  Expected: All PASS

- [ ] **Step 5: Commit**

  ```bash
  git add -A && git commit -m "feat: DB models and schema"
  ```

---

### Task 4: Config Loader

**Files:**
- Create: `src/config_loader.py`
- Create: `tests/test_config_loader.py`

- [ ] **Step 1: Write failing test for config loader**

  ```python
  # tests/test_config_loader.py
  import pytest
  from src.config_loader import load_all_configs, load_skills

  def test_load_schedule(tmp_path):
      d = tmp_path / "config"
      d.mkdir()
      (d / "schedule.md").write_text("run_days: [Monday, Wednesday]\nrun_time: 10:00\ntimezone: UTC")
      config = load_all_configs(str(d))
      assert config["schedule"]["run_days"] == ["Monday", "Wednesday"]
      assert config["schedule"]["timezone"] == "UTC"

  def test_load_filters(tmp_path):
      d = tmp_path / "config"
      d.mkdir()
      (d / "filters.md").write_text(
          "target_roles:\n  - Data Engineer\n  - AI Builder\nmax_to_search: 100\nmin_match_score: 80"
      )
      config = load_all_configs(str(d))
      assert config["filters"]["target_roles"] == ["Data Engineer", "AI Builder"]
      assert config["filters"]["min_match_score"] == 80

  def test_load_profile(tmp_path):
      d = tmp_path / "config"
      d.mkdir()
      (d / "profile.md").write_text("first_name: Joseph\ncity: Ottawa\npostal_code: K2E 0E1")
      config = load_all_configs(str(d))
      assert config["profile"]["first_name"] == "Joseph"
      assert config["profile"]["postal_code"] == "K2E 0E1"

  def test_load_skills_with_mock(tmp_path):
      skills_dir = tmp_path / "skills"
      skills_dir.mkdir()
      (skills_dir / "application-rules").mkdir()
      (skills_dir / "application-rules" / "SKILL.md").write_text("Never apply to jobs requiring security clearance.")
      rules = load_skills(str(skills_dir))
      assert "application-rules" in rules
      assert "security clearance" in rules["application-rules"]
  ```

- [ ] **Step 2: Run test to verify it fails**

  Run: `cd /home/joseph/MyProjects/my-job-agent && pytest tests/test_config_loader.py -v`
  Expected: FAIL with ImportError

- [ ] **Step 3: Implement src/config_loader.py**

  ```python
  from pathlib import Path
  from typing import Any
  from agent_commons.config import load_markdown_config

  def load_all_configs(config_dir: str = "config") -> dict[str, dict]:
      config_dir = Path(config_dir)
      configs = {}
      for name in ["schedule", "filters", "profile"]:
          path = config_dir / f"{name}.md"
          if path.exists():
              configs[name] = load_markdown_config(str(path))
          else:
              configs[name] = {}
      return configs

  def load_skills(skills_dir: str = ".agents/skills") -> dict[str, str]:
      skills_dir = Path(skills_dir)
      skills = {}
      if not skills_dir.exists():
          return skills
      for skill_dir in skills_dir.iterdir():
          if skill_dir.is_dir():
              skill_file = skill_dir / "SKILL.md"
              if skill_file.exists():
                  skills[skill_dir.name] = skill_file.read_text().strip()
      return skills
  ```

- [ ] **Step 4: Run test to verify it passes**

  Run: `cd /home/joseph/MyProjects/my-job-agent && pytest tests/test_config_loader.py -v`
  Expected: All PASS

- [ ] **Step 5: Commit**

  ```bash
  git add -A && git commit -m "feat: config loader"
  ```

---

### Task 5: LLM Client

**Files:**
- Create: `src/llm_client.py`
- Create: `tests/test_llm_client.py`

- [ ] **Step 1: Write failing test**

  ```python
  # tests/test_llm_client.py
  import pytest
  from src.llm_client import get_llm_client

  def test_get_llm_client_defaults(mock_env_vars):
      client = get_llm_client()
      assert client.model == "gpt-4o"
      assert client.api_key == "test-key"

  def test_get_llm_client_custom():
      client = get_llm_client(model="gpt-4o-mini", api_key="custom-key")
      assert client.model == "gpt-4o-mini"
      assert client.api_key == "custom-key"
  ```

- [ ] **Step 2: Run test to verify it fails**

  Run: `pytest tests/test_llm_client.py -v`
  Expected: FAIL

- [ ] **Step 3: Implement src/llm_client.py**

  ```python
  from agent_commons.llm import LLMClient

  def get_llm_client(model: str = None, api_key: str = None, base_url: str = None) -> LLMClient:
      return LLMClient(model=model, api_key=api_key, base_url=base_url)
  ```

- [ ] **Step 4: Run test to verify it passes**

  Run: `pytest tests/test_llm_client.py -v`
  Expected: All PASS

- [ ] **Step 5: Commit**

  ```bash
  git add -A && git commit -m "feat: LLM client wrapper"
  ```

---

### Task 6: Resume Tailor (JD Matching + Tailoring)

**Files:**
- Create: `src/resume_tailor.py`
- Create: `tests/test_resume_tailor.py`

- [ ] **Step 1: Write failing tests**

  ```python
  # tests/test_resume_tailor.py
  import pytest
  from unittest.mock import patch, MagicMock
  from src.resume_tailor import compute_match_score, tailor_resume, load_base_resume

  def test_load_base_resume(tmp_path):
      resume_file = tmp_path / "resume.md"
      resume_file.write_text("# Joseph Jiao\nData Leader")
      content = load_base_resume(str(resume_file))
      assert "Joseph Jiao" in content
      assert "Data Leader" in content

  def test_compute_match_score_high_match(sample_jd, sample_resume):
      with patch("src.resume_tailor.get_llm_client") as mock_get:
          mock_client = MagicMock()
          mock_client.query.return_value = "85"
          mock_get.return_value = mock_client
          score = compute_match_score(sample_jd, sample_resume)
          assert score == 85
          mock_client.query.assert_called_once()

  def test_compute_match_score_low_match(sample_jd, sample_resume):
      with patch("src.resume_tailor.get_llm_client") as mock_get:
          mock_client = MagicMock()
          mock_client.query.return_value = "35"
          mock_get.return_value = mock_client
          score = compute_match_score(sample_jd, sample_resume)
          assert score == 35

  def test_compute_match_score_handles_non_numeric(sample_jd, sample_resume):
      with patch("src.resume_tailor.get_llm_client") as mock_get:
          mock_client = MagicMock()
          mock_client.query.return_value = "around 80%"
          mock_get.return_value = mock_client
          score = compute_match_score(sample_jd, sample_resume)
          assert score == 0

  def test_tailor_resume(sample_jd, sample_resume):
      with patch("src.resume_tailor.get_llm_client") as mock_get:
          mock_client = MagicMock()
          mock_client.query.return_value = "# Tailored Resume\nEnhanced version"
          mock_get.return_value = mock_client
          tailored = tailor_resume(sample_jd, sample_resume)
          assert "Tailored Resume" in tailored
          assert "Enhanced" in tailored
  ```

- [ ] **Step 2: Run test to verify it fails**

  Run: `pytest tests/test_resume_tailor.py -v`
  Expected: FAIL

- [ ] **Step 3: Implement src/resume_tailor.py**

  ```python
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
      match = re.search(r"\d+", result.strip())
      return float(match.group()) if match else 0.0

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
  ```

- [ ] **Step 4: Run test to verify it passes**

  Run: `pytest tests/test_resume_tailor.py -v`
  Expected: All PASS

- [ ] **Step 5: Commit**

  ```bash
  git add -A && git commit -m "feat: resume tailor with JD matching"
  ```

---

### Task 7: Email Handler

**Files:**
- Create: `src/email_handler.py`
- Create: `tests/test_email_handler.py`

- [ ] **Step 1: Write failing tests**

  ```python
  # tests/test_email_handler.py
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
          call_args = instance.send.call_args[1]
          assert "blocked" in call_args["subject"].lower()
          assert "Co A" in call_args["body"]
          assert "Missing years of Python" in call_args["body"]

  def test_send_report_email():
      with patch("src.email_handler.EmailClient") as MockClient:
          instance = MockClient.return_value
          send_report_email("test@test.com", "<h1>Report</h1><p>Content</p>")
          instance.send_report.assert_called_once_with(
              "test@test.com", subject="Weekly Job Application Report", html_body="<h1>Report</h1><p>Content</p>"
          )
  ```

- [ ] **Step 2: Run test to verify it fails**

  Run: `pytest tests/test_email_handler.py -v`
  Expected: FAIL

- [ ] **Step 3: Implement src/email_handler.py**

  ```python
  from agent_commons.email import EmailClient
  from typing import Optional

  def _get_client() -> EmailClient:
      return EmailClient()

  def send_blocked_summary(blocked_jobs: list[dict], to: Optional[str] = None) -> None:
      client = _get_client()
      if not blocked_jobs:
          return
      lines = ["The following jobs were blocked during this run:\n"]
      for j in blocked_jobs:
          lines.append(f"- {j['title']} at {j['company']}: {j['block_reason']}")
      body = "\n".join(lines)
      client.send(to or client.username, subject="Job Agent: Blocked Jobs Summary", body=body)

  def send_report_email(to: str, html_body: str) -> None:
      _get_client().send_report(to, subject="Weekly Job Application Report", html_body=html_body)
  ```

- [ ] **Step 4: Run test to verify it passes**

  Run: `pytest tests/test_email_handler.py -v`
  Expected: All PASS

- [ ] **Step 5: Commit**

  ```bash
  git add -A && git commit -m "feat: email handler for blocked summary and report"
  ```

---

### Task 8: Browser Agent (Search + Apply)

**Files:**
- Create: `src/browser_agent.py`
- Create: `tests/test_browser_agent.py`

- [ ] **Step 1: Write failing tests**

  ```python
  # tests/test_browser_agent.py
  import pytest
  from unittest.mock import patch, MagicMock, AsyncMock
  from src.browser_agent import search_linkedin, apply_to_job, run_search_and_apply

  @pytest.mark.asyncio
  async def test_search_linkedin_returns_results():
      with patch("src.browser_agent.BrowserUseAgent") as MockAgent:
          agent = MockAgent.return_value
          agent.run.return_value = [
              {"title": "Data Engineering Manager", "company": "Test Co", "url": "https://linkedin.com/jobs/1", "jd": "JD text"}
          ]
          results = await search_linkedin("Data Engineering Manager", location="Ottawa", max_results=10)
          assert len(results) == 1
          assert results[0]["title"] == "Data Engineering Manager"

  @pytest.mark.asyncio
  async def test_apply_to_job_blocks_on_missing_info():
      profile = {"first_name": "Joseph", "city": "Ottawa"}
      with patch("src.browser_agent.BrowserUseAgent") as MockAgent:
          agent = MockAgent.return_value
          agent.run.side_effect = ValueError("Cannot answer: years of Python experience")
          result = await apply_to_job(
              job={"title": "DE Manager", "company": "Co", "url": "https://linkedin.com/jobs/1", "jd": "JD"},
              profile=profile,
              resume="# Joseph\nResume content",
          )
          assert result["status"] == "blocked"
          assert "Cannot answer" in result["block_reason"]

  @pytest.mark.asyncio
  async def test_apply_to_job_succeeds():
      profile = {"first_name": "Joseph", "city": "Ottawa"}
      with patch("src.browser_agent.BrowserUseAgent") as MockAgent:
          agent = MockAgent.return_value
          agent.run.return_value = None
          result = await apply_to_job(
              job={"title": "DE Manager", "company": "Co", "url": "https://linkedin.com/jobs/1", "jd": "JD"},
              profile=profile,
              resume="# Joseph\nResume content",
          )
          assert result["status"] == "applied"

  @pytest.mark.asyncio
  async def test_run_search_and_apply_full_flow():
      with patch("src.browser_agent.search_linkedin") as mock_search, \
           patch("src.browser_agent.apply_to_job") as mock_apply, \
           patch("src.browser_agent.compute_match_score") as mock_score, \
           patch("src.browser_agent.send_blocked_summary") as mock_summary, \
           patch("src.browser_agent.load_base_resume") as mock_resume:
          mock_resume.return_value = "# Resume"
          mock_search.return_value = [
              {"title": "Job A", "company": "Co A", "url": "url1", "jd": "JD1"},
              {"title": "Job B", "company": "Co B", "url": "url2", "jd": "JD2"},
          ]
          mock_score.return_value = 90
          mock_apply.side_effect = [
              {"status": "applied", "job_id": "url1", "title": "Job A"},
              {"status": "blocked", "job_id": "url2", "title": "Job B", "block_reason": "Missing info"},
          ]
          result = await run_search_and_apply(target_roles=["Data Engineering Manager"])
          assert result["applied_count"] == 1
          assert result["blocked_count"] == 1
          assert result["total_searched"] == 2
          mock_summary.assert_called_once()
  ```

- [ ] **Step 2: Run test to verify it fails**

  Run: `pytest tests/test_browser_agent.py -v`
  Expected: FAIL

- [ ] **Step 3: Implement src/browser_agent.py**

  ```python
  import json
  from typing import Optional
  from src.resume_tailor import compute_match_score, tailor_resume, load_base_resume
  from src.llm_client import get_llm_client
  from src.config_loader import load_all_configs, load_skills
  from src.email_handler import send_blocked_summary
  from src.db import AppliedJob, SearchResult, ResumeVersion, get_session
  from datetime import datetime, timezone

  class BrowserUseAgent:
      """Minimal interface abstraction for browser-use agent.
      In production, this wraps the actual Browser-use library + CloakBrowser."""

      async def run(self, task: str, headless: bool = True) -> any:
          raise NotImplementedError("Browser-use integration - see setup instructions")

  async def search_linkedin(
      role: str,
      location: str = "Ottawa",
      max_results: int = 100,
      headless: bool = True,
  ) -> list[dict]:
      agent = BrowserUseAgent()
      task = f"""Go to LinkedIn Jobs, search for "{role}" in "{location}".
  Collect the first {max_results} job results.
  For each result, extract: title, company, url, and full job description.
  Return as JSON array of objects with keys: title, company, url, jd."""
      result = await agent.run(task, headless=headless)
      if isinstance(result, str):
          return json.loads(result)
      return result or []

  async def apply_to_job(
      job: dict,
      profile: dict,
      resume: str,
      tailored_resume: str = None,
      skills: dict = None,
      headless: bool = True,
  ) -> dict:
      agent = BrowserUseAgent()
      skill_rules = (skills or {}).get("application-rules", "")
      answer_guide = (skills or {}).get("answer-guide", "")

      task = f"""Apply to this job: {job['title']} at {job['company']}
  URL: {job['url']}

  Profile info:
  - Name: {profile.get('first_name', '')} {profile.get('last_name', '')}
  - Address: {profile.get('address', '')}, {profile.get('city', '')}, {profile.get('province', '')} {profile.get('postal_code', '')}
  - Phone: {profile.get('phone', '')}
  - LinkedIn: {profile.get('linkedin', '')}

  Application rules:
  {skill_rules}

  Answer guide for custom questions:
  {answer_guide}

  Tailored resume (upload as PDF):
  {tailored_resume or resume}

  Steps:
  1. Navigate to the job URL
  2. Click "Apply" or "Easy Apply"
  3. Fill all required fields using the profile info above
  4. Upload the resume file (will be provided as PDF)
  5. For any custom questions (years of experience, skills, etc.), answer using the resume content
  6. If you CANNOT answer a required question, raise an error: "Cannot answer: <question text>"
  7. Submit the application"""
      try:
          await agent.run(task, headless=headless)
          return {"status": "applied", "job_id": job.get("url"), "title": job.get("title")}
      except Exception as e:
          return {"status": "blocked", "job_id": job.get("url"), "title": job.get("title"), "block_reason": str(e)}

  async def run_search_and_apply(
      target_roles: list[str] = None,
      location: str = "Ottawa",
      max_to_search: int = 100,
      max_to_apply: int = 10,
      min_match_score: float = 80.0,
      headless: bool = True,
  ) -> dict:
      config = load_all_configs()
      filters = config.get("filters", {})
      profile = config.get("profile", {})
      skills = load_skills()

      target_roles = target_roles or filters.get("target_roles", ["Data Engineering Manager"])
      location = location or filters.get("location", "Ottawa")
      max_to_search = max_to_search or filters.get("max_to_search", 100)
      max_to_apply = max_to_apply or filters.get("max_to_apply", 10)
      min_match_score = min_match_score or filters.get("min_match_score", 80.0)

      base_resume = load_base_resume()
      session = get_session()
      already_applied = {r.job_id for r in session.query(AppliedJob).filter(AppliedJob.status.in_(["applied", "blocked"])).all()}

      all_results = []

      for role in target_roles:
          results = await search_linkedin(role, location=location, max_results=max_to_search, headless=headless)
          all_results.extend(results)

      from src.report import extract_skill_frequency
      all_skills_freq = extract_skill_frequency(all_results)

      scored_jobs = []
      for job in all_results:
          if job["url"] in already_applied:
              continue
          score = compute_match_score(job.get("jd", ""), base_resume)
          if score >= min_match_score:
              scored_jobs.append((score, job))

      scored_jobs.sort(key=lambda x: x[0], reverse=True)
      top_jobs = scored_jobs[:max_to_apply]

      blocked = []
      applied = 0
      for score, job in top_jobs:
          tailored = tailor_resume(job.get("jd", ""), base_resume) if score >= min_match_score else base_resume
          result = await apply_to_job(
              job=job,
              profile=profile,
              resume=base_resume,
              tailored_resume=tailored,
              skills=skills,
              headless=headless,
          )
          entry = AppliedJob(
              job_id=job["url"],
              title=job["title"],
              company=job["company"],
              url=job["url"],
              source="linkedin",
              status=result["status"],
              block_reason=result.get("block_reason"),
              match_score=score,
              jd_raw=job.get("jd"),
          )
          session.add(entry)
          if result["status"] == "blocked":
              blocked.append(result)
          else:
              applied += 1

          rv = ResumeVersion(
              version=f"tailored-{job['url'].split('/')[-1][:30]}",
              content_md=tailored,
              source_job_id=job["url"],
          )
          session.add(rv)

      sr = SearchResult(
          keywords=", ".join(target_roles),
          source="linkedin",
          results=all_results,
          skill_frequency=all_skills_freq,
          applied_count=applied,
      )
      session.add(sr)
      session.commit()
      session.close()

      if blocked:
          send_blocked_summary(blocked)

      return {
          "total_searched": len(all_results),
          "scored": len(scored_jobs),
          "applied_count": applied,
          "blocked_count": len(blocked),
      }
  ```

- [ ] **Step 4: Run test to verify it passes**

  Run: `pytest tests/test_browser_agent.py -v`
  Expected: All PASS

- [ ] **Step 5: Commit**

  ```bash
  git add -A && git commit -m "feat: browser agent for search and apply"
  ```

---

### Task 9: MCP Server

**Files:**
- Create: `src/mcp_server.py`
- Create: `tests/test_mcp_server.py`

- [ ] **Step 1: Write failing tests**

  ```python
  # tests/test_mcp_server.py
  import pytest
  from unittest.mock import patch, AsyncMock
  from src.mcp_server import create_server

  def test_server_has_tools():
      server = create_server()
      tool_names = [t.name for t in server._tool_manager._tools]
      assert "search_and_apply" in tool_names
      assert "get_history" in tool_names
      assert "get_status" in tool_names
      assert "run_report" in tool_names
      assert "get_skill_frequency" in tool_names

  def test_get_history_returns_applied_jobs():
      server = create_server()
      with patch("src.mcp_server.get_session") as mock_session:
          mock_query = MagicMock()
          mock_session.return_value.query.return_value.order_by.return_value.limit.return_value.all.return_value = [
              MagicMock(job_id="url1", title="Job A", status="applied"),
          ]
          result = server.get_history()
          assert len(result) > 0
  ```

- [ ] **Step 2: Run test to verify it fails**

  Run: `pytest tests/test_mcp_server.py -v`
  Expected: FAIL

- [ ] **Step 3: Implement src/mcp_server.py**

  ```python
  from fastmcp import FastMCP
  from src.db import AppliedJob, SearchResult, get_session
  from src.browser_agent import run_search_and_apply
  from src.report import generate_weekly_report
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
          jobs = session.query(AppliedJob).order_by(AppliedJob.applied_at.desc()).limit(limit).all()
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
          applied = session.query(AppliedJob).filter(AppliedJob.status == "applied").count()
          blocked = session.query(AppliedJob).filter(AppliedJob.status == "blocked").count()
          failed = session.query(AppliedJob).filter(AppliedJob.status == "failed").count()
          session.close()
          return {"applied": applied, "blocked": blocked, "failed": failed}

      @mcp.tool()
      def run_report() -> dict:
          """Generate and send the weekly report immediately."""
          return asyncio.run(generate_weekly_report())

      @mcp.tool()
      def get_skill_frequency(limit: int = 20) -> list[dict]:
          """Get most common skills from recent search results."""
          session = get_session()
          results = session.query(SearchResult).order_by(SearchResult.searched_at.desc()).limit(5).all()
          session.close()
          freq = {}
          for r in results:
              if r.skill_frequency:
                  for skill, count in r.skill_frequency.items():
                      freq[skill] = freq.get(skill, 0) + count
          sorted_skills = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:limit]
          return [{"skill": s, "count": c} for s, c in sorted_skills]

      return mcp
  ```

- [ ] **Step 4: Run test to verify it passes**

  Run: `pytest tests/test_mcp_server.py -v`
  Expected: All PASS

- [ ] **Step 5: Commit**

  ```bash
  git add -A && git commit -m "feat: MCP server with tools"
  ```

---

### Task 10: Report Generator

**Files:**
- Create: `src/report.py`
- Create: `tests/test_report.py`

- [ ] **Step 1: Write failing tests**

  ```python
  # tests/test_report.py
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
      assert "5" in html

  def test_generate_weekly_report_sends_email():
      with patch("src.report.get_session") as mock_session, \
           patch("src.report.send_report_email") as mock_send, \
           patch("src.report.extract_skill_frequency") as mock_extract, \
           patch("src.report.datetime") as mock_dt:
          mock_dt.now.return_value = date(2026, 5, 16)
          mock_dt.side_effect = lambda *a, **kw: __import__("datetime").datetime(*a, **kw)

          mock_query = MagicMock()
          mock_session.return_value.query.return_value.filter.return_value.all.side_effect = [
              [MagicMock(title="DE Manager", company="Co A", match_score=92, applied_at="2026-05-14", jd_raw="", status="applied")],
              [],
          ]
          mock_extract.return_value = {"python": 45}

          result = generate_weekly_report()
          assert result["sent"] is True
          mock_send.assert_called_once()
  ```

- [ ] **Step 2: Run test to verify it fails**

  Run: `pytest tests/test_report.py -v`
  Expected: FAIL

- [ ] **Step 3: Implement src/report.py**

  ```python
  from datetime import datetime, timedelta, date
  from collections import Counter
  import re
  from src.db import AppliedJob, WeeklyReport, SearchResult, get_session
  from src.email_handler import send_report_email
  from src.config_loader import load_all_configs

  def extract_skill_frequency(results: list[dict]) -> dict[str, int]:
      all_text = " ".join(r.get("jd", "") for r in results)
      skills = re.findall(r"\b(Python|Azure|SQL|Spark|PySpark|Fabric|Synapse|ADF|Kubernetes|Docker|"
                          r"Airflow|ML|AI|Data\s*(Engineering|Lake|Warehouse)|DevOps|CI/CD|"
                          r"Dynamics\s*365|Databricks|Snowflake|Power\s*BI|Tableau)\b", all_text, re.I)
      return dict(Counter(s.lower() for s in skills))

  def build_report_html(data: dict) -> str:
      rows = ""
      for job in data.get("applied", []):
          rows += f"<tr><td>{job['title']}</td><td>{job['company']}</td><td>{job.get('match_score', 'N/A')}</td>"
          rows += f"<td>{job.get('applied_at', '')[:10]}</td></tr>"

      skill_rows = ""
      for s in data.get("skill_frequency", []):
          skill_rows += f"<tr><td>{s['skill']}</td><td>{s['count']}</td></tr>"

      return f"""<html><body>
      <h1>Weekly Job Application Report</h1>
      <p>Week of {data['week_start']}</p>
      <h2>Summary</h2>
      <p>Searched: {data['total_searched']} | Applied: {data['total_applied']} | Blocked: {data['total_blocked']}</p>
      <h2>Applied Roles</h2>
      <table border="1"><tr><th>Title</th><th>Company</th><th>Match %</th><th>Date</th></tr>{rows}</table>
      <h2>Top Skills in Market</h2>
      <table border="1"><tr><th>Skill</th><th>Frequency</th></tr>{skill_rows}</table>
      </body></html>"""

  async def generate_weekly_report() -> dict:
      config = load_all_configs()
      profile = config.get("profile", {})
      to_email = profile.get("email", "")

      session = get_session()
      week_ago = datetime.now() - timedelta(days=7)
      applied_jobs = session.query(AppliedJob).filter(
          AppliedJob.applied_at >= week_ago,
          AppliedJob.status == "applied",
      ).all()

      search_results = session.query(SearchResult).order_by(SearchResult.searched_at.desc()).limit(5).all()
      session.close()

      all_raw = []
      for sr in search_results:
          if sr.results:
              all_raw.extend(sr.results if isinstance(sr.results, list) else [])

      skill_freq = extract_skill_frequency(all_raw)
      sorted_skills = sorted(skill_freq.items(), key=lambda x: x[1], reverse=True)[:20]

      data = {
          "week_start": week_ago.strftime("%Y-%m-%d"),
          "applied": [
              {"title": j.title, "company": j.company, "match_score": j.match_score, "applied_at": str(j.applied_at)}
              for j in applied_jobs
          ],
          "skill_frequency": [{"skill": s, "count": c} for s, c in sorted_skills],
          "total_searched": sum(len(sr.results) for sr in search_results if sr.results) if search_results else 0,
          "total_applied": len(applied_jobs),
          "total_blocked": 0,
      }

      html = build_report_html(data)
      send_report_email(to_email or "user@example.com", html)

      wr = WeeklyReport(week_start=week_ago.date(), report_data=data, sent_at=datetime.now())
      session = get_session()
      session.add(wr)
      session.commit()
      session.close()

      return {"sent": True, "report": data}
  ```

- [ ] **Step 4: Run test to verify it passes**

  Run: `pytest tests/test_report.py -v`
  Expected: All PASS

- [ ] **Step 5: Commit**

  ```bash
  git add -A && git commit -m "feat: weekly report generator with skill popularity"
  ```

---

### Task 11: Skills Markdown Files

**Files:**
- Create: `.agents/skills/application-rules/SKILL.md`
- Create: `.agents/skills/resume-tailoring/SKILL.md`
- Create: `.agents/skills/answer-guide/SKILL.md`

- [ ] **Step 1: Create application-rules/SKILL.md**

  ```markdown
  # Application Rules

  ## Skip Conditions
  - Never apply to jobs requiring security clearance
  - Skip contract positions under 6 months
  - Skip positions outside 50km radius of Ottawa

  ## Blocklist
  - (Add company names here to skip them)

  ## Always Include
  - Remote and hybrid positions are preferred
  ```

- [ ] **Step 2: Create resume-tailoring/SKILL.md**

  ```markdown
  # Resume Tailoring Rules

  - Always keep OCS role as the most recent experience
  - Never change employment dates, titles, or company names
  - Keep education section as-is
  - Emphasize Azure, data engineering, and AI experience
  - Keep summary section as-is
  - Never fabricate or exaggerate facts
  ```

- [ ] **Step 3: Create answer-guide/SKILL.md**

  ```markdown
  # Custom Question Answer Guide

  ## Azure Experience
  When asked about Azure experience:
  "Extensive experience with Azure Synapse, Fabric, Data Lake, ADF, and PySpark at OCS."

  ## Management Experience
  When asked about team management:
  "Led data engineering team, managed stakeholders, delivered enterprise data platform."

  ## Years of Experience
  For "years of experience in X":
  - If X is data-related: use 20+ years
  - If X is Azure/AI: use 5+ years
  - If X is management: use 5+ years

  ## Salary Expectations
  If asked for salary: "Open to d****ssion based on role and responsibilities."
  ```

- [ ] **Step 4: Commit**

  ```bash
  git add -A && git commit -m "feat: skills markdown files"
  ```

---

### Task 12: Airflow DAGs

**Files:**
- Create: `dags/job_search_apply_dag.py`
- Create: `dags/friday_report_dag.py`

- [ ] **Step 1: Create job_search_apply_dag.py**

  ```python
  from datetime import datetime, timedelta
  from airflow import DAG
  from airflow.operators.python import PythonOperator
  from src.browser_agent import run_search_and_apply
  from src.config_loader import load_all_configs
  import asyncio

  default_args = {
      "owner": "jiaochunpeng",
      "depends_on_past": False,
      "email_on_failure": True,
      "email_on_retry": False,
      "retries": 1,
      "retry_delay": timedelta(minutes=5),
  }

  def run_job_search(**context):
      config = load_all_configs()
      schedule = config.get("schedule", {})
      filters = config.get("filters", {})

      result = asyncio.run(run_search_and_apply(
          target_roles=filters.get("target_roles"),
          location=filters.get("location", "Ottawa"),
          max_to_search=filters.get("max_to_search", 100),
          max_to_apply=filters.get("max_to_apply", 10),
          min_match_score=filters.get("min_match_score", 80),
          headline=True,
      ))
      context["ti"].xcom_push(key="result", value=result)

  with DAG(
      "job_search_apply",
      default_args=default_args,
      description="Search LinkedIn and apply to matching jobs",
      schedule_interval="0 9 * * 3,5",
      start_date=datetime(2026, 5, 18),
      catchup=False,
      tags=["job-agent"],
  ) as dag:
      search_apply = PythonOperator(
          task_id="search_and_apply",
          python_callable=run_job_search,
          provide_context=True,
      )
  ```

- [ ] **Step 2: Create friday_report_dag.py**

  ```python
  from datetime import datetime, timedelta
  from airflow import DAG
  from airflow.operators.python import PythonOperator
  from src.report import generate_weekly_report
  import asyncio

  default_args = {
      "owner": "jiaochunpeng",
      "depends_on_past": False,
      "email_on_failure": True,
      "retries": 1,
      "retry_delay": timedelta(minutes=5),
  }

  def run_report(**context):
      result = asyncio.run(generate_weekly_report())
      context["ti"].xcom_push(key="result", value=result)

  with DAG(
      "friday_report",
      default_args=default_args,
      description="Send weekly job application report",
      schedule_interval="0 17 * * 5",
      start_date=datetime(2026, 5, 22),
      catchup=False,
      tags=["job-agent"],
  ) as dag:
      report_task = PythonOperator(
          task_id="generate_and_send_report",
          python_callable=run_report,
          provide_context=True,
      )
  ```

- [ ] **Step 3: Commit**

  ```bash
  git add -A && git commit -m "feat: Airflow DAGs for search/apply and report"
  ```

---

### Task 13: Install and Wire Everything Together

**Files:**
- Modify: `setup.py` (create)
- Modify: `.env.example` (finalize)

- [ ] **Step 1: Create setup.py for installable package**

  ```python
  from setuptools import setup, find_packages

  setup(
      name="my-job-agent",
      version="0.1.0",
      packages=find_packages(),
      install_requires=[
          "browser-use",
          "fastmcp",
          "sqlalchemy>=2.0",
          "psycopg2-binary>=2.9",
          "httpx>=0.27",
          "cryptography>=41.0",
          "apache-airflow>=2.8",
      ],
      extras_require={
          "dev": ["pytest>=8.0", "pytest-mock>=3.12", "pytest-asyncio>=0.21"],
      },
  )
  ```

- [ ] **Step 2: Run all tests**

  Run: `cd /home/joseph/MyProjects/my-job-agent && pip install -e ".[dev]" && pytest tests/ -v`
  Expected: All PASS

- [ ] **Step 3: Final commit**

  ```bash
  git add -A && git commit -m "chore: setup.py and final wiring"
  ```
