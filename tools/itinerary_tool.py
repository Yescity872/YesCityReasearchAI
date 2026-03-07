"""
itinerary_tool.py
─────────────────
Fetches wishlist items for a given user + city from MongoDB, then resolves
each item by calling the appropriate existing tool (place, shopping, activities).

onModel routing:
  Place | HiddenGem | NearbySpot  →  place_tool  (collections: placestovisits, hiddengems, nearbytouristspots)
  Shop                            →  shopping_tool (collection: shoppings)
  Activity                        →  activities_tool (collection: activities)
  Accommodation / festivals / *   →  direct MongoDB lookup via base_tool
"""

from typing import Dict, Any, List, Optional
from bson import ObjectId
from database.mongodb_client import mongodb_client
from tools.base_tool import MongoDBQueryTool


# ── Collection map for onModels not handled by specialised tools ───────────────
_DIRECT_COLLECTION_MAP: Dict[str, str] = {
    "accommodation":  "accommodations",
    "accommodations": "accommodations",
    "festivals":      "festivals",
    "foods":          "foods",
    "transport":      "localtransports",
}

# ── onModel groups ──────────────────────────────────────────────────────────────
_PLACE_MODELS     = {"place", "hiddenGem", "hiddengem", "nearbyspot", "nearbySpot"}
_SHOPPING_MODELS  = {"shop"}
_ACTIVITY_MODELS  = {"activity"}


def _fetch_by_id(collection_name: str, doc_id: str) -> Optional[Dict[str, Any]]:
    """Direct single-document lookup by _id."""
    tool = MongoDBQueryTool(collection_name=collection_name)
    results = tool._run(query_filter={"_id": ObjectId(doc_id)}, limit=1)
    return results[0] if results else None


def _resolve_place(parent_id: str) -> Optional[Dict[str, Any]]:
    """Search across placestovisits, hiddengems, nearbytouristspots by _id."""
    for collection in ("placestovisits", "hiddengems", "nearbytouristspots"):
        doc = _fetch_by_id(collection, parent_id)
        if doc:
            doc["_resolvedFrom"] = collection
            return doc
    return None


def _resolve_shopping(parent_id: str) -> Optional[Dict[str, Any]]:
    doc = _fetch_by_id("shoppings", parent_id)
    if doc:
        doc["_resolvedFrom"] = "shoppings"
    return doc


def _resolve_activity(parent_id: str) -> Optional[Dict[str, Any]]:
    doc = _fetch_by_id("activities", parent_id)
    if doc:
        doc["_resolvedFrom"] = "activities"
    return doc


def _resolve_direct(on_model_lower: str, parent_id: str) -> Optional[Dict[str, Any]]:
    """Fallback: look up in the collection mapped from onModel."""
    collection = _DIRECT_COLLECTION_MAP.get(on_model_lower, on_model_lower + "s")
    doc = _fetch_by_id(collection, parent_id)
    if doc:
        doc["_resolvedFrom"] = collection
    return doc


# ── Public API ─────────────────────────────────────────────────────────────────

def fetch_wishlist_items(user_id: str, city_name: str) -> List[Dict[str, Any]]:
    """
    Load the user document, filter wishlist by city_name, then resolve
    every item to its full MongoDB document using the correct tool/collection.

    Returns a list of enriched dicts ready to be passed to the LLM.
    """
    # 1. Fetch user
    users_col = mongodb_client.get_collection("users")
    user_doc  = users_col.find_one({"_id": ObjectId(user_id)})
    if not user_doc:
        raise ValueError(f"User '{user_id}' not found.")

    raw_wishlist: List[Dict] = user_doc.get("wishlist", [])

    # 2. Filter by city (case-insensitive)
    city_items = [
        item for item in raw_wishlist
        if item.get("cityName", "").lower() == city_name.lower()
    ]

    if not city_items:
        return []

    # 3. Resolve each item
    enriched: List[Dict[str, Any]] = []
    for item in city_items:
        on_model   = item.get("onModel", "")
        on_lower   = on_model.lower()
        parent_ref = item.get("parentRef")
        wishlist_id = str(item.get("_id", ""))

        if not parent_ref:
            continue

        parent_id = str(parent_ref) if not isinstance(parent_ref, str) else parent_ref
        # parentRef may come as {"$oid": "..."} dict from the schema serialisation
        if isinstance(parent_ref, dict):
            parent_id = parent_ref.get("$oid", str(parent_ref))

        print(f"   🔎 Resolving onModel={on_model} id={parent_id}")

        resolved: Optional[Dict[str, Any]] = None

        if on_lower in _PLACE_MODELS:
            resolved = _resolve_place(parent_id)
        elif on_lower in _SHOPPING_MODELS:
            resolved = _resolve_shopping(parent_id)
        elif on_lower in _ACTIVITY_MODELS:
            resolved = _resolve_activity(parent_id)
        else:
            resolved = _resolve_direct(on_lower, parent_id)

        if resolved:
            resolved["_wishlistId"] = wishlist_id
            resolved["_onModel"]    = on_model
            resolved["_cityName"]   = item.get("cityName", city_name)
            enriched.append(resolved)
        else:
            print(f"   ⚠️  Could not resolve {on_model} id={parent_id}")

    print(f"   ✅ Resolved {len(enriched)}/{len(city_items)} wishlist items for {city_name}")
    return enriched
