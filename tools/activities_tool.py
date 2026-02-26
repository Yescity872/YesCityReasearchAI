from typing import Optional,Dict,Any,List,Type
from pydantic import BaseModel, Field, ConfigDict
from langchain_core.tools import BaseTool
from .base_tool import MongoDBQueryTool

import time

class ActivitiesInput(BaseModel):

    model_config=ConfigDict(arbitary_types_allowed=True)

    cityName:str=Field(..., description="City name to search for activities")
    category: Optional[str] = Field(None, description="Activities category to filter by")
    maxResults: int = Field(50, description="Maximum number of results to return")

class ActivitiesTool(BaseTool):
    name:str="activities"
    description:str="""

    """

    args_schema:Type[BaseModel]=ActivitiesInput

    def _run(
        self,
        cityName:str,
        category:Optional[str]=None,
        maxResults:int=50
    )->List[Dict[str,Any]]:
        start_time=time.time()
        
        query_filter={"cityName":{"$regex":cityName,"$options":"i"}}

        print("Fetching activities in ",cityName)

        base_tool=MongoDBQueryTool(
            collection_name="activities"
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
                "topActivities":str(result.get("topActivities","")),
                "bestPlaces":str(result.get("bestPlaces","")),
                "description":str(result.get("description","")),
                "essentials":str(result.get("essentials","")),
                "fee":str(result.get("fee","")),
                "premium":str(result.get("premium","")),
            }

            formatted_results.append(formatted)
        print(formatted_results[0])
        end_time=time.time()
        response_time=end_time-start_time
        print(f"Response Time: {response_time:.2f} seconds")
        
        print(f"✅ Found {len(formatted_results)} activities in {cityName}")
        return formatted_results

activities_tool = ActivitiesTool()
        




