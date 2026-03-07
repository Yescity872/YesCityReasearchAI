"""
itinerary_wrapper.py
────────────────────
Orchestrates the full itinerary generation pipeline:
  1. Classify budget + duration from the query
  2. Fetch + resolve wishlist items via itinerary_tool
  3. Call ChatGroq with all parameters (lat, lon, city, budget, duration, items)
  4. Return a structured JSON itinerary with _ids ordered by day/time slot
"""

import os
import json
import re
import time
from typing import Optional

from langchain_groq import ChatGroq
from dotenv import load_dotenv

from services.itinerary_classifier import itinerary_classifier
from tools.itinerary_tool import itinerary_tool

load_dotenv()


class ItineraryWrapper:
    def __init__(self):
        self.llm = ChatGroq(
            groq_api_key=os.getenv("GROQ_API_KEY"),
            model_name="llama-3.1-8b-instant",
            temperature=0.1,
            max_tokens=4096,
            model_kwargs={
                "top_p": 0.9,
                "frequency_penalty": 0.1,
                "presence_penalty": 0.1,
            },
        )

    # ── helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _clean(text: str) -> str:
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    # ── main ─────────────────────────────────────────────────────────────────

    def run_itinerary_flow(
        self,
        user_id: str,
        city: str,
        query: str,
        latitude: float,
        longitude: float,
    ) -> str:
        """
        Full pipeline. Returns a JSON string.
        """
        start = time.time()

        # ── Step 1: classify budget + duration ────────────────────────────────
        print("   📊 Classifying itinerary parameters...")
        classification = itinerary_classifier.classify(query)
        budget   = classification.budget
        duration = classification.duration

        # ── Step 2: fetch + resolve wishlist items via itinerary_tool ──────────
        print(f"   🗂️  Running itinerary_tool for {city}...")
        items = itinerary_tool._run(user_id=user_id, city_name=city)

        if not items:
            return json.dumps({
                "itinerary": [],
                "summary": f"No wishlist items found for {city}.",
                "tips": [],
                "budget": budget,
                "duration": duration,
            })

        # ── Step 3: build prompt ──────────────────────────────────────────────
        items_json = json.dumps(items, default=str, ensure_ascii=False, indent=2)

        system_msg = """You are an expert travel planner AI.

Your job is to create a day-wise itinerary using ONLY the places provided.

DISTANCE CALCULATION:
- Use the provided latitude/longitude of the user's current location and the lat/lon 
  fields of each place to estimate proximity.
- Schedule geographically closer places on the same day and group nearby ones in the 
  same time slot to minimise travel.

RULES:
1. Only use places from the provided wishlist — do NOT add external places.
2. For EACH time slot (Morning / Afternoon / Evening / Night), return ONLY the _id(s) 
   of places scheduled for that slot.
3. Respect budget: avoid expensive places if budget is "budget".
4. Spread places across the available days as evenly as possible.
5. ALWAYS respond with RAW JSON ONLY — no markdown, no code fences, no extra text.

OUTPUT FORMAT:
{
  "itinerary": [
    {
      "day": 1,
      "date_label": "Day 1",
      "slots": {
        "Morning":   [{"_id": "...", "name": "...", "category": "..."}],
        "Afternoon": [{"_id": "...", "name": "...", "category": "..."}],
        "Evening":   [{"_id": "...", "name": "...", "category": "..."}],
        "Night":     [{"_id": "...", "name": "...", "category": "..."}]
      }
    }
  ],
  "summary": "One-paragraph overview of the trip",
  "tips": ["Tip 1", "Tip 2", "Tip 3"],
  "budget": "budget|mid-range|luxury|not classified",
  "duration": "X days|not classified"
}"""

        user_msg = f"""Plan a trip with these details:

City: {city}
User Location: latitude={latitude}, longitude={longitude}
Budget: {budget}
Duration: {duration}
User Query: "{query}"

Wishlist Items (from MongoDB — use _id values exactly as given):
{items_json}

Generate the full day-wise itinerary JSON now."""

        # ── Step 4: call LLM ──────────────────────────────────────────────────
        print("   🤖 Generating itinerary via ChatGroq...")
        response = self.llm.invoke([
            {"role": "system", "content": system_msg},
            {"role": "user",   "content": user_msg},
        ])

        raw = response.content if hasattr(response, "content") else str(response)
        clean = self._clean(raw)

        # ── Step 5: validate JSON ─────────────────────────────────────────────
        try:
            result = json.loads(clean)
            # Inject classification fields if LLM omitted them
            result.setdefault("budget",   budget)
            result.setdefault("duration", duration)
            print(f"   ✅ Valid JSON itinerary generated")
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", clean, re.DOTALL)
            if match:
                try:
                    result = json.loads(match.group())
                    result.setdefault("budget",   budget)
                    result.setdefault("duration", duration)
                except Exception:
                    result = self._fallback(budget, duration, city)
            else:
                result = self._fallback(budget, duration, city)

        print(f"   ⏱️  Total itinerary time: {time.time() - start:.2f}s")
        return json.dumps(result, ensure_ascii=False)

    @staticmethod
    def _fallback(budget: str, duration: str, city: str) -> dict:
        return {
            "itinerary": [],
            "summary": f"Could not generate itinerary for {city}.",
            "tips": [],
            "budget": budget,
            "duration": duration,
            "error": "LLM returned invalid JSON",
        }


