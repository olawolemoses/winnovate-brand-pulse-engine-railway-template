# Winnovate Brand Pulse Engine

Brand Pulse is a closed-loop brand operations system built on top of the OpenClaw Railway template. It turns recent Google reviews into two business outputs:

- `Praise` for marketing, published into a live embeddable widget
- `Friction` for operations, dispatched into Trello as trackable work

This repo contains the full runtime:

- a Railway-hosted Express control plane
- an OpenClaw-derived workspace with custom Brand Pulse skills and tools
- a Streamlit HITL dashboard
- Notion-backed persistence for brand memory and approval queues
- SQLite-backed job tracking for audit progress and polling

The current production flow runs the audit pipeline inline inside the Express backend, while keeping the OpenClaw workspace and setup model for tool definitions, operational compatibility, and chat-channel integration.

## What This Repo Does

From a developer perspective, the system works like this:

1. A user starts an audit from Telegram or the Streamlit dashboard.
2. The Express server receives the request and creates a persisted audit job.
3. The backend fetches Google Places reviews and categorizes them into `Praise` or `Friction`.
4. The system writes the resulting items to Notion for long-term storage and approval.
5. A human approves the items in Streamlit.
6. Approved praise becomes `Live` and is exposed through an iframe widget.
7. Approved friction is dispatched into Trello and marked as sent.

## Architecture

Core runtime pieces:

- `src/server.js`
  Express control layer, audit endpoints, widget endpoint, dispatch endpoint, SQLite job tracker, and OpenClaw wrapper runtime.

- `workspace/tools/google_places_tool.js`
  Google Places review fetch tool.

- `workspace/tools/notion_sync.js`
  Notion brand upsert and pulse-item sync tool.

- `workspace/tools/action_dispatcher.js`
  Final-mile dispatcher for approved items, including Trello card creation and Notion status updates.

- `workspace/skills/*.md`
  OpenClaw skill definitions for the Brand Pulse workflow.

- `streamlit/app.py`
  Human-in-the-loop dashboard for running audits, reviewing items, approving outputs, and generating the marketing embed.

- `streamlit/utils.py`
  Dashboard helpers for Google Places search, Notion queries, and item retrieval.

### Runtime Data Stores

- `Notion`
  Long-term system of record for the Brand Registry and Pulse Actions database.

- `SQLite`
  Real-time job tracking for audit progress and status polling.

- `Railway Persistent Volume`
  Preserves `/data` so state survives redeploys.

## Repository Layout

```text
.
├── assets/                    # Submission/demo images
├── src/
│   ├── public/                # Setup UI, loading UI, TUI UI, logs UI
│   └── server.js              # Main runtime server
├── streamlit/
│   ├── app.py                 # Brand Pulse Console
│   ├── utils.py               # Streamlit helpers
│   └── requirements.txt       # Dashboard Python dependencies
├── workspace/
│   ├── skills/
│   │   ├── brand_pulse.md
│   │   ├── fetch_brand_pulse.md
│   │   ├── brand_pulse_categorizer.md
│   │   ├── sync_to_notion.md
│   │   └── execute_actions.md
│   └── tools/
│       ├── google_places_tool.js
│       ├── notion_sync.js
│       ├── action_dispatcher.js
│       └── resolve_notion_data_sources.js
├── Dockerfile
├── entrypoint.sh
├── railway.toml
├── package.json
└── README.md
```

## Stack

### Backend

- Node.js 22+
- Express
- `@googlemaps/google-maps-services-js`
- `@notionhq/client`
- SQLite via `node:sqlite`

### Dashboard

- Streamlit
- `notion-client==2.7.0`
- `httpx`
- `googlemaps`

### External Services

- Google Places API
- Notion
- Trello
- Railway
- Telegram Bot API

## Environment Variables

### Core Runtime

| Variable | Required | Purpose |
|---|---:|---|
| `PORT` | Yes | Express server port, defaults to `8080` |
| `SETUP_PASSWORD` | Yes | Password for the `/setup` UI |
| `OPENCLAW_STATE_DIR` | No | Defaults to `/data/.openclaw` in deployment |
| `OPENCLAW_WORKSPACE_DIR` | No | Defaults to `/data/workspace` in deployment |

### Brand Pulse Integrations

| Variable | Required | Purpose |
|---|---:|---|
| `Maps_API_KEY` | Yes | Google Places API access |
| `NOTION_TOKEN` | Yes | Notion integration token |
| `NOTION_BRAND_DB_ID` | Yes | Notion Brand Registry database id |
| `NOTION_PULSE_DB_ID` | Yes | Notion Pulse Actions database id |

### Trello Dispatch

| Variable | Required | Purpose |
|---|---:|---|
| `TRELLO_KEY` | Required for friction dispatch | Trello API key |
| `TRELLO_TOKEN` | Required for friction dispatch | Trello API token |
| `TRELLO_LIST_ID` | Required for friction dispatch | Trello list to create cards in |

### Dashboard / Public URLs

| Variable | Required | Purpose |
|---|---:|---|
| `RAILWAY_PUBLIC_URL` | Recommended | Used by Streamlit to build public audit, dispatch, and widget URLs |
| `OPENCLAW_WEBHOOK_URL` | Optional | Overrides the default audit trigger endpoint |

### Optional OpenClaw / TUI Runtime

| Variable | Required | Purpose |
|---|---:|---|
| `ENABLE_WEB_TUI` | No | Enables `/tui` |
| `TUI_IDLE_TIMEOUT_MS` | No | TUI idle timeout |
| `TUI_MAX_SESSION_MS` | No | Maximum TUI session duration |

## Deploying on Railway

This repo was adapted from the Railway OpenClaw template and keeps that deployment model.

### Expected Railway Shape

