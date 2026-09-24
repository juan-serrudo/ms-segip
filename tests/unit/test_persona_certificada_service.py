"""Pruebas unitarias para PersonaCertificadaService (Caché permanente, inmutabilidad y degradación grácil)."""

import base64
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.exceptions import (
    PersonaDuplicadaException,
    SegipNoResultsException,
    SegipQuotaExceededException,
    SegipUnavailableException,
)
from app.models.base import Base
from app.models.certificacion import CertificacionModel
from app.models.persona import PersonaModel
from app.repositories.persona_repository import PersonaRepository
from app.schemas.persona_certificada import PersonaCertificadaRequest
from app.schemas.segip import CertificacionResponseData
from app.services.persona_certificada_service import PersonaCertificadaService
from app.services.segip_service import SegipService
from app.services.storage_service import StorageService
from tests.fixtures.mock_pdfs import create_mock_segip_pdf


@pytest_asyncio.fixture
async def in_memory_session() -> AsyncSession:
    """Provee una sesión asíncrona conectada a SQLite en memoria."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    async with session_factory() as session:
        yield session


@pytest.fixture
def mock_storage_service():
    """Mock para StorageService."""
    storage = MagicMock(spec=StorageService)
    storage.guardar_pdf = AsyncMock(
        return_value=("certificados/6842190_1B/20260924_120000_abc12345.pdf", "hash_pdf_123", 2048)
    )
    storage.guardar_fotografia = AsyncMock(
        return_value=("fotografias/6842190_1B/20260924_120000_def67890.jpg", "hash_foto_123", 1024)
    )
    storage.generar_url_prefirmada = MagicMock(
        side_effect=lambda key, exp=300: f"http://localhost:9000/segip-archivos/{key}?exp={exp}"
    )
    return storage


@pytest.fixture
def mock_segip_service():
    """Mock para SegipService."""
    return MagicMock(spec=SegipService)


@pytest.mark.asyncio
async def test_cache_hit_retorna_directamente_de_bd(
    in_memory_session: AsyncSession,
    mock_storage_service,
    mock_segip_service,
):
    """Verifica que si la persona existe en BD y no se fuerza refresco, NO se llama a SEGIP SOAP."""
    # 1. Crear persona y certificación previa en BD
    persona = PersonaModel(
        numero_documento="6842190",
        complemento="1B",
        nombres="ROBERTO CARLOS",
        primer_apellido="FLORES",
        segundo_apellido="CONDORI",
        fecha_nacimiento=date(1988, 9, 24),
        sexo="MASCULINO",
        estado_civil="SOLTERO",
        fotografia_path="fotografias/6842190_1B/foto_original.jpg",
    )
    in_memory_session.add(persona)
    await in_memory_session.flush()

    cert = CertificacionModel(
        persona_id=persona.id,
        numero_emision="CERT-2026-0001",
        codigo_segip="SEG-112233",
        fecha_emision="10/01/2026 10:00:00",
        motivo_consulta="TRAMITE",
        pdf_path="certificados/6842190_1B/cert_original.pdf",
    )
    in_memory_session.add(cert)
    await in_memory_session.commit()

    repo = PersonaRepository(session=in_memory_session)
    service = PersonaCertificadaService(
        persona_repo=repo,
        segip_service=mock_segip_service,
        storage_service=mock_storage_service,
    )

    req = PersonaCertificadaRequest(
        numero_documento="6842190",
        complemento="1B",
        forzar_actualizacion=False,
        generar_url_pdf=True,
        generar_url_imagen=True,
        tiempo_expiracion_url_segundos=300,
    )

    resp = await service.consultar_o_certificar_persona(req)

    # SEGIP SOAP no debe haber sido llamado
    mock_segip_service.solicitar_certificacion.assert_not_called()

    # Validar respuesta
    assert resp.persona.numero_documento == "6842190"
    assert resp.persona.nombres == "ROBERTO CARLOS"
    assert resp.persona.estado_civil == "SOLTERO"
    assert resp.metadatos.origen_datos == "CACHE_BD"
    assert resp.metadatos.es_refrescado is False
    assert resp.metadatos.aviso is None
    assert resp.metadatos.total_certificaciones_registradas == 1

    # Validar URLs prefirmadas
    assert "cert_original.pdf" in resp.archivos.url_presignada_pdf
    assert "foto_original.jpg" in resp.archivos.url_presignada_imagen
    assert resp.archivos.vigencia_segundos == 300


@pytest.mark.asyncio
async def test_cache_miss_llama_soap_y_persiste(
    in_memory_session: AsyncSession,
    mock_storage_service,
    mock_segip_service,
):
    """Verifica que si la persona no existe en BD, llama a SEGIP, parsea PDF, guarda en RustFS y BD."""
    repo = PersonaRepository(session=in_memory_session)
    service = PersonaCertificadaService(
        persona_repo=repo,
        segip_service=mock_segip_service,
        storage_service=mock_storage_service,
    )

    pdf_bytes = create_mock_segip_pdf(include_photo=True, layout_variant="standard")
    pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")

    mock_segip_service.solicitar_certificacion = AsyncMock(
        return_value=CertificacionResponseData(
            es_valido=True,
            mensaje="Certificado emitido con éxito",
            codigo_respuesta=0,
            reporte_certificacion_base64=pdf_b64,
        )
    )

    req = PersonaCertificadaRequest(
        numero_documento="6842190",
        complemento="1B",
        forzar_actualizacion=False,
    )

    resp = await service.consultar_o_certificar_persona(req)

    # Validar llamada a SOAP
    mock_segip_service.solicitar_certificacion.assert_called_once()
    mock_storage_service.guardar_pdf.assert_called_once()
    mock_storage_service.guardar_fotografia.assert_called_once()

    # Validar datos procesados
    assert resp.persona.numero_documento == "6842190"
    assert resp.persona.complemento == "1B"
    assert resp.persona.primer_apellido == "FLORES"
    assert resp.metadatos.origen_datos == "SEGIP_SOAP"
    assert resp.metadatos.es_refrescado is True

    # Verificar que se guardó en la base de datos
    persona_db = await repo.buscar_con_desambiguacion("6842190", "1B")
    assert persona_db is not None
    assert persona_db.nombres == "ROBERTO CARLOS"


@pytest.mark.asyncio
async def test_forzar_actualizacion_actualiza_datos_sin_borrar_historicos(
    in_memory_session: AsyncSession,
    mock_storage_service,
    mock_segip_service,
):
    """Verifica que forzar actualización actualiza la entidad pero preserva el historial de certificaciones."""
    # 1. Crear persona previa
    persona = PersonaModel(
        numero_documento="6842190",
        complemento="1B",
        nombres="ROBERTO CARLOS",
        primer_apellido="FLORES",
        segundo_apellido="CONDORI",
        estado_civil="SOLTERO",
        fotografia_path="fotografias/6842190_1B/foto_v1.jpg",
    )
    in_memory_session.add(persona)
    await in_memory_session.flush()

    cert1 = CertificacionModel(
        persona_id=persona.id,
        numero_emision="CERT-2026-0001",
        pdf_path="certificados/6842190_1B/cert_v1.pdf",
    )
    in_memory_session.add(cert1)
    await in_memory_session.commit()

    repo = PersonaRepository(session=in_memory_session)
    service = PersonaCertificadaService(
        persona_repo=repo,
        segip_service=mock_segip_service,
        storage_service=mock_storage_service,
    )

    pdf_bytes = create_mock_segip_pdf(include_photo=True, layout_variant="standard")
    pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")

    mock_segip_service.solicitar_certificacion = AsyncMock(
        return_value=CertificacionResponseData(
            es_valido=True,
            mensaje="Certificación actualizada",
            codigo_respuesta=0,
            reporte_certificacion_base64=pdf_b64,
        )
    )

    req = PersonaCertificadaRequest(
        numero_documento="6842190",
        complemento="1B",
        forzar_actualizacion=True,
    )

    resp = await service.consultar_o_certificar_persona(req)

    assert resp.metadatos.origen_datos == "SEGIP_SOAP"
    assert resp.metadatos.es_refrescado is True
    # Total de certificaciones históricas debe ser 2 ahora
    assert resp.metadatos.total_certificaciones_registradas == 2


@pytest.mark.asyncio
async def test_forzar_actualizacion_falla_soap_aplica_degradacion_gracil(
    in_memory_session: AsyncSession,
    mock_storage_service,
    mock_segip_service,
):
    """Verifica que ante fallo de SEGIP en forzar_actualizacion, devuelve los datos de BD con aviso (Opción A)."""
    persona = PersonaModel(
        numero_documento="6842190",
        complemento="1B",
        nombres="ROBERTO CARLOS",
        primer_apellido="FLORES",
        segundo_apellido="CONDORI",
        estado_civil="CASADO",
        fotografia_path="fotografias/6842190_1B/foto_original.jpg",
    )
    in_memory_session.add(persona)
    await in_memory_session.flush()

    cert = CertificacionModel(
        persona_id=persona.id,
        numero_emision="CERT-2026-0001",
        pdf_path="certificados/6842190_1B/cert_original.pdf",
    )
    in_memory_session.add(cert)
    await in_memory_session.commit()

    repo = PersonaRepository(session=in_memory_session)
    service = PersonaCertificadaService(
        persona_repo=repo,
        segip_service=mock_segip_service,
        storage_service=mock_storage_service,
    )

    # Simular caída de SEGIP
    mock_segip_service.solicitar_certificacion = AsyncMock(
        side_effect=SegipUnavailableException("Servicio SEGIP caído por mantenimiento")
    )

    req = PersonaCertificadaRequest(
        numero_documento="6842190",
        complemento="1B",
        forzar_actualizacion=True,  # Se fuerza actualización pero SEGIP está caído
    )

    resp = await service.consultar_o_certificar_persona(req)

    # No debe lanzar excepción sino degradación grácil
    assert resp.metadatos.origen_datos == "CACHE_BD_DEGRADADO"
    assert resp.metadatos.es_refrescado is False
    assert resp.metadatos.aviso is not None
    assert "No fue posible refrescar los datos desde SEGIP" in resp.metadatos.aviso
    assert resp.persona.nombres == "ROBERTO CARLOS"


@pytest.mark.asyncio
async def test_desambiguacion_duplicados_homonimia_requiere_complemento(
    in_memory_session: AsyncSession,
    mock_storage_service,
    mock_segip_service,
):
    """Verifica que si existen homónimos con la misma CI y distinto complemento en BD, pide desambiguación."""
    p1 = PersonaModel(
        numero_documento="4892341",
        complemento="1A",
        nombres="JUAN",
        primer_apellido="PEREZ",
    )
    p2 = PersonaModel(
        numero_documento="4892341",
        complemento="1B",
        nombres="JUAN CARLOS",
        primer_apellido="PEREZ",
    )
    in_memory_session.add_all([p1, p2])
    await in_memory_session.commit()

    repo = PersonaRepository(session=in_memory_session)
    service = PersonaCertificadaService(
        persona_repo=repo,
        segip_service=mock_segip_service,
        storage_service=mock_storage_service,
    )

    req = PersonaCertificadaRequest(
        numero_documento="4892341",
        complemento="",  # Sin complemento
        forzar_actualizacion=False,
    )

    with pytest.raises(PersonaDuplicadaException) as exc_info:
        await service.consultar_o_certificar_persona(req)

    assert "múltiples registros" in str(exc_info.value.message).lower()


@pytest.mark.asyncio
async def test_soap_cuota_excedida_lanza_excepcion(
    in_memory_session: AsyncSession,
    mock_storage_service,
    mock_segip_service,
):
    """Verifica que si SEGIP retorna mensaje de cuota diaria superada, lanza SegipQuotaExceededException."""
    repo = PersonaRepository(session=in_memory_session)
    service = PersonaCertificadaService(
        persona_repo=repo,
        segip_service=mock_segip_service,
        storage_service=mock_storage_service,
    )

    mock_segip_service.solicitar_certificacion = AsyncMock(
        return_value=CertificacionResponseData(
            es_valido=False,
            mensaje="Ha sobrepasado el límite de cuota diaria autorizada de consultas",
            codigo_respuesta=99,
            reporte_certificacion_base64=None,
        )
    )

    req = PersonaCertificadaRequest(
        numero_documento="9999999",
        complemento="",
    )

    with pytest.raises(SegipQuotaExceededException):
        await service.consultar_o_certificar_persona(req)


@pytest.mark.asyncio
async def test_soap_sin_resultados_lanza_excepcion(
    in_memory_session: AsyncSession,
    mock_storage_service,
    mock_segip_service,
):
    """Verifica que si SEGIP no encuentra la persona, lanza SegipNoResultsException."""
    repo = PersonaRepository(session=in_memory_session)
    service = PersonaCertificadaService(
        persona_repo=repo,
        segip_service=mock_segip_service,
        storage_service=mock_storage_service,
    )

    mock_segip_service.solicitar_certificacion = AsyncMock(
        return_value=CertificacionResponseData(
            es_valido=False,
            mensaje="No existe registro para la cédula consultada",
            codigo_respuesta=1,
            reporte_certificacion_base64=None,
        )
    )

    req = PersonaCertificadaRequest(
        numero_documento="9999999",
        complemento="",
    )

    with pytest.raises(SegipNoResultsException):
        await service.consultar_o_certificar_persona(req)
