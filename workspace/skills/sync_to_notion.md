# Sync To Notion

## Role
Persistence Layer for Winnovate Brand Pulse.

## Purpose
Persist categorized insights into the permanent Notion record using the Brand Registry and Pulse Actions databases.

## Tool
- Script: `workspace/tools/notion_sync.js`
- Runtime: Node.js
- Dependency: `@notionhq/client`
- Required environment variables: `NOTION_TOKEN`, `NOTION_BRAND_DB_ID`, `NOTION_PULSE_DB_ID`

## Workflow
1. Execute `upsertBrand(placeId, name)` first to secure the brand anchor in the Brand Registry.
2. Execute `syncPulseItems(categorizedData, brandPageId)` second to upload all categorized items into the Pulse Actions database.
3. Report completion to the user with this exact summary format:
   `Staged X praise items and Y friction alerts in the Pulse Console.`

## Input
Accept the full Phase 2 categorized JSON payload.

Expected input shape:
```json
{
  "ok": true,
  "place_id": "...",
  "place_name": "Acme Cafe",
  "praise_candidates": [
    {
      "author": "Ada",
      "rating": 5,
      "text": "Amazing service and super fast turnaround.",
      "punchy_quote": "Amazing service and super fast turnaround"
    }
  ],
  "friction_alerts": [
    {
      "author": "Bola",
      "rating": 2,
      "text": "Service was slow during lunch.",
      "trello_action_item": "Fix slow service reported during lunch rush"
    }
  ]
}
```

## Property Mapping
Brand Registry database:
- `Name`: place name
- `Place ID`: Google Place ID

Pulse Actions database:
- `Content`: generated `punchy_quote` or `trello_action_item`
- `Type`: `Praise` or `Friction`
- `Status`: always `Pending`
- `Brand Registry`: relation to the Brand Registry page
- `Review Rating`: numeric rating from review
- `Author`: review author
- `Original Review`: original review text

## Invocation
```bash
node workspace/tools/notion_sync.js --data '{"ok":true,"place_id":"abc123","place_name":"Acme Cafe","praise_candidates":[],"friction_alerts":[]}'
```

## Output Contract
Return compact JSON only.

Success shape:
```json
{
  "ok": true,
  "brand_page_id": "...",
  "place_id": "abc123",
  "place_name": "Acme Cafe",
  "praise_count": 1,
  "friction_count": 1,
  "page_ids": ["...", "..."],
  "summary": "Staged 1 praise items and 1 friction alerts in the Pulse Console."
}
```

Failure shape:
```json
{"ok":false,"error":"..."}
```

## Guardrails
- Always run brand upsert before syncing pulse items.
- Do not create pulse records without a valid brand relation.
- Do not overwrite founder-approved generated content.
- Keep `Status` defaulted to `Pending` during sync.
- Fail fast if Notion credentials or database IDs are missing.
