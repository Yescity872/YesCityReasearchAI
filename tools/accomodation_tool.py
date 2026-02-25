from typing import Optional,Dict,Any,List,Type
from pydantic import BaseModel, Field, ConfigDict
from langchain_core.tools import BaseTool
from .base_tool import MongoDBQueryTool
import time

class accommodationsearchInput(BaseModel):

    model_config=ConfigDict(arbitary_types_allowed=True)

    cityName:str=Field(..., description="City name to search for accomodation places")
    category: Optional[str] = Field(None, description="Accomodation category to filter by")
    maxResults: int = Field(50, description="Maximum number of results to return")
    
class accommodationsearchTool(BaseTool):
    name:str="search_accomodation_places"
    description:str="""

    """

    args_schema:Type[BaseModel]=accommodationsearchInput

    def _run(
        self,
        cityName:str,
        category:Optional[str]=None,
        maxResults:int=50,
        **kwargs
    )->List[Dict[str,Any]]:
        start_time = time.time()
        query_filter={"cityName":{"$regex":cityName,"$options":"i"}}


        print("Fetching accomodation in ",cityName)

        base_tool=MongoDBQueryTool(
            collection_name="accommodations",
            )

        all_results=base_tool._run(
            query_filter=query_filter,
            limit=maxResults
        )

        formatted_results = []
        for result in all_results:
            # Keep ALL original fields, just ensure _id is string
            formatted = {
                "_id": str(result.get("_id", "")),
                "cityName": result.get("cityName", ""),
                "hotels": result.get("hotels", "Unknown"),
                "minPrice": result.get("minPrice", ""),
                "maxPrice": result.get("maxPrice", ""),
                "flagship": result.get("flagship", False),
                "premium": result.get("premium", "FREE"),
                "address": result.get("address", ""),
                "locationLink": result.get("locationLink", ""),
                "category":result.get("category", ""),
                "roomTypes":result.get("roomTypes"),
                "images": result.get("images", []),
                "engagement": result.get("engagement", {}),
                "reviews": result.get("reviews", []),
                "lat": result.get("lat"),
                "lon": result.get("lon"),
                "__v": result.get("__v", 0)
            }
            formatted_results.append(formatted)

        print(formatted_results[0])
        end_time = time.time()
        response_time = end_time - start_time
        print(f"Response Time: {response_time:.2f} seconds")
        
        print(f"✅ Found {len(formatted_results)} accomodation places in {cityName}")
        return formatted_results

accomodation_search_tool = accommodationsearchTool()