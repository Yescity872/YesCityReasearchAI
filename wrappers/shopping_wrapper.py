import os
from typing import Dict, Any, List
from langchain_community.llms import Ollama
from dotenv import load_dotenv

# Imports from project structure
from tools.shopping_tool import shopping_search_tool
from utils.formatting import format_tool_results

load_dotenv()

class ShoppingWrapper:
    def __init__(self):
        # Initialize LLM specifically for this wrapper
        self.llm = Ollama(
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            model="llama3.2:3b",
            temperature=0.1,
            num_ctx=8192
        )

    def run_shopping_flow(self, city_name: str, parameters: Dict[str, str], user_query: str,category:str) -> str:
        """
        Executes the full shopping search flow:
        1. Tool Execution
        2. Result Formatting
        3. LLM Response Generation
        """
        print("   🛍️  Shopping Wrapper: executing tool...")
        
        # 1. Execute Tool
        # User requested to avoid filtering by derived fields like product_type
        category = category
        
        print(f"   🔎 Filter Category: {category}")
        
        results = shopping_search_tool._run(
            cityName=city_name,
            category=category,
            maxResults=50
        )
        
        # 2. Format Results
        results_text = format_tool_results(results)
        
        # 3. Generate LLM Response
        print("   🛍️  Shopping Wrapper: generating response...")
        
        system_prompt = """You are a helpful travel assistant specialized in Shopping.
        
        IMPORTANT: You must response with a RAW JSON object ONLY. No markdown formatting, no code blocks, no explanation text.
        
        Goal: Recommend top 3 shopping places from the provided database results based on the user's query.

        OUTPUT FORMAT:
        {
            "recommendations": [
                {"_id": "unique_id_string", "shops": "Place Name", "reason": "Why this matches"},
                {"_id": "unique_id_string", "shops": "Place Name", "reason": "Why this matches"}
            ]
        }

        RULES:
        1. Each recommendation must have "_id" (as string) and "shops".
        2. Maximum 3 recommendations.
        3. Valid JSON only.
        """
        
        full_prompt = f"""
        {system_prompt}
        
        User Query: "{user_query}"
        
        Database Results:
        {results_text}
        
        Generate JSON response:
        """
        
        try:
            response = self.llm.invoke(full_prompt)
            return response
        except Exception as e:
            print(f"❌ LLM Error in Shopping Wrapper: {e}")
            return '{"error": "Failed to generate response", "recommendations": []}'

# Global Instance
shopping_wrapper = ShoppingWrapper()
