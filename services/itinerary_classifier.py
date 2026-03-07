import os
import json
import time
from typing import Optional
from pydantic import BaseModel
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()


class ItineraryClassification(BaseModel):
    budget: str        # e.g. "budget", "mid-range", "luxury", or "not classified"
    duration: str      # e.g. "3 days", "1 week", or "not classified"


class ItineraryClassifier:
    def __init__(self):
        self.llm = ChatGroq(
            groq_api_key=os.getenv("GROQ_API_KEY"),
            model_name="llama-3.1-8b-instant",
            temperature=0.1,
            max_tokens=256,
            model_kwargs={
                "top_p": 0.9,
                "frequency_penalty": 0.1,
                "presence_penalty": 0.1,
            },
        )

    def classify(self, query: str) -> ItineraryClassification:
        """
        Extract budget and duration from the user query.
        Returns "not classified" for fields that can't be determined.
        """
        start_time = time.time()

        prompt = f"""
You are a travel query parser. Extract ONLY budget and duration from the user query.

User Query: "{query}"

Rules:
- budget: one of "budget", "mid-range", "luxury". If not mentioned return "not classified".
- duration: a string like "2 days", "1 week", "3 nights". If not mentioned return "not classified".

Respond ONLY with valid JSON in this exact format:
{{
    "budget": "budget|mid-range|luxury|not classified",
    "duration": "X days|not classified"
}}

Examples:
- "Plan a 3-day budget trip" -> {{"budget": "budget", "duration": "3 days"}}
- "Luxury weekend getaway" -> {{"budget": "luxury", "duration": "2 days"}}
- "Show me places in Agra" -> {{"budget": "not classified", "duration": "not classified"}}
"""

        try:
            response = self.llm.invoke(prompt)
            text = response.content if hasattr(response, "content") else str(response)
            text = text.strip()

            # Strip markdown fences
            if text.startswith("```json"):
                text = text[7:]
            elif text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            data = json.loads(text)
            result = ItineraryClassification(
                budget=data.get("budget", "not classified"),
                duration=data.get("duration", "not classified"),
            )

        except Exception as e:
            print(f"⚠️  Itinerary classifier fallback: {e}")
            result = ItineraryClassification(
                budget="not classified",
                duration="not classified",
            )

        print(f"⏱️  Classifier: {time.time() - start_time:.2f}s | budget={result.budget} | duration={result.duration}")
        return result


# Global instance
itinerary_classifier = ItineraryClassifier()
