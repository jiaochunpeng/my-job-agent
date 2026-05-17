# Job Application Agent — Design Spec

## Overview

An automated job application agent that searches LinkedIn (and eventually other boards) for roles matching Joseph Jiao's profile, tailors the resume to each job description, applies to the best-matching positions, and tracks everything in PostgreSQL. Runs on a configurable schedule (default: Wed/Fri) orchestrated by Airflow. Uses Browser-use as the AI browser agent with CloakBrowser for stealth.

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                   Airflow Scheduler                        │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ Job Search   │  │ Missing Info │  │ Friday Report │  │
│  │ + Apply DAG  │  │ Check DAG    │  │ DAG           │  │
│  │ (Wed, Fri)   │  │ (daily)      │  │ (Fri)         │  │
│  └──────┬───────┘  └──────┬───────┘  └───────┬───────┘  │
└─────────┼──────────────────┼──────────────────┼──────────┘
          │                  │                  │
┌─────────▼──────────────────▼──────────────────▼──────────┐
│                 my-job-agent Python Package                │
│                                                           │
│  ┌─────────────────┐  ┌──────────────────────────────┐   │
│  │  MCP Server      │  │  Browser Agent               │   │
│  │  (FastMCP)       │  │  (Browser-use + CloakBrowser)│   │
│  │                  │  │                              │   │
│  │  Tools:          │  │  1. Load profile + config    │   │
│  │  - search_jobs   │  │  2. Search LinkedIn (100)    │   │
│  │  - apply_job     │  │  3. Score vs resume (≥80%)   │   │
│  │  - get_status    │  │  4. Apply top 10             │   │
│  │  - run_report    │  │  5. Tailor resume per JD     │   │
│  │  - query_history │  │  6. Extract skill frequency  │   │
│  └─────────────────┘  └──────────────────────────────┘   │
│                                                           │
│  ┌──────────────────┐  ┌────────────────────────────┐    │
│  │  Resume Module    │  │  Skills (.agents/skills/) │    │
│  │  - markdown store │  │  - application-rules      │    │
│  │  - JD matching    │  │  - resume-tailoring       │    │
│  │  - tailored copy  │  │  - answer-guide           │    │
│  └──────────────────┘  └────────────────────────────┘    │
└──────────────────────────┬───────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────┐
│  Agent Commons (shared module for all agents)             │
│                                                           │
│  ├── email.py       (send, read, poll inbox)              │
│  ├── db.py          (PostgreSQL connection, migrations)   │
│  ├── config.py      (read markdown config files)          │
│  ├── llm.py         (abstracted LLM calls)                │
│  └── encryption.py  (local creds storage)                 │
└──────────────────────────┬───────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────┐
│  PostgreSQL Database                                      │
│                                                           │
│  applied_jobs | pending_missing_info | search_results     │
│  resume_versions | weekly_reports | config                │
└───────────────────────────────────────────────────────────┘
```

### Key Technology Choices

| Component | Choice | Reason |
|---|---|---|
| Browser agent | **Browser-use** (90.7k stars, MIT) | Mature AI agent framework, LLM-native form handling |
| Stealth | **CloakBrowser** (8.1k stars, MIT) | Drop-in Playwright replacement, bypasses bot detection |
| Orchestration | **Airflow** | Specified by user, industry standard scheduler |
| Database | **PostgreSQL** | User's existing stack, also used by my-dba-agent |
| Agent framework | **FastMCP** | Matches my-crm-agent and my-dba-agent patterns |
| Shared library | **agent_commons/** | Reusable email, DB, config, LLM, encryption |

## Data Model (PostgreSQL)

### `applied_jobs`
| Column | Type | Description |
|---|---|---|
| id | SERIAL PK | Auto-increment |
| job_id | VARCHAR(255) | External job ID |
| title | VARCHAR(500) | Job title |
| company | VARCHAR(500) | Company name |
| url | TEXT | Job posting URL |
| source | VARCHAR(50) | linkedin, indeed, etc. |
| applied_at | TIMESTAMP | When submitted |
| status | VARCHAR(20) | applied, pending_info, failed |
| match_score | DECIMAL(5,2) | JD-resume match % |
| resume_version_id | INTEGER FK → resume_versions |
| jd_raw | TEXT | Full job description text |
| skills_extracted | JSONB | Skills/keywords from JD |
| notes | TEXT | Any error or notes |

### `pending_missing_info`
| Column | Type | Description |
|---|---|---|
| id | SERIAL PK | |
| job_id | VARCHAR(255) | Related job |
| company | VARCHAR(500) | |
| question | TEXT | The question asked on the form |
| requested_at | TIMESTAMP | When email was sent |
| responded_at | TIMESTAMP | When answer received (nullable) |
| answer | TEXT | The answer (nullable) |
| status | VARCHAR(20) | pending, answered, cancelled |

### `search_results`
| Column | Type | Description |
|---|---|---|
| id | SERIAL PK | |
| searched_at | TIMESTAMP | |
| keywords | VARCHAR(500) | Search terms used |
| source | VARCHAR(50) | |
| results | JSONB | Array of up to 100 raw results |
| skill_frequency | JSONB | Aggregated skill → count across results |
| applied_count | INTEGER | How many from this batch were applied |

### `resume_versions`
| Column | Type | Description |
|---|---|---|
| id | SERIAL PK | |
| version | VARCHAR(50) | e.g., "2026-05-16-base", "tailored-<job_id>" |
| content_md | TEXT | Full resume in markdown |
| created_at | TIMESTAMP | |
| source_job_id | VARCHAR(255) | Null for base, job ID for tailored |

### `weekly_reports`
| Column | Type | Description |
|---|---|---|
| id | SERIAL PK | |
| week_start | DATE | Monday of the report week |
| report_data | JSONB | Applied roles, skill popularity, stats |
| sent_at | TIMESTAMP | When email was sent |

### `config`
| Column | Type | Description |
|---|---|---|
| key | VARCHAR(100) PK | Config key |
| value | TEXT | JSON value |
| updated_at | TIMESTAMP | |

## Configuration Files

### `config/schedule.md`
```markdown
# Schedule
run_days: [Wednesday, Friday]
run_time: "09:00"
timezone: America/Toronto
```

### `config/filters.md`
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

### `config/profile.md`
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
linkedin: https://linkedin.com/in/jiaochunpeng
```

