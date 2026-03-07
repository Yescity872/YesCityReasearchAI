"""
itinerary_tool.py
─────────────────
Structured like the other project tools (BaseTool subclass).

Strategy:
  1. Group wishlist items by onModel type.
  2. Call the pre-built tools (place / shopping / activities) by cityName
     to get all relevant docs in one batch.
  3. Filter those results to only the _ids that appear in the wishlist.
  4. Keep ONLY essential slim fields → minimises LLM input tokens.

onModel routing:
  Place | HiddenGem | NearbySpot  →  place_search_tool
  Shop                            →  shopping_search_tool
  Activity                        →  activities_tool
  Accommodation / festivals / *   →  direct MongoDBQueryTool lookup by _id
"""

from typing import Optional, Dict, Any, List, Type
from pydantic import BaseModel, Field, ConfigDict
from langchain_core.tools import BaseTool
from bson import ObjectId
import time

from database.mongodb_client import mongodb_client
from tools.base_tool import MongoDBQueryTool
from tools.place_tool import place_search_tool
from tools.shopping_tool import shopping_search_tool
from tools.activities_tool import activities_tool


# ── Input schema ───────────────────────────────────────────────────────────────

class ItineraryToolInput(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    user_id:   str = Field(..., description="MongoDB ObjectId of the user")
    city_name: str = Field(..., description="City to filter wishlist items by")


# ── Slim field sets (only what the LLM needs to plan an itinerary) ─────────────

_PLACE_FIELDS    = ("_id", "places", "hiddenGem", "category", "description",
                    "address", "openDay", "openTime", "lat", "lon", "fee", "type")
_SHOPPING_FIELDS = ("_id", "shops", "famousFor", "priceRange",
                    "address", "openDay", "openTime", "lat", "lon")
_ACTIVITY_FIELDS = ("_id", "topActivities", "description",
                    "fee", "essentials")
_DIRECT_FIELDS   = ("_id", "name", "description", "address", "lat", "lon")

# onModel groupings
_PLACE_MODELS    = {"place", "hiddenGem", "hiddengem", "nearbyspot", "nearbySpot"}
_SHOPPING_MODELS = {"shop"}
_ACTIVITY_MODELS = {"activity"}

_DIRECT_COLLECTION_MAP = {
    "accommodation":  "accommodations",
    "accommodations": "accommodations",
    "festivals":      "festivals",
    "foods":          "foods",
    "transport":      "localtransports",
}


def _slim(doc: Dict, fields: tuple) -> Dict:
    """Return only the specified fields (non-None) from a doc."""
    return {f: doc[f] for f in fields if doc.get(f) is not None}


# ── Tool class ─────────────────────────────────────────────────────────────────

class ItineraryTool(BaseTool):
    name: str = "itinerary_tool"
    description: str = (
        "Fetches and resolves a user's wishlist items for a given city "
        "using the appropriate pre-built tools, returning slim data for "
        "itinerary planning."
    )
    args_schema: Type[BaseModel] = ItineraryToolInput

    def _run(
        self,
        user_id: str,
        city_name: str,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        start = time.time()

        # ── 1. Fetch user and filter wishlist by city ──────────────────────────
        users_col = mongodb_client.get_collection("users")
        user_doc  = users_col.find_one({"_id": ObjectId(user_id)})
        if not user_doc:
            raise ValueError(f"User '{user_id}' not found.")

        city_items = [
            item for item in user_doc.get("wishlist", [])
            if item.get("cityName", "").lower() == city_name.lower()
        ]
        if not city_items:
            print(f"   ⚠️  No wishlist items found for {city_name}")
            return []

        # ── 2. Bucket parentRef _ids by onModel type ───────────────────────────
        place_ids    : Dict[str, Dict] = {}   # parentId → wishlist meta
        shopping_ids : Dict[str, Dict] = {}
        activity_ids : Dict[str, Dict] = {}
        direct_items : List[Dict]      = []   # items for fallback direct lookup

        for item in city_items:
            on_model   = item.get("onModel", "")
            on_lower   = on_model.lower()
            parent_ref = item.get("parentRef", {})
            parent_id  = (
                parent_ref.get("$oid", str(parent_ref))
                if isinstance(parent_ref, dict)
                else str(parent_ref)
            )
            meta = {
                "_wishlistId": str(item.get("_id", "")),
                "_onModel":    on_model,
                "_cityName":   item.get("cityName", city_name),
                "_parentId":   parent_id,
            }
            if on_lower in _PLACE_MODELS:
                place_ids[parent_id] = meta
            elif on_lower in _SHOPPING_MODELS:
                shopping_ids[parent_id] = meta
            elif on_lower in _ACTIVITY_MODELS:
                activity_ids[parent_id] = meta
            else:
                direct_items.append({"meta": meta, "on_lower": on_lower, "parent_id": parent_id})

        wishlist: List[Dict[str, Any]] = []

        # ── 3a. Place / HiddenGem / NearbySpot → place_search_tool ────────────
        if place_ids:
            print(f"   🏛️  place_search_tool → fetching for {city_name}")
            all_places = place_search_tool._run(cityName=city_name, maxResults=200)
            for doc in all_places:
                if doc.get("_id") in place_ids:
                    meta = place_ids[doc["_id"]]
                    entry = _slim(doc, _PLACE_FIELDS)
                    entry.update(meta)
                    wishlist.append(entry)

        # ── 3b. Shop → shopping_search_tool ───────────────────────────────────
        if shopping_ids:
            print(f"   🛍️  shopping_search_tool → fetching for {city_name}")
            all_shops = shopping_search_tool._run(cityName=city_name, maxResults=200)
            for doc in all_shops:
                if doc.get("_id") in shopping_ids:
                    meta = shopping_ids[doc["_id"]]
                    entry = _slim(doc, _SHOPPING_FIELDS)
                    entry.update(meta)
                    wishlist.append(entry)

        # ── 3c. Activity → activities_tool ────────────────────────────────────
        if activity_ids:
            print(f"   🎯  activities_tool → fetching for {city_name}")
            all_activities = activities_tool._run(cityName=city_name, maxResults=200)
            for doc in all_activities:
                if doc.get("_id") in activity_ids:
                    meta = activity_ids[doc["_id"]]
                    entry = _slim(doc, _ACTIVITY_FIELDS)
                    entry.update(meta)
                    wishlist.append(entry)

        # ── 3d. Direct fallback (Accommodation, festivals, etc.) ───────────────
        for item_info in direct_items:
            meta      = item_info["meta"]
            on_lower  = item_info["on_lower"]
            parent_id = item_info["parent_id"]
            col = _DIRECT_COLLECTION_MAP.get(on_lower, on_lower + "s")
            print(f"   📦  direct lookup → {col} id={parent_id}")
            tool    = MongoDBQueryTool(collection_name=col)
            results = tool._run(
                query_filter={"_id": ObjectId(parent_id)},
                limit=1,
            )
            if results:
                entry = _slim(results[0], _DIRECT_FIELDS)
                entry.update(meta)
                wishlist.append(entry)

        print(f"   ✅ {len(wishlist)}/{len(city_items)} items resolved | "
              f"{time.time() - start:.2f}s")
        print(f"   🗂️  Wishlist items: {wishlist}")
        return wishlist


# Global instance
itinerary_tool = ItineraryTool()
