"""
Enhanced Supabase client with Auth, Storage, and Realtime support
"""
import os
import logging
from supabase import create_client, Client
from dotenv import load_dotenv
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Supabase configuration
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', SUPABASE_KEY)  # Use service role key if available

logger = logging.getLogger(__name__)

# Create Supabase clients
try:
    # Regular client for authenticated requests
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Service role client for admin operations (bypasses RLS)
    supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    
    logger.info(f"✅ Supabase clients connected to {SUPABASE_URL}")
except Exception as e:
    logger.error(f"❌ Failed to create Supabase client: {str(e)}")
    raise


class SupabaseAuth:
    """Handle Supabase authentication operations"""
    
    @staticmethod
    def sign_up(email: str, password: str, metadata: dict = None):
        """Sign up a new user"""
        try:
            response = supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": metadata or {}
                }
            })
            return response
        except Exception as e:
            logger.error(f"Sign up error: {str(e)}")
            raise
    
    @staticmethod
    def sign_in(email: str, password: str):
        """Sign in with email and password"""
        try:
            response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            return response
        except Exception as e:
            logger.error(f"Sign in error: {str(e)}")
            raise
    
    @staticmethod
    def sign_out():
        """Sign out current user"""
        try:
            response = supabase.auth.sign_out()
            return response
        except Exception as e:
            logger.error(f"Sign out error: {str(e)}")
            raise
    
    @staticmethod
    def get_user(access_token: str):
        """Get user from access token"""
        try:
            response = supabase.auth.get_user(access_token)
            return response
        except Exception as e:
            logger.error(f"Get user error: {str(e)}")
            raise
    
    @staticmethod
    def refresh_session(refresh_token: str):
        """Refresh user session"""
        try:
            response = supabase.auth.refresh_session(refresh_token)
            return response
        except Exception as e:
            logger.error(f"Refresh session error: {str(e)}")
            raise


class SupabaseStorage:
    """Handle Supabase Storage operations"""
    
    BUCKET_NAME = "gst-uploads"
    
    @staticmethod
    def upload_file(file_path: str, file_content: bytes, user_id: str, content_type: str = "application/octet-stream"):
        """Upload file to Supabase Storage"""
        try:
            # Create user-specific path
            storage_path = f"{user_id}/{file_path}"
            
            response = supabase_admin.storage.from_(SupabaseStorage.BUCKET_NAME).upload(
                storage_path,
                file_content,
                {
                    "content-type": content_type,
                    "upsert": "true"
                }
            )
            
            # Get public URL
            url = supabase_admin.storage.from_(SupabaseStorage.BUCKET_NAME).get_public_url(storage_path)
            
            return {
                "path": storage_path,
                "url": url,
                "size": len(file_content)
            }
        except Exception as e:
            logger.error(f"Upload file error: {str(e)}")
            raise
    
    @staticmethod
    def download_file(file_path: str):
        """Download file from Supabase Storage"""
        try:
            response = supabase_admin.storage.from_(SupabaseStorage.BUCKET_NAME).download(file_path)
            return response
        except Exception as e:
            logger.error(f"Download file error: {str(e)}")
            raise
    
    @staticmethod
    def delete_file(file_path: str):
        """Delete file from Supabase Storage"""
        try:
            response = supabase_admin.storage.from_(SupabaseStorage.BUCKET_NAME).remove([file_path])
            return response
        except Exception as e:
            logger.error(f"Delete file error: {str(e)}")
            raise
    
    @staticmethod
    def list_files(user_id: str):
        """List files for a user"""
        try:
            response = supabase_admin.storage.from_(SupabaseStorage.BUCKET_NAME).list(user_id)
            return response
        except Exception as e:
            logger.error(f"List files error: {str(e)}")
            raise