### `resume/joseph-jiao.md`
The base resume in markdown format. Each tailored version saved as `resume/tailored-<job_id>.md`.

## Browser Agent Flow (Search + Apply)

1. **DAG triggers** — Airflow starts the Job Search + Apply DAG on configured days
2. **Load state** — agent reads profile, filters, applied history from DB
3. **Search** — Browser-use navigates LinkedIn (authenticated), searches each target role, collects 100 results
4. **Score** — for each result, LLM compares JD against resume, produces match score
5. **Filter** — exclude already-applied, keep only ≥80% match, cap at 10
6. **Apply** — for each matched job:
   - Navigate to application page
   - Fill standard fields (name, address, phone, LinkedIn, etc.)
   - Upload tailored resume PDF (converted from markdown)
   - Answer custom questions from resume context via LLM
   - If question can't be answered → save to pending_missing_info, send email, skip
   - Submit
   - Save tailored resume version
7. **Post-run** — extract skill frequency from search results, store in search_results.skill_frequency

## Resume Tailoring

When applying, the agent:
1. Sends JD + base resume to LLM with instruction: "Reorder/rephrase bullet points to emphasize skills matching this JD. Keep all facts accurate. Never change dates, titles, or company names."
2. Output is saved as `resume/tailored-<job_id>.md`
3. Converted to PDF for upload

The resume-tailoring skill (`.agents/skills/resume-tailoring/SKILL.md`) controls tailoring rules.

## Missing Info Flow

