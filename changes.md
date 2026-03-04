# Changelog: ZenTrades AI (ACC001)
**Transition:** v1 (demo) -> v2 (onboarding)
**Generated:** 2026-03-04T13:35:43.414129

## Summary
- Memo fields changed: 21
- Unknowns resolved: 5
- Unknowns remaining: 0

## Resolved Unknowns (Demo → Onboarding)
- ✅ Missing or unconfirmed: business_hours.start_time
- ✅ Missing or unconfirmed: business_hours.timezone
- ✅ Missing or unconfirmed: emergency_routing_rules.primary_number
- ✅ Missing or unconfirmed: emergency_routing_rules.transfer_timeout_seconds
- ✅ Missing or unconfirmed: office_address

## Changes Made
- ✏️ **call_transfer_rules.timeout_seconds**: `None` → `45`
- ✏️ **call_transfer_rules.on_fail**: `None` → `callback within 2 hours`
- ✏️ **call_transfer_rules.retry_number**: `None` → `+14035550193`
- ✏️ **office_address**: `None` → `142 Industrial Blvd, Calgary, AB T2E 7N4.`
- ✏️ **emergency_definition**: `["[CLIENT]: Anything electrical that's a safety hazard — exposed wires, power outages at a facility, electrical fires, sparking panels", 'Those need someone on the line immediately', 'We handle electrical service for commercial clients — mostly inspections, repairs, and emergency electrical work']` → `['[CLIENT]: Electrical fire, sparking panels, complete power outage at a facility, exposed live wires, or any situation that poses immediate safety risk', '[CLIENT]: Yes — for electrical fire calls, always ask the caller if they have already called 911', 'And your emergency dispatch number']`
- ✏️ **non_emergency_definition**: `['[CLIENT]: Scheduling inspections, getting quotes, general questions', 'We handle electrical service for commercial clients — mostly inspections, repairs, and emergency electrical work', 'Those can wait till next business day']` → `['[CLIENT]: Inspection scheduling, quotes, routine maintenance requests', "Collect their info and we'll call back next business day"]`
- ✏️ **phone**: `None` → `+14035550192`
- ✏️ **emergency_routing_rules.primary_number**: `None` → `+14035550192`
- ✏️ **emergency_routing_rules.transfer_timeout_seconds**: `None` → `45`
- ✏️ **emergency_routing_rules.fallback_action**: `None` → `callback within 2 hours`
- ✏️ **emergency_routing_rules.backup_number**: `None` → `+14035550193`
- ✏️ **email**: `info@zentrades.ai` → `info@benselectricsolutionsteam.com`
- ✏️ **non_emergency_routing_rules.callback_timing**: `next business day` → `callback within 2 hours`
- ✏️ **business_hours.days**: `Monday to Friday` → `Monday through Friday`
- ✏️ **business_hours.timezone**: `None` → `MOUNTAIN`
- ✏️ **business_hours.start_time**: `None` → `7:30 AM`
- ✏️ **business_hours.confirmed**: `False` → `True`
- ✏️ **business_hours.end_time**: `None` → `5:00 PM`
- ✏️ **services_supported**: `['Electrical Service', 'Inspections', 'Repairs', 'Quotes/Estimates']` → `['Electrical Service', 'Inspections', 'Maintenance', 'Quotes/Estimates']`
- ✏️ **integration_constraints**: `['[CLIENT]: We use ServiceTrade for job management', "don't have that number on me right now"]` → `['[ONBOARDING REP]: What about ServiceTrade — any constraints', 'no answer within 45 seconds, try the backup line: 403-555-0193', 'do NOT create jobs in ServiceTrade automatically', 'no answer, apologize to caller and tell them someone will call back within 2 hours for emergencies, next business day for non-emergency']`
- ✏️ **questions_or_unknowns**: `['Missing or unconfirmed: business_hours.start_time', 'Missing or unconfirmed: business_hours.timezone', 'Missing or unconfirmed: emergency_routing_rules.primary_number', 'Missing or unconfirmed: emergency_routing_rules.transfer_timeout_seconds', 'Missing or unconfirmed: office_address']` → `[]`