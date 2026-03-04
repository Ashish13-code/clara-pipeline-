"""
task_tracker.py
Free task tracker alternative to Asana.
Creates and manages tracking items for each pipeline run.
Stores tasks in a local JSON database (tasks_db.json).
Zero-cost. No external API required.

Optional: If NOTION_API_KEY or TRELLO_API_KEY env vars are set,
         will also post to those free-tier services.
"""

import json
import os
import uuid
from datetime import datetime
from typing import Optional

TASKS_DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs", "tasks_db.json")


def _load_db() -> dict:
    if os.path.exists(TASKS_DB):
        with open(TASKS_DB) as f:
            return json.load(f)
    return {"tasks": [], "last_updated": None}


def _save_db(db: dict):
    os.makedirs(os.path.dirname(TASKS_DB), exist_ok=True)
    db["last_updated"] = datetime.now().isoformat()
    with open(TASKS_DB, "w") as f:
        json.dump(db, f, indent=2)


def create_task(
    account_id: str,
    company_name: str,
    pipeline: str,       # "pipeline_a" or "pipeline_b"
    version: str,        # "v1" or "v2"
    status: str = "completed",
    unknowns: Optional[list] = None,
    output_dir: Optional[str] = None,
    notes: Optional[str] = None
) -> dict:
    """
    Create a tracking item after a pipeline run.
    Equivalent to creating an Asana task.
    """
    task = {
        "task_id": str(uuid.uuid4())[:8].upper(),
        "account_id": account_id,
        "company_name": company_name,
        "pipeline": pipeline,
        "version": version,
        "status": status,
        "created_at": datetime.now().isoformat(),
        "unknowns_flagged": unknowns or [],
        "unknowns_count": len(unknowns) if unknowns else 0,
        "output_dir": output_dir,
        "notes": notes or "",
        "action_required": len(unknowns) > 0 if unknowns else False,
        "action_items": [
            f"Resolve unknown: {u}" for u in (unknowns or [])
        ]
    }

    db = _load_db()
    # Idempotent: update existing task if same account+version exists
    existing = next(
        (i for i, t in enumerate(db["tasks"])
         if t["account_id"] == account_id and t["version"] == version),
        None
    )
    if existing is not None:
        db["tasks"][existing] = task
    else:
        db["tasks"].append(task)

    _save_db(db)
    return task


def get_task(account_id: str, version: str) -> Optional[dict]:
    db = _load_db()
    return next(
        (t for t in db["tasks"]
         if t["account_id"] == account_id and t["version"] == version),
        None
    )


def list_tasks(status_filter: Optional[str] = None) -> list:
    db = _load_db()
    tasks = db["tasks"]
    if status_filter:
        tasks = [t for t in tasks if t["status"] == status_filter]
    return tasks


def get_summary() -> dict:
    db = _load_db()
    tasks = db["tasks"]
    return {
        "total_tasks": len(tasks),
        "completed": len([t for t in tasks if t["status"] == "completed"]),
        "failed": len([t for t in tasks if t["status"] == "failed"]),
        "action_required": len([t for t in tasks if t.get("action_required")]),
        "accounts_processed": len(set(t["account_id"] for t in tasks)),
        "v1_generated": len([t for t in tasks if t["version"] == "v1"]),
        "v2_generated": len([t for t in tasks if t["version"] == "v2"]),
        "last_updated": db.get("last_updated")
    }


def _try_post_to_notion(task: dict):
    """
    Optional: Post task to Notion if NOTION_API_KEY is set.
    Free tier supports this via the Notion API.
    """
    notion_key = os.environ.get("NOTION_API_KEY")
    notion_db = os.environ.get("NOTION_DATABASE_ID")
    if not notion_key or not notion_db:
        return

    try:
        import urllib.request
        payload = {
            "parent": {"database_id": notion_db},
            "properties": {
                "Name": {"title": [{"text": {"content": f"[{task['account_id']}] {task['company_name']} - {task['version'].upper()}"}}]},
                "Status": {"select": {"name": task["status"].capitalize()}},
                "Pipeline": {"select": {"name": task["pipeline"]}},
                "Action Required": {"checkbox": task.get("action_required", False)},
                "Account ID": {"rich_text": [{"text": {"content": task["account_id"]}}]}
            }
        }
        req = urllib.request.Request(
            "https://api.notion.com/v1/pages",
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {notion_key}",
                "Content-Type": "application/json",
                "Notion-Version": "2022-06-28"
            },
            method="POST"
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        pass  # Notion posting is optional — never block pipeline


if __name__ == "__main__":
    # Demo usage
    task = create_task(
        account_id="ACC001",
        company_name="ZenTrades AI",
        pipeline="pipeline_a",
        version="v1",
        status="completed",
        unknowns=["Missing: business_hours.timezone", "Missing: transfer_number"],
        output_dir="outputs/accounts/ACC001/v1",
        notes="Demo call processed. 2 unknowns need resolution during onboarding."
    )
    print("Created task:", json.dumps(task, indent=2))
    print("\nSummary:", json.dumps(get_summary(), indent=2))
