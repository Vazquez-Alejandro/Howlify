"""
tests/test_ml_api.py — Tests for ML API and rate limiter
"""
import pytest
from unittest.mock import patch, MagicMock
from scraper.ml_api import _extract_item_id, get_price_from_url, search_items
from scraper.rate_limiter import SiteRateLimiter


class TestExtractItemId:
    def test_standard_url(self):
        url = "https://articulo.mercadolibre.com.ar/MLA-1234567890"
        assert _extract_item_id(url) == "MLA1234567890"

    def test_url_with_variant(self):
        url = "https://articulo.mercadolibre.com.ar/MLA-1234567890#variant=MLA1234567891"
        assert _extract_item_id(url) == "MLA1234567890"

    def test_short_url(self):
        url = "https://mercadolibre.com.ar/MLA1234567890"
        assert _extract_item_id(url) == "MLA1234567890"

    def test_product_url(self):
        url = "https://www.mercadolibre.com.ar/p/MLA123456"
        assert _extract_item_id(url) == "MLA123456"

    def test_no_mercadolibre(self):
        assert _extract_item_id("https://www.google.com") is None

    def test_no_id(self):
        assert _extract_item_id("https://mercadolibre.com.ar") is None

    def test_empty(self):
        assert _extract_item_id("") is None

    def test_mluruguay(self):
        url = "https://articulo.mercadolibre.com.uy/MLU-12345678"
        assert _extract_item_id(url) == "MLU12345678"


class TestRateLimiter:
    def test_initial_state(self):
        limiter = SiteRateLimiter()
        stats = limiter.get_stats()
        assert "mercadolibre.com" in stats
        assert stats["mercadolibre.com"]["ready"] is True

    def test_get_site(self):
        limiter = SiteRateLimiter()
        assert limiter._get_site("https://articulo.mercadolibre.com.ar/MLA-123") == "mercadolibre.com"
        assert limiter._get_site("https://www.despegar.com.ar") == "despegar.com"
        assert limiter._get_site("https://www.google.com") == "default"

    def test_can_proceed(self):
        limiter = SiteRateLimiter()
        assert limiter.can_proceed("https://articulo.mercadolibre.com.ar/MLA-123") is True


class TestSearchItems:
    @patch("scraper.ml_api.requests.get")
    def test_returns_results(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"results": [{"id": "MLA123", "title": "Test", "price": 100}]}
        )
        results = search_items("test query")
        assert len(results) == 1
        assert results[0]["id"] == "MLA123"

    @patch("scraper.ml_api.requests.get")
    def test_handles_error(self, mock_get):
        mock_get.side_effect = Exception("Connection error")
        results = search_items("test query")
        assert results == []
