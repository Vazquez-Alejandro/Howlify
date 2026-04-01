"""
Price Audit Service

Este módulo permitirá auditar posibles variaciones de precio
en una misma publicación dependiendo del contexto.

Por ahora es solo un esqueleto para futuras implementaciones.
"""

from typing import Dict


def audit_price(url: str) -> Dict:
    """
    Ejecuta un chequeo básico de precio.

    Futuro:
    - contexto limpio
    - contexto logueado
    - mobile
    - distintas ubicaciones
    """

    result = {
        "url": url,
        "clean_price": None,
        "logged_price": None,
        "difference_pct": None,
        "difference_detected": False,
    }

    return result