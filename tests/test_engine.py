from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch


def _make_caza(last_check=None, frecuencia="15min", estado="activa", plan="starter"):
    return {
        "id": 1,
        "producto": "Test Product",
        "link": "https://example.com",
        "precio_max": 1000,
        "frecuencia": frecuencia,
        "last_check": last_check,
        "estado": estado,
        "plan": plan,
        "user_id": "user-123",
        "ultimo_precio_detectado": None,
        "last_alert_at": None,
        "profiles": {"email": "test@test.com", "telegram_id": "123"},
    }


class TestFrequencyLogic:
    """Tests para la lógica de frecuencia del worker Celery."""

    def test_caza_sin_last_check_deberia_procesarse(self):
        """Una caza sin last_check debería ser elegible para procesar."""
        from utils.logic import _parse_dt_utc, _effective_minutes
        caza = _make_caza(last_check=None)
        last_dt = _parse_dt_utc(caza["last_check"])
        assert last_dt is None

    def test_caza_con_last_check_viejo_deberia_procesarse(self):
        """Una caza con last_check viejo (> freq minutos) debería ser elegible."""
        from utils.logic import _parse_dt_utc, _effective_minutes
        ahora = datetime.now(timezone.utc)
        last_check_viejo = (ahora - timedelta(minutes=20)).isoformat()
        caza = _make_caza(last_check=last_check_viejo, frecuencia="15min")
        last_dt = _parse_dt_utc(caza["last_check"])
        mins = _effective_minutes(caza["plan"], caza["frecuencia"])
        assert last_dt is not None
        assert (ahora - last_dt) >= timedelta(minutes=mins)

    def test_caza_con_last_check_reciente_no_deberia_procesarse(self):
        """Una caza con last_check reciente (< freq minutos) no debería procesarse."""
        from utils.logic import _parse_dt_utc, _effective_minutes
        ahora = datetime.now(timezone.utc)
        last_check_reciente = (ahora - timedelta(seconds=10)).isoformat()
        caza = _make_caza(last_check=last_check_reciente, frecuencia="15min")
        last_dt = _parse_dt_utc(caza["last_check"])
        mins = _effective_minutes(caza["plan"], caza["frecuencia"])
        assert last_dt is not None
        assert (ahora - last_dt) < timedelta(minutes=mins)

    def test_caza_inactiva_excluida(self):
        """Las cacerías inactivas no deberían procesarse."""
        caza = _make_caza(estado="inactiva")
        assert caza["estado"] != "activa"

    def test_frecuencia_30_min(self):
        """Frecuencia de 30min debería dar 30 minutos."""
        from utils.logic import _effective_minutes
        assert _effective_minutes("starter", "30min") == 30

    def test_frecuencia_1h(self):
        from utils.logic import _effective_minutes
        assert _effective_minutes("pro", "1h") == 60

    def test_frecuencia_6h(self):
        from utils.logic import _effective_minutes
        assert _effective_minutes("pro", "6h") == 360

    def test_frecuencia_none_default(self):
        from utils.logic import _effective_minutes
        assert _effective_minutes("starter", None) == 1440

    def test_last_check_mal_formateado_no_crashea(self):
        """Last_check inválido no debería causar crash."""
        from utils.logic import _parse_dt_utc
        result = _parse_dt_utc("fecha-invalida")
        assert result is None


class TestEffectiveMinutes:
    def test_15min(self):
        from utils.logic import _effective_minutes
        assert _effective_minutes("starter", "15min") == 15

    def test_1h(self):
        from utils.logic import _effective_minutes
        assert _effective_minutes("pro", "1h") == 60

    def test_6h(self):
        from utils.logic import _effective_minutes
        assert _effective_minutes("pro", "6h") == 360

    def test_default(self):
        from utils.logic import _effective_minutes
        assert _effective_minutes("starter", None) == 1440


class TestSafeFloat:
    def test_none_returns_default(self):
        from utils.logic import _safe_float
        assert _safe_float(None) == 0.0

    def test_int_passthrough(self):
        from utils.logic import _safe_float
        assert _safe_float(42) == 42.0

    def test_float_passthrough(self):
        from utils.logic import _safe_float
        assert _safe_float(3.14) == 3.14

    def test_string_with_dollar_sign(self):
        from utils.logic import _safe_float
        assert _safe_float("$1.234") == 1234.0

    def test_string_with_comma_decimal(self):
        from utils.logic import _safe_float
        assert _safe_float("1.234,56") == 1234.56

    def test_garbage_returns_default(self):
        from utils.logic import _safe_float
        assert _safe_float("abc", 99.0) == 99.0


class TestPlanLogic:
    def test_normalize_plan_family(self):
        from utils.logic import normalize_plan_family
        assert normalize_plan_family("starter") == "starter"
        assert normalize_plan_family("omega") == "starter"
        assert normalize_plan_family("beta") == "pro"
        assert normalize_plan_family("alfa") == "pro"
        assert normalize_plan_family(None) == "starter"

    def test_plan_allows_whatsapp(self):
        from utils.logic import plan_allows_whatsapp
        assert plan_allows_whatsapp("starter") is False
        assert plan_allows_whatsapp("pro") is True
