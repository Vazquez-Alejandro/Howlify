from supabase import create_client, Client

# Conexión a Supabase
url = "https://aqzkysgzljxqmckzfpfq.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFxemt5c2d6bGp4cW1ja3pmcGZxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzIxMTU4NTMsImV4cCI6MjA4NzY5MTg1M30.XDqg5IG1ES_4UWAuWxwdGws43siLhYkDZciIRVzr3Lc"
supabase: Client = create_client(url, key)

# Consultar los últimos 10 registros
res = supabase.table("infracciones_log") \
    .select("caza_id, status, error, url_captura, fecha") \
    .order("fecha", desc=True) \
    .limit(10) \
    .execute()

print("📋 Últimos registros en infracciones_log:")
for row in res.data:
    print(f"- caza_id={row['caza_id']} | status={row['status']} | error={row['error']} | captura={row['url_captura']} | fecha={row['fecha']}")
