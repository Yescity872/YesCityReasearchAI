from typing import Optional,Dict,Any,List,Type
from pydantic import BaseModel, Field, ConfigDict
from langchain_core.tools import BaseTool
from .base_tool import MongoDBQueryTool

import time

class FoodSearchInput(BaseModel):

    model_config=ConfigDict(arbitary_types_allowed=True)

    cityName:str=Field(..., description="City name to search for food places")
    category: Optional[str] = Field(None, description="Food category to filter by")
    maxResults: int = Field(50, description="Maximum number of results to return")

class FoodSearchTool(BaseTool):
    name:str="food_search"
    description:str="""

    """

    args_schema:Type[BaseModel]=FoodSearchInput

    def _run(
        self,
        cityName:str,
        category:Optional[str]=None,
        maxResults:int=50
    )->List[Dict[str,Any]]:
        start_time=time.time()
        
        query_filter={"cityName":{"$regex":cityName,"$options":"i"}}

        print("Fetching food places in ",cityName)

        base_tool=MongoDBQueryTool(
            collection_name="foods"
        )

        all_results=base_tool._run(
            query_filter=query_filter,
            limit=maxResults
        )

        formatted_results=[]
        for result in all_results:
            formatted={
                "_id":str(result.get("_id","")),
                "cityName":str(result.get("cityName","")),
                "flagship":bool(result.get("flagship",False)),
                "category":str(result.get("category","")),
                "foodPlace":str(result.get("foodPlace","")),
                "address":str(result.get("address","")),
                "locationLink":str(result.get("locationLink","")),
                "openDay":str(result.get("openDay","")),
                "openTime":str(result.get("openTime","")),
                "phone":str(result.get("phone","")),
                "website":str(result.get("website","")),
                "lat":result.get("lat"),
                "lon":result.get("lon"),
                "description":str(result.get("description","")),
                "menuSpecial":str(result.get("menuSpecial","")),
                "hygeine":int(result.get("hygeine",0)),
                "taste":int(result.get("taste",0)),
                "service":int(result.get("service",0)),
                "valueForMoney":int(result.get("valueForMoney",0)),
                "vegOrNonVeg":str(result.get("vegOrNonVeg","")),
            }

            formatted_results.append(formatted)

        end_time=time.time()
        response_time=end_time-start_time
        print(f"Response Time: {response_time:.2f} seconds")
        
        print(f"✅ Found {len(formatted_results)} food places in {cityName}")
        return formatted_results

food_search_tool = FoodSearchTool()
        




