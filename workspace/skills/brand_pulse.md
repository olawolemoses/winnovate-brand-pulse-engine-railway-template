---
name: brand-pulse
description: Full pipeline brand pulse auditor for the Winnovate Brand Pulse Engine. Use when a user asks to run a pulse audit, check brand health, or review customer sentiment for a specific business or location. Orchestrates the complete 4-phase pipeline: fetch 7-day Google reviews → categorize into praise/friction → upsert Brand Registry → sync categorized items (Pending status) to Pulse Actions database. Single-command "Run a pulse audit for [business name or place ID]".
---

# Brand Pulse

## Role
Full-pipeline orchestrator for the Winnovate Brand Pulse Engine.

## Purpose
Take a single business name or Google Place ID and run the complete 4-phase brand pulse pipeline end-to-end:
1. **Fetch** — Get last 7 days of Google Places reviews
2. **Categorize** — Split into Praise and Friction with enriched content
3. **Upsert Brand** — Register or update the brand in the Notion Brand Registry
4. **Sync Pulse Items** — Write all items to the Pulse Actions database with Pending status

## Pipeline Steps

Follow this exact sequence. Never deviate.

### Phase 1: Fetch Reviews
- Tool: `node workspace/tools/google_places_tool.js <PLACE_ID> --max-results 5`
- If you only have a business name, look up the Place ID first (search the web or check memory)
- Parse the JSON output
- If `ok` is false, stop and report the error to the user

### Phase 2: Categorize & Enrich
- Read through every review from Phase 1
- Follow the categorization logic from `workspace/skills/brand_pulse_categorizer.md`:
  - Ratings 4-5 with positive text → `praise_candidates` with a `punchy_quote` (max 15 words)
  - Ratings 1-3 or negative text → `friction_alerts` with a `trello_action_item` (concrete, assignable)
  - When in doubt, prioritize operational risk → put it in friction
- Output: structured JSON with both arrays

### Phase 3: Upsert Brand + Sync to Notion
- Tool: `node workspace/tools/notion_sync.js --data '<FULL_PHASE2_JSON>'`
- This handles both brand upsert (finds or creates brand by Place ID) and pulse item sync
- All items get `Status: Pending` automatically

### Phase 4: Report
- Read the Notion sync output JSON
- Report to the user with this exact format:
  > **Brand Pulse: {place_name}** ✅  
  > Staged {N} praise items and {M} friction alerts in the Pulse Console.  
  > Check Notion → Pulse Actions database to review and approve.

## Single Command Mode
If the user provides a Place ID directly, skip Phase 1 search and jump straight into the pipeline.

## Requirements
- Environment: `NOTION_TOKEN`, `NOTION_BRAND_DB_ID`, `NOTION_PULSE_DB_ID`, `Maps_API_KEY`
- Dependencies: `@notionhq/client`, `@googlemaps/google-maps-services-js` (via package.json)
- All tools live in `workspace/tools/`

## Guardrails
- Never skip the categorize step — raw reviews go to Notion only after enrichment
- Never change `Status` from `Pending` during sync — that's the founder's call
- If any phase fails, report which phase and the error — don't proceed with partial data
- If no reviews in the last 7 days, report "No recent brand pulse data available for this location" — don't sync empty records
- Keep final report concise — the data lives in Notion, not in the chat
