"""
Winnovate Brand Pulse Dashboard

Streamlit UI for:
- Searching Google Places and selecting a brand
- Triggering pulse audits via the OpenClaw agent webhook
- Viewing pending praise/friction items from Notion
- Approving items to move them Live and send to Trello
"""

import os
import json
import streamlit as st
import httpx
from utils import (
    search_places,
    fetch_all_brands,
    fetch_pulse_items,
    update_pulse_status,
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
        brand_options = {"No brand selected": None}
        for brand in brands:
            label = brand["name"] or brand["place_id"] or brand["page_id"]
            brand_options[label] = brand

        current_brand = next(
            (brand for brand in brands if brand["page_id"] == st.session_state.get("selected_brand_page_id")),
            None,
        )
        default_label = current_brand["name"] if current_brand and current_brand["name"] in brand_options else "No brand selected"
        selected_brand_label = st.selectbox(
            "Active brand context",
            options=list(brand_options.keys()),
            index=list(brand_options.keys()).index(default_label),
            key="brand_context_selector",
        )
        selected_brand = brand_options[selected_brand_label]
        if selected_brand:
            st.session_state["selected_brand_page_id"] = selected_brand["page_id"]
            st.session_state["selected_place_name"] = selected_brand["name"]
            st.session_state["selected_place_id"] = selected_brand["place_id"]
        else:
            st.session_state["selected_brand_page_id"] = None

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
        set_selected_brand(place_name, place_id, brands)

        st.json(
            {"name": place_name, "place_id": place_id},
            expanded=False,
        )

        st.caption(
            f"Viewing context: **{place_name}** (`{place_id[:16]}...`)"
        )

        if st.button("🚀 Run Pulse Audit Now", type="primary"):
            target_url = os.getenv("OPENCLAW_WEBHOOK_URL", "")
            if not target_url:
                railway_url = os.getenv("RAILWAY_PUBLIC_URL", "")
                if railway_url:
                    target_url = railway_url.rstrip("/") + "/api/pulse-audit"

            if target_url:
                with st.spinner("Triggering audit pipeline..."):
                    try:
                        resp = httpx.post(
                            target_url,
                            json={
                                "place_id": place_id,
                                "place_name": place_name,
                            },
                            timeout=30,
                        )
                        if resp.is_success:
                            st.success(
                                f"✅ Pulse audit triggered for **{place_name}**!\n\n"
                                "Check the Pending Review tab in a moment."
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
    if active_brand_name:
        st.caption(f"Viewing pending items for **{active_brand_name}**")
    else:
        st.caption("Select a brand to view pending items")

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
                            update_pulse_status(item["page_id"], "Live")
                            st.success("Approved! Now Live.")
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
                status_filter="Live",
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