- Dockerfile build
- public service on port `8080`
- persistent volume mounted at `/data`
- healthcheck on `/setup/healthz`

`railway.toml` currently uses:

```toml
[build]
builder = "dockerfile"

[deploy]
healthcheckPath = "/setup/healthz"
healthcheckTimeout = 300
restartPolicyType = "on_failure"

[variables]
PORT = "8080"
```

### Deployment Steps

1. Fork this repo.
2. Create a Railway project from the repo.
3. Attach a persistent volume at `/data`.
4. Set the required environment variables.
5. Deploy.
6. Open `/setup` and complete OpenClaw onboarding.
7. Connect Telegram if you want chat-triggered audits.

### Important Setup Behavior

- The repo syncs workspace content from `/app/workspace` into `/data/workspace` on startup.
- Runtime state is preserved in `/data`, not `/app`.
- The setup page remains the operational entry point for the OpenClaw runtime.

## Running the Streamlit Dashboard

The dashboard can be deployed separately or run locally.

### Required Dashboard Secrets

| Secret | Purpose |
|---|---|
| `NOTION_TOKEN` | Notion access |
| `NOTION_BRAND_DB_ID` | Brand Registry database |
| `NOTION_PULSE_DB_ID` | Pulse Actions database |
| `Maps_API_KEY` | Google Places autocomplete/search |
| `RAILWAY_PUBLIC_URL` | Public URL of the Railway backend |
| `OPENCLAW_WEBHOOK_URL` | Optional override for audit trigger |

### Local Run

```bash
cd streamlit
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Local Development

### Node Runtime

```bash
pnpm install
pnpm run dev
```

### Docker

```bash
docker build -t winnovate-brand-pulse .

docker run --rm -p 8080:8080 \
  -e PORT=8080 \
  -e SETUP_PASSWORD=test \
  -e OPENCLAW_STATE_DIR=/data/.openclaw \
  -e OPENCLAW_WORKSPACE_DIR=/data/workspace \
  -v $(pwd)/.tmpdata:/data \
  winnovate-brand-pulse
```

## HTTP Endpoints

### Audit

- `POST /api/pulse-audit`
  Starts a new audit job.

Request:

```json
{
  "place_id": "PLACE_ID",
  "place_name": "Business Name"
}
```

- `GET /api/pulse-audit/:jobId`
  Returns the current audit status and event trail.

### Dispatch

- `POST /api/pulse-dispatch`
  Dispatches an approved item.

Request:

```json
{
  "item_id": "notion-page-id",
  "brand_id": "notion-brand-page-id",
  "content": "Fix slow service during lunch rush",
  "type": "Friction"
}
```

### Widget

- `GET /widget/:brandId`
  Returns the standalone iframe widget document for live praise items.

## Brand Pulse Workflow

### Phase 1: Review Fetch

- Source: Google Places API
- Tool: `workspace/tools/google_places_tool.js`
- Output: recent review JSON

### Phase 2: Categorization

- Skill: `workspace/skills/brand_pulse_categorizer.md`
- Output:
  - `praise_candidates`
  - `friction_alerts`
  - `punchy_quote`
  - `trello_action_item`

### Phase 3: Persistence

- Tool: `workspace/tools/notion_sync.js`
- Skill: `workspace/skills/sync_to_notion.md`
- Effect:
  - upsert brand
  - create pulse items in Notion
  - set initial status to `Pending`

### Phase 4: Approval and Final Action

- Dashboard approval happens in Streamlit
- Praise:
  - becomes `Live`
  - appears in the iframe widget
- Friction:
  - becomes `Sent to Trello`
  - gets a Trello card via `action_dispatcher.js`

## Notion Model

### Brand Registry

Stores:

- canonical brand name
- Google Place ID
- relation anchor for downstream pulse items

### Pulse Actions Database

Stores:

- content
- type (`Praise` or `Friction`)
- status (`Pending`, `Live`, `Sent to Trello`)
- brand relation
- rating
- author
- original review text
- Trello ticket link when dispatched

## Widget Behavior

The marketing widget is served as a full HTML document and intended to be embedded through an iframe.

Characteristics:

- one review card at a time
- 5-second auto-rotation
- dot indicators
- isolated CSS and JS
- no styling conflicts with host sites

This is the intended embed shape:

```html
<iframe
  src="https://your-backend.example.com/widget/BRAND_PAGE_ID"
  width="100%"
  height="320"
  style="border:0;border-radius:18px;overflow:hidden;background:transparent;"
  loading="lazy"
  referrerpolicy="no-referrer-when-downgrade"
></iframe>
```

## Telegram Usage

You can connect Telegram to the OpenClaw runtime and trigger audits conversationally through the bot.

Typical flow:

- send a request to audit a business
- backend starts the pipeline
- operator reviews results in Streamlit
- approved items are pushed to their final destinations

## Troubleshooting

### Streamlit shows no brands or pulse items

Check:

- `NOTION_TOKEN`
- `NOTION_BRAND_DB_ID`
- `NOTION_PULSE_DB_ID`
- Notion integration permissions on both databases

### Widget is blank

Check:

- the selected brand has at least one `Praise` item with status `Live`
- `RAILWAY_PUBLIC_URL` points to the correct backend

### Trello dispatch fails

Check:

- `TRELLO_KEY`
- `TRELLO_TOKEN`
- `TRELLO_LIST_ID`
- that the target list exists and the token has access

### Railway deploy works but state disappears

Check:

- persistent volume is mounted at `/data`
- `entrypoint.sh` is syncing workspace into `/data/workspace`

## Notes

- This repo started from the Railway OpenClaw template but has been adapted heavily for the Brand Pulse use case.
- `submission.md` contains the challenge-facing writeup.
- `README.md` is intentionally developer-oriented.
