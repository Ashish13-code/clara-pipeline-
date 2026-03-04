"""
versioning.py
Handles v1 -> v2 patching, diff generation, and changelog creation.
"""

import json
import copy
from datetime import datetime
from typing import Optional


def deep_diff(v1: dict, v2: dict, path: str = "") -> list:
    """
    Recursively compare two dicts and return list of changes.
    Each change is a dict: {field, old_value, new_value, change_type}
    """
    changes = []

    all_keys = set(list(v1.keys()) + list(v2.keys()))

    for key in all_keys:
        full_path = f"{path}.{key}" if path else key

        if key not in v1:
            changes.append({
                "field": full_path,
                "change_type": "added",
                "old_value": None,
                "new_value": v2[key]
            })
        elif key not in v2:
            changes.append({
                "field": full_path,
                "change_type": "removed",
                "old_value": v1[key],
                "new_value": None
            })
        elif isinstance(v1[key], dict) and isinstance(v2[key], dict):
            nested = deep_diff(v1[key], v2[key], full_path)
            changes.extend(nested)
        elif v1[key] != v2[key]:
            changes.append({
                "field": full_path,
                "change_type": "updated",
                "old_value": v1[key],
                "new_value": v2[key]
            })

    return changes


def apply_patch(v1_memo: dict, onboarding_memo: dict) -> dict:
    """
    Merge onboarding data into v1 memo to produce v2 memo.
    Rules:
    - Onboarding values override demo values if not None/empty
    - questions_or_unknowns cleared for fields now confirmed
    - version bumped to v2
    - Preserve fields not touched by onboarding
    """
    v2 = copy.deepcopy(v1_memo)
    v2["version"] = "v2"

    def patch_field(v2_dict, onboard_dict, key):
        val = onboard_dict.get(key)
        if val is not None and val != [] and val != "":
            v2_dict[key] = val

    # Top-level fields
    for field in ["company_name", "contact_name", "email", "phone",
                  "office_address", "services_supported",
                  "emergency_definition", "non_emergency_definition",
                  "integration_constraints", "notes"]:
        patch_field(v2, onboarding_memo, field)

    # Nested: business_hours
    if onboarding_memo.get("business_hours"):
        ob_bh = onboarding_memo["business_hours"]
        for subfield in ["days", "start_time", "end_time", "timezone"]:
            val = ob_bh.get(subfield)
            if val:
                v2["business_hours"][subfield] = val
                v2["business_hours"]["confirmed"] = True

    # Nested: emergency_routing_rules
    if onboarding_memo.get("emergency_routing_rules"):
        ob_routing = onboarding_memo["emergency_routing_rules"]
        for subfield in ["primary_number", "backup_number",
                         "transfer_timeout_seconds", "fallback_action"]:
            val = ob_routing.get(subfield)
            if val:
                v2["emergency_routing_rules"][subfield] = val

    # Nested: call_transfer_rules
    if onboarding_memo.get("call_transfer_rules"):
        ob_ctr = onboarding_memo["call_transfer_rules"]
        for subfield in ["timeout_seconds", "retry_number", "on_fail"]:
            val = ob_ctr.get(subfield)
            if val:
                v2["call_transfer_rules"][subfield] = val

    # Nested: non_emergency_routing_rules
    if onboarding_memo.get("non_emergency_routing_rules"):
        ob_ner = onboarding_memo["non_emergency_routing_rules"]
        for subfield in ["action", "callback_timing"]:
            val = ob_ner.get(subfield)
            if val:
                v2["non_emergency_routing_rules"][subfield] = val

    # Update summaries
    v2["after_hours_flow_summary"] = onboarding_memo.get(
        "after_hours_flow_summary") or v2.get("after_hours_flow_summary")
    v2["office_hours_flow_summary"] = onboarding_memo.get(
        "office_hours_flow_summary") or v2.get("office_hours_flow_summary")

    # Recompute unknowns - remove ones now resolved
    from scripts.extractor import detect_unknowns
    v2["questions_or_unknowns"] = detect_unknowns(v2)

    v2["notes"] = f"Updated from onboarding call. Version: v2. Generated: {datetime.now().strftime('%Y-%m-%d')}."

    return v2


def generate_changelog(account_id: str, company_name: str,
                        v1_memo: dict, v2_memo: dict,
                        v1_spec: dict, v2_spec: dict) -> dict:
    """
    Generate a structured changelog comparing v1 and v2.
    """
    memo_changes = deep_diff(v1_memo, v2_memo)
    spec_changes = deep_diff(v1_spec, v2_spec)

    # Filter out noise (version, notes, timestamp changes)
    noise_fields = {"version", "notes", "agent_name", "system_prompt"}
    meaningful_memo = [c for c in memo_changes if c["field"].split(".")[0] not in noise_fields]
    meaningful_spec = [c for c in spec_changes if c["field"].split(".")[0] not in noise_fields]

    changelog = {
        "account_id": account_id,
        "company_name": company_name,
        "generated_at": datetime.now().isoformat(),
        "transition": "v1 (demo) -> v2 (onboarding)",
        "summary": {
            "total_memo_changes": len(meaningful_memo),
            "total_spec_changes": len(meaningful_spec),
            "unknowns_resolved": len(v1_memo.get("questions_or_unknowns", [])) - len(v2_memo.get("questions_or_unknowns", [])),
            "unknowns_remaining": len(v2_memo.get("questions_or_unknowns", []))
        },
        "memo_changes": meaningful_memo,
        "spec_changes": meaningful_spec,
        "resolved_unknowns": [
            u for u in v1_memo.get("questions_or_unknowns", [])
            if u not in v2_memo.get("questions_or_unknowns", [])
        ],
        "remaining_unknowns": v2_memo.get("questions_or_unknowns", [])
    }

    return changelog


def generate_changelog_md(changelog: dict) -> str:
    """
    Generate a human-readable markdown changelog.
    """
    lines = [
        f"# Changelog: {changelog['company_name']} ({changelog['account_id']})",
        f"**Transition:** {changelog['transition']}",
        f"**Generated:** {changelog['generated_at']}",
        "",
        "## Summary",
        f"- Memo fields changed: {changelog['summary']['total_memo_changes']}",
        f"- Unknowns resolved: {changelog['summary']['unknowns_resolved']}",
        f"- Unknowns remaining: {changelog['summary']['unknowns_remaining']}",
        "",
        "## Resolved Unknowns (Demo → Onboarding)",
    ]

    if changelog.get("resolved_unknowns"):
        for item in changelog["resolved_unknowns"]:
            lines.append(f"- ✅ {item}")
    else:
        lines.append("- None")

    lines += ["", "## Changes Made"]

    if changelog.get("memo_changes"):
        for change in changelog["memo_changes"]:
            emoji = "➕" if change["change_type"] == "added" else "✏️" if change["change_type"] == "updated" else "➖"
            lines.append(f"- {emoji} **{change['field']}**: `{change['old_value']}` → `{change['new_value']}`")
    else:
        lines.append("- No significant changes detected")

    if changelog.get("remaining_unknowns"):
        lines += ["", "## ⚠️ Still Unknown / Unconfirmed"]
        for item in changelog["remaining_unknowns"]:
            lines.append(f"- ❓ {item}")

    return "\n".join(lines)
