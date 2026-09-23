"""Pruebas unitarias para la capa de Base de Datos y Repositorios (SQLAlchemy 2.0 Async)."""

from datetime import date

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.core.database import check_database_health, close_database_engine, get_async_engine
from app.models.base import Base
from app.models.bitacora import BitacoraConsultaModel
from app.models.certificacion import CertificacionModel
from app.models.persona import PersonaModel
from app.repositories.persona_repository import PersonaRepository
from app.schemas.pdf import DatosCertificadoPdf
from app.schemas.segip import DatosNacimiento, DatosPersona


@pytest.fixture
def test_db_settings() -> Settings:
    """Configuración de base de datos para pruebas."""
    return Settings(
        DB_HOST="localhost",
        DB_PORT=5432,
        DB_USER="test_user",
        DB_PASSWORD="test_password",
        DB_NAME="test_db",
        DATABASE_URL=None,
        DB_POOL_SIZE=5,
        DB_MAX_OVERFLOW=5,
    )


def test_database_settings_url_generation(test_db_settings: Settings):
    """Verifica que la URL asíncrona se genere con el driver postgresql+asyncpg://."""
    expected = "postgresql+asyncpg://test_user:test_password@localhost:5432/test_db"
    assert test_db_settings.async_database_url == expected


def test_database_settings_explicit_url():
    """Verifica la normalización si se provee una URL explícita."""
    s1 = Settings(DATABASE_URL="postgresql://user:pass@remote:5432/db")
    assert s1.async_database_url == "postgresql+asyncpg://user:pass@remote:5432/db"

    s2 = Settings(DATABASE_URL="postgresql+asyncpg://user:pass@remote:5432/db")
    assert s2.async_database_url == "postgresql+asyncpg://user:pass@remote:5432/db"


