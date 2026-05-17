from pathlib import Path
from typing import Any
from agent_commons.config import load_markdown_config


def _convert_value(v: str) -> Any:
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        pass
    return v


def _convert_config(data: dict[str, Any]) -> dict[str, Any]:
    result = {}
    for k, v in data.items():
        if isinstance(v, list):
            result[k] = v
        elif isinstance(v, str):
            result[k] = _convert_value(v)
        else:
            result[k] = v
    return result


def load_all_configs(config_dir: str = "config") -> dict[str, dict]:
    config_dir = Path(config_dir)
    configs = {}
    for name in ["schedule", "filters", "profile"]:
        path = config_dir / f"{name}.md"
        if path.exists():
            configs[name] = _convert_config(load_markdown_config(str(path)))
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