# Global instance
itinerary_wrapper = ItineraryWrapper()

# """
# itinerary_wrapper.py (Improved with OpenDay/OpenTime)
# ────────────────────
# Orchestrates the full itinerary generation pipeline with uniqueness enforcement,
# accommodation suggestions, and operating hours validation.
# """

# import os
# import json
# import re
# import time
# from typing import Optional, List, Dict, Any
# from collections import defaultdict
# from datetime import datetime, timedelta

# from langchain_groq import ChatGroq
# from dotenv import load_dotenv

# from services.itinerary_classifier import itinerary_classifier
# from tools.itinerary_tool import itinerary_tool

# load_dotenv()


# class ItineraryWrapper:
#     def __init__(self):
#         self.llm = ChatGroq(
#             groq_api_key=os.getenv("GROQ_API_KEY"),
#             model_name="llama-3.1-8b-instant",
#             temperature=0.1,
#             max_tokens=4096,
#             model_kwargs={
#                 "top_p": 0.9,
#                 "frequency_penalty": 0.2,  # Slightly increased to reduce repetition
#                 "presence_penalty": 0.2,    # Slightly increased to encourage new items
#             },
#         )

#     # ── helpers ──────────────────────────────────────────────────────────────

#     @staticmethod
#     def _clean(text: str) -> str:
#         text = text.strip()
#         if text.startswith("```json"):
#             text = text[7:]
#         elif text.startswith("```"):
#             text = text[3:]
#         if text.endswith("```"):
#             text = text[:-3]
#         return text.strip()

#     @staticmethod
#     def _group_items_by_type(items: List[Dict]) -> Dict[str, List[Dict]]:
#         """Group wishlist items by their model type for better context."""
#         grouped = defaultdict(list)
#         for item in items:
#             model = item.get("_onModel", "unknown").lower()
#             grouped[model].append(item)
#         return grouped

#     @staticmethod
#     def _extract_operating_hours(item: Dict) -> Dict[str, Any]:
#         """Extract and normalize operating hours information."""
#         hours = {
#             "openDay": item.get("openDay", "Not specified"),
#             "openTime": item.get("openTime", "Not specified"),
#             "has_night_viewing": False,
#             "closed_days": []
#         }
        
#         # Check for night viewing indicators
#         open_time = str(hours["openTime"]).lower()
#         if "night" in open_time or "moon" in open_time or "8:30 pm" in open_time:
#             hours["has_night_viewing"] = True
        
