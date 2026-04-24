"""Shared utilities for the Winnovate Brand Pulse dashboard."""

import os
import logging
import googlemaps
import httpx
from notion_client import Client as NotionClient
from notion_client.errors import APIResponseError

# --- Clients (lazy init) ---
_gmaps = None
_notion = None
logger = logging.getLogger(__name__)


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


def get_notion_token():
    token = os.getenv("NOTION_TOKEN")
    if not token:
        raise RuntimeError("Missing NOTION_TOKEN")
    return token


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


def _query_notion_collection(notion, collection_id: str, **kwargs):
    """Query a Notion data source on newer SDKs, or a database on older ones."""
    if hasattr(notion, "data_sources") and hasattr(notion.data_sources, "query"):
        try:
            return notion.data_sources.query(data_source_id=collection_id, **kwargs)
        except APIResponseError as error:
            logger.warning(
                "data_sources.query failed for %s with code=%s; retrying as database",
                collection_id,
                getattr(error, "code", "unknown"),
            )
            if getattr(error, "status", None) != 404:
                raise
    if hasattr(notion, "databases") and hasattr(notion.databases, "query"):
        return notion.databases.query(database_id=collection_id, **kwargs)
    logger.warning(
        "SDK query methods unavailable for %s; falling back to raw HTTP databases/query",
        collection_id,
    )
    return _query_notion_database_http(collection_id, **kwargs)


def _query_notion_database_http(database_id: str, **kwargs):
    token = get_notion_token()
    payload = {key: value for key, value in kwargs.items() if value is not None}
    response = httpx.post(
        f"https://api.notion.com/v1/databases/{database_id}/query",
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=20.0,
    )
    if response.status_code >= 400:
        logger.warning(
            "raw HTTP database query failed for %s with status=%s body=%s",
            database_id,
            response.status_code,
            response.text,
        )
    response.raise_for_status()
    return response.json()


def fetch_all_brands():
    """Return list of {page_id, name, place_id} from Brand Registry."""
    notion = get_notion()
    db_id = get_brand_db_id()
    if not db_id:
        return []

    results = _query_notion_collection(notion, db_id, page_size=100)
    brands = []
    for page in results.get("results", []):
        props = page.get("properties", {})
        name = ""
        if "Name" in props and props["Name"].get("title"):
            name = props["Name"]["title"][0]["text"]["content"]
        place_id = ""
        if "Place ID" in props and props["Place ID"].get("rich_text"):
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

    results = _query_notion_collection(
        notion,
        db_id,
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
            "rating": _number(props, ["Review Rating", "Rating"]),
            "review_text": _rich_text_any(props, ["Original Review", "Review Text"]),
            "brand_relation": _relation_id(props, ["Brand Registry", "Brand"]),
        })
    if status_filter:
        items = [item for item in items if item["status"] == status_filter]
    return sorted(items, key=lambda item: item["content"], reverse=True)


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


def _rich_text_any(props, keys):
    for key in keys:
        value = _rich_text(props, key)
        if value:
            return value
    return ""


def _select(props, key):
    if key not in props:
        return ""
    sel = props[key].get("select")
    return sel["name"] if sel else ""


def _number(props, keys):
    for key in keys:
        if key in props:
            return props[key].get("number")
    return None


def _relation_id(props, keys):
    for key in keys:
        relation = props.get(key, {}).get("relation") or []
        if relation:
            return relation[0].get("id")
    return None
