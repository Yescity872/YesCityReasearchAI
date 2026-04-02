from fastapi import APIRouter, HTTPException, Depends, Response
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from dependencies.credit_check import check_and_deduct_credits
# Import capabilities
from services.query_classifier import query_classifier, QueryCategory

# Wrappers
from wrappers.shopping_wrapper import shopping_wrapper
from wrappers.food_wrapper import food_wrapper
from wrappers.accomodation_wrapper import accomodation_wrapper
from wrappers.place_wrapper import place_wrapper
from wrappers.activities_wrapper import activities_wrapper
from wrappers.transport_wrapper import transport_wrapper

class SearchRouter:
    def handle_request(self, user_query: str) -> str:
        """
        Orchestrates the query processing flow by dispatching to appropriate domain wrappers.
        """
        print("\n🤖 Router: Classifying...")
        try:
            classification: QueryCategory = query_classifier.classify_query(user_query)
            
            print(f"   Category: {classification.category}")
            print(f"   City: {classification.cityName}")
            
            # Dispatch Logic
            if classification.category == "shoppings":
                print("   ➡️ Dispatching to ShoppingWrapper...")
                return shopping_wrapper.run_shopping_flow(
                    city_name=classification.cityName,
                    parameters=classification.parameters,
                    user_query=user_query,
                    category=classification.category
                )

            elif classification.category == "foods":
                print("   ➡️ Dispatching to FoodWrapper")
                # Placeholder for FoodWrapper
                return food_wrapper.run_food_flow(
                    city_name=classification.cityName,
                    parameters=classification.parameters,
                    user_query=user_query,
                    category=classification.category
                )
            
            elif classification.category == "accommodations":
                print("   ➡️ Dispatching to AccomodationWrapper")
                # Placeholder for FoodWrapper
                return accomodation_wrapper.run_accomodation_flow(
                    city_name=classification.cityName,
                    parameters=classification.parameters,
                    user_query=user_query,
                    category=classification.category
                )

            elif classification.category == "places":
                print("   ➡️ Dispatching to PLacesWrapper")
                # Placeholder for FoodWrapper
                return place_wrapper.run_place_flow(
                    city_name=classification.cityName,
                    parameters=classification.parameters,
                    user_query=user_query,
                    category=classification.category
                )

            elif classification.category == "activities":
                print("   ➡️ Dispatching to ActivitiesWrapper")
                # Placeholder for FoodWrapper
                return activities_wrapper.run_activities_flow(
                    city_name=classification.cityName,
                    parameters=classification.parameters,
                    user_query=user_query,
                    category=classification.category
                )

            elif classification.category == "transport":
                print("   ➡️ Dispatching to TransportWrapper")
                # Placeholder for FoodWrapper
                return transport_wrapper.run_transport_flow(
                    city_name=classification.cityName,
                    parameters=classification.parameters,
                    user_query=user_query,
                    category=classification.category
                )
            
                
            else:
                print(f"⚠️ Tool for category '{classification.category}' is not implemented yet.")
                return '{"error": "Category not implemented"}'

        except Exception as e:
            print(f"❌ Router Error: {e}")
            return f'{{"error": "{str(e)}"}}'

search_handler = SearchRouter()

router = APIRouter(tags=["Search"])

class SearchRequest(BaseModel):
    query: str

class SearchResponse(BaseModel):
    response: str
    status: str
    query: str

class ErrorResponse(BaseModel):
    error: str
    status: str

@router.post("/search", response_model=SearchResponse, responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def api_search(request: SearchRequest, response_obj: Response, remaining_credits: int = Depends(check_and_deduct_credits)):
    """
    Search endpoint for YesCity.
    Send a POST request with JSON body: {"query": "your search query"}
    """
    try:
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        response = search_handler.handle_request(request.query)
        
        response_obj.headers["X-Remaining-Credits"] = str(remaining_credits)
        return SearchResponse(
            response=response,
            status="success",
            query=request.query
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search", response_model=SearchResponse)
async def api_search_get(response_obj: Response, q: Optional[str] = None, remaining_credits: int = Depends(check_and_deduct_credits)):
    """
    GET endpoint for search.
    Usage: /api/search?q=your+query
    """
    try:
        if not q or not q.strip():
            raise HTTPException(status_code=400, detail="Query parameter 'q' is required")
        
        response = search_handler.handle_request(q)
        
        response_obj.headers["X-Remaining-Credits"] = str(remaining_credits)
        return SearchResponse(
            response=response,
            status="success",
            query=q
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
