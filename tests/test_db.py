import pytest
from datetime import date
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
    wr = WeeklyReport(week_start=date(2026, 5, 11), report_data={"applied": [], "skills": {}})
    db_session.add(wr)
    db_session.commit()
    assert db_session.query(WeeklyReport).first().week_start == date(2026, 5, 11)
