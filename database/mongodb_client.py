import os
from typing import Optional
from pymongo.database import Database
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

class MongoDBClient:
    _instance:Optional["MongoDBClient"]=None
    _client:Optional[MongoClient]=None
    _db:Optional[Database]=None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDBClient, cls).__new__(cls)
            cls._instance._init_client()
        return cls._instance
    
    def _init_client(self):
        mongodb_uri = os.getenv("MONGODB_URI")
        if not mongodb_uri:
            raise ValueError("MONGODB_URI environment variable is not set.")
        database_name = os.getenv("MONGODB_DATABASE","YesCity3")

        try:
            self._client = MongoClient(mongodb_uri)
            self._db = self._client[database_name]
            print(f"✅ Connected to MongoDB: {database_name}")
            
            # Test connection by listing collections
            collections = self._db.list_collection_names()
            print(f"📊 Available collections: {len(collections)}")

        except Exception as e:
            print(f"❌ Failed to connect to MongoDB: {e}")
            raise

    @property
    def db(self) -> Database:
        if self._db is None:
            self._init_client()
        return self._db
    
    def get_collection(self,collection_name: str):
        if collection_name not in self.db.list_collection_names():
            print(f"⚠️ Collection '{collection_name}' not found")
        return self.db[collection_name]
    
    def get_foods_collection(self):
        """Get foods collection specifically."""
        return self.get_collection("foods")

    def close(self):
        """Close MongoDB connection."""
        if self._client:
            self._client.close()
            print("🔌 MongoDB connection closed.")

# Global instance
mongodb_client = MongoDBClient()