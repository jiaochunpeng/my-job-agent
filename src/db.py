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