#         # Extract closed days
#         open_day = str(hours["openDay"]).lower()
#         if "friday closed" in open_day:
#             hours["closed_days"].append("Friday")
#         if "monday closed" in open_day:
#             hours["closed_days"].append("Monday")
            
#         return hours

#     @staticmethod
#     def _validate_no_duplicates(itinerary: Dict) -> Dict:
#         """Post-process to ensure no duplicate items across the itinerary."""
#         if "itinerary" not in itinerary:
#             return itinerary
        
#         used_ids = set()
#         cleaned_itinerary = []
        
#         for day in itinerary["itinerary"]:
#             cleaned_day = {
#                 "day": day["day"],
#                 "date_label": day.get("date_label", f"Day {day['day']}"),
#                 "slots": {}
#             }
            
#             # Add theme if present
#             if "theme" in day:
#                 cleaned_day["theme"] = day["theme"]
            
#             # Add accommodation suggestion if present
#             if "suggested_accommodation" in day:
#                 cleaned_day["suggested_accommodation"] = day["suggested_accommodation"]
            
#             # Clean each slot
#             for slot_name, slot_items in day.get("slots", {}).items():
#                 if not isinstance(slot_items, list):
#                     cleaned_day["slots"][slot_name] = []
#                     continue
                
#                 cleaned_slot = []
#                 for item in slot_items:
#                     item_id = item.get("_id")
#                     if item_id and item_id not in used_ids:
#                         used_ids.add(item_id)
#                         cleaned_slot.append(item)
#                     # If duplicate found, skip it
                
#                 cleaned_day["slots"][slot_name] = cleaned_slot
            
#             # Only add day if it has any items
#             if any(cleaned_day["slots"].values()):
#                 cleaned_itinerary.append(cleaned_day)
        
#         itinerary["itinerary"] = cleaned_itinerary
#         return itinerary

#     @staticmethod
#     def _get_current_day_name() -> str:
#         """Get current day name for reference."""
#         return datetime.now().strftime("%A")

#     # ── main ─────────────────────────────────────────────────────────────────

#     def run_itinerary_flow(
#         self,
#         user_id: str,
#         city: str,
#         query: str,
#         latitude: float,
#         longitude: float,
#     ) -> str:
#         """
#         Full pipeline. Returns a JSON string.
#         """
#         start = time.time()

#         # ── Step 1: classify budget + duration ────────────────────────────────
#         print("   📊 Classifying itinerary parameters...")
#         classification = itinerary_classifier.classify(query)
#         budget   = classification.budget
#         duration = classification.duration

#         # ── Step 2: fetch + resolve wishlist items via itinerary_tool ──────────
#         print(f"   🗂️  Running itinerary_tool for {city}...")
#         items = itinerary_tool._run(user_id=user_id, city_name=city)

#         if not items:
#             return json.dumps({
#                 "itinerary": [],
#                 "summary": f"No wishlist items found for {city}. Add items to your wishlist first!",
#                 "tips": ["Explore the city and add places you like to your wishlist"],
#                 "budget": budget,
#                 "duration": duration,
#             })

#         # Group items for better context in prompt
#         grouped_items = self._group_items_by_type(items)
        
#         # Separate accommodations for later use
#         accommodations = [item for item in items if item.get("_onModel", "").lower() == "accommodation"]
#         other_items = [item for item in items if item.get("_onModel", "").lower() != "accommodation"]

#         # ── Step 3: build enhanced prompt with OpenDay/OpenTime considerations ──
#         items_json = json.dumps(other_items, default=str, ensure_ascii=False, indent=2)
        
#         # Create a summary of available items by category
#         category_summary = []
#         for model, model_items in grouped_items.items():
#             if model != "accommodation":  # Handle accommodations separately
#                 category_summary.append(f"- {model}: {len(model_items)} items")
        
#         accommodations_json = json.dumps(accommodations, default=str, ensure_ascii=False, indent=2) if accommodations else "[]"
        
