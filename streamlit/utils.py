"""Shared utilities for the Winnovate Brand Pulse dashboard."""

import os
import googlemaps
from notion_client import Client as NotionClient

# --- Clients (lazy init) ---
_gmaps = None
_notion = None


def get_gmaps():
    global _gmaps
    if _gmaps is None:
        key = os.getenv("Maps_API_KEY")
        if not key:
            raise RuntimeError("Missing Maps_API_KEY")
        _gmaps = googlemaps.Client(key=key)
    return _gmaps


def get_notion():
    global _notion
    if _notion is None:
        token = os.getenv("NOTION_TOKEN")
        if not token:
            raise RuntimeError("Missing NOTION_TOKEN")
        _notion = NotionClient(auth=token)
    return _notion


# --- Google Places ---
def search_places(query: str, max_results: int = 6):
    """Text search for places. Returns list of {place_id, name, address}."""
    gmaps = get_gmaps()
    results = gmaps.places(query=query, type="establishment")
    candidates = results.get("results", [])
    return [
        {
            "place_id": p["place_id"],
            "name": p.get("name", ""),
            "address": p.get("formatted_address", ""),
        }
        for p in candidates[:max_results]
    ]


# --- Notion ---
def get_brand_db_id():
    return os.getenv("NOTION_BRAND_DB_ID", "")


def get_pulse_db_id():
    return os.getenv("NOTION_PULSE_DB_ID", "")


def fetch_all_brands():
    """Return list of {page_id, name, place_id} from Brand Registry."""
    notion = get_notion()
    db_id = get_brand_db_id()
    if not db_id:
        return []

    results = notion.databases.query(database_id=db_id, page_size=100)
    brands = []
    for page in results.get("results", []):
        props = page.get("properties", {})
        name = ""
        if "Name" in props and props["Name"]["title"]:
            name = props["Name"]["title"][0]["text"]["content"]
        place_id = ""
        if "Place ID" in props and props["Place ID"]["rich_text"]:
            place_id = props["Place ID"]["rich_text"][0]["text"]["content"]
        brands.append({
            "page_id": page["id"],
            "name": name,
            "place_id": place_id,
        })
    return brands


def fetch_pulse_items(status_filter: str = "Pending", page_size: int = 50):
    """Fetch pulse items, optionally filtered by status."""
    notion = get_notion()
    db_id = get_pulse_db_id()
    if not db_id:
        return []

    filter_params = None
    if status_filter:
        filter_params = {
            "property": "Status",
            "select": {"equals": status_filter},
        }

    results = notion.databases.query(
        database_id=db_id,
        filter=filter_params,
        sorts=[{"property": "Content", "direction": "descending"}],
        page_size=page_size,
    )
    items = []
    for page in results.get("results", []):
        props = page.get("properties", {})
        items.append({
            "page_id": page["id"],
            "content": _rich_text(props, "Content"),
            "type": _select(props, "Type"),
            "status": _select(props, "Status"),
            "author": _rich_text(props, "Author"),
            "rating": props.get("Review Rating", {}).get("number"),
            "review_text": _rich_text(props, "Original Review"),
            "brand_relation": props.get("Brand Registry", {}).get("relation", [{}])[0].get("id") if props.get("Brand Registry", {}).get("relation") else None,
        })
    return items


def update_pulse_status(page_id: str, new_status: str):
    """Set a pulse item's status to Live or Pending."""
    notion = get_notion()
    notion.pages.update(
        page_id=page_id,
        properties={
            "Status": {"select": {"name": new_status}},
        },
    )


# --- Helpers ---
def _rich_text(props, key):
    if key not in props:
        return ""
    arr = props[key].get("rich_text") or props[key].get("title") or []
    return arr[0]["text"]["content"] if arr else ""


def _select(props, key):
    if key not in props:
        return ""
    sel = props[key].get("select")
    return sel["name"] if sel else ""
