import os
import json
import time
from typing import Dict, Any, List
from langchain_community.llms import Ollama
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from tools.transport_tool import transport_search_tool
from utils.formatting import format_tool_results

load_dotenv()

class TransportWrapper:
    def __init__(self):
        # self.llm=Ollama(
        #     base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        #     model="llama3.2:3b",
        #     temperature=0.1,
        #     num_ctx=8192
        # )

        self.llm = ChatGroq(
            groq_api_key=os.getenv("GROQ_API_KEY"),
            model_name="llama-3.1-8b-instant",
            temperature=0.1,
            max_tokens=1024,
            model_kwargs={
                "top_p": 0.9,
                "frequency_penalty": 0.1,
                "presence_penalty": 0.1
            }
        )

    def run_transport_flow(self,city_name:str,parameters:Dict[str,str],user_query:str,category:str)->str:
        
        print("Executing Transport Search Wrapper")
        start_time=time.time()

        print("transport in city ",city_name)

        category=category

        print(f"   🔎 Filter Category: {category}")

        results=transport_search_tool._run(
            cityName=city_name,
            category=category,
            maxResults=50
        )

        results_text=format_tool_results(results)

        print(" Transport Wrapper : Generating response")

        system_prompt="""
        You are a helpful travel assistant specialized in Transport.
        
        IMPORTANT: You must response with a RAW JSON object ONLY. No markdown formatting, no code blocks, no explanation text.
        
        Goal: Recommend top 3 transportaions from the provided database results based on the user's query.

        OUTPUT FORMAT:
        {
            "recommendations": [
                {"_id": "unique_id_string", "transport name/nearestAirportStationBusStand
": "transport/Place Name", "reason": "Why this matches"},
                {"_id": "unique_id_string", "transport name/nearestAirportStationBusStand
": "transport/Place Name", "reason": "Why this matches"}
            ]
        }

        RULES:
        1. Each recommendation must have "_id" (as string) and "transport name/nearestAirportStationBusStand".
        2. Maximum 3 recommendations.
        3. Valid JSON only.
        """

        full_prompt=f"""
        {system_prompt}
        
        User Query: "{user_query}"
        
        Database Results:
        {results_text}
        
        Generate JSON response:
        """

        try:
            response=self.llm.invoke(full_prompt)
            if hasattr(response,'content'):
                response_text=response.content
            else:
                response_text=str(response)

            response_text=response_text.strip()

            if response_text.startswith('```json'):
                response_text=response_text[7:]
            elif response_text.startswith('```'):
                response_text=response_text[3:]
            
            if response_text.endswith('```'):
                response_text=response_text[:-3]
            
            response_text=response_text.strip()

            try:
                json.loads(response_text)
                print(f"✅ Valid JSON response generated")
            except json.JSONDecodeError as e:
                print(f"⚠️ Response is not valid JSON, attempting to fix...")
                # Try to extract JSON from the response using regex
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group()
                    # Validate again
                    json.loads(response_text)
                    print(f"✅ Fixed JSON response")
                else:
                    # If no JSON found, create a fallback response
                    print(f"❌ Could not extract valid JSON")
                    response_text = json.dumps({
                        "recommendations": [],
                        "error": "Could not generate valid recommendations"
                    })
            
            end_time = time.time()
            print(f"Response Time: {end_time - start_time:.2f} seconds")
            
            # ✅ Return the string, not the AIMessage object
            return response_text
            
        except Exception as e:
            print(f"❌ LLM Error in transport Wrapper: {e}")
            # Return a proper JSON error string
            return json.dumps({
                "error": "Failed to generate response",
                "recommendations": [],
                "error_details": str(e)
            })

transport_wrapper=TransportWrapper()