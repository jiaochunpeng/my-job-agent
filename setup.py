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
