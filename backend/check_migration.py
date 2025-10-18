"""
Direct PostgreSQL migration runner for Supabase
Uses psycopg2 to execute SQL directly
"""
import os
from pathlib import Path
from dotenv import load_dotenv
import sys
from urllib.parse import urlparse

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: SUPABASE_URL and SUPABASE_KEY must be set in .env file")
    sys.exit(1)

def get_postgres_connection_string():
    """
    Extract Supabase project ref from URL and build PostgreSQL connection string
    """
    parsed = urlparse(SUPABASE_URL)
    project_ref = parsed.hostname.split('.')[0]
    
    # Supabase PostgreSQL connection format
    # You'll need to get the database password from Supabase dashboard
    return f"postgresql://postgres.[project_ref]:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres"

def run_migration_via_supabase_api():
    """
    Run migration using Supabase REST API
    """
    import requests
    
    migration_file = ROOT_DIR / 'migrations' / '001_create_tables.sql'
    
    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return False
    
    print(f"📂 Reading migration file: {migration_file}")
    with open(migration_file, 'r') as f:
        sql = f.read()
    
    print("🚀 Attempting to create tables using Supabase client...")
    
    try:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Test if tables exist by trying to query them
        tables = ['uploads', 'invoice_lines', 'gstr_exports']
        existing_tables = []
        
        for table in tables:
            try:
                supabase.table(table).select('*').limit(1).execute()
                existing_tables.append(table)
                print(f"   ℹ️  Table '{table}' already exists")
            except Exception as e:
                if 'relation' in str(e).lower() or 'not found' in str(e).lower():
                    print(f"   ❌ Table '{table}' does not exist")
                else:
                    print(f"   ⚠️  Error checking table '{table}': {str(e)}")
        
        if len(existing_tables) == len(tables):
            print("\n✅ All tables already exist!")
            return True
        else:
            print(f"\n⚠️  Found {len(existing_tables)}/{len(tables)} tables")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def print_manual_instructions():
    """
    Print instructions for manual migration
    """
    print("\n" + "=" * 70)
    print("📋 MANUAL MIGRATION REQUIRED")
    print("=" * 70)
    print("\nSince Supabase Python client doesn't support direct SQL execution,")
    print("please follow these steps to create the database tables:\n")
    print("1️⃣  Open your Supabase Dashboard")
    print(f"   URL: {SUPABASE_URL.replace('supabase.co', 'supabase.com')}")
    print("\n2️⃣  Navigate to: SQL Editor (in left sidebar)")
    print("\n3️⃣  Click 'New Query'")
    print("\n4️⃣  Copy the SQL from this file:")
    print(f"   📄 /app/backend/migrations/001_create_tables.sql")
    print("\n5️⃣  Paste into SQL Editor and click 'Run'")
    print("\n6️⃣  Verify tables were created by checking 'Table Editor'")
    print("\n" + "=" * 70)
    print("\n💡 TIP: You can also view the SQL file content here:")
    migration_file = ROOT_DIR / 'migrations' / '001_create_tables.sql'
    if migration_file.exists():
        with open(migration_file, 'r') as f:
            print("\n" + "-" * 70)
            print(f.read())
            print("-" * 70)

if __name__ == '__main__':
    print("=" * 70)
    print("GST Filing Automation - Database Migration Runner")
    print("=" * 70)
    print(f"\n🔗 Supabase URL: {SUPABASE_URL}")
    print(f"🔑 Using key: {'*' * 20}...{SUPABASE_KEY[-10:]}\n")
    
    # Check if tables exist
    tables_exist = run_migration_via_supabase_api()
    
    if not tables_exist:
        print_manual_instructions()
        print("\n⏳ After running the SQL in Supabase dashboard, run this script again to verify.")
        sys.exit(1)
    else:
        print("\n✅ Database is ready!")
        print("🚀 You can now start the backend server.")
        sys.exit(0)
