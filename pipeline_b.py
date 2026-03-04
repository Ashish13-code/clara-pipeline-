"""
pipeline_b.py
Pipeline B: Onboarding Call Transcript -> v2 Account Memo + Agent Spec + Changelog

Usage:
    python pipeline_b.py --transcript sample_data/ACC001_onboarding.txt --account_id ACC001
    python pipeline_b.py --transcript sample_data/ACC002_onboarding.txt --account_id ACC002
"""

import argparse
import json
import os
import sys
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.extractor import extract_memo_from_transcript
from scripts.prompt_generator import generate_agent_spec
from scripts.versioning import apply_patch, generate_changelog, generate_changelog_md
from scripts.task_tracker import create_task

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("pipeline.log")
    ]
)
log = logging.getLogger("pipeline_b")


def run_pipeline_b(transcript_path: str, account_id: str, output_base: str = "outputs") -> dict:
    """
    Full Pipeline B execution.
    Requires v1 outputs to already exist (run pipeline_a first).
    Returns dict with paths to generated files.
    Idempotent: safe to run multiple times.
    """
    log.info(f"[Pipeline B] Starting | account_id={account_id} | transcript={transcript_path}")

    # ── 1. Load existing v1 outputs ─────────────────────────────
    v1_dir = os.path.join(output_base, "accounts", account_id, "v1")
    v1_memo_path = os.path.join(v1_dir, "account_memo.json")
    v1_spec_path = os.path.join(v1_dir, "agent_spec.json")

    if not os.path.exists(v1_memo_path):
        log.error(f"v1 memo not found at {v1_memo_path}. Run pipeline_a first.")
        raise FileNotFoundError(f"v1 memo not found. Run pipeline_a first for {account_id}")

    with open(v1_memo_path) as f:
        v1_memo = json.load(f)

    with open(v1_spec_path) as f:
        v1_spec = json.load(f)

    log.info(f"[Pipeline B] Loaded v1 memo and spec for {account_id}")

    # ── 2. Read onboarding transcript ────────────────────────────
    if not os.path.exists(transcript_path):
        log.error(f"Transcript file not found: {transcript_path}")
        raise FileNotFoundError(f"Transcript not found: {transcript_path}")

    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript_text = f.read()

    log.info(f"[Pipeline B] Onboarding transcript loaded: {len(transcript_text)} chars")

    # ── 3. Extract onboarding updates ───────────────────────────
    log.info("[Pipeline B] Extracting onboarding data...")
    onboarding_memo = extract_memo_from_transcript(transcript_text, account_id, version="v2")

    # ── 4. Patch v1 with onboarding data → v2 ──────────────────
    log.info("[Pipeline B] Applying patch v1 → v2...")
    v2_memo = apply_patch(v1_memo, onboarding_memo)

    # ── 5. Generate v2 agent spec ────────────────────────────────
    log.info("[Pipeline B] Generating v2 agent spec...")
    v2_spec = generate_agent_spec(v2_memo)

    # ── 6. Generate changelog ────────────────────────────────────
    log.info("[Pipeline B] Generating changelog...")
    changelog = generate_changelog(
        account_id,
        v2_memo.get("company_name", account_id),
        v1_memo, v2_memo,
        v1_spec, v2_spec
    )
    changelog_md = generate_changelog_md(changelog)

    log.info(f"[Pipeline B] Changes detected: {changelog['summary']['total_memo_changes']} memo, "
             f"{changelog['summary']['unknowns_resolved']} unknowns resolved")

    # ── 7. Write outputs ─────────────────────────────────────────
    v2_dir = os.path.join(output_base, "accounts", account_id, "v2")
    changelog_dir = os.path.join(output_base, "accounts", account_id, "changelog")
    os.makedirs(v2_dir, exist_ok=True)
    os.makedirs(changelog_dir, exist_ok=True)

    memo_path = os.path.join(v2_dir, "account_memo.json")
    spec_path = os.path.join(v2_dir, "agent_spec.json")
    prompt_path = os.path.join(v2_dir, "agent_prompt.txt")
    changelog_json_path = os.path.join(changelog_dir, "changes.json")
    changelog_md_path = os.path.join(changelog_dir, "changes.md")

    with open(memo_path, "w") as f:
        json.dump(v2_memo, f, indent=2)

    with open(spec_path, "w") as f:
        json.dump(v2_spec, f, indent=2)

    with open(prompt_path, "w") as f:
        f.write(v2_spec["system_prompt"])

    with open(changelog_json_path, "w") as f:
        json.dump(changelog, f, indent=2)

    with open(changelog_md_path, "w") as f:
        f.write(changelog_md)

    log.info(f"[Pipeline B] ✅ Outputs written to {v2_dir}")
    log.info(f"  → account_memo.json")
    log.info(f"  → agent_spec.json")
    log.info(f"  → agent_prompt.txt")
    log.info(f"  → changelog/changes.json")
    log.info(f"  → changelog/changes.md")

    # ── 8. Create task tracker item ─────────────────────────────
    task = create_task(
        account_id=account_id,
        company_name=v2_memo.get("company_name", account_id),
        pipeline="pipeline_b",
        version="v2",
        status="completed",
        unknowns=v2_memo.get("questions_or_unknowns", []),
        output_dir=v2_dir,
        notes=f"Onboarding processed. {changelog['summary']['unknowns_resolved']} unknowns resolved. {changelog['summary']['unknowns_remaining']} remaining."
    )
    log.info(f"[Pipeline B] 📋 Task updated: {task['task_id']} — action_required={task['action_required']}")

    return {
        "account_id": account_id,
        "version": "v2",
        "status": "success",
        "output_dir": v2_dir,
        "memo_path": memo_path,
        "spec_path": spec_path,
        "prompt_path": prompt_path,
        "changelog_json": changelog_json_path,
        "changelog_md": changelog_md_path,
        "changes_count": changelog["summary"]["total_memo_changes"],
        "unknowns_resolved": changelog["summary"]["unknowns_resolved"],
        "unknowns_remaining": changelog["summary"]["unknowns_remaining"],
        "generated_at": datetime.now().isoformat()
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline B: Onboarding → v2 Agent")
    parser.add_argument("--transcript", required=True, help="Path to onboarding transcript file")
    parser.add_argument("--account_id", required=True, help="Account ID (e.g. ACC001)")
    parser.add_argument("--output", default="outputs", help="Output base directory")
    args = parser.parse_args()

    result = run_pipeline_b(args.transcript, args.account_id, args.output)
    print(json.dumps(result, indent=2))
