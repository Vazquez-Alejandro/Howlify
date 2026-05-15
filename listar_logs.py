import os
from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_ANON_KEY")
supabase = create_client(url, key)

res = supabase.table("infracciones_log") \
    .select("caza_id, status, error, url_captura, fecha") \
    .order("fecha", desc=True) \
    .limit(10) \
    .execute()

print("Últimos registros en infracciones_log:")
for row in res.data:
    print(f"- caza_id={row['caza_id']} | status={row['status']} | error={row['error']} | captura={row['url_captura']} | fecha={row['fecha']}")
