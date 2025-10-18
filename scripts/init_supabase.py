#!/usr/bin/env python3
"""
Script to initialize Supabase database tables
Run this once to create the database schema
"""
import os
from supabase import create_client
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent / 'backend'
load_dotenv(ROOT_DIR / '.env')

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Read SQL schema
with open(ROOT_DIR / 'supabase_schema.sql', 'r') as f:
    sql_schema = f.read()

print("Initializing Supabase database...")
print(f"URL: {SUPABASE_URL}")
print("\nPlease run the following SQL in your Supabase SQL Editor:")
print("=" * 80)
print(sql_schema)
print("=" * 80)
print("\nAfter running the SQL, your database will be ready!")
print("\nTo access Supabase SQL Editor:")
print(f"1. Go to: {SUPABASE_URL.replace('.supabase.co', '.supabase.co/project/_/sql/new')}")
print("2. Paste the SQL schema above")
print("3. Click 'Run'")
