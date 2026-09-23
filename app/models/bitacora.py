"""Modelo ORM para la tabla bitacora_consultas (SQLAlchemy 2.0)."""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class BitacoraConsultaModel(Base):
    """Mapeo relacional de la tabla 'bitacora_consultas'.

    Permite auditoría y trazabilidad histórica de todas las consultas efectuadas
    contra SEGIP o procesadas mediante documentos PDF.
    """

    __tablename__ = "bitacora_consultas"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    numero_documento: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    complemento: Mapped[str] = mapped_column(String(10), default="", server_default="")
    tipo_origen: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # 'SOAP_JSON', 'PDF_EXTRACT', 'PDF_BASE64', 'QR_VERIFY'
    exitoso: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    codigo_respuesta: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mensaje: Mapped[str | None] = mapped_column(Text, nullable=True)
    usuario_operador: Mapped[str | None] = mapped_column(String(100), nullable=True)
    duracion_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    def __repr__(self) -> str:
        return (
            f"<BitacoraConsultaModel(id={self.id}, doc='{self.numero_documento}', "
            f"origen='{self.tipo_origen}', exitoso={self.exitoso})>"
        )
