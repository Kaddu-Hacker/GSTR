"""
Verify that Supabase tables have been created
"""
import os
from dotenv import load_dotenv
from pathlib import Path
from supabase import create_client

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

def verify_tables():
    """Check if all required tables exist"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    tables = ['uploads', 'invoice_lines', 'gstr_exports']
    results = {}
    
    print("=" * 70)
    print("🔍 Verifying Supabase Database Tables")
    print("=" * 70)
    print()
    
    for table in tables:
        try:
            # Try to query the table
            result = supabase.table(table).select('*').limit(1).execute()
            results[table] = True
            print(f"✅ Table '{table}' exists and is accessible")
        except Exception as e:
            results[table] = False
            error_msg = str(e)
            if 'PGRST205' in error_msg or 'not found' in error_msg.lower():
                print(f"❌ Table '{table}' does not exist")
            else:
                print(f"⚠️  Table '{table}' error: {error_msg[:100]}")
    
    print()
    print("=" * 70)
    
    all_exist = all(results.values())
    
    if all_exist:
        print("✅ ✨ SUCCESS! All tables exist and are ready!")
        print()
        print("🚀 Your database is fully configured.")
        print("   You can now use the GST Filing Automation app.")
        print("=" * 70)
        return True
    else:
        missing = [t for t, exists in results.items() if not exists]
        print(f"❌ Missing tables: {', '.join(missing)}")
        print()
        print("⚠️  Please complete the SQL migration steps first.")
        print("   Run: bash /app/backend/show_migration_instructions.sh")
        print("=" * 70)
        return False

if __name__ == '__main__':
    verify_tables()
