"""
extractor.py
Rule-based transcript extraction for Clara pipeline.
Zero-cost: no LLM API calls. Uses keyword matching + pattern rules.
"""

import re
import json
from typing import Optional


# ---------------------------------------------
# KEYWORD PATTERNS
# ---------------------------------------------

EMERGENCY_KEYWORDS = [
    "fire", "electrical fire", "sparking", "power outage", "exposed wire",
    "live wire", "smoke", "flood", "leak", "sprinkler", "alarm triggered",
    "hazmat", "chemical spill", "biohazard", "safety risk", "safety hazard",
    "immediately", "urgent", "emergency"
]

NON_EMERGENCY_KEYWORDS = [
    "schedule", "scheduling", "inspection", "quote", "maintenance",
    "booking", "question", "inquiry", "routine", "general", "next business day"
]

DAYS_PATTERN = re.compile(
    r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)[\s\w]*"
    r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)?",
    re.IGNORECASE
)

TIME_PATTERN = re.compile(
    r"(\d{1,2}(?::\d{2})?\s*(?:am|pm))\s*(?:to|-)\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm))",
    re.IGNORECASE
)

PHONE_PATTERN = re.compile(r"\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")

# Phone number validation helpers
def normalize_phone(raw: str) -> str:
    """Strip all non-digit characters, then format as +1XXXXXXXXXX (E.164)."""
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 10:
        return f"+1{digits}"
    elif len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    return raw  # return as-is if format unrecognized

def validate_phone(raw: str) -> dict:
    """
    Validate a phone number and return structured result.
    Returns: {raw, normalized, valid, issue}
    """
    digits = re.sub(r"\D", "", raw)
    result = {"raw": raw.strip(), "normalized": None, "valid": False, "issue": None}

    if len(digits) == 0:
        result["issue"] = "empty"
    elif len(digits) < 10:
        result["issue"] = f"too short ({len(digits)} digits)"
    elif len(digits) == 10:
        result["normalized"] = f"+1{digits}"
        result["valid"] = True
    elif len(digits) == 11 and digits.startswith("1"):
        result["normalized"] = f"+{digits}"
        result["valid"] = True
    else:
        result["issue"] = f"unexpected length ({len(digits)} digits)"

    return result

EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")

TIMEZONE_PATTERN = re.compile(
    r"\b(mountain|pacific|eastern|central|MST|PST|EST|CST|MT|PT|ET|CT)\b",
    re.IGNORECASE
)

TIMEOUT_PATTERN = re.compile(r"(\d+)\s*seconds?", re.IGNORECASE)

ADDRESS_PATTERN = re.compile(
    r"\d+\s+[\w\s]+(?:blvd|ave|st|rd|drive|way|lane|court|place|boulevard|street|road)",
    re.IGNORECASE
)

SOFTWARE_KEYWORDS = ["servicetrade", "google sheets", "salesforce", "hubspot",
                     "jobber", "housecall", "quickbooks", "airtable"]


# ---------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------

