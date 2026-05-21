import os
import re
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse


def get_affiliate_url(original_url: str) -> str:
    """
    Transforma una URL original en un link de afiliado.
    Soporta MercadoLibre (MLA), Despegar y afiliados genéricos.
    Las keys se configuran vía environment variables.
    """
    if not original_url:
        return original_url

    domain = urlparse(original_url).netloc.lower()

    if "mercadolibre" in domain or "mercadolibre.com" in domain:
        return _ml_affiliate(original_url)

    if "despegar" in domain:
        return _despegar_affiliate(original_url)

    return original_url


def _ml_affiliate(url: str) -> str:
    token = os.getenv("ML_AFFILIATE_TOKEN", "")
    if not token:
        return url
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    query["partner_id"] = [token]
    new_query = urlencode(query, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def _despegar_affiliate(url: str) -> str:
    tag = os.getenv("DESPEGAR_AFFILIATE_TAG", "")
    if not tag:
        return url
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    query["utm_source"] = ["howlify"]
    query["utm_medium"] = ["affiliate"]
    query["utm_campaign"] = [tag]
    new_query = urlencode(query, doseq=True)
    return urlunparse(parsed._replace(query=new_query))
