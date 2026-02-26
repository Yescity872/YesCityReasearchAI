from typing import Optional,Dict,Any,List,Type
from pydantic import BaseModel, Field, ConfigDict
from langchain_core.tools import BaseTool
from .base_tool import MongoDBQueryTool
import time

class PlaceSearchInput(BaseModel):

    model_config=ConfigDict(arbitary_types_allowed=True)

    cityName:str=Field(..., description="City name to search for places")
    category: Optional[str] = Field(None, description="Places category to filter by")
    maxResults: int = Field(50, description="Maximum number of results to return")
    
class PlaceSearchTool(BaseTool):
    name:str="search_places"
    description:str="""

    """

    args_schema:Type[BaseModel]=PlaceSearchInput

    def _run(
        self,
        cityName:str,
        category:Optional[str]=None,
        maxResults:int=50,
        **kwargs
    )->List[Dict[str,Any]]:
        start_time = time.time()
        query_filter={"cityName":{"$regex":cityName,"$options":"i"}}

        # if category and category!='null' and category.lower()!='none':
        #     query_filter["category"]={"$regex":category,"$options":"i"}

        print("Fetching places in ",cityName)

        # 🔹 Query 1
        places_to_visit_tool = MongoDBQueryTool(
            collection_name="placestovisits",
        )

        places_to_visit_results = places_to_visit_tool._run(
            query_filter=query_filter,
            limit=maxResults
        )

        # 🔹 Query 2
        nearby_tourist_spots_tool = MongoDBQueryTool(
            collection_name="nearbytouristspots",
        )

        nearby_tourist_spots_results = nearby_tourist_spots_tool._run(
            query_filter=query_filter,
            limit=maxResults  
        )

        # Query 3

        hidden_gems_tool = MongoDBQueryTool(
            collection_name="hiddengems",
        )

        hidden_gems_results = hidden_gems_tool._run(
            query_filter=query_filter,
            limit=maxResults  
        )


        formatted_results = []

        # ✅ Format local transport results
        for result in places_to_visit_results:
            formatted = {
                "type":"tourist-places/top-attractions",
                "_id": str(result.get("_id", "")),
                "cityName": result.get("cityName", ""),
                "places": result.get("places", "Unknown"),
                "category": result.get("category", ""),
                "description": result.get("description", ""),
                "premium": result.get("premium", "FREE"),
                "address": result.get("address", ""),
                "locationLink": result.get("locationLink", ""),
                "openDay": result.get("openDay", ""),
                "openTime": result.get("openTime", ""),
                "esssential": result.get("essential", ""),
                "story": result.get("story", ""),
                "images": result.get("images", []),
                "engagement": result.get("engagement", {}),
                "reviews": result.get("reviews", []),
                "lat": result.get("lat"),
                "lon": result.get("lon"),
                "fee": result.get("fee"),
                "establishYear": result.get("establishYear"),
                "__v": result.get("__v", 0)
            }
            formatted_results.append(formatted)

        # ✅ Format connectivity results
        for result in nearby_tourist_spots_results:
            formatted = {
                "type":"nearby-tourist-place",
                "_id": str(result.get("_id", "")),
                "cityName": result.get("cityName", ""),
                "places": result.get("places", "Unknown"),
                "distance":result.get("distance",""),
                "category": result.get("category", ""),
                "description": result.get("description", ""),
                "premium": result.get("premium", "FREE"),
                "address": result.get("address", ""),
                "locationLink": result.get("locationLink", ""),
                "openDay": result.get("openDay", ""),
                "openTime": result.get("openTime", ""),
                "esssential": result.get("essential", ""),
                "story": result.get("story", ""),
                "images": result.get("images", []),
                "engagement": result.get("engagement", {}),
                "reviews": result.get("reviews", []),
                "lat": result.get("lat"),
                "lon": result.get("lon"),
                "fee": result.get("fee"),
                "establishYear": result.get("establishYear"),
                "__v": result.get("__v", 0)
            }
            formatted_results.append(formatted)

        for result in hidden_gems_results:
            formatted = {
                "type":"hidden-gems",
                "_id": str(result.get("_id", "")),
                "cityName": result.get("cityName", ""),
                "places": result.get("hiddenGem", "Unknown"),
                "category": result.get("category", ""),
                "description": result.get("description", ""),
                "premium": result.get("premium", "FREE"),
                "address": result.get("address", ""),
                "locationLink": result.get("locationLink", ""),
                "openDay": result.get("openDay", ""),
                "openTime": result.get("openTime", ""),
                "esssential": result.get("essential", ""),
                "story": result.get("story", ""),
                "images": result.get("images", []),
                "engagement": result.get("engagement", {}),
                "reviews": result.get("reviews", []),
                "lat": result.get("lat"),
                "lon": result.get("lon"),
                "fee": result.get("fee"),
                "establishYear": result.get("establishYear"),
                "__v": result.get("__v", 0)
            }
            formatted_results.append(formatted)

        end_time = time.time()
        response_time = end_time - start_time
        print(f"Response Time: {response_time:.2f} seconds")
        
        print(f"✅ Found {len(formatted_results)} places in {cityName}")
        return formatted_results

place_search_tool = PlaceSearchTool()
        

            

            