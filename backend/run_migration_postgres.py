"""
Direct PostgreSQL migration for Supabase
Connects to PostgreSQL and creates tables
"""
import os
from pathlib import Path
from dotenv import load_dotenv
import sys
import psycopg2
from urllib.parse import urlparse

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

SUPABASE_URL = os.environ.get('SUPABASE_URL')
DB_PASSWORD = "Kaddu@Anshu"  # Provided password

def get_connection_params():
    """Extract connection parameters from Supabase URL"""
    parsed = urlparse(SUPABASE_URL)
    project_ref = parsed.hostname.split('.')[0]
    
    # Try direct connection first
    return {
        'host': f'db.{project_ref}.supabase.co',
        'port': 5432,
        'database': 'postgres',
        'user': 'postgres',
        'password': DB_PASSWORD,
        'sslmode': 'require'
    }

def run_migration():
    """Run the SQL migration"""
    migration_file = ROOT_DIR / 'migrations' / '001_create_tables.sql'
    
    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return False
    
    print(f"📂 Reading migration file: {migration_file}")
    with open(migration_file, 'r') as f:
        sql = f.read()
    
    conn_params = get_connection_params()
    print(f"\n🔗 Connecting to PostgreSQL...")
    print(f"   Host: {conn_params['host']}")
    print(f"   Database: {conn_params['database']}")
    print(f"   User: {conn_params['user']}")
    
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(**conn_params)
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("✅ Connected successfully!")
        print("\n🚀 Executing migration SQL...")
        
        # Execute the entire SQL script
        cursor.execute(sql)
        
        print("✅ Migration executed successfully!")
        
        # Verify tables were created
        print("\n🔍 Verifying tables...")
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('uploads', 'invoice_lines', 'gstr_exports')
            ORDER BY table_name;
        """)
        
        tables = cursor.fetchall()
        if tables:
            print(f"✅ Found {len(tables)} tables:")
            for table in tables:
                print(f"   ✓ {table[0]}")
        else:
            print("⚠️  No tables found")
        
        cursor.close()
        conn.close()
        
        return len(tables) == 3
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == '__main__':
    print("=" * 70)
    print("GST Filing Automation - Database Migration")
    print("=" * 70)
    
    success = run_migration()
    
    if success:
        print("\n✅ ✨ Database migration completed successfully! ✨")
        print("\n🚀 All tables are ready. You can now start using the application.")
    else:
        print("\n❌ Migration failed. Please check the errors above.")
        sys.exit(1)
