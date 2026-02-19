import os
from langchain_community.llms import Ollama
from dotenv import load_dotenv

load_dotenv()

class LLMService:
    def __init__(self):
        self.generation_llm = Ollama(
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            model="llama3.2:3b",
            temperature=0.1,  # Lower temperature for valid JSON
            num_ctx=8192      # Request larger context window if supported
        )

    def generate_response(self, prompt: str) -> str:
        """Invokes the LLM with the given prompt."""
        try:
            response = self.generation_llm.invoke(prompt)
            return response
        except Exception as e:
            print(f"❌ LLM Error: {e}")
            return '{"error": "Failed to generate response"}'

# Global instance
llm_service = LLMService()
