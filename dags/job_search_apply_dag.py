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
    filters = config.get("filters", {})

    result = asyncio.run(run_search_and_apply(
        target_roles=filters.get("target_roles"),
        location=filters.get("location", "Ottawa"),
        max_to_search=filters.get("max_to_search", 100),
        max_to_apply=filters.get("max_to_apply", 10),
        min_match_score=filters.get("min_match_score", 80),
        headless=True,
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