#         # Extract operating hours for key items to help LLM understand
#         hours_summary = []
#         for item in other_items[:10]:  # Show hours for first 10 items as examples
#             name = item.get("places") or item.get("shops") or item.get("topActivities") or "Unknown"
#             hours = self._extract_operating_hours(item)
#             hours_summary.append(f"- {name}: Open {hours['openDay']} | Hours: {hours['openTime']}")

#         current_day = self._get_current_day_name()

#         system_msg = f"""You are an expert travel planner AI specializing in creating efficient, realistic day-wise itineraries.

# CRITICAL RULES - READ CAREFULLY:
# 1. UNIQUENESS: Each place/activity/shop can appear ONLY ONCE in the entire itinerary. NO DUPLICATES across different days or slots.
# 2. USE ONLY PROVIDED ITEMS: You must ONLY use places from the wishlist provided - do NOT invent or add external places.
# 3. OPERATING HOURS VALIDATION: You MUST check each place's OpenDay and OpenTime fields and ONLY schedule them when they are open:
#    - Morning (8am-12pm): Only places open during morning hours
#    - Afternoon (12pm-5pm): Only places open during afternoon hours  
#    - Evening (5pm-8pm): Only places open during evening hours
#    - Night (8pm+): Only places explicitly mentioning night viewing or evening performances
# 4. DAY VALIDATION: Check OpenDay field - if a place is closed on certain days, don't schedule it on those days
# 5. PROXIMITY: Group geographically close places on the same day to minimize travel time (use lat/lon fields)
# 6. BUDGET RESPECT: Avoid expensive places (high fee/priceRange) if budget is "budget"

# NIGHT SLOT GUIDELINES:
# - Only include places in Night slot if:
#   * They have "night viewing" in their openTime description
#   * They are evening cultural performances/dinner places
#   * Their openTime explicitly mentions evening/night hours (e.g., "8:30 PM to 12:30 AM")
# - Otherwise, leave Night slot empty []

# TIME SLOT GUIDELINES (use these time ranges):
# - Morning: 8:00 AM - 12:00 PM (suitable for places opening early, sunrise views)
# - Afternoon: 12:00 PM - 5:00 PM (suitable for indoor places during hot hours)
# - Evening: 5:00 PM - 8:00 PM (suitable for sunset views, markets, light shows)
# - Night: 8:00 PM onwards (only for night-specific activities)

# ACCOMMODATION SUGGESTIONS:
# - At the end of each day, suggest a nearby accommodation from the accommodations list
# - Choose based on proximity to that day's last activity

# OUTPUT FORMAT - RETURN ONLY VALID JSON:
# {{
#   "itinerary": [
#     {{
#       "day": 1,
#       "date_label": "Day 1",
#       "theme": "Brief theme for the day (e.g., 'Mughal Heritage')",
#       "slots": {{
#         "Morning":   [{{"_id": "...", "name": "...", "category": "...", "best_time": "Why this fits morning"}}],
#         "Afternoon": [{{"_id": "...", "name": "...", "category": "...", "best_time": "Why this fits afternoon"}}],
#         "Evening":   [{{"_id": "...", "name": "...", "category": "...", "best_time": "Why this fits evening"}}],
#         "Night":     []  // Empty unless night-appropriate
#       }},
#       "suggested_accommodation": {{
#         "_id": "accommodation_id",
#         "name": "Accommodation name or address",
#         "reason": "Why this accommodation works for this day"
#       }}
#     }}
#   ],
#   "summary": "One-paragraph overview of the complete trip",
#   "tips": ["Tip 1", "Tip 2", "Tip 3"],
#   "budget_estimate": {{
#     "category": "budget|mid-range|luxury",
#     "accommodation": "Estimated range per night",
#     "food": "Estimated per day",
#     "activities": "Estimated total",
#     "total": "Estimated total for the trip"
#   }},
#   "budget": "budget|mid-range|luxury|not classified",
#   "duration": "X days|not classified"
# }}

