"""
pipeline_a.py
Pipeline A: Demo Call Transcript -> v1 Account Memo + Retell Agent Spec

Usage:
    python pipeline_a.py --transcript sample_data/ACC001_demo.txt --account_id ACC001
    python pipeline_a.py --transcript sample_data/ACC002_demo.txt --account_id ACC002
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
from scripts.task_tracker import create_task

# ---------------------------------------------
# LOGGING
# ---------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(open(__import__("sys").stdout.fileno(), mode="w", encoding="utf-8", closefd=False)),
        logging.FileHandler("pipeline.log")
    ]
)
import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8")
log = logging.getLogger("pipeline_a")


def run_pipeline_a(transcript_path: str, account_id: str, output_base: str = "outputs") -> dict:
    """
    Full Pipeline A execution.
    Returns dict with paths to generated files.
    Idempotent: safe to run multiple times on same input.
    """
    log.info(f"[Pipeline A] Starting | account_id={account_id} | transcript={transcript_path}")

    # -- 1. Read transcript --------------------------------------
    if not os.path.exists(transcript_path):
        log.error(f"Transcript file not found: {transcript_path}")
        raise FileNotFoundError(f"Transcript not found: {transcript_path}")

    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript_text = f.read()

    log.info(f"[Pipeline A] Transcript loaded: {len(transcript_text)} characters")

    # -- 2. Extract Account Memo ---------------------------------
    log.info("[Pipeline A] Extracting account memo...")
    memo = extract_memo_from_transcript(transcript_text, account_id, version="v1")

    if memo.get("questions_or_unknowns"):
        log.warning(f"[Pipeline A] {len(memo['questions_or_unknowns'])} unknowns detected:")
        for u in memo["questions_or_unknowns"]:
            log.warning(f"  [WARN]  {u}")

    # -- 3. Generate Agent Spec ----------------------------------
    log.info("[Pipeline A] Generating Retell agent spec...")
    spec = generate_agent_spec(memo)

    # -- 4. Write Outputs ----------------------------------------
    out_dir = os.path.join(output_base, "accounts", account_id, "v1")
    os.makedirs(out_dir, exist_ok=True)

    memo_path = os.path.join(out_dir, "account_memo.json")
    spec_path = os.path.join(out_dir, "agent_spec.json")
    prompt_path = os.path.join(out_dir, "agent_prompt.txt")

    with open(memo_path, "w", encoding="utf-8") as f:
        json.dump(memo, f, indent=2)

    with open(spec_path, "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2)

    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(spec["system_prompt"])

    log.info(f"[Pipeline A] [OK] Outputs written to {out_dir}")
    log.info(f"  -> account_memo.json")
    log.info(f"  -> agent_spec.json")
    log.info(f"  -> agent_prompt.txt")

    # -- 5. Create task tracker item -----------------------------
    task = create_task(
        account_id=account_id,
        company_name=memo.get("company_name", account_id),
        pipeline="pipeline_a",
        version="v1",
        status="completed",
        unknowns=memo.get("questions_or_unknowns", []),
        output_dir=out_dir,
        notes=f"Demo call processed. {len(memo.get('questions_or_unknowns', []))} unknowns flagged for onboarding."
    )
    log.info(f"[Pipeline A] [TASK] Task created: {task['task_id']} — action_required={task['action_required']}")

    return {
        "account_id": account_id,
        "version": "v1",
        "status": "success",
        "output_dir": out_dir,
        "memo_path": memo_path,
        "spec_path": spec_path,
        "prompt_path": prompt_path,
        "unknowns_count": len(memo.get("questions_or_unknowns", [])),
        "generated_at": datetime.now().isoformat()
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline A: Demo -> v1 Agent")
    parser.add_argument("--transcript", required=True, help="Path to demo transcript file")
    parser.add_argument("--account_id", required=True, help="Account ID (e.g. ACC001)")
    parser.add_argument("--output", default="outputs", help="Output base directory")
    args = parser.parse_args()

    result = run_pipeline_a(args.transcript, args.account_id, args.output)
    print(json.dumps(result, indent=2))
