import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not supabase_url or not supabase_key:
    print("Error: Supabase environment variables not found.")
    exit(1)

supabase = create_client(supabase_url, supabase_key)

try:
    # Fetch one row from reviews to check its columns
    res = supabase.table("reviews").select("*").limit(1).execute()
    print("Reviews table schema / columns:")
    if res.data:
        print(res.data[0].keys())
    else:
        print("No data in reviews table. Checking structure by inserting/selecting...")
        # We can also fetch the table definition or run an empty select
        print("Columns from empty select:", res.data)
except Exception as e:
    print(f"Error querying Supabase: {e}")
