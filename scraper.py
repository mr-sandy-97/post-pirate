"""
Post Pirate: Automated Gazette Sync & Self-Heal Engine
Enterprise-Grade Upgrades: Schema Validation, Atomic Writes, and Webhook Observability
"""

import json
import os
import sys
import re
import urllib.request
import urllib.error
import traceback
from datetime import datetime

JOBS_FILE = os.path.join("data", "jobs.json")
BACKUP_FILE = os.path.join("data", "jobs_backup.json")
TEMP_FILE = os.path.join("data", "jobs_temp.json")

# Observability: Set this in GitHub Actions Secrets (Settings -> Secrets and variables -> Actions)
# Name it DISCORD_WEBHOOK_URL or TELEGRAM_WEBHOOK_URL
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")

CANONICAL_BRANCHES = {
    "civil": "Civil", "mechanical": "Mechanical", "eee": "EEE", "ece": "ECE", 
    "eie": "EIE", "cse": "CSE", "it": "IT", "mining": "Mining", 
    "chemical": "Chemical", "metallurgy": "Metallurgy", "biomedical": "Biomedical"
}

def send_alert(message):
    """Observability: Sends a failure alert to Discord/Telegram if a webhook is configured."""
    print(message)
    if not WEBHOOK_URL:
        return
        
    try:
        # Simple payload format that works for both Discord and standard JSON webhooks
        data = json.dumps({"content": f"🏴‍☠️ **Post Pirate Alert:**\n{message}"}).encode('utf-8')
        req = urllib.request.Request(WEBHOOK_URL, data=data, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"[ALERT FAILED] Could not send webhook: {e}")

def load_jobs():
    """Loads existing jobs with deep error handling and fallback to backup."""
    if os.path.exists(JOBS_FILE):
        try:
            with open(JOBS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except json.JSONDecodeError as e:
            send_alert(f"⚠️ **CRITICAL:** `jobs.json` is corrupted! Error: {e}. Attempting backup restoration.")
            if os.path.exists(BACKUP_FILE):
                with open(BACKUP_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
    return []

def atomic_save(jobs):
    """Data Integrity: Writes to a temp file first, then renames. Prevents half-written files."""
    os.makedirs(os.path.dirname(JOBS_FILE), exist_ok=True)
    
    # 1. Write to temp file
    with open(TEMP_FILE, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)
        
    # 2. Backup old file if it exists
    if os.path.exists(JOBS_FILE):
        os.replace(JOBS_FILE, BACKUP_FILE)
        
    # 3. Swap temp to live
    os.replace(TEMP_FILE, JOBS_FILE)

def validate_schema(job):
    """Data Integrity: Strict schema enforcement. Discards broken records."""
    try:
        title = str(job.get("title", "")).strip()
        deadline = str(job.get("deadline", "")).strip()
        branches = job.get("branches", [])

        if not title or not deadline:
            return None

        # Regex validation for YYYY-MM-DD
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", deadline):
            return None
            
        if not isinstance(branches, list) or len(branches) == 0:
            return None

        return {
            "id": int(job.get("id", int(datetime.utcnow().timestamp()))),
            "title": title,
            "level": str(job.get("level", "Central")),
            "vacancies": int(job.get("vacancies", 0)),
            "branches": [CANONICAL_BRANCHES.get(str(b).lower().strip(), str(b).strip()) for b in branches if b],
            "startDate": str(job.get("startDate", datetime.utcnow().strftime("%Y-%m-%d"))),
            "deadline": deadline,
            "fee": str(job.get("fee", "As per Notification")),
            "description": str(job.get("description", "")),
            "selectionProcess": str(job.get("selectionProcess", "")),
            "syllabus": str(job.get("syllabus", "")),
            "officialLink": str(job.get("officialLink", "https://tspsc.gov.in/"))
        }
    except Exception as e:
        print(f"[PRUNE] Failed schema validation for a job: {e}")
        return None

def run_nightly_pipeline():
    """Main execution block."""
    existing_jobs = load_jobs()
    cleaned_jobs = []
    seen_keys = set()

    for item in existing_jobs:
        validated = validate_schema(item)
        if not validated:
            continue

        unique_key = f"{validated['title'].lower()}_{validated['deadline']}"
        if unique_key in seen_keys:
            continue

        seen_keys.add(unique_key)
        cleaned_jobs.append(validated)

    cleaned_jobs.sort(key=lambda x: x["deadline"], reverse=True)
    atomic_save(cleaned_jobs)
    return len(cleaned_jobs)

if __name__ == "__main__":
    try:
        count = run_nightly_pipeline()
        print(f"[{datetime.utcnow().isoformat()}] Pipeline SUCCESS. {count} records verified.")
    except Exception as e:
        error_trace = traceback.format_exc()
        send_alert(f"🚨 **PIPELINE CRASHED** 🚨\nThe nightly scraper hit a fatal error:\n```python\n{error_trace}\n```")
        sys.exit(1)
