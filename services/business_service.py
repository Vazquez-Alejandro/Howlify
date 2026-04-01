from auth.supabase_client import supabase


def calcular_score_oportunidad(precio_actual, precio_minimo, diff_vs_min):
    """
    Calcula un score simple de oportunidad
    """
    score = 0

    # nuevo mínimo histórico
    if precio_minimo and precio_actual < precio_minimo:
        score += 50

    # cercanía al mínimo
    if diff_vs_min is not None:
        score += abs(diff_vs_min)

    return round(score, 2)


def guardar_oportunidad_business(
    caza_id,
    product_id,
    title,
    source,
    precio_actual,
    precio_minimo,
    diff_vs_min,
):
    """
    Guarda una oportunidad detectada para el módulo Business
    """
    try:
        score = calcular_score_oportunidad(
            precio_actual,
            precio_minimo,
            diff_vs_min,
        )

        supabase.table("business_opportunities").insert(
            {
                "caza_id": caza_id,
                "product_id": product_id,
                "title": title,
                "source": source,
                "current_price": precio_actual,
                "historic_min_price": precio_minimo,
                "diff_vs_min": diff_vs_min,
                "opportunity_score": score,
            }
        ).execute()

    except Exception as e:
        print("⚠ error guardando oportunidad business:", e)


def obtener_top_oportunidades(limit=20):
    """
    Devuelve las mejores oportunidades detectadas
    """
    try:
        res = (
            supabase.table("business_opportunities")
            .select("*")
            .order("opportunity_score", desc=True)
            .limit(limit)
            .execute()
        )

        return res.data or []

    except Exception as e:
        print("⚠ error obteniendo oportunidades:", e)
        return []