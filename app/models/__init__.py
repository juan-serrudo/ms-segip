"""Exportación de modelos declarativos de SQLAlchemy 2.0 para ms-segip."""

from app.models.base import Base
from app.models.bitacora import BitacoraConsultaModel
from app.models.certificacion import CertificacionModel
from app.models.persona import PersonaModel

__all__ = [
    "Base",
    "PersonaModel",
    "CertificacionModel",
    "BitacoraConsultaModel",
]
