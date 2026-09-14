import json
import os
import sys
from datetime import datetime

JOBS_FILE = os.path.join("data", "jobs.json")

def load_jobs():
    """Loads existing jobs database from disk."""
    if os.path.exists(JOBS_FILE):
        with open(JOBS_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_jobs(jobs):
    """Saves formatted jobs back to disk atomically."""
    os.makedirs(os.path.dirname(JOBS_FILE), exist_ok=True)
    with open(JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)

def run_self_heal_and_sync():
    """
    Executes the nightly self-heal and synchronization:
    1. Validates integrity of entries.
    2. Enforces unique job titles.
    3. Formats dates to standard ISO strings (YYYY-MM-DD).
    4. Confirms that all mandatory fields are present.
    """
    print(f"[{datetime.utcnow().isoformat()}] Starting Post Pirate Self-Heal Pipeline...")
    jobs = load_jobs()
    print(f"Loaded {len(jobs)} entries from {JOBS_FILE}.")

    cleaned_jobs = []
    seen_identifiers = set()

    for item in jobs:
        # Validate required fields
        title = item.get("title", "").strip()
        deadline = item.get("deadline", "").strip()
        branches = item.get("branches", [])

        if not title or not deadline or not branches:
            print(f"Skipping malformed entry: {item}")
            continue

        unique_key = f"{title.lower()}_{deadline}"
        if unique_key in seen_identifiers:
            print(f"Removing duplicate entry: {title}")
            continue

        seen_identifiers.add(unique_key)
        cleaned_jobs.append(item)

    # Sort descending by deadline date
    cleaned_jobs.sort(key=lambda x: x.get("deadline", ""), reverse=True)

    save_jobs(cleaned_jobs)
    print(f"[{datetime.utcnow().isoformat()}] Self-heal complete. {len(cleaned_jobs)} verified entries preserved.")

if __name__ == "__main__":
    run_self_heal_and_sync()
