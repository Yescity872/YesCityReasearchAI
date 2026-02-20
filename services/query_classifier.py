# from asyncio import timeout
import os
import json
import time
from typing import Dict, Optional
from pydantic import BaseModel
from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

class QueryCategory(BaseModel):
    category:str
    cityName:Optional[str]=None
    parameters:Dict[str,str]={}

class QueryClassifier:
    def __init__(self):
        # Ollama_url=os.getenv("OLLAMA_BASE_URL","http://localhost:11434")
        # model="llama3.2:3b"
        # # model="qwen2.5:7b"

        # self.llm=Ollama(
        #     base_url=Ollama_url,
        #     model=model,
        #     temperature=0.1,
        #     timeout=6000,
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

        self.categories=[
            "foods",
            "accomodation",
            "activities",
            "transport", # local transport + connectivities
            "shoppings",
            "places", # hidden gems + places to visit + nearby tourist places
            "others", # misc + cityinfo
        ]

        self.prompt_template=PromptTemplate(

            input_variables=["query","categories"],
            template="""
                You are a travel query classifier for YesCity travel assistant.

                    COLLECTIONS in database:
                    1. foods - restaurants, cafes, street food, local delicacies
                    2. accommodations - rooms, hotels, hostels, guesthouses, vacation rentals, stays
                    3. activities - things to do, experinces
                    4. localtransports - local transportation, public transport, taxis, bike rentals, connectivities
                    5. places - popular tourist attractions, landmarks, must-see places, lesser known local spots, off-the-beaten-path places, unique spots
                    6. shoppings - markets, malls, shopping streets, local products, shops, souvenirs
                    7. others

                    classify this user query into ONE category from: {categories}

                    Also extract:
                    1. The city name ( extracted from query if mentioned)
                    2. key parameters relevant to the category

                    User Query: "{query}"

                    Respond ONLY with valid JSON in this exact format:
                    {{
                        "category":"category_name",
                        "cityName":"city_name_or_null",
                        "parameters":
                        {{
                            "param1":"value1",
                            "param2":"value2"
                        }},
                        "confidence":confidence_score_between_0_and_1
                    }}

                    Example response for "Find pizza places in Agra":
                    {{
                        "category":"foods",
                        "cityName":"Agra",
                        "parameters":
                        {{
                            "category": "pizza",
                            "food_type": "restaurant"
                        }},
                        "confidence":0.95
                    }}

                    IMPORTANT: If city is not mentioned, use "cityName": null
            """
        )

    def classify_query(self,user_query:str)->QueryCategory:
        
        start_time = time.time()
        
        try:
            prompt=self.prompt_template.format(
                query=user_query,
                categories=",".join(self.categories)
            )

            response=self.llm.invoke(prompt)

            # ✅ FIX: Extract content from AIMessage
            if hasattr(response, 'content'):
                response_text = response.content
            else:
                response_text = str(response)
            
            # Clean up response
            response_text = response_text.strip()
            
            # Remove any markdown code blocks if present
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            elif response_text.startswith('```'):
                response_text = response_text[3:]
            
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            end_time = time.time()
            response_time = end_time - start_time
            print(f"Response Time: {response_time:.2f} seconds")
            print(f"Response : {response_text}")

            try:
                data=json.loads(response_text)
                return QueryCategory(**data)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON from LLM: {e}")
        except Exception as e:
            raise ValueError(f"Error classifying query: {e}")

query_classifier=QueryClassifier()