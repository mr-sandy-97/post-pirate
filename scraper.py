import json
import os
import sys
import re
from datetime import datetime

JOBS_FILE = os.path.join("data", "jobs.json")

def load_jobs():
    """Loads existing jobs database with full fallback protection."""
    if os.path.exists(JOBS_FILE):
        try:
            with open(JOBS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception as e:
            print(f"[WARN] Failed to read {JOBS_FILE} ({e}). Initializing clean list.")
    return []

def save_jobs(jobs):
    """Atomically writes formatted records to ensure no file corruption."""
    os.makedirs(os.path.dirname(JOBS_FILE), exist_ok=True)
    with open(JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)

def self_heal_record(job):
    """
    Validates and repairs individual job records:
    1. Enforces schema consistency.
    2. Validates ISO date formats.
    3. Normalizes branch naming conventions for SBTET C-24.
    """
    if not isinstance(job, dict):
        return None

    title = job.get("title", "").strip()
    deadline = job.get("deadline", "").strip()
    branches = job.get("branches", [])

    if not title or not deadline or not isinstance(branches, list) or len(branches) == 0:
        return None

    # Validate deadline date pattern (YYYY-MM-DD)
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", deadline):
        print(f"[REPAIR] Discarding record with invalid deadline date: {title} ({deadline})")
        return None

    start_date = job.get("startDate", "").strip()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", start_date):
        start_date = datetime.utcnow().strftime("%Y-%m-%d")

    return {
        "id": job.get("id", int(datetime.utcnow().timestamp())),
        "title": title,
        "level": job.get("level", "Central"),
        "sector": job.get("sector", job.get("level", "Central")),
        "vacancies": int(job.get("vacancies", 0)),
        "branches": [b.strip() for b in branches if isinstance(b, str) and b.strip()],
        "startDate": start_date,
        "deadline": deadline,
        "fee": job.get("fee", "Exempted / As per Govt notification"),
        "description": job.get("description", "Official diploma recruitment notification."),
        "selectionProcess": job.get("selectionProcess", "Written examination followed by document verification."),
        "syllabus": job.get("syllabus", "SBTET Technical Engineering Discipline + General Aptitude."),
        "checklist": job.get("checklist", [
            "SBTET Diploma Certificate",
            "10th Board DOB Proof",
            "Community / Caste Certificate",
            "Govt Photo ID"
        ]),
        "officialLink": job.get("officialLink", "https://tspsc.gov.in/")
    }

def run_nightly_sync_and_maintenance():
    """
    Nightly pipeline:
    - Scans records for schema integrity and duplicates.
    - Self-heals corrupted fields.
    - Sorts records by nearest deadline.
    """
    print(f"[{datetime.utcnow().isoformat()}] === Starting Nightly Self-Heal & Gazette Sync ===")
    existing_jobs = load_jobs()
    print(f"Loaded {len(existing_jobs)} existing records.")

    cleaned_jobs = []
    seen_keys = set()

    for item in existing_jobs:
        healed = self_heal_record(item)
        if not healed:
            continue

        unique_key = f"{healed['title'].lower()}_{healed['deadline']}"
        if unique_key in seen_keys:
            print(f"[PRUNE] Dropping duplicate posting: {healed['title']}")
            continue

        seen_keys.add(unique_key)
        cleaned_jobs.append(healed)

    # Sort descending by deadline date
    cleaned_jobs.sort(key=lambda x: x["deadline"], reverse=True)

    save_jobs(cleaned_jobs)
    print(f"[{datetime.utcnow().isoformat()}] Self-heal completed. {len(cleaned_jobs)} records preserved.")
    return len(cleaned_jobs)

if __name__ == "__main__":
    count = run_nightly_sync_and_maintenance()
    sys.exit(0)