1. Agent encounters unanswerable question → saves to `pending_missing_info` (status: pending)
2. Sends email via `agent_commons/email.py` with subject: `[JOB-AGENT] Q-<id>: <company> - <question snippet>`
3. A daily Airflow DAG runs `pending_missing_info` check:
   - Polls email inbox for replies matching `[JOB-AGENT] Q-<id>` subject prefix
   - Parses reply body as the answer
   - Updates `pending_missing_info.answer` and sets status = answered
4. On next search+apply run, re-process jobs that were skipped due to missing info (if answer received)

## Friday Report

Weekly email containing:
- Roles applied that week (title, company, match score, date)
- JD summary for each applied role
- **Skill popularity** — top 10-20 most mentioned skills across all search results that week
- Application statistics (total applied, success rate, etc.)

Configurable via report DAG parameters.

## Skills (`.agents/skills/`)

### `application-rules/SKILL.md`
Behavioral rules you can edit. Examples:
- "Never apply to jobs requiring security clearance"
- "Skip contract positions under 6 months"
- "Don't apply to companies on blocklist: [list]"

### `resume-tailoring/SKILL.md`
Rules for how resume is tailored:
- "Always keep OCS role as most recent experience"
- "Never change employment dates"
- "Keep education section as-is"

### `answer-guide/SKILL.md`
Templates for common questions:
- "When asked about Azure experience, emphasize: Synapse, Fabric, Data Lake"
- For "years of experience in X": provide rules like "round up to nearest year, max 20"

These are editable markdown files — if the agent does something wrong, correct it here.

## `agent_commons/` (Shared Module)

Located at `/home/joseph/MyProjects/agent_commons/`, a shared directory for all agents. Installed as editable package (`pip install -e /home/joseph/MyProjects/agent_commons`).

### `email.py`
- `send_email(to, subject, body)` — SMTP send
- `poll_inbox(folder="INBOX", since=today)` — IMAP poll, returns unread messages
- `send_report(to, subject, html_body)` — formatted report email

### `db.py`
- `get_connection()` — PostgreSQL connection from env vars
- `run_migrations()` — Alembic or raw SQL migrations
- Query helpers for each table

### `config.py`
- `load_config(path)` — parse markdown config files (YAML front matter or key: value format)
- `get_config(key)` — runtime config, fallback to config table in DB

### `llm.py`
- `query_llm(prompt, system, model="default")` — abstracted LLM call
- Supports: OpenAI API, Ollama local, any OpenAI-compatible endpoint
- User controls which model via env var — no data sent outside machine

### `encryption.py`
- `encrypt_value(plaintext)` — encrypt with local key
- `decrypt_value(ciphertext)` — decrypt
- Used for credentials in `.env`

## Security

- All credentials stored in local `.env` file, never committed
- LLM calls go to user-configured endpoint (local Ollama or API key — user's choice)
- No data sent to external AI model vendors beyond what user configures
- `agent_commons/encryption.py` provides optional at-rest encryption for stored creds
- Airflow connections use local .env variables

## Error Handling

| Error | Behavior |
|---|---|
| Site blocks automation | CloakBrowser handles stealth; retry with different fingerprint |
| Form can't be filled | Skip job, log reason, continue to next |
| Missing info needed | Save to pending, send email, skip job, retry later |
| LLM call fails | Retry 2x, then fail the job apply for that run |
| LinkedIn login fails | Log error, fail DAG, send alert email |
| Email send fails | Log error, continue (report write to DB still occurs) |

## Out of Scope (v1)

- Indeed and other job boards (v2 after LinkedIn is stable)
- Automated interview scheduling
- Salary negotiation
- Multi-user support
- Parallel job applying (sequential to avoid rate limits)
- Resume PDF styling/layout customization (basic clean PDF only)

## Testing

- Unit tests for scoring/matching logic
- Unit tests for config parsing
- Mock-based tests for email send/poll
- Integration tests with a test LinkedIn account (optional, manual)
- Skills tested by editing SKILL.md and verifying behavior change