def extract_company_name(text: str) -> Optional[str]:
    patterns = [
        r"(?:company|business|we'?re|we are|called|name is)[:\s]+([A-Z][^\n.]+?)(?:\.|,|\n)",
        r"(?:Company|company)[:\s]+(.+?)(?:\n|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    # Try header extraction
    lines = text.split("\n")
    for line in lines:
        if "Company:" in line:
            return line.split("Company:")[1].strip()
    return None


def extract_contact_name(text: str) -> Optional[str]:
    patterns = [
        r"Contact:\s*(.+?)(?:\n|$)",
        r"\[CLIENT - ([A-Z]+)\]",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip().title()
    return None


def extract_email(text: str) -> Optional[str]:
    match = EMAIL_PATTERN.search(text)
    return match.group(0) if match else None


def extract_phones(text: str) -> list:
    """Extract and validate all phone numbers found in transcript."""
    raw_matches = list(set(PHONE_PATTERN.findall(text)))
    validated = []
    for raw in raw_matches:
        result = validate_phone(raw)
        validated.append(result)
    validated.sort(key=lambda x: (0 if x["valid"] else 1, x["raw"]))
    return validated

def extract_valid_phone_strings(text: str) -> list:
    """Return only normalized E.164 strings for valid phones."""
    return [p["normalized"] for p in extract_phones(text) if p["valid"]]


def extract_business_hours(text: str) -> dict:
    hours = {
        "days": None,
        "start_time": None,
        "end_time": None,
        "timezone": None,
        "raw": None,
        "confirmed": False
    }

    # Find timezone
    tz_match = TIMEZONE_PATTERN.search(text)
    if tz_match:
        hours["timezone"] = tz_match.group(0).upper()
        hours["confirmed"] = True

    # Find time range
    time_match = TIME_PATTERN.search(text)
    if time_match:
        hours["start_time"] = time_match.group(1).strip()
        hours["end_time"] = time_match.group(2).strip()
        hours["confirmed"] = True

    # Find days
    days_match = DAYS_PATTERN.search(text)
    if days_match:
        hours["days"] = days_match.group(0).strip()
        hours["raw"] = days_match.group(0).strip()

    return hours


def extract_emergency_definitions(text: str) -> list:
    found = []
    text_lower = text.lower()
    for kw in EMERGENCY_KEYWORDS:
        if kw in text_lower:
            # Extract sentence containing keyword
            for sentence in re.split(r'[.!?\n]', text):
                if kw in sentence.lower() and len(sentence.strip()) > 10:
                    cleaned = sentence.strip()
                    if cleaned not in found:
                        found.append(cleaned)
                        break
    return found[:5]  # cap at 5


def extract_non_emergency_definitions(text: str) -> list:
    found = []
    text_lower = text.lower()
    for kw in NON_EMERGENCY_KEYWORDS:
        if kw in text_lower:
            for sentence in re.split(r'[.!?\n]', text):
                if kw in sentence.lower() and len(sentence.strip()) > 10:
                    cleaned = sentence.strip()
                    if cleaned not in found:
                        found.append(cleaned)
                        break
    return found[:5]


def extract_routing(text: str) -> dict:
    phones_validated = extract_phones(text)
    phones = [p["normalized"] for p in phones_validated if p["valid"]]
    invalid_phones = [p for p in phones_validated if not p["valid"]]
    timeout_match = TIMEOUT_PATTERN.search(text)
    timeout = int(timeout_match.group(1)) if timeout_match else None

    routing = {
        "primary_number": phones[0] if phones else None,
        "backup_number": phones[1] if len(phones) > 1 else None,
        "invalid_numbers_flagged": [p["raw"] for p in invalid_phones] if invalid_phones else [],
        "transfer_timeout_seconds": timeout,
        "fallback_action": None
    }

    text_lower = text.lower()
    if "call back" in text_lower or "follow up" in text_lower:
        if "2 hours" in text_lower:
            routing["fallback_action"] = "callback within 2 hours"
        elif "next business day" in text_lower or "next morning" in text_lower:
            routing["fallback_action"] = "callback next business day"
        else:
            routing["fallback_action"] = "callback promised"

    return routing


def extract_integration_constraints(text: str) -> list:
    constraints = []
    text_lower = text.lower()

    for sw in SOFTWARE_KEYWORDS:
        if sw in text_lower:
            for sentence in re.split(r'[.!?\n]', text):
                if sw in sentence.lower() and len(sentence.strip()) > 5:
                    constraints.append(sentence.strip())
                    break

    # Look for "do not", "never", "don't" rules
    restriction_pattern = re.compile(
        r"(?:do not|never|don't|no)\s+[^\n.!?]+", re.IGNORECASE
    )
    for match in restriction_pattern.finditer(text):
        rule = match.group(0).strip()
        if rule not in constraints and len(rule) > 10:
            constraints.append(rule)

    return constraints[:5]


def extract_address(text: str) -> Optional[str]:
    match = ADDRESS_PATTERN.search(text)
    if match:
        # Try to get full address with city/province
        start = match.start()
        snippet = text[start:start+100]
        return snippet.split("\n")[0].strip()

    # Check for "no fixed address" type statements
    if "mobile" in text.lower() or "no fixed address" in text.lower():
        # Extract service area
        area_match = re.search(r"(?:service area|based in|located in)[:\s]+(.+?)(?:\n|$)", text, re.IGNORECASE)
        if area_match:
            return f"Mobile - Service Area: {area_match.group(1).strip()}"

    return None


def detect_unknowns(memo: dict) -> list:
    unknowns = []
    checks = {
        "business_hours.days": memo.get("business_hours", {}).get("days"),
        "business_hours.start_time": memo.get("business_hours", {}).get("start_time"),
        "business_hours.timezone": memo.get("business_hours", {}).get("timezone"),
        "emergency_routing_rules.primary_number": memo.get("emergency_routing_rules", {}).get("primary_number"),
        "emergency_routing_rules.transfer_timeout_seconds": memo.get("emergency_routing_rules", {}).get("transfer_timeout_seconds"),
        "emergency_definition": memo.get("emergency_definition"),
        "office_address": memo.get("office_address"),
    }
    for field, value in checks.items():
        if not value:
            unknowns.append(f"Missing or unconfirmed: {field}")
    return unknowns


# ---------------------------------------------
# MAIN EXTRACTION FUNCTION
# ---------------------------------------------

def extract_memo_from_transcript(text: str, account_id: str, version: str = "v1") -> dict:
    """
    Extract structured account memo from raw transcript text.
    Returns a dict matching the required JSON schema.
    """
    company_name = extract_company_name(text)
    contact_name = extract_contact_name(text)
    email = extract_email(text)
    phones_raw = extract_phones(text)
    phones_valid = [p["normalized"] for p in phones_raw if p["valid"]]
    phones_invalid = [p for p in phones_raw if not p["valid"]]
    business_hours = extract_business_hours(text)
    emergency_defs = extract_emergency_definitions(text)
    non_emergency_defs = extract_non_emergency_definitions(text)
    routing = extract_routing(text)
    constraints = extract_integration_constraints(text)
    address = extract_address(text)

    memo = {
        "account_id": account_id,
        "version": version,
        "company_name": company_name,
        "contact_name": contact_name,
        "email": email,
        "phone": phones_valid[0] if phones_valid else None,
        "office_address": address,
        "business_hours": business_hours,
        "services_supported": extract_services(text),
        "emergency_definition": emergency_defs if emergency_defs else None,
        "non_emergency_definition": non_emergency_defs if non_emergency_defs else None,
        "emergency_routing_rules": routing,
        "non_emergency_routing_rules": {
            "action": "collect_details_and_callback",
            "callback_timing": routing.get("fallback_action") or "next business day"
        },
        "call_transfer_rules": {
            "timeout_seconds": routing.get("transfer_timeout_seconds"),
            "retry_number": routing.get("backup_number"),
            "on_fail": routing.get("fallback_action")
        },
        "integration_constraints": constraints if constraints else None,
        "after_hours_flow_summary": build_after_hours_summary(emergency_defs, non_emergency_defs),
        "office_hours_flow_summary": "Greet -> Ask purpose -> Collect name and number -> Transfer call -> Fallback if fails -> Close",
        "phone_validation": {"valid": phones_valid, "invalid": [p["raw"] for p in phones_invalid]},
        "questions_or_unknowns": [],
        "notes": f"Extracted from {'demo' if version == 'v1' else 'onboarding'} transcript. Version: {version}."
    }

    memo["questions_or_unknowns"] = detect_unknowns(memo)
    return memo


def extract_services(text: str) -> list:
    service_keywords = {
        "electrical": "Electrical Service",
        "inspection": "Inspections",
        "fire protection": "Fire Protection",
        "sprinkler": "Sprinkler Service",
        "alarm": "Alarm Service",
        "hvac": "HVAC",
        "pressure wash": "Pressure Washing",
        "maintenance": "Maintenance",
        "repair": "Repairs",
        "quote": "Quotes/Estimates",
    }
    services = []
    text_lower = text.lower()
    for keyword, label in service_keywords.items():
        if keyword in text_lower and label not in services:
            services.append(label)
    return services if services else None


def build_after_hours_summary(emergency_defs: list, non_emergency_defs: list) -> str:
    parts = []
    if emergency_defs:
        parts.append("Emergency: collect name/number/address -> transfer immediately")
    if non_emergency_defs:
        parts.append("Non-emergency: collect details -> confirm callback next business day")
    return " | ".join(parts) if parts else "After-hours flow pending configuration"


if __name__ == "__main__":
    # Quick test
    with open("sample_data/ACC001_demo.txt") as f:
        text = f.read()
    memo = extract_memo_from_transcript(text, "ACC001", "v1")
    print(json.dumps(memo, indent=2))