class SupabaseUploads:
    """Handle uploads table operations"""
    
    @staticmethod
    async def create(upload_data: dict, user_id: str = None):
        """Create new upload record"""
        # Set user_id to default if not provided (backward compatibility)
        if user_id:
            upload_data['user_id'] = user_id
        else:
            # Use default UUID for backward compatibility
            upload_data['user_id'] = '00000000-0000-0000-0000-000000000001'
        result = supabase_admin.table('uploads').insert(upload_data).execute()
        return result.data[0] if result.data else None
    
    @staticmethod
    async def find_one(upload_id: str):
        """Find upload by ID"""
        result = supabase_admin.table('uploads').select('*').eq('id', upload_id).execute()
        return result.data[0] if result.data else None
    
    @staticmethod
    async def find_by_user(user_id: str, limit: int = 100):
        """Find uploads by user"""
        result = supabase_admin.table('uploads').select('*').eq('user_id', user_id).order('upload_date', desc=True).limit(limit).execute()
        return result.data
    
    @staticmethod
    async def update(upload_id: str, update_data: dict):
        """Update upload record"""
        result = supabase_admin.table('uploads').update(update_data).eq('id', upload_id).execute()
        return result.data[0] if result.data else None
    
    @staticmethod
    async def find_all(limit: int = 100):
        """Get all uploads (admin only)"""
        result = supabase_admin.table('uploads').select('*').order('upload_date', desc=True).limit(limit).execute()
        return result.data
    
    @staticmethod
    async def delete(upload_id: str):
        """Delete upload (cascade deletes related records)"""
        result = supabase_admin.table('uploads').delete().eq('id', upload_id).execute()
        return result.data


class SupabaseInvoiceLines:
    """Handle invoice_lines table operations"""
    
    @staticmethod
    async def insert_many(invoice_lines: list, user_id: str = None):
        """Insert multiple invoice lines"""
        if not invoice_lines:
            return []
        
        # Add user_id to each line (default if not provided)
        default_user_id = '00000000-0000-0000-0000-000000000001'
        for line in invoice_lines:
            line['user_id'] = user_id if user_id else default_user_id
        
        result = supabase_admin.table('invoice_lines').insert(invoice_lines).execute()
        return result.data
    
    @staticmethod
    async def find_by_upload(upload_id: str):
        """Find all invoice lines for an upload"""
        result = supabase_admin.table('invoice_lines').select('*').eq('upload_id', upload_id).execute()
        return result.data
    
    @staticmethod
    async def find_by_user(user_id: str, limit: int = 1000):
        """Find invoice lines by user"""
        result = supabase_admin.table('invoice_lines').select('*').eq('user_id', user_id).limit(limit).execute()
        return result.data
    
    @staticmethod
    async def count(upload_id: str):
        """Count invoice lines for an upload"""
        result = supabase_admin.table('invoice_lines').select('id', count='exact').eq('upload_id', upload_id).execute()
        return result.count


class SupabaseGSTRExports:
    """Handle gstr_exports table operations"""
    
    @staticmethod
    async def insert(export_data: dict, user_id: str = None):
        """Insert GSTR export"""
        # Set user_id to default if not provided
        if user_id:
            export_data['user_id'] = user_id
        else:
            export_data['user_id'] = '00000000-0000-0000-0000-000000000001'
        result = supabase_admin.table('gstr_exports').insert(export_data).execute()
        return result.data[0] if result.data else None
    
    @staticmethod
    async def find_by_upload(upload_id: str):
        """Find all exports for an upload"""
        result = supabase_admin.table('gstr_exports').select('*').eq('upload_id', upload_id).execute()
        return result.data
    
    @staticmethod
    async def find_by_user(user_id: str, limit: int = 100):
        """Find exports by user"""
        result = supabase_admin.table('gstr_exports').select('*').eq('user_id', user_id).limit(limit).execute()
        return result.data


class SupabaseDocumentRanges:
    """Handle document_ranges table operations"""
    
    @staticmethod
    async def insert_many(ranges: list, user_id: str = None):
        """Insert multiple document ranges"""
        if not ranges:
            return []
        
        if user_id:
            for r in ranges:
                r['user_id'] = user_id
        
        result = supabase_admin.table('document_ranges').insert(ranges).execute()
        return result.data
    
    @staticmethod
    async def find_by_upload(upload_id: str):
        """Find all document ranges for an upload"""
        result = supabase_admin.table('document_ranges').select('*').eq('upload_id', upload_id).execute()
        return result.data


# Export instances
auth = SupabaseAuth()
storage = SupabaseStorage()
uploads_collection = SupabaseUploads()
invoice_lines_collection = SupabaseInvoiceLines()
gstr_exports_collection = SupabaseGSTRExports()
document_ranges_collection = SupabaseDocumentRanges()
