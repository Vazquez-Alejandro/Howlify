from scraper.despegar import hunt_despegar_vuelos

# La URL de "Todos los meses" que pasaste
url_pro = "https://www.despegar.com.ar/vuelos/bue/mad/vuelos-a-madrid-desde-buenos+aires?from=SB&di=1&currency=USD"

print("🐺 INICIANDO TEST DEL LOBO PRO EN TERMINAL...")

# Probamos con un presupuesto de 1000 USD
# Pasamos es_pro=True para que entre a la nueva función
resultados = hunt_despegar_vuelos(url_pro, keyword="MAD", max_price=1000, es_pro=True)

print("-" * 30)
if resultados:
    print(f"✅ ¡ÉXITO! El Lobo encontró {len(resultados)} meses que entran en el presupuesto:")
    for res in resultados:
        print(f"👉 {res['title']}: USD {res['price']} (Ganga: {res['is_ganga']})")
else:
    print("❌ No se encontraron resultados. Puede que los precios superen los 1000 USD o el selector falló.")
print("-" * 30)