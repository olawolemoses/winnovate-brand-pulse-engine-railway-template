"""
Winnovate Brand Pulse Dashboard

Streamlit UI for:
- Searching Google Places and selecting a brand
- Triggering pulse audits via the OpenClaw agent webhook
- Viewing pending praise/friction items from Notion
- Approving items to move them Live and send to Trello
- Generating iframe marketing widgets for live praise
"""

import os
import json
import streamlit as st
import streamlit.components.v1 as components
import httpx
from utils import (
    search_places,
    fetch_all_brands,
    fetch_pulse_items,
)

st.set_page_config(
    page_title="Brand Pulse Console",
    page_icon="📊",
    layout="wide",
)


def set_selected_brand(place_name: str, place_id: str, brands: list[dict]):
    st.session_state["selected_place_name"] = place_name
    st.session_state["selected_place_id"] = place_id
    matched_brand = next((brand for brand in brands if brand.get("place_id") == place_id), None)
    st.session_state["selected_brand_page_id"] = matched_brand["page_id"] if matched_brand else None


if "selected_place_name" not in st.session_state:
    st.session_state["selected_place_name"] = None
if "selected_place_id" not in st.session_state:
    st.session_state["selected_place_id"] = None
if "selected_brand_page_id" not in st.session_state:
    st.session_state["selected_brand_page_id"] = None
if "search_results" not in st.session_state:
    st.session_state["search_results"] = []
if "active_audit_job" not in st.session_state:
    st.session_state["active_audit_job"] = None
if "audit_place_name" not in st.session_state:
    st.session_state["audit_place_name"] = None
if "audit_place_id" not in st.session_state:
    st.session_state["audit_place_id"] = None


def get_audit_target_url():
    target_url = os.getenv("OPENCLAW_WEBHOOK_URL", "")
    if not target_url:
        railway_url = os.getenv("RAILWAY_PUBLIC_URL", "")
        if railway_url:
            target_url = railway_url.rstrip("/") + "/api/pulse-audit"
    return target_url


def get_dispatch_target_url():
    audit_url = get_audit_target_url()
    if not audit_url:
        return ""
    return audit_url.rsplit("/api/pulse-audit", 1)[0] + "/api/pulse-dispatch"


def get_public_base_url():
    audit_url = get_audit_target_url()
    if audit_url and "/api/pulse-audit" in audit_url:
        return audit_url.rsplit("/api/pulse-audit", 1)[0].rstrip("/")
    return os.getenv("RAILWAY_PUBLIC_URL", "").rstrip("/")


def get_widget_url(brand_id: str):
    base_url = get_public_base_url()
    if not base_url or not brand_id:
        return ""
    return f"{base_url}/widget/{brand_id}"


def build_iframe_snippet(brand_id: str):
    widget_url = get_widget_url(brand_id)
    if not widget_url:
        return ""
    return (
        f'<iframe src="{widget_url}" width="100%" height="320" '
        'style="border:0;border-radius:18px;overflow:hidden;background:transparent;" loading="lazy" '
        'referrerpolicy="no-referrer-when-downgrade"></iframe>'
    )


def render_codepen_button(brand_id: str):
    iframe_snippet = build_iframe_snippet(brand_id)
    if not iframe_snippet:
        st.caption("Set `RAILWAY_PUBLIC_URL` or `OPENCLAW_WEBHOOK_URL` to generate a widget preview.")
        return

    codepen_payload = json.dumps(
        {
            "title": "Winnovate Pulse Widget Preview",
            "html": iframe_snippet,
            "css": "body{margin:0;padding:24px;background:#0f1117;font-family:Inter,system-ui,sans-serif;}",
        }
    )
    safe_payload = (
        codepen_payload.replace("&", "&amp;").replace("'", "&#39;")
    )
    components.html(
        f"""
        <form action="https://codepen.io/pen/define" method="POST" target="_blank">
          <input type="hidden" name="data" value='{safe_payload}' />
          <button type="submit" style="
            width:100%;
            min-height:42px;
            padding:0.72rem 1rem;
            border:none;
            border-radius:14px;
            background:linear-gradient(135deg,#2563eb,#111827);
            color:#ffffff;
            font:600 14px Inter, system-ui, sans-serif;
            cursor:pointer;
            box-shadow:0 12px 24px rgba(37,99,235,.22);
          ">↗ Preview in CodePen</button>
        </form>
        """,
        height=54,
    )


