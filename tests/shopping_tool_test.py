import unittest
from unittest.mock import MagicMock, patch
import sys
import os
from typing import Dict, Optional
from pydantic import BaseModel

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.shopping_tool import ShoppingSearchTool

# Define local mock for structure
class QueryCategory(BaseModel):
    category:str
    cityName:Optional[str]=None
    parameters:Dict[str,str]={}

class TestShoppingToolFlow(unittest.TestCase):
    
    @patch('tools.shopping_tool.MongoDBQueryTool')
    def test_complete_flow(self, MockDBTool):
        print("\n--- Starting Complete Flow Test ---")
        
        # 1. User Query
        user_query = "Best malls in Delhi for clothes"
        print(f"1. User enters query: '{user_query}'")

        # 2. Mock Classifier Output
        # Simulating the classifier without importing the broken module
        expected_category = QueryCategory(
            category="shoppings",
            cityName="Delhi",
            parameters={"category": "malls"} 
        )
        print(f"2. Query Classifier (Simulated) identifies: City={expected_category.cityName}, Category={expected_category.category}, Params={expected_category.parameters}")

        # 3. Initialize Shopping Tool
        shopping_tool = ShoppingSearchTool()
        
        # 4. Mock Database Response
        mock_db_instance = MockDBTool.return_value
        mock_db_instance._run.return_value = [
            {
                "_id": "123",
                "cityName": "Delhi",
                "shops": "Select Citywalk",
                "famousFor": "Fashion",
                "priceRange": "High",
                "address": "Saket District Centre",
                "openTime": "10:00 AM - 11:00 PM"
            },
            {
                "_id": "456",
                "cityName": "Delhi",
                "shops": "DLF Promenade",
                "famousFor": "Luxury Brands",
                "priceRange": "Very High",
                "address": "Vasant Kunj",
                "openTime": "11:00 AM - 10:00 PM"
            }
        ]
        
        # 5. Execute Tool with Clasified Parameters
        print(f"3. Calling ShoppingSearchTool with: cityName='{expected_category.cityName}', category='{expected_category.parameters.get('category')}'")
        
        results = shopping_tool._run(
            cityName=expected_category.cityName,
            category=expected_category.parameters.get('category')
        )

        # 6. Verify Results
        print(f"4. Tool returned {len(results)} results")
        for res in results:
            print(f"   - Found: {res['shops']} ({res['famousFor']}) at {res['address']}")

        # Assertions
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["shops"], "Select Citywalk")
        
        # Verify DB Tool was initialized correctly
        MockDBTool.assert_called_with(collection_name="shoppings")
        
        # Verify DB Query was correct
        expected_filter = {
            "cityName": {"$regex": "Delhi", "$options": "i"},
            "category": {"$regex": "malls", "$options": "i"}
        }
        mock_db_instance._run.assert_called_with(
            query_filter=expected_filter,
            limit=50
        )
        print("--- Test Passed Successfully ---")

if __name__ == '__main__':
    unittest.main()
