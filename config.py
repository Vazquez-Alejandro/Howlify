# howlify/config.py

# Estos nombres deben coincidir con los que guardás en la columna 'plan' de tu tabla 'profiles'
PLANS_PUBLIC = ["starter", "pro", "business_reseller", "business_monitor"]  
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
    "business_reseller": {
        "max_cazas_activas": 40,
        "min_interval_minutes": 10,
        "stores": ["mercadolibre", "generic", "duffel", "despegar", "airbnb"],
        "features": {
            "whatsapp": True,
            "telegram": True,
            "vuelos_anuales": True,
            "reporte_diario": True,
            "export_csv": True,
            "multi_store_same_hunt": True,
        },
    },
    "business_monitor": {
        "max_cazas_activas": 100,
        "min_interval_minutes": 10,
        "stores": ["mercadolibre", "generic", "duffel", "despegar", "airbnb"],
        "features": {
            "whatsapp": True,
            "telegram": True,
            "vuelos_anuales": True,
            "reporte_diario": True,
            "export_csv": True,
            "dashboard_empresa": True,
            "multi_store_same_hunt": True,
        },
    },
}