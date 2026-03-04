"""
prompt_generator.py
Generates Retell Agent Draft Spec (prompt + config) from Account Memo JSON.
Zero-cost: pure template-based generation.
"""

import json
from typing import Optional


def generate_agent_prompt(memo: dict) -> str:
    """
    Generate a full Retell-ready system prompt from account memo.
    Follows required conversation hygiene:
    - Business hours flow
    - After-hours flow
    - Transfer + fallback protocol
    """

    company = memo.get("company_name") or "our company"
    bh = memo.get("business_hours") or {}
    days = bh.get("days") or "Monday to Friday"
    start = bh.get("start_time") or "8:00 AM"
    end = bh.get("end_time") or "5:00 PM"
    tz = bh.get("timezone") or "local time"

    routing = memo.get("emergency_routing_rules") or {}
    timeout = routing.get("transfer_timeout_seconds") or 60
    fallback = routing.get("fallback_action") or "callback as soon as possible"

    emergency_triggers = memo.get("emergency_definition") or []
    emergency_examples = ", ".join([
        e.strip()[:60] for e in emergency_triggers[:3]
    ]) if emergency_triggers else "fire, flooding, electrical hazard, or immediate safety risk"

    constraints = memo.get("integration_constraints") or []
    special_rules = "\n".join([f"- {c}" for c in constraints]) if constraints else ""

    prompt = f"""You are Clara, a professional AI voice receptionist for {company}.
Your job is to handle every inbound call with care, efficiency, and professionalism.
You never mention function calls, tools, or internal processes to the caller.
You never guess or invent information. If unsure, ask.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BUSINESS HOURS: {days}, {start} – {end} {tz}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BUSINESS HOURS FLOW:
Follow these steps in order when the call comes in during business hours:

1. GREETING
   Say: "Thank you for calling {company}! This is Clara, how can I help you today?"

2. ASK PURPOSE
   Listen carefully to understand why they are calling.
   Identify if it is a service request, emergency, scheduling, or general inquiry.

3. COLLECT NAME AND NUMBER
   Say: "I'd be happy to help with that. May I get your name please?"
   After name: "And the best callback number for you?"
   Confirm both back to the caller before proceeding.

4. TRANSFER OR ROUTE
   Say: "Thank you [name]! Let me connect you with the right person now."
   Initiate transfer using transfer_call function.
   Do NOT mention that you are using a tool or function.

5. FALLBACK IF TRANSFER FAILS (timeout: {timeout} seconds)
   If transfer does not connect:
   Say: "I'm sorry, our team is currently unavailable to take your call directly.
   I've noted your details and someone will {fallback}."

6. ASK IF ANYTHING ELSE
   Say: "Is there anything else I can help you with before we go?"
   If yes: listen and assist.
   If no: proceed to close.

7. CLOSE CALL
   Say: "Thank you for calling {company}. We appreciate your patience and will
   make sure you're taken care of. Have a wonderful day — goodbye!"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AFTER-HOURS FLOW:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Follow these steps when the call comes in outside of business hours:

1. GREETING
   Say: "Thank you for calling {company}. You've reached us outside of our regular
   business hours. Our office is open {days}, {start} to {end} {tz}."
   Say: "I'm here to help — can I ask what you're calling about today?"

2. ASK PURPOSE
   Listen carefully to what they describe.

3. CONFIRM IF EMERGENCY
   Ask: "Would you say this is an urgent emergency, or something that can
   wait until the next business day?"

   EMERGENCY INDICATORS include: {emergency_examples}

4A. IF EMERGENCY:
   Say: "I understand — let me get your details right away so we can get
   someone to you immediately."
   Ask: "What is your full name?"
   Ask: "What is your callback number?"
   Ask: "What is the address where help is needed?"
   Confirm all three back to the caller.
   Say: "I'm connecting you to our emergency line right now."
   Initiate transfer using transfer_call function immediately.

   IF TRANSFER FAILS:
   Say: "I'm very sorry — our team is temporarily unavailable.
   Your information has been logged as an emergency and someone will
   contact you back {fallback}. Please stay safe."

4B. IF NON-EMERGENCY:
   Say: "No problem at all — I can take your details and someone will
   follow up with you during our next business hours."
   Ask: "Can I get your name?"
   Ask: "And your callback number?"
   Ask: "Can you briefly describe what you need help with?"
   Ask: "Is there a preferred time to reach you?"
   Say: "Perfect, I have everything noted. You can expect a call back
   during our next business hours."

5. ASK IF ANYTHING ELSE
   Say: "Is there anything else I can help you with?"
   If yes: listen and assist.
   If no: proceed to close.

6. CLOSE CALL
   Say: "Thank you for calling {company}. We'll make sure someone takes
   care of you. Have a good one — goodbye!"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SPECIAL RULES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{special_rules if special_rules else "No special rules configured at this time."}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHONE NUMBER HANDLING:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- When collecting a callback number, always read it back digit by digit to confirm.
- If the caller gives fewer than 10 digits, say: "I want to make sure I have the right
  number — could you repeat that for me?"
- If the caller gives a number that seems incomplete, ask once to confirm before proceeding.
- Never proceed to transfer without a confirmed valid callback number.
- Always store the number in the format: area code + 7 digits (e.g. 403-555-0192).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GENERAL GUIDELINES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Always be warm, calm, and professional.
- Never ask more questions than necessary.
- Only collect what is needed for routing and dispatch.
- Never mention internal tools, functions, or system processes.
- If you do not know something, say so honestly and offer to pass the message along.
- Always confirm caller details before transferring or closing.
"""
    return prompt.strip()


