"""Pruebas unitarias para la configuración de la aplicación."""

from app.core.config import Settings


def test_default_settings():
    settings = Settings()
    assert settings.APP_NAME == "ms-segip"
    assert settings.APP_VERSION == "1.0.0"
    assert "https://segip-api.fiscalia.gob.bo" in settings.SEGIP_SERVICE_URL
    assert settings.PDF_MAX_SIZE_MB == 10.0
    assert settings.pdf_max_size_bytes == 10 * 1024 * 1024
    assert settings.SEGIP_MAX_RETRIES == 3
    assert settings.LOG_FORMAT == "text"
    assert not settings.is_production


def test_cors_origins_parsing():
    s1 = Settings(CORS_ORIGINS=["https://fiscalia.gob.bo", "http://localhost:3000"])
    assert len(s1.CORS_ORIGINS) == 2
    assert "https://fiscalia.gob.bo" in s1.CORS_ORIGINS

    s2 = Settings(CORS_ORIGINS="https://app.fiscalia.gob.bo, https://admin.fiscalia.gob.bo")
    assert len(s2.CORS_ORIGINS) == 2
    assert "https://app.fiscalia.gob.bo" in s2.CORS_ORIGINS
