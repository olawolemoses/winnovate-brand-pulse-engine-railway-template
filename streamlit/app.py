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

    if place_query and search_clicked:
        with st.spinner(f"Searching for '{place_query}'..."):
            candidates = search_places(place_query)

        if not candidates:
            st.warning("No results found. Try a different search term.")
        else:
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

            st.json(
                {"name": place_name, "place_id": place_id},
                expanded=False,
            )

            st.session_state["selected_place_name"] = place_name
            st.session_state["selected_place_id"] = place_id

            # Trigger audit via OpenClaw webhook
            if st.button("🚀 Run Pulse Audit Now", type="primary"):
                target_url = os.getenv("OPENCLAW_WEBHOOK_URL", "")
                # Fallback: guess Railway URL
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

    elif place_query and not search_clicked:
        # Live search as user types
        if len(place_query) >= 3:
            candidates = search_places(place_query)
            if candidates:
                options = {
                    f"{c['name']} — {c['address']}": c for c in candidates
                }
                selected_label = st.selectbox(
                    "Select the correct location:",
                    options=list(options.keys()),
                    key="live_selector",
                )
                selected = options[selected_label]
                st.session_state["selected_place_name"] = selected["name"]
                st.session_state["selected_place_id"] = selected["place_id"]
                st.caption(
                    f"Selected: **{selected['name']}** (`{selected['place_id'][:16]}...`)"
                )

# ── Tab 2: Pending Items ──
with tab_pending:
    st.subheader("⏳ Items Awaiting Approval")

    with st.spinner("Loading pending pulse items..."):
        pending_items = fetch_pulse_items(status_filter="Pending")

    if not pending_items:
        st.info("No pending items. Run a new pulse audit!")
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

    with st.spinner("Loading approved pulse items..."):
        live_items = fetch_pulse_items(status_filter="Live", page_size=100)

    if not live_items:
        st.info("No approved items yet. Approve some pending items first!")
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
