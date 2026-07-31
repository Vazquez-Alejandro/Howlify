# howlify/config.py

PLANS_PUBLIC = ["starter", "pro"]  
PLAN_DEFAULT = "starter" 

PLAN_LIMITS = {
    "starter": {
        "max_cazas_activas": 5,
        "min_interval_minutes": 100,
        "stores": ["mercadolibre", "generic"],
        "features": {
            "whatsapp": False,
            "telegram": True,
            "vuelos_anuales": False,
            "reporte_diario": False,
            "export_csv": False,
        },
    },
    "pro": {
        "max_cazas_activas": 15,
        "min_interval_minutes": 30,
        "stores": ["mercadolibre", "generic", "duffel", "despegar", "airbnb"],
        "features": {
            "whatsapp": True,
            "telegram": True,
            "vuelos_anuales": True,
            "reporte_diario": False,
            "export_csv": True,
        },
    },
}