def render_widget_section(brand_id: str):
    widget_url = get_widget_url(brand_id)
    if not widget_url:
        st.caption("Set `RAILWAY_PUBLIC_URL` or `OPENCLAW_WEBHOOK_URL` to generate a widget preview.")
        return

    iframe_snippet = build_iframe_snippet(brand_id)

    st.markdown("### 🎨 Marketing Widget")
    with st.container(border=True):
        st.markdown("**Embed Kit**")
        st.caption("Clean iframe embed for landing pages, partner sites, and campaign pages.")

        components.html(
            f"""
            <div style="
              padding:14px;
              border-radius:22px;
              background:linear-gradient(180deg, rgba(37,99,235,0.10), rgba(255,255,255,0.03));
              border:1px solid rgba(148,163,184,0.20);
            ">
              <iframe
                src="{widget_url}"
                width="100%"
                height="320"
                loading="lazy"
                scrolling="no"
                style="
                  display:block;
                  border:0;
                  border-radius:18px;
                  overflow:hidden;
                  background:transparent;
                "
              ></iframe>
            </div>
            """,
            height=352,
        )

        action_a, action_b = st.columns(2)
        with action_a:
            st.link_button(
                "🔗 Open Widget",
                widget_url,
                type="secondary",
                use_container_width=True,
            )
        with action_b:
            render_codepen_button(brand_id)

        st.caption("Iframe Embed Snippet")
        st.code(iframe_snippet, language="html", line_numbers=False, wrap_lines=True)


def fetch_audit_job(job_id: str):
    target_url = get_audit_target_url()
    if not target_url:
        return None
    status_url = target_url.rstrip("/") + f"/{job_id}"
    response = httpx.get(status_url, timeout=15)
    response.raise_for_status()
    return response.json().get("job")

# ── Styling ──
st.markdown(
    """
<style>
    .praise-badge {
        background: #d4edda; color: #155724;
        padding: 2px 10px; border-radius: 12px;
        font-size: 0.8rem; font-weight: 600;
    }
    .friction-badge {
        background: #f8d7da; color: #721c24;
        padding: 2px 10px; border-radius: 12px;
        font-size: 0.8rem; font-weight: 600;
    }
    .pending-badge {
        background: #fff3cd; color: #856404;
        padding: 2px 10px; border-radius: 12px;
    }
    .live-badge {
        background: #cce5ff; color: #004085;
        padding: 2px 10px; border-radius: 12px;
    }
    .ops-callout {
        border: 1px solid rgba(96, 165, 250, 0.22);
        background:
            linear-gradient(135deg, rgba(30, 64, 175, 0.18), rgba(15, 23, 42, 0.22)),
            rgba(17, 24, 39, 0.82);
        border-radius: 22px;
        padding: 1rem 1.1rem;
        box-shadow: 0 18px 36px rgba(15, 23, 42, 0.18);
        margin: 0.35rem 0 1rem;
    }
    .ops-kicker {
        color: #93c5fd;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-size: 0.74rem;
        font-weight: 700;
        margin-bottom: 0.35rem;
    }
    .ops-title {
        color: #f8fafc;
        font-size: 1.2rem;
        font-weight: 700;
        margin: 0 0 0.3rem;
    }
    .ops-copy {
        color: #cbd5e1;
        font-size: 0.96rem;
        line-height: 1.5;
        margin: 0;
    }
    .stApp { max-width: 1200px; margin: 0 auto; }
</style>
""",
    unsafe_allow_html=True,
)