# REMEMBER: 
# - Each _id can appear ONLY ONCE in the entire itinerary
# - Always check OpenDay and OpenTime before scheduling
# - Don't put places in Night slot unless they're actually open at night
# - Current day is {current_day} - plan accordingly for closures"""

#         # Create a more detailed user message with operating hours context
#         operating_hours_context = f"""
# OPERATING HOURS REFERENCE (sample of items):
# {chr(10).join(hours_summary[:15])}

# IMPORTANT: When scheduling, you must check each item's full OpenDay and OpenTime fields in the JSON below.
# """

#         user_msg = f"""Plan a trip with these details:

# City: {city}
# User Current Location: latitude={latitude}, longitude={longitude}
# Budget Preference: {budget}
# Trip Duration: {duration}
# User Request: "{query}"

# {operating_hours_context}

# AVAILABLE WISHLIST ITEMS (use ONLY these - {len(other_items)} total):
# {items_json}

# AVAILABLE ACCOMMODATIONS ({len(accommodations)}):
# {accommodations_json}

# Generate the day-wise itinerary JSON now. Remember these CRITICAL points:
# 1. ✅ Each item appears MAXIMUM ONCE across all days
# 2. ✅ Check OpenDay - don't schedule places on their closed days
# 3. ✅ Check OpenTime - match places to appropriate time slots (Morning/Afternoon/Evening/Night)
# 4. ✅ Consider proximity to user's location and between attractions
# 5. ✅ Suggest appropriate accommodations for each day
# 6. ✅ {len(other_items)} items to schedule across {duration if 'not classified' not in duration else 'the available'} days

# Take a deep breath and plan thoughtfully, ensuring every scheduled place is actually open at that time."""

#         # ── Step 4: call LLM with retry logic ──────────────────────────────────
#         print(f"   🤖 Generating itinerary via ChatGroq ({len(other_items)} items)...")
        
#         max_retries = 2
#         result = None
        
#         for attempt in range(max_retries):
#             try:
#                 response = self.llm.invoke([
#                     {"role": "system", "content": system_msg},
#                     {"role": "user",   "content": user_msg},
#                 ])

#                 raw = response.content if hasattr(response, "content") else str(response)
#                 clean = self._clean(raw)

#                 # ── Step 5: validate JSON ─────────────────────────────────────
#                 result = json.loads(clean)
                
#                 # Validate and remove any duplicates
#                 result = self._validate_no_duplicates(result)
                
#                 # Inject classification fields if LLM omitted them
#                 result.setdefault("budget", budget)
#                 result.setdefault("duration", duration)
                
#                 # Count unique items used
#                 used_items = set()
#                 for day in result.get("itinerary", []):
#                     for slot_items in day.get("slots", {}).values():
#                         for item in slot_items:
#                             if item.get("_id"):
#                                 used_items.add(item["_id"])
                
#                 print(f"   ✅ Valid JSON generated with {len(used_items)}/{len(other_items)} unique items")
                
#                 # If we used significantly fewer items than available, try again
#                 if len(used_items) < len(other_items) * 0.5 and attempt < max_retries - 1:
#                     print(f"   ⚠️  Only used {len(used_items)}/{len(other_items)} items, retrying...")
#                     # Add instruction to use more items
#                     user_msg += f"\n\nPrevious attempt only used {len(used_items)} items. Please try to include more of the available {len(other_items)} items in your itinerary."
#                     continue
                
#                 break  # Success, exit retry loop
                
#             except json.JSONDecodeError as e:
#                 print(f"   ⚠️  JSON decode error (attempt {attempt + 1}): {e}")
#                 if attempt == max_retries - 1:
#                     # Try to extract JSON from response
#                     match = re.search(r"\{.*\}", clean if 'clean' in locals() else raw, re.DOTALL)
#                     if match:
#                         try:
#                             result = json.loads(match.group())
#                             result = self._validate_no_duplicates(result)
#                             result.setdefault("budget", budget)
#                             result.setdefault("duration", duration)
#                         except Exception:
#                             result = self._fallback(budget, duration, city, items)
#                     else:
#                         result = self._fallback(budget, duration, city, items)
#                 else:
#                     # Continue to next attempt
#                     continue
                    
