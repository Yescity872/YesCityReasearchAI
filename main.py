import os
import sys
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.mongodb_client import mongodb_client
from routes.search_routes import router as search_router
from routes.itinerary_routes import router as itinerary_router
from dependencies.credit_check import check_and_deduct_credits

load_dotenv()

# Initialize FastAPI
app = FastAPI(title="YesCity Search API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://www.yescity.in",
        "https://yescity.in",
        "http://localhost:3000" # Added localhost for local development just in case
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(itinerary_router, prefix="/api")
app.include_router(search_router, prefix="/api")

@app.head('/')
def root_head():
    return "YesCityAI api is running"

# Startup event
@app.on_event("startup")
async def startup_event():
    try:
        if mongodb_client.db is None:
            print("❌ Failed to connect to database.")
        else:
            # Setup credits collection indices
            try:
                db = mongodb_client.db
                db.credits.create_index("ip_address")
                # Expire documents after 30 days (2592000 seconds)
                db.credits.create_index("last_updated", expireAfterSeconds=2592000)
            except Exception as e:
                print(f"⚠️ Failed to create indexes: {e}")
    except Exception as e:
        print(f"❌ Database error: {e}")



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
    