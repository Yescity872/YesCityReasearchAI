from typing import Optional,Dict,Any,List,Type
from pydantic import BaseModel, Field, ConfigDict
from langchain_core.tools import BaseTool
from .base_tool import MongoDBQueryTool
import time

class TransportSearchInput(BaseModel):

    model_config=ConfigDict(arbitary_types_allowed=True)

    cityName:str=Field(..., description="City name to search for transport places")
    category: Optional[str] = Field(None, description="Transport category to filter by")
    maxResults: int = Field(50, description="Maximum number of results to return")
    
class TransportSearchTool(BaseTool):
    name:str="search_transport_places"
    description:str="""

    """

    args_schema:Type[BaseModel]=TransportSearchInput

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

        print("Fetching transport places in ",cityName)

        # 🔹 Query 1: localtransports collection
        transport_tool = MongoDBQueryTool(
            collection_name="localtransports",
        )

        transport_results = transport_tool._run(
            query_filter=query_filter,
            limit=maxResults
        )

        # 🔹 Query 2: connectivities collection
        connectivity_tool = MongoDBQueryTool(
            collection_name="connectivities",
        )

        connectivity_results = connectivity_tool._run(
            query_filter=query_filter,
            limit=maxResults  
        )

        formatted_results = []

        # ✅ Format local transport results
        for result in transport_results:
            formatted = {
                "_id": str(result.get("_id", "")),
                "type": "transport",
                "cityName": result.get("cityName", ""),
                "from": result.get("from", ""),
                "to": result.get("to", ""),
                "autoPrice": result.get("autoPrice", ""),
                "cabPrice": result.get("cabPrice", ""),
                "bikePrice": result.get("bikePrice", ""),
                "premium": result.get("premium", ""),
            }
            formatted_results.append(formatted)

        # ✅ Format connectivity results
        for result in connectivity_results:
            formatted = {
                "_id": str(result.get("_id", "")),
                "type": "connectivity",
                "cityName": result.get("cityName", ""),
                "nearestAirportStationBusStand": result.get("nearestAirportStationBusStand", ""),
                "distance": result.get("distance", ""),
                "majorFlightsTrainsBuses": result.get("majorFlightsTrainsBuses", ""),
                "lat": result.get("lat", ""),
                "lon": result.get("lon", ""),
                "locationLink": result.get("locationLink", ""),
                "premium": result.get("premium", ""),
                "views": result.get("engagement", {}).get("views", 0),
            }
            formatted_results.append(formatted)

        end_time = time.time()
        response_time = end_time - start_time
        print(f"Response Time: {response_time:.2f} seconds")
        
        print(f"✅ Found {len(formatted_results)} shopping places in {cityName}")
        return formatted_results

transport_search_tool = TransportSearchTool()
        

            

            