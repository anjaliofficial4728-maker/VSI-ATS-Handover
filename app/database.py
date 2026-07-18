# app/database.py
"""
Database configuration and Supabase client initialization.
"""

from supabase import Client, create_client
from app.config import SUPABASE_URL, SUPABASE_KEY

# Initialize Supabase client
supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

# Verify connection on startup
try:
    print(f"✓ Supabase connected: {SUPABASE_URL[:50]}...")
except Exception as e:
    print(f"✗ Supabase connection error: {str(e)}")
    raise