@pytest_asyncio.fixture
async def in_memory_session() -> AsyncSession:
    """Provee una sesión asíncrona conectada a una base de datos SQLite en memoria."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_persona_repository_upsert_and_get(in_memory_session: AsyncSession):
    """Prueba el registro y recuperación de una persona a través de PersonaRepository."""
    repo = PersonaRepository(session=in_memory_session)

    # 1. Persona no existe inicialmente
    existente = await repo.get_by_documento("1146351", None)
    assert existente is None

    # 2. Registrar nueva persona
    datos_persona = DatosPersona(
        numero_documento="1146351",
        complemento=None,
        nombres="JUAN VICTOR",
        primer_apellido="SERRUDO",
        segundo_apellido="CHAVEZ",
        fecha_nacimiento="1986-10-16",
        sexo="MASCULINO",
        estado_civil="CASADO",
        domicilio="CLL/INDEPENDENCIA N° 120 ZONA YURAC YURAC-SUCRE",
        profesion_ocupacion="ING. DE SISTEMAS",
    )
    datos_nacimiento = DatosNacimiento(
        pais="BOLIVIA",
        departamento="CHUQUISACA",
        provincia="OROPEZA",
        localidad="SUCRE",
    )

    persona = await repo.upsert_persona(
        data=datos_persona,
        nacimiento=datos_nacimiento,
        fotografia_path="personas/1146351/foto.jpg",
    )

    assert persona.id is not None
    assert persona.numero_documento == "1146351"
    assert persona.complemento == ""
    assert persona.nombres == "JUAN VICTOR"
    assert persona.primer_apellido == "SERRUDO"
    assert persona.fecha_nacimiento == date(1986, 10, 16)
    assert persona.pais_nacimiento == "BOLIVIA"
    assert persona.departamento_nacimiento == "CHUQUISACA"
    assert persona.fotografia_path == "personas/1146351/foto.jpg"

    # 3. Recuperar persona por documento
    recuperada = await repo.get_by_documento("1146351")
    assert recuperada is not None
    assert recuperada.id == persona.id
    assert recuperada.primer_apellido == "SERRUDO"


@pytest.mark.asyncio
async def test_persona_repository_upsert_update_existing(in_memory_session: AsyncSession):
    """Prueba la actualización de datos de una persona existente en lugar de duplicarla."""
    repo = PersonaRepository(session=in_memory_session)

    # Crear persona inicial
    p1 = await repo.upsert_persona(
        data=DatosPersona(
            numero_documento="2233445",
            nombres="MARIA",
            primer_apellido="LOPEZ",
            profesion_ocupacion="ESTUDIANTE",
        )
    )
    initial_id = p1.id

    # Actualizar con nueva ocupación y nuevo domicilio
    p2 = await repo.upsert_persona(
        data=DatosPersona(
            numero_documento="2233445",
            nombres="MARIA",
            primer_apellido="LOPEZ",
            profesion_ocupacion="ABOGADA",
            domicilio="AV. CENTRAL N° 45",
        )
    )

    assert p2.id == initial_id
    assert p2.profesion_ocupacion == "ABOGADA"
    assert p2.domicilio == "AV. CENTRAL N° 45"


@pytest.mark.asyncio
async def test_registrar_certificacion_e_historial(in_memory_session: AsyncSession):
    """Prueba el registro de una certificación SEGIP ligada a una persona."""
    repo = PersonaRepository(session=in_memory_session)

    persona = await repo.upsert_persona(
        data=DatosPersona(
            numero_documento="5566778",
            nombres="CARLOS",
            primer_apellido="MENDOZA",
        )
    )

    cert_data = DatosCertificadoPdf(
        numero_emision="c4CAXTej-4774047",
        codigo_segip="c4CAXTej-4774047",
        fecha_emision="23-09-2026 2:42:15 PM",
        motivo_consulta="CONVENIO - FISCALIA GENERAL DEL ESTADO",
        paginas=1,
    )

    cert = await repo.registrar_certificacion(
        persona_id=persona.id,
        certificado=cert_data,
        pdf_path="certificados/c4CAXTej-4774047.pdf",
        pdf_tamanio_bytes=1048576,
        pdf_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        usuario_consulta="operador_fge",
    )

    assert cert.id is not None
    assert cert.persona_id == persona.id
    assert cert.numero_emision == "c4CAXTej-4774047"
    assert cert.pdf_path == "certificados/c4CAXTej-4774047.pdf"
    assert cert.pdf_tamanio_bytes == 1048576

    # Consultar historial
    historial = await repo.get_historial_certificaciones(persona.id)
    assert len(historial) == 1
    assert historial[0].id == cert.id


@pytest.mark.asyncio
async def test_registrar_bitacora(in_memory_session: AsyncSession):
    """Prueba el registro de auditoría en la tabla bitacora_consultas."""
    repo = PersonaRepository(session=in_memory_session)

    bitacora = await repo.registrar_bitacora(
        numero_documento="1146351",
        complemento="1A",
        tipo_origen="PDF_EXTRACT",
        exitoso=True,
        codigo_respuesta="200",
        mensaje="Extracción exitosa",
        usuario_operador="test_user",
        duracion_ms=150,
    )

    assert bitacora.id is not None
    assert bitacora.numero_documento == "1146351"
    assert bitacora.complemento == "1A"
    assert bitacora.tipo_origen == "PDF_EXTRACT"
    assert bitacora.exitoso is True
    assert bitacora.duracion_ms == 150


@pytest.mark.asyncio
async def test_database_engine_lifecycle():
    """Prueba que el motor singleton y el cierre ordenado (dispose) funcionen sin fallas."""
    settings = Settings(DATABASE_URL="sqlite+aiosqlite:///:memory:")
    engine = get_async_engine(settings)
    assert engine is not None

    ok, msg = await check_database_health(engine)
    assert ok is True
    assert "disponible" in msg

    # Probar cierre ordenado (Graceful Shutdown)
    await close_database_engine()


def test_models_repr():
    """Prueba las representaciones textuales __repr__ de los modelos."""
    p = PersonaModel(
        id=1, numero_documento="123", complemento="", nombres="ANA", primer_apellido="RUIZ"
    )
    assert "123" in repr(p)

    c = CertificacionModel(id=1, persona_id=1, numero_emision="E-001", pdf_path="path/test.pdf")
    assert "E-001" in repr(c)

    b = BitacoraConsultaModel(id=1, numero_documento="123", tipo_origen="SOAP", exitoso=True)
    assert "SOAP" in repr(b)
