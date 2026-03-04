# Clara — ZenTrades AI Onboarding Automation Pipeline

> **Assignment:** Build a Zero-Cost Automation Pipeline: Demo Call → Retell Agent Draft → Onboarding Updates → Agent Revision
> **Constraint:** Zero spend. Free-tier only. Fully reproducible.

---

## Architecture & Data Flow

```
sample_data/<ACC_ID>_demo.txt
       │
       ▼
  extractor.py (rule-based, no LLM)
       │
       ▼
  prompt_generator.py (template-based)
       │
       ├──► outputs/<ACC_ID>/v1/account_memo.json
       ├──► outputs/<ACC_ID>/v1/agent_spec.json
       ├──► outputs/<ACC_ID>/v1/agent_prompt.txt
       └──► task_tracker.py ──► outputs/tasks_db.json

sample_data/<ACC_ID>_onboarding.txt
       │
       ▼
  extractor.py + versioning.py (patch v1→v2)
       │
       ├──► outputs/<ACC_ID>/v2/account_memo.json
       ├──► outputs/<ACC_ID>/v2/agent_spec.json
       ├──► outputs/<ACC_ID>/v2/agent_prompt.txt
       └──► outputs/<ACC_ID>/changelog/changes.json + changes.md
```

---

## How to Run Locally

### Option A — Pure Python (No Docker)
Requirements: Python 3.8+. No external libraries needed.

```bash
git clone <your-repo-url>
cd clara_pipeline

# Run all 10 files at once (batch)
python scripts/batch_runner.py

# Or run one account manually:
python scripts/pipeline_a.py --transcript sample_data/ACC001_demo.txt --account_id ACC001
python scripts/pipeline_b.py --transcript sample_data/ACC001_onboarding.txt --account_id ACC001
```

### Option B — n8n via Docker

```bash
cp .env.example .env
docker-compose up -d
# Open http://localhost:5678 (login: admin / clara123)
# Workflows → Import from file → select workflows/n8n_pipeline.json
# Activate and POST to: http://localhost:5678/webhook/demo-transcript
```

---

## How to Plug In the Dataset Files

Name files using this convention and place in sample_data/:

- ACC001_demo.txt / ACC001_onboarding.txt
- ACC002_demo.txt / ACC002_onboarding.txt
- ... up to ACC005

If you receive audio files (.m4a/.mp3), transcribe locally for free:
```bash
pip install openai-whisper
whisper recording.m4a --model base --output_format txt
```

---

## Where Outputs Are Stored

```
outputs/
├── batch_summary.json            <- Run summary: success/fail counts + metrics
├── tasks_db.json                 <- Task tracker (Asana-equivalent, local JSON)
└── accounts/
    └── ACC001/
        ├── v1/
        │   ├── account_memo.json <- Structured data from demo call
        │   ├── agent_spec.json   <- Full Retell agent configuration
        │   └── agent_prompt.txt  <- Ready-to-paste prompt for Retell UI
        ├── v2/
        │   ├── account_memo.json <- Updated after onboarding
        │   ├── agent_spec.json   <- v2 Retell config
        │   └── agent_prompt.txt  <- Updated prompt
        └── changelog/
            ├── changes.json      <- Machine-readable diff
            └── changes.md        <- Human-readable diff
```

---

## Required Output Checklist

### 1) Account Memo JSON fields
account_id, company_name, business_hours (days/start/end/timezone),
office_address, services_supported, emergency_definition,
emergency_routing_rules, non_emergency_routing_rules,
call_transfer_rules, integration_constraints,
after_hours_flow_summary, office_hours_flow_summary,
questions_or_unknowns, notes — ALL PRESENT

### 2) Retell Agent Draft Spec fields
agent_name, voice_style, system_prompt, key_variables,
tool_invocation_placeholders, call_transfer_protocol,
fallback_protocol, version — ALL PRESENT

### 3) Versioning and Diff
v2 memo, v2 agent spec, changes.json, changes.md — ALL GENERATED

