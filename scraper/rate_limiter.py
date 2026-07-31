"""
scraper/rate_limiter.py — Rate limiting por sitio
Previene bloqueos y bans por exceso de requests.
"""
import time
import threading
from collections import defaultdict
from utils.logger import get_logger

logger = get_logger("rate_limiter")

# Configuracion por sitio (segundos entre requests)
SITE_LIMITS = {
    "mercadolibre.com": {"min_interval": 2.0, "max_concurrent": 2},
    "despegar.com": {"min_interval": 3.0, "max_concurrent": 1},
    "almundo.com": {"min_interval": 3.0, "max_concurrent": 1},
    "turismocity": {"min_interval": 3.0, "max_concurrent": 1},
    "avantrip.com": {"min_interval": 3.0, "max_concurrent": 1},
    "airbnb": {"min_interval": 5.0, "max_concurrent": 1},
    "booking.com": {"min_interval": 4.0, "max_concurrent": 1},
    "tripadvisor": {"min_interval": 4.0, "max_concurrent": 1},
}

DEFAULT_LIMITS = {"min_interval": 1.5, "max_concurrent": 2}


class SiteRateLimiter:
    """Rate limiter independiente por sitio."""
    
    def __init__(self):
        self._last_request = defaultdict(float)
        self._active = defaultdict(int)
        self._locks = defaultdict(threading.Lock)
    
    def _get_site(self, url: str) -> str:
        """Identifica el sitio desde la URL."""
        url_lower = url.lower()
        for site in SITE_LIMITS:
            if site in url_lower:
                return site
        return "default"
    
    def wait(self, url: str) -> float:
        """Espera si es necesario y retorna el tiempo de espera."""
        site = self._get_site(url)
        limits = SITE_LIMITS.get(site, DEFAULT_LIMITS)
        min_interval = limits["min_interval"]
        
        with self._locks[site]:
            now = time.time()
            last = self._last_request[site]
            wait_time = max(0, min_interval - (now - last))
            
            if wait_time > 0:
                logger.debug(f"Rate limit {site}: waiting {wait_time:.1f}s")
                time.sleep(wait_time)
            
            self._last_request[site] = time.time()
            return wait_time
    
    def can_proceed(self, url: str) -> bool:
        """Verifica si puede hacer un request (sin bloquear)."""
        site = self._get_site(url)
        limits = SITE_LIMITS.get(site, DEFAULT_LIMITS)
        
        with self._locks[site]:
            now = time.time()
            last = self._last_request[site]
            min_interval = limits["min_interval"]
            
            return (now - last) >= min_interval
    
    def get_stats(self) -> dict:
        """Retorna estadisticas de uso."""
        stats = {}
        for site in SITE_LIMITS:
            with self._locks[site]:
                last = self._last_request[site]
                elapsed = time.time() - last if last > 0 else float('inf')
                stats[site] = {
                    "last_request": last,
                    "elapsed": elapsed,
                    "ready": elapsed >= SITE_LIMITS[site]["min_interval"]
                }
        return stats


# Singleton global
rate_limiter = SiteRateLimiter()