# ── Sidebar ──
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/brand.png", width=48)
    st.title("Brand Pulse")
    st.caption("Powered by Winnovate")

    # Check env vars
    notion_token = os.getenv("NOTION_TOKEN", "")
    maps_key = os.getenv("Maps_API_KEY", "")
    openclaw_webhook_url = os.getenv("OPENCLAW_WEBHOOK_URL", os.getenv("RAILWAY_PUBLIC_URL", "") + "/api/pulse-audit")

    if not notion_token:
        st.warning("⚠️ NOTION_TOKEN not set")
    if not maps_key:
        st.warning("⚠️ Maps_API_KEY not set")

    st.divider()
    st.subheader("Registered Brands")
    brands = fetch_all_brands()
    if brands:
        brand_by_id = {brand["page_id"]: brand for brand in brands}
        brand_option_ids = ["__none__", *brand_by_id.keys()]
        current_brand_id = st.session_state.get("selected_brand_page_id")
        default_brand_id = current_brand_id if current_brand_id in brand_by_id else "__none__"

        def format_brand_option(option_id: str):
            if option_id == "__none__":
                return "No brand selected"
            brand = brand_by_id[option_id]
            label = brand["name"] or brand["place_id"] or brand["page_id"]
            suffix = f" · {brand['place_id'][:10]}..." if brand.get("place_id") else ""
            return f"{label}{suffix}"

        selected_brand_id = st.selectbox(
            "Active brand context",
            options=brand_option_ids,
            index=brand_option_ids.index(default_brand_id),
            format_func=format_brand_option,
            key="brand_context_selector",
        )
        if selected_brand_id != "__none__":
            selected_brand = brand_by_id[selected_brand_id]
            st.session_state["selected_brand_page_id"] = selected_brand["page_id"]
            st.session_state["selected_place_name"] = selected_brand["name"]
            st.session_state["selected_place_id"] = selected_brand["place_id"]
        else:
            st.session_state["selected_brand_page_id"] = None
            st.session_state["selected_place_name"] = None
            st.session_state["selected_place_id"] = None

        for b in brands:
            st.caption(f"🏪 {b['name']}" + (f"  `{b['place_id'][:12]}...`" if b["place_id"] else ""))
    else:
        st.caption("No brands registered yet.")

# ── Main Layout ──
st.title("📊 Brand Pulse Console")
st.caption("Monitor brand health, review customer sentiment, and dispatch actions.")

# ── Tab 1: New Audit ──
tab_new, tab_pending, tab_approved = st.tabs(
    ["🔍 New Pulse Audit", "⏳ Pending Review", "✅ Approved / Live"]
)

