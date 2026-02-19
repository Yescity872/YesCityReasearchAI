import os
import sys
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.mongodb_client import mongodb_client
from routes.search_routes import search_router

load_dotenv()

# Initialize FastAPI
app = FastAPI(title="YesCity Search API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response
class SearchRequest(BaseModel):
    query: str

class SearchResponse(BaseModel):
    response: str
    status: str
    query: str

class ErrorResponse(BaseModel):
    error: str
    status: str

@app.head('/')
def root_head():
    return "YesCityAI api is running"

# Startup event
@app.on_event("startup")
async def startup_event():
    try:
        if mongodb_client.db is None:
            print("❌ Failed to connect to database.")
    except Exception as e:
        print(f"❌ Database error: {e}")

# Search endpoint
@app.post("/api/search", response_model=SearchResponse, responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def api_search(request: SearchRequest):
    """
    Search endpoint for YesCity.
    Send a POST request with JSON body: {"query": "your search query"}
    """
    try:
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        # Call your existing search function
        response = search_router.handle_request(request.query)
        
        return SearchResponse(
            response=response,
            status="success",
            query=request.query
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# GET endpoint for simple queries
@app.get("/api/search", response_model=SearchResponse)
async def api_search_get(q: Optional[str] = None):
    """
    GET endpoint for search.
    Usage: /api/search?q=your+query
    """
    try:
        if not q or not q.strip():
            raise HTTPException(status_code=400, detail="Query parameter 'q' is required")
        
        response = search_router.handle_request(q)
        
        return SearchResponse(
            response=response,
            status="success",
            query=q
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Health check

@app.get("/")
async def root():
    return {"message": "Welcome to YesCity Search API"}

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected" if mongodb_client.db is not None else "disconnected",
        "version": "1.0.0"
    }



if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
    