"""
Create Supabase tables using Supabase Management API and direct SQL execution
"""
import os
from pathlib import Path
from dotenv import load_dotenv
import sys
import requests

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

def create_tables_via_api():
    """
    Create tables by executing SQL through Supabase REST API
    Uses a workaround by creating records that will auto-create tables
    """
    from supabase import create_client
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("🔧 Attempting to create tables via Supabase client...")
    
    # Since we can't execute raw SQL, we'll need to use Supabase dashboard
    # But let's try to access the SQL editor API endpoint
    
    project_ref = SUPABASE_URL.split('//')[1].split('.')[0]
    sql_api_url = f"https://{project_ref}.supabase.co/rest/v1/rpc/exec_sql"
    
    migration_file = ROOT_DIR / 'migrations' / '001_create_tables.sql'
    with open(migration_file, 'r') as f:
        sql = f.read()
    
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json'
    }
    
    # Try to call exec_sql function if it exists
    try:
        response = requests.post(
            sql_api_url,
            headers=headers,
            json={'query': sql}
        )
        print(f"Response: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"API call failed: {str(e)}")
    
    return False

def verify_tables():
    """Check if tables exist using Supabase client"""
    from supabase import create_client
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    tables = ['uploads', 'invoice_lines', 'gstr_exports']
    existing = []
    
    print("\n🔍 Checking for existing tables...")
    for table in tables:
        try:
            result = supabase.table(table).select('*').limit(1).execute()
            existing.append(table)
            print(f"   ✅ Table '{table}' exists")
        except Exception as e:
            if 'PGRST205' in str(e) or 'not found' in str(e).lower():
                print(f"   ❌ Table '{table}' not found")
            else:
                print(f"   ⚠️  Error: {str(e)}")
    
    return len(existing) == len(tables)

def print_instructions():
    """Print manual instructions"""
    print("\n" + "=" * 70)
    print("📋 PLEASE RUN THE MIGRATION MANUALLY")
    print("=" * 70)
    print("\nSince direct SQL execution is not available through the API,")
    print("please complete these quick steps:\n")
    print("1. Open: https://supabase.com/dashboard/project/cuqvhbyymoeeiumqbfge/editor")
    print("2. Click 'SQL Editor' in the left sidebar")
    print("3. Click 'New Query'")
    print("4. Copy the SQL below and paste it:")
    print("\n" + "─" * 70)
    
    migration_file = ROOT_DIR / 'migrations' / '001_create_tables.sql'
    with open(migration_file, 'r') as f:
        print(f.read())
    
    print("─" * 70)
    print("\n5. Click 'Run' (or press Cmd/Ctrl + Enter)")
    print("6. Come back and let me know when done!")
    print("=" * 70)

if __name__ == '__main__':
    print("=" * 70)
    print("GST Filing Automation - Table Creation")
    print("=" * 70)
    
    # Check if tables already exist
    if verify_tables():
        print("\n✅ All tables already exist! Database is ready.")
        sys.exit(0)
    
    # Try API creation
    print("\n⚠️  Tables not found. Attempting creation...")
    create_tables_via_api()
    
    # Check again
    if not verify_tables():
        print_instructions()
        sys.exit(1)
    else:
        print("\n✅ Tables created successfully!")
        sys.exit(0)
