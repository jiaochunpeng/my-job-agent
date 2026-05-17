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


def test_load_skills(tmp_path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "application-rules").mkdir()
    (skills_dir / "application-rules" / "SKILL.md").write_text("Never apply to jobs requiring security clearance.")
    rules = load_skills(str(skills_dir))
    assert "application-rules" in rules
    assert "security clearance" in rules["application-rules"]
