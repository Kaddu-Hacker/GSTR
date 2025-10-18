"""
Run database migrations for Supabase
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
import sys

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: SUPABASE_URL and SUPABASE_KEY must be set in .env file")
    sys.exit(1)

# Create Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def run_migration():
    """
    Run the SQL migration to create database tables
    """
    migration_file = ROOT_DIR / 'migrations' / '001_create_tables.sql'
    
    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        sys.exit(1)
    
    print(f"📂 Reading migration file: {migration_file}")
    with open(migration_file, 'r') as f:
        sql = f.read()
    
    print("🚀 Executing migration...")
    
    try:
        # Split SQL into individual statements
        statements = [s.strip() for s in sql.split(';') if s.strip() and not s.strip().startswith('--')]
        
        success_count = 0
        error_count = 0
        
        for i, statement in enumerate(statements):
            try:
                # Execute using Supabase's RPC or direct SQL execution
                # Note: Supabase Python client may not support direct SQL execution
                # You might need to run this in Supabase SQL Editor instead
                result = supabase.rpc('execute_sql', {'query': statement}).execute()
                success_count += 1
                print(f"✅ Statement {i+1}/{len(statements)} executed successfully")
            except Exception as e:
                error_count += 1
                print(f"⚠️  Statement {i+1}/{len(statements)} failed: {str(e)}")
                # Continue with other statements
        
        print(f"\n📊 Migration Summary:")
        print(f"   ✅ Successful: {success_count}")
        print(f"   ❌ Failed: {error_count}")
        
        if error_count == 0:
            print("\n🎉 Migration completed successfully!")
        else:
            print(f"\n⚠️  Migration completed with {error_count} error(s)")
            print("\n💡 Note: If direct SQL execution is not supported by Supabase Python client,")
            print("   please run the SQL file manually in Supabase SQL Editor:")
            print(f"   File: {migration_file}")
            
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        print("\n💡 Alternative approach:")
        print("   1. Go to your Supabase dashboard")
        print("   2. Navigate to SQL Editor")
        print("   3. Copy and paste the contents of:")
        print(f"      {migration_file}")
        print("   4. Click 'Run' to execute the migration")
        sys.exit(1)

def test_tables():
    """
    Test if tables were created successfully
    """
    print("\n🔍 Testing table creation...")
    
    tables = ['uploads', 'invoice_lines', 'gstr_exports']
    
    for table in tables:
        try:
            result = supabase.table(table).select('*').limit(1).execute()
            print(f"   ✅ Table '{table}' is accessible")
        except Exception as e:
            print(f"   ❌ Table '{table}' error: {str(e)}")

if __name__ == '__main__':
    print("=" * 60)
    print("GST Filing Automation - Database Migration")
    print("=" * 60)
    print(f"\n🔗 Supabase URL: {SUPABASE_URL}")
    print(f"🔑 Using service role key: {'*' * 10}{SUPABASE_KEY[-10:]}\n")
    
    print("\n⚠️  IMPORTANT NOTE:")
    print("=" * 60)
    print("Supabase Python client may not support direct SQL execution.")
    print("If this script fails, please run the migration manually:")
    print("\n1. Open Supabase Dashboard → SQL Editor")
    print("2. Copy contents from: /app/backend/migrations/001_create_tables.sql")
    print("3. Paste and execute in SQL Editor")
    print("=" * 60)
    print("\nPress Enter to continue or Ctrl+C to cancel...")
    input()
    
    run_migration()
    test_tables()
    
    print("\n✨ Done!")
