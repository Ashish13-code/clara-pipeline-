"""
batch_runner.py
Batch-processes all demo + onboarding transcripts.
Runs Pipeline A on all demo files, then Pipeline B on all onboarding files.

Usage:
    python batch_runner.py
    python batch_runner.py --data_dir sample_data --output_dir outputs
"""

import argparse
import json
import os
import sys
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.pipeline_a import run_pipeline_a
from scripts.pipeline_b import run_pipeline_b

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(open(__import__("sys").stdout.fileno(), mode="w", encoding="utf-8", closefd=False)),
        logging.FileHandler("batch_run.log")
    ]
)
import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8")
log = logging.getLogger("batch_runner")


def discover_files(data_dir: str):
    """
    Discover all demo and onboarding transcript files.
    Convention: <ACCOUNT_ID>_demo.txt and <ACCOUNT_ID>_onboarding.txt
    """
    demo_files = {}
    onboarding_files = {}

    for fname in os.listdir(data_dir):
        if fname.endswith("_demo.txt"):
            account_id = fname.replace("_demo.txt", "")
            demo_files[account_id] = os.path.join(data_dir, fname)
        elif fname.endswith("_onboarding.txt"):
            account_id = fname.replace("_onboarding.txt", "")
            onboarding_files[account_id] = os.path.join(data_dir, fname)

    return demo_files, onboarding_files


def run_batch(data_dir: str = "sample_data", output_dir: str = "outputs") -> dict:
    """
    Run all pipelines in batch. Idempotent.
    """
    log.info("=" * 60)
    log.info("CLARA PIPELINE - BATCH RUN STARTING")
    log.info(f"Data dir: {data_dir}")
    log.info(f"Output dir: {output_dir}")
    log.info("=" * 60)

    demo_files, onboarding_files = discover_files(data_dir)

    log.info(f"Found {len(demo_files)} demo files: {list(demo_files.keys())}")
    log.info(f"Found {len(onboarding_files)} onboarding files: {list(onboarding_files.keys())}")

    results = {
        "batch_run_at": datetime.now().isoformat(),
        "pipeline_a_results": [],
        "pipeline_b_results": [],
        "summary": {}
    }

    pipeline_a_success = 0
    pipeline_a_failed = 0

    # -- Pipeline A: Demo -> v1 ------------------------------------
    log.info("\n" + "-" * 40)
    log.info("RUNNING PIPELINE A (Demo -> v1)")
    log.info("-" * 40)

    for account_id, transcript_path in demo_files.items():
        try:
            result = run_pipeline_a(transcript_path, account_id, output_dir)
            results["pipeline_a_results"].append(result)
            pipeline_a_success += 1
            log.info(f"[OK] Pipeline A complete: {account_id}")
        except Exception as e:
            log.error(f"[FAIL] Pipeline A failed for {account_id}: {e}")
            results["pipeline_a_results"].append({
                "account_id": account_id,
                "status": "failed",
                "error": str(e)
            })
            pipeline_a_failed += 1

    pipeline_b_success = 0
    pipeline_b_failed = 0

    # -- Pipeline B: Onboarding -> v2 -----------------------------
    log.info("\n" + "-" * 40)
    log.info("RUNNING PIPELINE B (Onboarding -> v2)")
    log.info("-" * 40)

    for account_id, transcript_path in onboarding_files.items():
        if account_id not in demo_files:
            log.warning(f"[WARN]  No demo file found for {account_id}, skipping Pipeline B")
            continue
        try:
            result = run_pipeline_b(transcript_path, account_id, output_dir)
            results["pipeline_b_results"].append(result)
            pipeline_b_success += 1
            log.info(f"[OK] Pipeline B complete: {account_id}")
        except Exception as e:
            log.error(f"[FAIL] Pipeline B failed for {account_id}: {e}")
            results["pipeline_b_results"].append({
                "account_id": account_id,
                "status": "failed",
                "error": str(e)
            })
            pipeline_b_failed += 1

    # -- Summary --------------------------------------------------
    results["summary"] = {
        "total_accounts": len(demo_files),
        "pipeline_a": {
            "success": pipeline_a_success,
            "failed": pipeline_a_failed
        },
        "pipeline_b": {
            "success": pipeline_b_success,
            "failed": pipeline_b_failed
        }
    }

    # Write batch summary
    summary_path = os.path.join(output_dir, "batch_summary.json")
    os.makedirs(output_dir, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    log.info("\n" + "=" * 60)
    log.info("BATCH RUN COMPLETE")
    log.info(f"Pipeline A: {pipeline_a_success} success, {pipeline_a_failed} failed")
    log.info(f"Pipeline B: {pipeline_b_success} success, {pipeline_b_failed} failed")
    log.info(f"Summary written to {summary_path}")
    log.info("=" * 60)

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch runner for all Clara pipelines")
    parser.add_argument("--data_dir", default="sample_data", help="Directory with transcript files")
    parser.add_argument("--output_dir", default="outputs", help="Output base directory")
    args = parser.parse_args()

    results = run_batch(args.data_dir, args.output_dir)
    print(json.dumps(results["summary"], indent=2))
