"""
itinerary_routes.py
───────────────────
Route:  POST /api/{user_id}/itinerary
        GET  /api/{user_id}/itinerary

Required query params: latitude, longitude, city, query
"""

from fastapi import APIRouter, HTTPException, Query, Depends, Response
from pydantic import BaseModel
from typing import Any, Dict

from wrappers.itinerary_wrapper import itinerary_wrapper
from dependencies.credit_check import check_and_deduct_credits

router = APIRouter(tags=["Itinerary"])


# ── Response / Error models ────────────────────────────────────────────────────

class ItineraryResponse(BaseModel):
    user_id:   str
    city:      str
    status:    str
    data:      Dict[str, Any]


class ErrorResponse(BaseModel):
    error:  str
    status: str


# ── Shared handler ─────────────────────────────────────────────────────────────

async def _handle(
    user_id:   str,
    latitude:  float,
    longitude: float,
    city:      str,
    query:     str,
) -> ItineraryResponse:
    print(f"\n🗺️  Itinerary — user={user_id} | city={city} | lat={latitude} | lon={longitude}")
    print(f"   Query: {query}")

    try:
        result_json = itinerary_wrapper.run_itinerary_flow(
            user_id=user_id,
            city=city,
            query=query,
            latitude=latitude,
            longitude=longitude,
        )

        import json
        data = json.loads(result_json)

        return ItineraryResponse(
            user_id=user_id,
            city=city,
            status="success",
            data=data,
        )

    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        print(f"❌ Itinerary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── POST ──────────────────────────────────────────────────────────────────────

@router.post(
    "/{user_id}/itinerary",
    response_model=ItineraryResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Generate a day-wise itinerary from the user's wishlist",
)
async def create_itinerary(
    user_id: str,
    response_obj: Response,
    latitude: float = Query(..., description="User's current latitude"),
    longitude: float = Query(..., description="User's current longitude"),
    city: str = Query(..., description="City to generate itinerary for"),
    query: str = Query(..., description="Natural-language trip query (e.g. '3-day budget trip in Agra')"),
    remaining_credits: int = Depends(check_and_deduct_credits)
):
    """
    Generates a personalised day-wise itinerary using the user's wishlist
    for the specified city, taking into account the user's location,
    budget, and trip duration extracted from the query.
    """
    response_obj.headers["X-Remaining-Credits"] = str(remaining_credits)
    return await _handle(user_id, latitude, longitude, city, query)


# ── GET ───────────────────────────────────────────────────────────────────────

@router.get(
    "/{user_id}/itinerary",
    response_model=ItineraryResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Generate a day-wise itinerary (GET variant)",
)
async def get_itinerary(
    user_id: str,
    response_obj: Response,
    latitude: float = Query(..., description="User's current latitude"),
    longitude: float = Query(..., description="User's current longitude"),
    city: str = Query(..., description="City to generate itinerary for"),
    query: str = Query(..., description="Natural-language trip query"),
    remaining_credits: int = Depends(check_and_deduct_credits)
):
    """GET convenience wrapper — identical to POST."""
    response_obj.headers["X-Remaining-Credits"] = str(remaining_credits)
    return await _handle(user_id, latitude, longitude, city, query)
