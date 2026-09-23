"""Pruebas de integración contra el contenedor PostgreSQL de desarrollo en localhost:5432."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.database import check_database_health
from app.repositories.persona_repository import PersonaRepository
from app.schemas.pdf import DatosCertificadoPdf
from app.schemas.segip import DatosNacimiento, DatosPersona


@pytest.mark.asyncio
async def test_postgres_container_integration():
    """Valida la conectividad real, healthcheck, inserción y consulta en el PostgreSQL de desarrollo."""
    settings = get_settings()
    engine = create_async_engine(
        settings.async_database_url,
        pool_size=2,
        max_overflow=1,
        pool_pre_ping=True,
    )

    # 1. Comprobar salud del contenedor
    is_healthy, msg = await check_database_health(engine)
    if not is_healthy:
        await engine.dispose()
        pytest.skip(f"Contenedor PostgreSQL no disponible en {settings.async_database_url}: {msg}")

    # 2. Probar inserción y recuperación con sesión real
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        repo = PersonaRepository(session=session)

        # Upsert persona de prueba
        persona = await repo.upsert_persona(
            data=DatosPersona(
                numero_documento="TEST-998877",
                complemento=None,
                nombres="TEST NOMBRE",
                primer_apellido="TEST APELLIDO",
                segundo_apellido="TEST MATERNO",
                fecha_nacimiento="1990-05-20",
                sexo="MASCULINO",
                domicilio="DIRECCION TEST",
                profesion_ocupacion="TEST OCCUPATION",
            ),
            nacimiento=DatosNacimiento(
                pais="BOLIVIA",
                departamento="LA PAZ",
                provincia="MURILLO",
                localidad="LA PAZ",
            ),
            fotografia_path="personas/TEST-998877/foto.jpg",
        )
        assert persona.id is not None
        assert persona.numero_documento == "TEST-998877"

        # Registrar certificación vinculada
        cert = await repo.registrar_certificacion(
            persona_id=persona.id,
            certificado=DatosCertificadoPdf(
                numero_emision="CERT-TEST-001",
                codigo_segip="COD-TEST-001",
                fecha_emision="23-09-2026 18:00:00",
                motivo_consulta="TEST INTEGRATION",
                paginas=1,
            ),
            pdf_path="certificados/CERT-TEST-001.pdf",
            pdf_tamanio_bytes=2048,
            pdf_sha256="abc123hash",
        )
        assert cert.id is not None
        assert cert.persona_id == persona.id

        # Bitácora
        bitacora = await repo.registrar_bitacora(
            numero_documento="TEST-998877",
            complemento=None,
            tipo_origen="TEST_RUNNER",
            exitoso=True,
            mensaje="Prueba de integración exitosa",
        )
        assert bitacora.id is not None

        # Confirmar transacción
        await session.commit()

        # Limpiar datos de prueba para mantener idempotente la BD
        await session.delete(cert)
        await session.delete(persona)
        await session.delete(bitacora)
        await session.commit()

    await engine.dispose()