#             except Exception as e:
#                 print(f"   ⚠️  Error (attempt {attempt + 1}): {e}")
#                 if attempt == max_retries - 1:
#                     result = self._fallback(budget, duration, city, items)
#                 else:
#                     continue

#         # Final safety check - ensure result exists
#         if result is None:
#             result = self._fallback(budget, duration, city, items)

#         # Add operating hours validation warning if needed
#         if "itinerary" in result:
#             night_items_without_night_viewing = []
#             for day in result["itinerary"]:
#                 for night_item in day.get("slots", {}).get("Night", []):
#                     # Find original item
#                     original = next((i for i in items if i.get("_id") == night_item.get("_id")), None)
#                     if original:
#                         hours = self._extract_operating_hours(original)
#                         if not hours["has_night_viewing"]:
#                             night_items_without_night_viewing.append(night_item.get("name"))
            
#             if night_items_without_night_viewing:
#                 result["warning"] = f"Some items in Night slots may not have night viewing hours: {', '.join(night_items_without_night_viewing[:3])}"

#         # Add unused items as "also consider" section
#         if items:
#             used_ids = set()
#             for day in result.get("itinerary", []):
#                 for slot_items in day.get("slots", {}).values():
#                     for item in slot_items:
#                         if item.get("_id"):
#                             used_ids.add(item["_id"])
            
#             unused_items = [item for item in items if item.get("_id") not in used_ids and item.get("_onModel", "").lower() != "accommodation"]
#             if unused_items:
#                 result["also_consider"] = unused_items[:5]  # Limit to 5 suggestions

#         print(f"   ⏱️  Total itinerary time: {time.time() - start:.2f}s")
#         return json.dumps(result, ensure_ascii=False)

#     @staticmethod
#     def _fallback(budget: str, duration: str, city: str, items: List = None) -> dict:
#         """Enhanced fallback with basic grouping if available."""
#         if items and len(items) > 0:
#             # Create a simple grouped by type fallback
#             places = [i for i in items if i.get("_onModel", "").lower() in ["place", "hiddengem", "nearbyspot"]]
#             activities = [i for i in items if i.get("_onModel", "").lower() == "activity"]
#             shops = [i for i in items if i.get("_onModel", "").lower() == "shop"]
            
#             return {
#                 "itinerary": [
#                     {
#                         "day": 1,
#                         "date_label": "Day 1",
#                         "theme": "Suggested Places",
#                         "slots": {
#                             "Morning": places[:2] if places else [],
#                             "Afternoon": places[2:4] if len(places) > 2 else (activities[:1] if activities else []),
#                             "Evening": activities[1:2] if len(activities) > 1 else (shops[:1] if shops else []),
#                             "Night": []
#                         }
#                     }
#                 ] if places or activities or shops else [],
#                 "summary": f"Here are some places from your wishlist in {city}. Try a more specific query for a detailed itinerary with operating hours considered.",
#                 "tips": [
#                     "Be more specific in your query (e.g., '3-day budget trip')", 
#                     "Add more items to your wishlist for better itineraries",
#                     "Check each place's open hours before visiting"
#                 ],
#                 "budget": budget,
#                 "duration": duration,
#                 "error": "LLM returned invalid JSON, showing basic grouping instead",
#             }
        
#         return {
#             "itinerary": [],
#             "summary": f"Could not generate itinerary for {city}.",
#             "tips": [
#                 "Add items to your wishlist first", 
#                 "Try a different city",
#                 "Make sure your wishlist items have operating hours information"
#             ],
#             "budget": budget,
#             "duration": duration,
#             "error": "LLM returned invalid JSON",
#         }


# # Global instance
# itinerary_wrapper = ItineraryWrapper()