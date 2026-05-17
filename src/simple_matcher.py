import re


def extract_keywords(text: str) -> set[str]:
    text = text.lower()
    tech_keywords = {
        "python", "sql", "java", "scala", "spark", "hadoop", "aws", "azure",
        "gcp", "docker", "kubernetes", "terraform", "airflow", "kafka",
        "data engineering", "etl", "data pipeline", "data warehouse",
        "data lake", "data modeling", "machine learning", "deep learning",
        "nlp", "statistics", "pandas", "numpy", "pyspark", "databricks",
        "snowflake", "redshift", "bigquery", "postgresql", "mysql",
        "mongodb", "cassandra", "redis", "elasticsearch", "tableau",
        "power bi", "looker", "dbt", "ci/cd", "git", "linux", "rest api",
        "graphql", "microservices", "leadership", "management", "mentoring",
        "agile", "scrum", "project management", "stakeholder",
        "strategic", "architecture", "design", "optimization",
        "performance", "scalability", "reliability", "monitoring",
        "alerting", "testing", "deployment", "automation",
    }
    found = set()
    for kw in tech_keywords:
        if re.search(r"\b" + re.escape(kw) + r"\b", text):
            found.add(kw)
    return found


def simple_match_score(jd: str, resume: str) -> float:
    jd_keywords = extract_keywords(jd)
    resume_keywords = extract_keywords(resume)
    if not jd_keywords:
        return 0.0
    overlap = jd_keywords & resume_keywords
    return round((len(overlap) / len(jd_keywords)) * 100, 1)