with tab_new:
    st.subheader("Run a New Brand Pulse Audit")

    @st.fragment(run_every="2s")
    def render_audit_status():
        active_job = st.session_state.get("active_audit_job")
        if not active_job:
            return
        try:
            job = fetch_audit_job(active_job["job_id"])
        except Exception as exc:
            st.warning(f"Could not refresh audit status: {exc}")
            return
        if not job:
            return

        should_refresh_page = False
        if job.get("brand_page_id") and job.get("brand_page_id") != active_job.get("brand_page_id"):
            should_refresh_page = True
        st.session_state["active_audit_job"] = job
        if job.get("brand_page_id"):
            st.session_state["selected_brand_page_id"] = job["brand_page_id"]
        if job.get("status") in {"completed", "failed", "timed_out"} and job.get("status") != active_job.get("status"):
            should_refresh_page = True

        status_state = "running"
        if job["status"] == "completed":
            status_state = "complete"
        elif job["status"] in {"failed", "timed_out"}:
            status_state = "error"

        with st.status(
            f"Audit status: {job['current_stage'].replace('_', ' ').title()}",
            state=status_state,
            expanded=True,
        ):
            st.progress(max(0, min(int(job.get("progress", 0)), 100)))
            st.caption(
                f"Job `{job['job_id']}` for **{job['place_name']}** is `{job['status']}`."
            )
            if job.get("summary"):
                st.write(job["summary"])
            if job.get("error"):
                st.error(job["error"])
            events = job.get("events") or []
            if events:
                for event in events[-5:]:
                    st.caption(f"{event['created_at']} · {event['message']}")
        if should_refresh_page:
            st.rerun()

    render_audit_status()

    col1, col2 = st.columns([3, 1])
    with col1:
        place_query = st.text_input(
            "Search for a business",
            placeholder="e.g. Hard Rock Cafe Lagos, Tantalizers Allen...",
            key="place_search",
        )
    with col2:
        st.write("")  # vertical spacing
        st.write("")
        search_clicked = st.button("🔍 Search", type="primary", use_container_width=True)

    if place_query and len(place_query) >= 2:
        with st.spinner(f"Searching for '{place_query}'..."):
            st.session_state["search_results"] = search_places(place_query, max_results=8)
    elif not place_query:
        st.session_state["search_results"] = []

    candidates = st.session_state.get("search_results", [])
    if place_query and search_clicked:
        pass

    if place_query and candidates:
        st.success(f"Found {len(candidates)} result(s)")
        options = {f"{c['name']} — {c['address']}": c for c in candidates}
        selected_label = st.selectbox(
            "Select the correct location:",
            options=list(options.keys()),
            key="place_selector",
        )

        selected = options[selected_label]
        place_name = selected["name"]
        place_id = selected["place_id"]
        st.session_state["audit_place_name"] = place_name
        st.session_state["audit_place_id"] = place_id

        st.json(
            {"name": place_name, "place_id": place_id},
            expanded=False,
        )

        st.caption(
            f"Viewing context: **{place_name}** (`{place_id[:16]}...`)"
        )

        if st.button("🚀 Run Pulse Audit Now", type="primary"):
            target_url = get_audit_target_url()

            if target_url:
                with st.spinner("Triggering audit pipeline..."):
                    try:
                        set_selected_brand(place_name, place_id, brands)
                        resp = httpx.post(
                            target_url,
                            json={
                                "place_id": place_id,
                                "place_name": place_name,
                            },
                            timeout=30,
                        )
                        if resp.is_success:
                            payload = resp.json()
                            st.session_state["active_audit_job"] = {
                                "job_id": payload.get("job_id"),
                                "place_id": place_id,
                                "place_name": place_name,
                                "status": payload.get("status", "queued"),
                                "current_stage": payload.get("status", "queued"),
                                "progress": 0,
                                "events": [],
                            }
                            st.success(
                                f"✅ Pulse audit triggered for **{place_name}**."
                            )
                        else:
                            st.error(
                                f"Failed to trigger audit: {resp.status_code}"
                            )
                    except Exception as e:
                        st.error(f"Connection error: {e}")
            else:
                st.info(
                    "Set OPENCLAW_WEBHOOK_URL env var to enable one-click audits.\n\n"
                    "For now, ask the agent directly on Telegram."
                )
    elif place_query:
        st.warning("No results found. Try a different search term.")

