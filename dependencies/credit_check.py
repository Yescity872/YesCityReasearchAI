import os
from datetime import datetime, timezone
from fastapi import Request, HTTPException
from pymongo import ReturnDocument

from database.mongodb_client import mongodb_client

MAX_CREDITS = 100

def get_today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

async def check_and_deduct_credits(request: Request) -> int:
    """
    Middleware/dependency logic to check if user (ip_address) has enough credits.
    Reduces the credit by 1 if credits are > 0.
    Throws 429 if the daily limit is reached.
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(',')[0].strip()
    else:
        client_ip = request.client.host if request.client else "unknown"
        
    db = mongodb_client.db
    if db is None:
        # Failsafe if DB connection isn't working for some reason
        return MAX_CREDITS

    credits_collection = db["credits"]
    today_str = get_today_str()

    doc = credits_collection.find_one({"ip_address": client_ip})

    if not doc:
        # Create brand new record, one query consumed
        user_credits = MAX_CREDITS - 1
        credits_collection.insert_one({
            "ip_address": client_ip,
            "credits": user_credits,
            "date": today_str,
            "last_updated": datetime.now(timezone.utc)
        })
        return user_credits
    else:
        if doc.get("date") != today_str:
            # Older date: reset to 100 - 1
            user_credits = MAX_CREDITS - 1
            credits_collection.update_one(
                {"_id": doc["_id"]},
                {
                    "$set": {
                        "date": today_str,
                        "credits": user_credits,
                        "last_updated": datetime.now(timezone.utc)
                    }
                }
            )
            return user_credits
        else:
            # Same day
            current_credits = doc.get("credits", 0)
            if current_credits <= 0:
                raise HTTPException(status_code=429, detail="Daily limit reached")
            
            updated_doc = credits_collection.find_one_and_update(
                {"_id": doc["_id"], "credits": {"$gt": 0}, "date": today_str},
                {
                    "$inc": {"credits": -1},
                    "$set": {"last_updated": datetime.now(timezone.utc)}
                },
                return_document=ReturnDocument.AFTER
            )
            
            if not updated_doc:
                raise HTTPException(status_code=429, detail="Daily limit reached")
                
            return updated_doc["credits"]
