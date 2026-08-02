# howlify/config.py

PLANS_PUBLIC = ["starter", "pro", "alpha"]
PLAN_DEFAULT = "starter"

# Display names (wolf hierarchy)
PLAN_DISPLAY_NAMES = {
    "starter": "Omega",
    "pro": "Beta",
    "alpha": "Alpha",
}

# Map old plan names to new ones
PLAN_ALIAS = {
    "omega": "starter",
    "trial": "starter",
    "starter": "starter",
    "beta": "pro",
    "alfa": "pro",
    "revendedor": "pro",
    "empresa": "pro",
    "pro": "pro",
    "alpha": "alpha",
}

PLAN_LIMITS = {
    "starter": {
        "max_cazas_activas": 3,
        "min_interval_minutes": 60,
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
        "min_interval_minutes": 15,
        "stores": ["mercadolibre", "generic", "duffel", "despegar", "airbnb"],
        "features": {
            "whatsapp": True,
            "telegram": True,
            "vuelos_anuales": True,
            "reporte_diario": True,
            "export_csv": True,
        },
    },
    "alpha": {
        "max_cazas_activas": 999,
        "min_interval_minutes": 5,
        "stores": ["mercadolibre", "generic", "duffel", "despegar", "airbnb"],
        "features": {
            "whatsapp": True,
            "telegram": True,
            "vuelos_anuales": True,
            "reporte_diario": True,
            "export_csv": True,
            "api_access": True,
            "priority_support": True,
        },
    },
}
