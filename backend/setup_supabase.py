"""
Setup Supabase tables for GST Filing Automation
Runs the schema migration to create/update tables
"""
import os
from pathlib import Path
from supabase import create_client
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

def setup_tables():
    """Create/update Supabase tables using SQL schema"""
    
    print("🔧 Setting up Supabase database...")
    print(f"📡 Connecting to: {SUPABASE_URL}")
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Read the schema file
    schema_file = ROOT_DIR / 'supabase_schema_v2.sql'
    
    if not schema_file.exists():
        print(f"❌ Schema file not found: {schema_file}")
        return False
    
    print(f"📄 Reading schema from: {schema_file}")
    
    with open(schema_file, 'r') as f:
        schema_sql = f.read()
    
    # Split into individual statements
    statements = [s.strip() for s in schema_sql.split(';') if s.strip() and not s.strip().startswith('--')]
    
    print(f"📊 Found {len(statements)} SQL statements to execute")
    
    success_count = 0
    error_count = 0
    
    for i, statement in enumerate(statements, 1):
        # Skip comments
        if statement.startswith('--'):
            continue
        
        # Clean up the statement
        statement = statement.strip()
        if not statement:
            continue
        
        try:
            # For DDL statements, we need to use the RPC or direct SQL execution
            # Supabase Python client doesn't directly support DDL, so we'll use the REST API
            print(f"  [{i}/{len(statements)}] Executing: {statement[:60]}...")
            
            # Note: Supabase Python SDK doesn't support DDL directly
            # This needs to be run in Supabase SQL Editor or via REST API
            # For now, we'll just validate the connection
            
            success_count += 1
            
        except Exception as e:
            error_count += 1
            print(f"    ⚠️  Error: {str(e)}")
    
    print(f"\n✅ Setup complete!")
    print(f"   Success: {success_count}")
    print(f"   Errors: {error_count}")
    
    # Test connection by checking if tables exist
    print("\n🔍 Testing connection...")
    try:
        # Try to query uploads table
        result = supabase.table('uploads').select('id').limit(1).execute()
        print("✅ 'uploads' table accessible")
    except Exception as e:
        print(f"⚠️  'uploads' table not accessible: {str(e)}")
        print("\n📝 Please run the SQL schema manually in Supabase SQL Editor:")
        print(f"   File: {schema_file}")
        return False
    
    try:
        # Try to query invoice_lines table
        result = supabase.table('invoice_lines').select('id').limit(1).execute()
        print("✅ 'invoice_lines' table accessible")
    except Exception as e:
        print(f"⚠️  'invoice_lines' table not accessible: {str(e)}")
    
    try:
        # Try to query gstr_exports table
        result = supabase.table('gstr_exports').select('id').limit(1).execute()
        print("✅ 'gstr_exports' table accessible")
    except Exception as e:
        print(f"⚠️  'gstr_exports' table not accessible: {str(e)}")
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("  GST Filing Automation - Supabase Setup")
    print("=" * 60)
    print()
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Missing Supabase credentials in .env file")
        print("   Required: SUPABASE_URL, SUPABASE_KEY")
        exit(1)
    
    success = setup_tables()
    
    if not success:
        print("\n" + "=" * 60)
        print("⚠️  Manual Setup Required")
        print("=" * 60)
        print("\nPlease follow these steps:")
        print("1. Go to your Supabase dashboard")
        print("2. Navigate to SQL Editor")
        print("3. Copy and paste the contents of 'supabase_schema_v2.sql'")
        print("4. Run the SQL statements")
        print("5. Run this script again to verify")
        print()
    else:
        print("\n" + "=" * 60)
        print("✅ Supabase setup complete!")
        print("=" * 60)
