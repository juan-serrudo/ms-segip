"""Seguridad y mecanismos de autenticación desacoplados para ms-segip."""

from collections.abc import Callable
from typing import Any

from fastapi import Depends, Header, HTTPException, status

from app.core.config import Settings, get_settings


async def verify_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    settings: Settings = Depends(get_settings),
) -> str | None:
    """Verifica la API Key institucional si está configurada en el entorno.

    Si Settings.API_KEY es None o vacío, la autenticación no es obligatoria
    (adecuado para intranet protegida a nivel de red).
    Si está definida, se rechaza cualquier petición sin la clave correcta.
    """
    if not settings.API_KEY:
        # Autenticación no exigida por configuración
        return None

    if not x_api_key or x_api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clave de API inválida o ausente en cabecera X-API-Key",
        )

    return x_api_key


def get_auth_dependency() -> Callable[..., Any]:
    """Retorna la dependencia de autenticación activa.

    Permite sustituir fácilmente la lógica de autenticación en el futuro
    (ej. JWT, OAuth2, mTLS institucional) sin alterar los routers.
    """
    return verify_api_key
