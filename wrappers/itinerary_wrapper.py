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

