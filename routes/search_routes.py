from typing import Dict, Any, List, Optional
# Import capabilities
from services.query_classifier import query_classifier, QueryCategory

# Wrappers
from wrappers.shopping_wrapper import shopping_wrapper
from wrappers.food_wrapper import food_wrapper
from wrappers.accomodation_wrapper import accomodation_wrapper

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
            
                
            else:
                print(f"⚠️ Tool for category '{classification.category}' is not implemented yet.")
                return '{"error": "Category not implemented"}'

        except Exception as e:
            print(f"❌ Router Error: {e}")
            return f'{{"error": "{str(e)}"}}'

search_router = SearchRouter()
