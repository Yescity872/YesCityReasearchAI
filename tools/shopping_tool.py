from typing import Optional,Dict,Any,List
from langchain_core import BaseTool
from .base_tool import MongoDBQueryTool
import time

class ShoppingSearchInput(BaseModel):

    model_config=ConfigDict(arbitary_types_allowed=True)

    cityName:str=Field(..., description="City name to search for shopping places")
    category: Optional[str] = Field(None, description="Shopping category to filter by")
    maxResults: int = Field(50, description="Maximum number of results to return")
    
class ShoppingSearchTool(BaseTool):
    name:str="search_shopping_places"
    description:str="""

    """

    args_schema:Type[BaseModel]=ShoppingSearchInput

    def _run(
        self,
        cityName:str,
        category:Optional[str]=None,
        maxResults:int=50,
        **kwargs
    )->List[Dict[str,Any]]:
        start_time = time.time()
        query_filter:{"cityName":{"$regex":cityName,"$options":"i"}}

        if category and category!='null' and category.lower()!='none':
            query_filter["category"]={"$regex":category,"$options":"i"}

        print("Fetching shopping places in ",cityName,"with category",category)

        base_tool=MongoDBQueryTool(
            collection_name="shoppings",
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
                "shops": result.get("shops", "Unknown"),
                "famousFor": result.get("famousFor", ""),
                "priceRange": result.get("priceRange", ""),
                "flagship": result.get("flagship", False),
                "premium": result.get("premium", "FREE"),
                "address": result.get("address", ""),
                "locationLink": result.get("locationLink", ""),
                "openDay": result.get("openDay", ""),
                "openTime": result.get("openTime", ""),
                "phone": result.get("phone", ""),
                "website": result.get("website", ""),
                "images": result.get("images", []),
                "engagement": result.get("engagement", {}),
                "reviews": result.get("reviews", []),
                "lat": result.get("lat"),
                "lon": result.get("lon"),
                "__v": result.get("__v", 0)
            }
            formatted_results.append(formatted)

        end_time = time.time()
        response_time = end_time - start_time
        print(f"Response Time: {response_time:.2f} seconds")
        
        print(f"✅ Found {len(formatted_results)} shopping places in {cityName}")
        return formatted_results

shopping_search_tool = ShoppingSearchTool()
        

            

            