### 4) Orchestrator Workflow
workflows/n8n_pipeline.json — importable into n8n (self-hosted Docker)

### 5) Task Tracker
After each Pipeline A run, a task is logged in outputs/tasks_db.json.
Fields: task_id, account_id, company_name, pipeline, version, status,
unknowns_flagged, action_required, action_items, output_dir.
Optional Notion integration via NOTION_API_KEY env var.

---

## Environment Variables

See .env.example for all variables. Key ones:

| Variable         | Required     | Description                        |
|------------------|--------------|------------------------------------|
| N8N_USER         | Docker only  | n8n login username                 |
| N8N_PASSWORD     | Docker only  | n8n login password                 |
| TIMEZONE         | Docker only  | e.g. America/Edmonton              |
| NOTION_API_KEY   | Optional     | Post tasks to Notion free tier     |
| NOTION_DATABASE_ID | Optional   | Target Notion database             |
| RETELL_API_KEY   | Optional     | Auto-create agents (paid tier)     |

---

## Retell Setup — Manual Import Steps

Since programmatic agent creation requires Retell's paid tier:

1. Create a Retell account at retellai.com (free)
2. Click Create New Agent → Multi-State Agent
3. Create 6 states: greeting, business_hours_intake, emergency_intake,
   non_emergency_intake, transfer_failed, close_call
4. Open outputs/accounts/<ID>/v1/agent_prompt.txt
5. Paste each section into the corresponding state prompt
6. In business_hours_intake and emergency_intake: add Transfer Call tool
7. Set transfer number from agent_spec.json → key_variables.emergency_transfer_number
8. Publish as "Clara-Demo-Build" (v1)
9. Repeat with v2 files after onboarding → publish as "Clara-Onboarding-Build" (v2)

---

## Prompt Hygiene Compliance

Every generated agent_prompt.txt includes:

Business Hours Flow:
- Greeting
- Ask purpose
- Collect name and callback number (confirmed back digit by digit)
- Transfer or route
- Fallback if transfer fails
- "Is there anything else?"
- Close call

After-Hours Flow:
- Greeting + inform of hours
- Ask purpose
- Confirm emergency or non-emergency
- Emergency: collect name, number, address immediately → transfer
- Transfer fail: apologize + assure follow-up
- Non-emergency: collect details + confirm next-business-day callback
- "Is there anything else?"
- Close

Guardrails: never mentions function calls or tools. Only collects
what is needed for routing and dispatch.

---

## LLM Usage — Zero Cost

Zero LLM API calls used. All extraction is rule-based regex + keyword
matching. No OpenAI, Anthropic, or paid API called. Runs fully offline.

---

## Automation Behavior

| Property     | Status                                      |
|--------------|---------------------------------------------|
| Repeatable   | Re-running produces same outputs            |
| Idempotent   | Running twice does not duplicate data       |
| Batch-capable | batch_runner.py processes all files        |
| Logged       | pipeline.log + batch_run.log               |
| Reproducible | Python stdlib only, no pip installs needed |

---

## Bonus Features

- dashboard.html — open in browser for visual UI showing all accounts,
  diffs, prompts, unknowns tracker, and task summary
- Diff viewer — per account, shows v1→v2 field changes in green/red
- Batch metrics — batch_summary.json with per-run counts and status

---

## Known Limitations

1. Extraction depends on transcript formatting (labeled speakers work best)
2. Retell API requires paid tier — outputs specs for manual import
3. Phone number parsing picks first/second number found
4. No LLM — very indirect or implied answers may not extract

---

## What I Would Improve with Production Access

1. Add Ollama + Llama3 (local, free) for smarter extraction
2. Retell API auto-create/update agents on paid tier
3. Supabase for queryable storage instead of local JSON
4. Confidence scoring to flag uncertain extractions for review
5. ServiceTrade webhook for automatic job creation post-call
6. n8n folder-watch trigger to auto-run when transcript is dropped in
