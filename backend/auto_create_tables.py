"""
Direct connection to Supabase PostgreSQL to run migration
"""
import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from urllib.parse import quote_plus

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

SUPABASE_URL = os.environ.get('SUPABASE_URL')
DB_PASSWORD = "Kaddu@Anshu"

def create_tables():
    """Connect to Supabase and create tables"""
    
    # Extract project reference from URL
    project_ref = SUPABASE_URL.split('//')[1].split('.')[0]
    
    # Supabase direct connection parameters
    # Format: host.region.supabase.co
    host = f"db.{project_ref}.supabase.co"
    
    # URL encode password for special characters
    encoded_password = quote_plus(DB_PASSWORD)
    
    # Build connection string
    conn_string = f"postgresql://postgres:{encoded_password}@{host}:5432/postgres"
    
    print("=" * 70)
    print("🔗 Connecting to Supabase PostgreSQL...")
    print(f"   Project: {project_ref}")
    print(f"   Host: {host}")
    print("=" * 70)
    
    try:
        # Connect
        conn = psycopg2.connect(conn_string)
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("✅ Connected successfully!")
        
        # Read migration SQL
        migration_file = ROOT_DIR / 'migrations' / '001_create_tables.sql'
        with open(migration_file, 'r') as f:
            sql = f.read()
        
        print("\n🚀 Executing migration...")
        
        # Execute SQL
        cursor.execute(sql)
        
        print("✅ Migration executed!")
        
        # Verify tables
        print("\n🔍 Verifying tables...")
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('uploads', 'invoice_lines', 'gstr_exports')
            ORDER BY table_name;
        """)
        
        tables = cursor.fetchall()
        print(f"\n📊 Found {len(tables)} tables:")
        for table in tables:
            print(f"   ✅ {table[0]}")
        
        cursor.close()
        conn.close()
        
        if len(tables) == 3:
            print("\n" + "=" * 70)
            print("🎉 SUCCESS! Database is ready!")
            print("=" * 70)
            return True
        else:
            print("\n⚠️ Warning: Expected 3 tables, found", len(tables))
            return False
            
    except psycopg2.OperationalError as e:
        error_msg = str(e)
        print(f"\n❌ Connection Error: {error_msg}")
        
        if "could not translate host name" in error_msg:
            print("\n💡 Trying alternative connection method...")
            # Try with IPv4 pooler
            return try_pooler_connection(project_ref, encoded_password)
        else:
            print("\n💡 This might be a connection issue. Let me try another approach...")
            return try_pooler_connection(project_ref, encoded_password)
    
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False

def try_pooler_connection(project_ref, encoded_password):
    """Try connection using transaction pooler"""
    print("\n🔄 Attempting connection via pooler...")
    
    # Try pooler connection
    pooler_host = f"aws-0-us-west-1.pooler.supabase.com"
    conn_string = f"postgresql://postgres.{project_ref}:{encoded_password}@{pooler_host}:6543/postgres"
    
    print(f"   Host: {pooler_host}")
    
    try:
        conn = psycopg2.connect(conn_string)
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("✅ Connected via pooler!")
        
        # Read and execute migration
        migration_file = Path(__file__).parent / 'migrations' / '001_create_tables.sql'
        with open(migration_file, 'r') as f:
            sql = f.read()
        
        print("🚀 Executing migration...")
        cursor.execute(sql)
        
        print("✅ Migration executed!")
        
        cursor.close()
        conn.close()
        
        print("\n🎉 SUCCESS!")
        return True
        
    except Exception as e:
        print(f"❌ Pooler connection failed: {str(e)}")
        return False

if __name__ == '__main__':
    success = create_tables()
    
    if not success:
        print("\n" + "=" * 70)
        print("⚠️  Automated connection didn't work")
        print("=" * 70)
        print("\nLet's try the manual approach - it only takes 1 minute:")
        print("\n1. Open: https://supabase.com/dashboard/project/cuqvhbyymoeeiumqbfge/editor")
        print("2. Click 'SQL Editor' → 'New Query'")
        print("3. Copy SQL from: /app/backend/migrations/001_create_tables.sql")
        print("4. Paste and click 'Run'")
        print("\nThat's it! 🚀")
