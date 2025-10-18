"""
Supabase database client for GST Filing Automation
Replaces MongoDB with Supabase PostgreSQL
"""
import os
from supabase import create_client, Client
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Supabase configuration
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

# Create Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


async def init_database():
    """
    Initialize Supabase tables if they don't exist
    
    Tables:
    1. uploads - Store upload metadata
    2. invoice_lines - Store parsed invoice line items
    3. gstr_exports - Store generated GSTR JSON files
    """
    # Note: Tables should be created in Supabase dashboard or via SQL migration
    # This function is a placeholder for any initialization logic needed
    pass


class SupabaseUploads:
    """Handle uploads table operations"""
    
    @staticmethod
    async def create(upload_data: dict):
        """Create new upload record"""
        result = supabase.table('uploads').insert(upload_data).execute()
        return result.data[0] if result.data else None
    
    @staticmethod
    async def find_one(upload_id: str):
        """Find upload by ID"""
        result = supabase.table('uploads').select('*').eq('id', upload_id).execute()
        return result.data[0] if result.data else None
    
    @staticmethod
    async def update(upload_id: str, update_data: dict):
        """Update upload record"""
        result = supabase.table('uploads').update(update_data).eq('id', upload_id).execute()
        return result.data[0] if result.data else None
    
    @staticmethod
    async def find_all(limit: int = 100):
        """Get all uploads"""
        result = supabase.table('uploads').select('*').order('upload_date', desc=True).limit(limit).execute()
        return result.data


class SupabaseInvoiceLines:
    """Handle invoice_lines table operations"""
    
    @staticmethod
    async def insert_many(invoice_lines: list):
        """Insert multiple invoice lines"""
        if not invoice_lines:
            return []
        result = supabase.table('invoice_lines').insert(invoice_lines).execute()
        return result.data
    
    @staticmethod
    async def find_by_upload(upload_id: str):
        """Find all invoice lines for an upload"""
        result = supabase.table('invoice_lines').select('*').eq('upload_id', upload_id).execute()
        return result.data
    
    @staticmethod
    async def count(upload_id: str):
        """Count invoice lines for an upload"""
        result = supabase.table('invoice_lines').select('id', count='exact').eq('upload_id', upload_id).execute()
        return result.count


class SupabaseGSTRExports:
    """Handle gstr_exports table operations"""
    
    @staticmethod
    async def insert(export_data: dict):
        """Insert GSTR export"""
        result = supabase.table('gstr_exports').insert(export_data).execute()
        return result.data[0] if result.data else None
    
    @staticmethod
    async def find_by_upload(upload_id: str):
        """Find all exports for an upload"""
        result = supabase.table('gstr_exports').select('*').eq('upload_id', upload_id).execute()
        return result.data


# Export instances
uploads_collection = SupabaseUploads()
invoice_lines_collection = SupabaseInvoiceLines()
gstr_exports_collection = SupabaseGSTRExports()
