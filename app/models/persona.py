"""Modelo ORM para la tabla personas (SQLAlchemy 2.0)."""

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Date, DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.certificacion import CertificacionModel


class PersonaModel(Base):
    """Mapeo relacional de la tabla 'personas'.

    Almacena los datos normalizados de identidad y lugar de nacimiento.
    La fotografía física no se almacena como BLOB/Base64 en la base de datos,
    sino que se guarda en RustFS/S3 y aquí se persiste su ruta (fotografia_path).
    """

    __tablename__ = "personas"
    __table_args__ = (
        UniqueConstraint("numero_documento", "complemento", name="uq_personas_doc_comp"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    numero_documento: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    complemento: Mapped[str] = mapped_column(String(10), default="", server_default="")
    nombres: Mapped[str] = mapped_column(String(100), nullable=False)
    primer_apellido: Mapped[str] = mapped_column(String(100), nullable=False)
    segundo_apellido: Mapped[str] = mapped_column(String(100), default="", server_default="")
    fecha_nacimiento: Mapped[date | None] = mapped_column(Date, nullable=True)
    sexo: Mapped[str | None] = mapped_column(String(20), nullable=True)
    estado_civil: Mapped[str | None] = mapped_column(String(30), nullable=True)
    domicilio: Mapped[str | None] = mapped_column(Text, nullable=True)
    profesion_ocupacion: Mapped[str | None] = mapped_column(String(150), nullable=True)

    # Datos de nacimiento
    pais_nacimiento: Mapped[str | None] = mapped_column(
        String(100), default="BOLIVIA", server_default="BOLIVIA"
    )
    departamento_nacimiento: Mapped[str | None] = mapped_column(String(100), nullable=True)
    provincia_nacimiento: Mapped[str | None] = mapped_column(String(100), nullable=True)
    localidad_nacimiento: Mapped[str | None] = mapped_column(String(150), nullable=True)

    # Referencia al objeto en RustFS / S3
    fotografia_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    fotografia_content_type: Mapped[str] = mapped_column(
        String(50), default="image/jpeg", server_default="image/jpeg"
    )

    # Trazabilidad
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relación bidireccional con certificaciones
    certificaciones: Mapped[list["CertificacionModel"]] = relationship(
        back_populates="persona",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<PersonaModel(id={self.id}, doc='{self.numero_documento}-{self.complemento}', "
            f"nombre='{self.nombres} {self.primer_apellido}')>"
        )
