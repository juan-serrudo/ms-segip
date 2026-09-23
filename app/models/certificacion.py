"""Modelo ORM para la tabla certificaciones_segip (SQLAlchemy 2.0)."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.persona import PersonaModel


class CertificacionModel(Base):
    """Mapeo relacional de la tabla 'certificaciones_segip'.

    Registra el historial de emisiones de certificados en PDF obtenidos para cada persona.
    El documento binario PDF se resguarda en RustFS/S3 y aquí se persiste su ruta (pdf_path)
    junto al hash criptográfico SHA-256 para validación de integridad.
    """

    __tablename__ = "certificaciones_segip"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    persona_id: Mapped[int] = mapped_column(

        BigInteger, ForeignKey("personas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    numero_emision: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    codigo_segip: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    fecha_emision: Mapped[str | None] = mapped_column(String(50), nullable=True)
    motivo_consulta: Mapped[str | None] = mapped_column(Text, nullable=True)
    paginas: Mapped[int] = mapped_column(Integer, default=1, server_default="1")

    # Referencia al archivo PDF en RustFS / S3
    pdf_path: Mapped[str] = mapped_column(String(500), nullable=False)
    pdf_tamanio_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    pdf_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Auditoría
    usuario_consulta: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ip_origen: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relación inversa con Persona
    persona: Mapped["PersonaModel"] = relationship(back_populates="certificaciones")

    def __repr__(self) -> str:
        return (
            f"<CertificacionModel(id={self.id}, persona_id={self.persona_id}, "
            f"emision='{self.numero_emision}', path='{self.pdf_path}')>"
        )
