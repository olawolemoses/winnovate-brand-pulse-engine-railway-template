# Fetch Brand Pulse

## Purpose
Use `workspace/tools/google_places_tool.js` to collect only the last 7 days of Google Places reviews for a known `place_id`. Treat the returned review set as the live Brand Pulse for that location.

## Tool
- Script: `workspace/tools/google_places_tool.js`
- Runtime: Node.js
- Dependency: `@googlemaps/google-maps-services-js`
- Required environment variable: `Maps_API_KEY`

## Invocation
```bash
node workspace/tools/google_places_tool.js <PLACE_ID> --max-results 5
```

## Output Contract
The tool prints compact JSON for LLM ingestion.

Success shape:
```json
{"ok":true,"place_id":"...","place_name":"...","review_count":2,"reviews":[{"author":"...","rating":5,"text":"...","relative_time":"2 days ago","timestamp":1713888000}]}
```

Failure shape:
```json
{"ok":false,"place_id":"...","error":"...","reviews":[]}
```

Each review contains:
- `author`
- `rating`
- `text`
- `relative_time`
- `timestamp`

## Agent Instructions
1. Supply a valid Google Places `place_id`.
2. Run the tool and parse the JSON directly.
3. If `ok` is `false`, stop and surface the error exactly.
4. If no reviews are returned, report that there is no usable Brand Pulse in the last 7 days.
5. Use the returned reviews as the evidence base for marketing proof points and operational follow-up.

## Brand Pulse Interpretation
- Repeated praise plus high ratings indicates strong verified social proof.
- Repeated complaints, lower ratings, or topic clusters indicate prioritized action areas.
- Review volume in the 7-day window indicates freshness and signal strength.
- `timestamp` is authoritative; `relative_time` is convenience text.

## Guardrails
- Do not claim coverage beyond the last 7 days.
- Do not invent sentiment not present in the review text.
- Do not treat missing reviews as positive sentiment.
- Keep summaries concise and evidence-based.
