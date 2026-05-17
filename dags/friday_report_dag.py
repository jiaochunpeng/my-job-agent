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
