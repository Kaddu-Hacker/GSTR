"""
MongoDB client as fallback when Supabase is not configured
"""
import os
import logging
from pymongo import MongoClient
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# MongoDB configuration
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017/')
DB_NAME = "gst_filing"

try:
    mongo_client = MongoClient(MONGO_URL)
    db = mongo_client[DB_NAME]
    logger.info(f"✅ MongoDB connected to {MONGO_URL}")
except Exception as e:
    logger.error(f"❌ Failed to connect to MongoDB: {str(e)}")
    raise


class MongoUploads:
    """MongoDB collection wrapper for uploads"""
    
    def __init__(self):
        self.collection = db["uploads"]
    
    async def create(self, data: Dict, user_id: str = "default_user"):
        """Insert a new upload"""
        data["user_id"] = user_id
        result = self.collection.insert_one(data)
        return str(result.inserted_id)
    
    async def find_one(self, upload_id: str):
        """Find upload by ID"""
        return self.collection.find_one({"id": upload_id})
    
    async def find_all(self):
        """Find all uploads"""
        return list(self.collection.find({}).limit(100))
    
    async def update(self, upload_id: str, update_data: Dict):
        """Update upload"""
        if isinstance(update_data, dict) and not any(key.startswith('$') for key in update_data.keys()):
            update_data = {"$set": update_data}
        self.collection.update_one({"id": upload_id}, update_data)


class MongoInvoiceLines:
    """MongoDB collection wrapper for invoice lines"""
    
    def __init__(self):
        self.collection = db["invoice_lines"]
    
    async def insert_many(self, documents: List[Dict], user_id: str = "default_user"):
        """Insert multiple invoice lines"""
        for doc in documents:
            doc["user_id"] = user_id
        if documents:
            self.collection.insert_many(documents)
    
    async def find_by_upload(self, upload_id: str):
        """Find invoice lines by upload ID"""
        return list(self.collection.find({"upload_id": upload_id}))
    
    async def count(self, upload_id: str):
        """Count invoice lines for upload"""
        return self.collection.count_documents({"upload_id": upload_id})


class MongoGSTRExports:
    """MongoDB collection wrapper for GSTR exports"""
    
    def __init__(self):
        self.collection = db["gstr_exports"]
    
    async def insert(self, data: Dict, user_id: str = "default_user"):
        """Insert GSTR export"""
        data["user_id"] = user_id
        result = self.collection.insert_one(data)
        return str(result.inserted_id)
    
    async def find_by_upload(self, upload_id: str):
        """Find exports by upload ID"""
        return list(self.collection.find({"upload_id": upload_id}))


class MongoDocumentRanges:
    """MongoDB collection wrapper for document ranges"""
    
    def __init__(self):
        self.collection = db["document_ranges"]
    
    async def insert_many(self, documents: List[Dict], user_id: str = "default_user"):
        """Insert multiple document ranges"""
        for doc in documents:
            doc["user_id"] = user_id
        if documents:
            self.collection.insert_many(documents)


class MockAuth:
    """Mock auth for when Supabase is not available"""
    
    @staticmethod
    def sign_up(email: str, password: str, metadata: dict = None):
        return {"user": {"id": "mock_user", "email": email}}
    
    @staticmethod
    def sign_in(email: str, password: str):
        return {"user": {"id": "mock_user", "email": email}, "session": {"access_token": "mock_token"}}


class MockStorage:
    """Mock storage for when Supabase is not available"""
    
    def upload_file(self, path: str, content: bytes, user_id: str, content_type: str):
        # Just return success - data will be stored in MongoDB
        return {"path": path, "url": f"mock://storage/{path}"}


# Export instances
uploads_collection = MongoUploads()
invoice_lines_collection = MongoInvoiceLines()
gstr_exports_collection = MongoGSTRExports()
document_ranges_collection = MongoDocumentRanges()
auth = MockAuth()
storage = MockStorage()

logger.info("✅ MongoDB collections initialized")