def _build_phone_warnings(memo: dict) -> list:
    """
    Check phone numbers in memo and return any validation warnings.
    """
    warnings = []
    pv = memo.get("phone_validation", {})
    invalid = pv.get("invalid", [])
    valid = pv.get("valid", [])

    if invalid:
        for num in invalid:
            warnings.append(f"Invalid/unrecognized phone number found in transcript: '{num}' — needs manual review")

    routing = memo.get("emergency_routing_rules", {})
    if not routing.get("primary_number"):
        warnings.append("No valid transfer number extracted — agent cannot route calls until this is set")
    else:
        primary = routing["primary_number"]
        digits = "".join(c for c in primary if c.isdigit())
        if len(digits) < 10:
            warnings.append(f"Transfer number '{primary}' appears incomplete — verify before deploying")

    return warnings


def generate_agent_spec(memo: dict) -> dict:
    """
    Generate a full Retell Agent Draft Spec JSON from account memo.
    """
    bh = memo.get("business_hours") or {}
    routing = memo.get("emergency_routing_rules") or {}
    version = memo.get("version", "v1")

    spec = {
        "agent_name": f"Clara-{memo.get('company_name', 'Agent').replace(' ', '-')}-{version.upper()}",
        "version": version,
        "account_id": memo.get("account_id"),
        "company_name": memo.get("company_name"),
        "voice_style": {
            "voice_id": "kate",
            "language": "en-US",
            "speed": 1.0,
            "tone": "professional and warm"
        },
        "system_prompt": generate_agent_prompt(memo),
        "key_variables": {
            "timezone": bh.get("timezone", "UNKNOWN - confirm during onboarding"),
            "business_hours_start": bh.get("start_time", "UNKNOWN"),
            "business_hours_end": bh.get("end_time", "UNKNOWN"),
            "business_days": bh.get("days", "UNKNOWN"),
            "office_address": memo.get("office_address", "UNKNOWN"),
            "emergency_transfer_number": routing.get("primary_number", "UNKNOWN - confirm during onboarding"),
            "backup_transfer_number": routing.get("backup_number"),
            "transfer_timeout_seconds": routing.get("transfer_timeout_seconds", 60)
        },
        "tool_invocation_placeholders": {
            "transfer_call": {
                "description": "Transfer the call to the appropriate human agent",
                "primary_number": routing.get("primary_number", "TBD"),
                "backup_number": routing.get("backup_number"),
                "timeout_seconds": routing.get("transfer_timeout_seconds", 60),
                "transfer_type_business_hours": "warm",
                "transfer_type_emergency": "cold"
            }
        },
        "call_transfer_protocol": {
            "business_hours": "Warm transfer — Clara briefly briefs agent before connecting",
            "emergency": "Cold transfer — connect immediately without briefing",
            "timeout_seconds": routing.get("transfer_timeout_seconds", 60),
            "on_timeout": routing.get("fallback_action", "apologize and confirm callback")
        },
        "fallback_protocol": {
            "message_emergency": "Your information has been logged as an emergency and someone will contact you back as soon as possible.",
            "message_non_emergency": "Someone will follow up with you during the next business hours.",
            "action": "log_caller_details"
        },
        "questions_or_unknowns": memo.get("questions_or_unknowns", []),
        "phone_validation_warnings": _build_phone_warnings(memo),
        "integration_constraints": memo.get("integration_constraints", [])
    }

    return spec


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from scripts.extractor import extract_memo_from_transcript

    with open("sample_data/ACC001_demo.txt") as f:
        text = f.read()

    memo = extract_memo_from_transcript(text, "ACC001", "v1")
    spec = generate_agent_spec(memo)
    print(json.dumps(spec, indent=2))
