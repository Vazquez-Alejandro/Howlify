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


def _bloque_activo(minutos):
    """True si el minuto actual está alineado con el bloque."""
    return datetime.now(timezone.utc).minute % minutos == 0


class TestObtenerCazasPendientes:
    def test_caza_sin_last_check_es_pendiente_en_bloque(self):
        caza = _make_caza(last_check=None)
        supabase_mock = MagicMock()
        supabase_mock.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [caza]

        with patch("engine.worker.supabase", supabase_mock):
            from engine.worker import obtener_cazas_pendientes
            pendientes = obtener_cazas_pendientes()
            if _bloque_activo(15):
                assert len(pendientes) == 1
                assert pendientes[0]["id"] == 1
            else:
                assert len(pendientes) == 0

    def test_caza_con_last_check_reciente_no_es_pendiente(self):
        ahora = datetime.now(timezone.utc)
        last_check_reciente = (ahora - timedelta(seconds=10)).isoformat()
        caza = _make_caza(last_check=last_check_reciente)
        supabase_mock = MagicMock()
        supabase_mock.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [caza]

        with patch("engine.worker.supabase", supabase_mock):
            from engine.worker import obtener_cazas_pendientes
            pendientes = obtener_cazas_pendientes()
            assert len(pendientes) == 0

    def test_caza_con_last_check_viejo_es_pendiente_en_bloque(self):
        ahora = datetime.now(timezone.utc)
        last_check_viejo = (ahora - timedelta(minutes=5)).isoformat()
        caza = _make_caza(last_check=last_check_viejo)
        supabase_mock = MagicMock()
        supabase_mock.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [caza]

        with patch("engine.worker.supabase", supabase_mock):
            from engine.worker import obtener_cazas_pendientes
            pendientes = obtener_cazas_pendientes()
            if _bloque_activo(15):
                assert len(pendientes) == 1
            else:
                assert len(pendientes) == 0

    def test_caza_inactiva_excluida(self):
        caza = _make_caza(last_check=None, estado="inactiva")
        supabase_mock = MagicMock()
        supabase_mock.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [caza]

        with patch("engine.worker.supabase", supabase_mock):
            from engine.worker import obtener_cazas_pendientes
            pendientes = obtener_cazas_pendientes()
            assert len(pendientes) == 0

    def test_frecuencia_30_afecta_bloque(self):
        caza = _make_caza(last_check=None, frecuencia="30min")
        supabase_mock = MagicMock()
        supabase_mock.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [caza]

        with patch("engine.worker.supabase", supabase_mock):
            from engine.worker import obtener_cazas_pendientes
            pendientes = obtener_cazas_pendientes()
            if _bloque_activo(30):
                assert len(pendientes) == 1
            else:
                assert len(pendientes) == 0

    def test_last_check_mal_formateado_no_crashea(self):
        caza = _make_caza(last_check="fecha-invalida")
        supabase_mock = MagicMock()
        supabase_mock.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [caza]

        with patch("engine.worker.supabase", supabase_mock):
            from engine.worker import obtener_cazas_pendientes
            try:
                obtener_cazas_pendientes()
            except Exception:
                assert False, "No debería lanzar excepción"

    def test_last_check_viejo_no_bloque_no_vuelve(self):
        ahora = datetime.now(timezone.utc)
        caza = _make_caza(last_check=(ahora - timedelta(seconds=50)).isoformat())
        supabase_mock = MagicMock()
        supabase_mock.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [caza]

        with patch("engine.worker.supabase", supabase_mock):
            from engine.worker import obtener_cazas_pendientes
            pendientes = obtener_cazas_pendientes()
            assert len(pendientes) == 0


class TestEffectiveMinutes:
    def test_15min(self):
        from utils.logic import _effective_minutes
        assert _effective_minutes("starter", "15min") == 15

    def test_1h(self):
        from utils.logic import _effective_minutes
        assert _effective_minutes("pro", "1h") == 60

    def test_6h(self):
        from utils.logic import _effective_minutes
        assert _effective_minutes("business", "6h") == 360

    def test_default(self):
        from utils.logic import _effective_minutes
        assert _effective_minutes("starter", None) == 1440