# ── Tab 2: Pending Items ──
with tab_pending:
    st.subheader("⏳ Items Awaiting Approval")
    active_brand_name = st.session_state.get("selected_place_name")
    active_brand_page_id = st.session_state.get("selected_brand_page_id")
    trello_board_url = "https://trello.com/b/ldQuJBhF/brand-pulse-demo-board"
    if active_brand_name:
        st.caption(f"Viewing pending items for **{active_brand_name}**")
    else:
        st.caption("Select a brand to view pending items")

    with st.container(border=False):
        board_a, board_b = st.columns([1.05, 2.2], vertical_alignment="center")
        with board_a:
            st.link_button(
                "📋 Open Trello Board",
                trello_board_url,
                type="secondary",
                use_container_width=True,
            )
        with board_b:
            st.markdown(
                """
                <div class="ops-callout">
                  <div class="ops-kicker">Ops Board</div>
                  <div class="ops-title">Friction items flow into Trello</div>
                  <p class="ops-copy">Approve a friction alert here and it is dispatched to the board in a new tab. Trello blocks iframe embeds, so this stays as a direct launch action.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    pending_items = []
    if active_brand_page_id:
        with st.spinner("Loading pending pulse items..."):
            pending_items = fetch_pulse_items(
                status_filter="Pending",
                brand_page_id=active_brand_page_id,
            )

    if not active_brand_page_id:
        if active_brand_name:
            st.info(f"No staged items are available for **{active_brand_name}** yet. Run an audit first.")
        else:
            st.info("Choose a registered brand or run a new audit to create one.")
    elif not pending_items:
        st.info("No pending items for this brand.")
    else:
        st.caption(f"{len(pending_items)} item(s) pending review")

        for item in pending_items:
            badge = (
                "praise-badge"
                if item["type"] == "Praise"
                else "friction-badge"
            )
            label = f"🙌 {item['type']}" if item["type"] == "Praise" else f"🚨 {item['type']}"

            with st.container(border=True):
                cols = st.columns([5, 1, 1])
                with cols[0]:
                    st.markdown(f"**{item['content']}**")
                    if item["author"]:
                        st.caption(f"— {item['author']}" + (f" ★{item['rating']}" if item["rating"] else ""))
                    if item["review_text"]:
                        st.caption(f"_{item['review_text'][:120]}..._")
                with cols[1]:
                    st.markdown(
                        f"<span class='{badge}'>{label}</span>",
                        unsafe_allow_html=True,
                    )
                with cols[2]:
                    if st.button("✅ Approve", key=f"approve_{item['page_id']}"):
                        with st.spinner("Approving..."):
                            resp = httpx.post(
                                get_dispatch_target_url(),
                                json={
                                    "item_id": item["page_id"],
                                    "brand_id": item["brand_relation"],
                                    "content": item["content"],
                                    "type": item["type"],
                                },
                                timeout=30,
                            )
                            if resp.is_success:
                                payload = resp.json()
                                st.toast(payload.get("toast", "Approved"))
                            else:
                                error_message = "Dispatch failed"
                                try:
                                    error_message = resp.json().get("error", error_message)
                                except Exception:
                                    pass
                                st.error(error_message)
                                st.stop()
                            st.rerun()

# ── Tab 3: Live Items ──
with tab_approved:
    st.subheader("✅ Live / Approved Items")
    active_brand_name = st.session_state.get("selected_place_name")
    active_brand_page_id = st.session_state.get("selected_brand_page_id")
    if active_brand_name:
        st.caption(f"Viewing approved items for **{active_brand_name}**")
    else:
        st.caption("Select a brand to view approved items")

    live_items = []
    if active_brand_page_id:
        with st.spinner("Loading approved pulse items..."):
            live_items = fetch_pulse_items(
                status_filter=["Live", "Sent to Trello"],
                page_size=100,
                brand_page_id=active_brand_page_id,
            )

    if not active_brand_page_id:
        if active_brand_name:
            st.info(f"No approved items are available for **{active_brand_name}** yet.")
        else:
            st.info("Choose a registered brand to view approved items.")
    elif not live_items:
        st.info("No approved items for this brand yet.")
    else:
        praise_live_items = [item for item in live_items if item["type"] == "Praise" and item["status"] == "Live"]

        render_widget_section(active_brand_page_id)

        if not praise_live_items:
            st.caption("Approve at least one praise item to populate the widget.")

        st.divider()
        st.caption(f"{len(live_items)} item(s) approved and live")

        for item in live_items[:20]:  # show latest 20
            badge = "praise-badge" if item["type"] == "Praise" else "friction-badge"
            label = f"🙌 {item['type']}" if item["type"] == "Praise" else f"🚨 {item['type']}"

            with st.container(border=True):
                cols = st.columns([4, 1])
                with cols[0]:
                    st.markdown(f"**{item['content']}**")
                    if item["author"]:
                        st.caption(f"— {item['author']}")
                with cols[1]:
                    st.markdown(
                        f"<span class='{badge}'>{label}</span>",
                        unsafe_allow_html=True,
                    )
