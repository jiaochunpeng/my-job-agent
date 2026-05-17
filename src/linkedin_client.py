import json
import re
import os
import pickle
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
import requests
from requests.adapters import HTTPAdapter, Retry

FIREFOX_PROFILE = Path.home() / "snap/firefox/common/.mozilla/firefox/2sxygIfm.Profile 1"
COOKIE_FILE = Path.home() / ".cache/job-agent/linkedin_cookies.pkl"

LINKEDIN_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class LinkedInClient:
    def __init__(self):
        self.session = requests.Session()
        retries = Retry(total=2, backoff_factor=2, status_forcelist=[429, 502, 503])
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("https://", adapter)
        self.session.headers.update(LINKEDIN_HEADERS)
        self._load_cookies()

    def _load_cookies(self):
        if COOKIE_FILE.exists():
            with open(COOKIE_FILE, "rb") as f:
                cookies = pickle.load(f)
            for c in cookies:
                self.session.cookies.set(c["name"], c["value"], domain=c.get("domain", ".linkedin.com"))
            return

        db_path = FIREFOX_PROFILE / "cookies.sqlite"
        if not db_path.exists():
            raise RuntimeError(f"Firefox cookie DB not found at {db_path}. Log into LinkedIn in Firefox first.")

        copy_path = Path("/tmp/linkedin_cookies_copy.sqlite")
        shutil.copy2(db_path, copy_path)
        src = sqlite3.connect(str(copy_path))
        rows = src.execute(
            "SELECT name, value, host, path, isSecure, isHttpOnly, expiry FROM moz_cookies WHERE host LIKE '%linkedin%'"
        ).fetchall()
        src.close()
        copy_path.unlink(missing_ok=True)

        for name, value, host, path, secure, httponly, expiry in rows:
            self.session.cookies.set(name, value, domain=host, path=path)

        self.save_cookies()

    def save_cookies(self):
        COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)
        cookies = [{"name": c.name, "value": c.value, "domain": c.domain} for c in self.session.cookies]
        with open(COOKIE_FILE, "wb") as f:
            pickle.dump(cookies, f)

    def _get_csrf_token(self) -> str:
        for c in self.session.cookies:
            if c.name == "JSESSIONID":
                val = c.value
                if val.startswith('"') and val.endswith('"'):
                    val = val[1:-1]
                return val
        return ""

    def _api_headers(self):
        return {
            "csrf-token": self._get_csrf_token(),
            "accept": "application/json",
        }

    def search_jobs(self, keywords: str, location: str = "Ottawa", max_results: int = 25) -> list[dict]:
        url = "https://www.linkedin.com/jobs/search/"
        params = {"keywords": keywords, "location": location}
        resp = self.session.get(url, params=params, timeout=30)
        resp.raise_for_status()

        job_ids = set(re.findall(r"jobPostingCard:\((\d+),JOB_DETAILS\)", resp.text))
        path_ids = set(re.findall(r"/jobs/view/(\d+)", resp.text))
        all_ids = list(job_ids | path_ids)

        jobs = []
        for jid in all_ids[:max_results]:
            job = self._fetch_job_details(jid)
            if job:
                jobs.append(job)
        return jobs

    def _fetch_job_details(self, job_id: str) -> Optional[dict]:
        api_url = f"https://www.linkedin.com/voyager/api/jobs/jobPostings/{job_id}"
        try:
            resp = self.session.get(api_url, headers=self._api_headers(), timeout=15)
            if resp.status_code != 200:
                return None
            data = resp.json()
        except Exception:
            return None

        title = data.get("title", "")
        location = data.get("formattedLocation", "")
        desc = data.get("description", {}).get("text", "")
        apply_method = data.get("applyMethod", {})
        url_path = data.get("urlPathSegment", "")

        company = ""
        company_match = re.search(r"-at-([^-]+)-", url_path)
        if company_match:
            company = company_match.group(1).replace("-", " ").title()

        if not company:
            company = data.get("companyDetails", {}).get(
                "com.linkedin.voyager.jobs.JobPostingCompany", {}
            ).get("companyName", "")

        apply_type = "external"
        apply_url = ""
        if "com.linkedin.voyager.jobs.OffsiteApply" in apply_method:
            apply_type = "external"
            apply_url = apply_method["com.linkedin.voyager.jobs.OffsiteApply"].get("companyApplyUrl", "")
        elif "com.linkedin.voyager.jobs.SimpleApply" in apply_method:
            apply_type = "easy_apply"
            apply_url = f"https://www.linkedin.com/jobs/view/{job_id}/"

        return {
            "title": title,
            "company": company,
            "location": location,
            "url": f"https://www.linkedin.com/jobs/view/{job_id}/",
            "job_id": job_id,
            "jd": desc,
            "apply_type": apply_type,
            "apply_url": apply_url,
        }

    def get_job_details(self, url: str) -> dict:
        job_id = url.strip("/").split("/")[-1]
        if job_id.isdigit():
            return self._fetch_job_details(job_id) or {"jd": "", "url": url}
        return {"jd": "", "url": url}

    def close(self):
        self.session.close()
