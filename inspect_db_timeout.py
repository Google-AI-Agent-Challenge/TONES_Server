import os
import httpx
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not supabase_url or not supabase_key:
    print("Error: Supabase environment variables not found.")
    exit(1)

print(f"Connecting to Supabase at {supabase_url}...")
# Create a custom httpx client with a short timeout
http_client = httpx.Client(timeout=3.0)
supabase = create_client(supabase_url, supabase_key, options=None)
# Manually override the postgrest client timeout if possible, or just run a direct request
try:
    # Let's perform a direct HTTP request to Postgrest to inspect columns
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}"
    }
    url = f"{supabase_url}/rest/v1/reviews?limit=1"
    response = httpx.get(url, headers=headers, timeout=3.0)
    print("Response Status:", response.status_code)
    if response.status_code == 200:
        data = response.json()
        if data:
            print("Columns in live database:")
            print(data[0].keys())
        else:
            print("Table reviews is empty. Let's try to query table definition or schemas.")
            # Querying list of columns from public schema via postgres API or a simple request
            print("Response text:", response.text)
    else:
        print("Response Error:", response.text)
except Exception as e:
    print(f"Error querying Supabase directly: {e}")
