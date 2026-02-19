from typing import Dict, List, Any, Optional
from pydantic import Field
from langchain_core.tools import BaseTool
from database.mongodb_client import mongodb_client
from bson import ObjectId
import datetime

class MongoDBQueryTool(BaseTool):
    name: str = "mongodb_query_tool"
    description: str = "Base tool to query MongoDB collections"
    collection_name: str = Field(..., description="Name of the MongoDB collection to query")

    def _run(self, query_filter: Dict[str, Any] = None, limit: int = 50, **kwargs) -> List[Dict]:
        """
        Run a query on the specified collection.
        Returns ALL fields, only converts ObjectId to string.
        """
        try:
            collection = mongodb_client.get_collection(self.collection_name)
            
            # Build query filter
            filter_dict = query_filter or {}
            if kwargs:
                filter_dict.update(kwargs)

            # Make city search case-insensitive
            if "cityName" in filter_dict:
                if isinstance(filter_dict["cityName"], dict):
                    # Already has regex
                    pass
                else:
                    filter_dict["cityName"] = {'$regex': f"^{filter_dict['cityName']}$", '$options': 'i'}

            print(f"🔍 Querying {self.collection_name} with filter: {filter_dict}")

            cursor = collection.find(filter_dict).limit(limit)
            results = list(cursor)

            # Process results - convert ObjectId to string
            processed_results = []
            for doc in results:
                processed = self._convert_objectids(doc)
                processed_results.append(processed)
            
            print(f"✅ Found {len(processed_results)} documents")
            return processed_results
        
        except Exception as e:
            error_msg = f"Failed to query collection {self.collection_name}: {str(e)}"
            print(f"❌ {error_msg}")
            return []
    
    def _convert_objectids(self, data: Any, visited=None) -> Any:
        """
        Recursively convert ObjectId instances to strings without recursion issues.
        """
        if visited is None:
            visited = set()
        
        # Handle ObjectId
        if isinstance(data, ObjectId):
            return str(data)
        
        # Handle datetime
        elif isinstance(data, datetime.datetime):
            return data.isoformat()
        
        # Handle dictionary
        elif isinstance(data, dict):
            # Create a new dict to avoid modifying the original
            result = {}
            for key, value in data.items():
                # Skip processing if we've seen this object before (prevents recursion)
                if id(value) in visited:
                    result[key] = str(value) if hasattr(value, '__str__') else value
                else:
                    visited.add(id(value))
                    result[key] = self._convert_objectids(value, visited)
            return result
        
        # Handle list
        elif isinstance(data, list):
            result = []
            for item in data:
                if id(item) in visited:
                    result.append(str(item) if hasattr(item, '__str__') else item)
                else:
                    visited.add(id(item))
                    result.append(self._convert_objectids(item, visited))
            return result
        
        # Handle other types
        else:
            return data