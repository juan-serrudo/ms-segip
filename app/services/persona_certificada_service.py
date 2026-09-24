"""Servicio orquestador para consulta y certificación de personas con almacenamiento inmutable en RustFS."""

import base64
import logging
from datetime import UTC, datetime, timedelta

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    PersonaDuplicadaException,
    SegipAuthException,
    SegipNoResultsException,
    SegipQuotaExceededException,
    SegipTimeoutException,
    SegipUnavailableException,
)
from app.models.certificacion import CertificacionModel
from app.models.persona import PersonaModel
from app.parsers.segip_pdf_parser import SegipPdfParser
from app.repositories.persona_repository import PersonaRepository
from app.schemas.pdf import DatosCertificadoPdf
from app.schemas.persona_certificada import (
    ArchivosCertificacion,
    MetadatosConsultaPersona,
    PersonaCertificadaRequest,
    PersonaCertificadaResponseData,
)
from app.schemas.segip import (
    CertificacionConsultaRequest,
    DatosNacimiento,
    DatosPersona,
)
from app.services.segip_service import SegipService
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)


class PersonaCertificadaService:
    """Orquesta la consulta con caché permanente en PostgreSQL e inmutabilidad en RustFS."""

    def __init__(
        self,
        persona_repo: PersonaRepository,
        segip_service: SegipService,
        storage_service: StorageService,
        settings: Settings | None = None,
    ) -> None:
        self.persona_repo = persona_repo
        self.segip_service = segip_service
        self.storage_service = storage_service
        self.settings = settings or get_settings()

    async def consultar_o_certificar_persona(
        self, req: PersonaCertificadaRequest
    ) -> PersonaCertificadaResponseData:
        """Consulta los datos de una persona desde BD local o solicita y procesa la certificación SEGIP."""
        doc = req.numero_documento.strip()
        comp = (req.complemento or "").strip().upper()
        fecha_nac = (req.fecha_nacimiento or "").strip()

        # ==============================================================================
        # 1. Búsqueda en Base de Datos Local (si no se fuerza refresco)
        # ==============================================================================
        if not req.forzar_actualizacion:
            persona_local = await self.persona_repo.buscar_con_desambiguacion(
                numero_documento=doc,
                complemento=comp,
                fecha_nacimiento=fecha_nac,
            )

            if persona_local is not None:
                logger.info(
                    "Persona encontrada en BD local (Cache Hit): doc=%s, comp=%s",
                    persona_local.numero_documento,
                    persona_local.complemento,
                )
                return await self._construir_respuesta_desde_db(
                    persona=persona_local,
                    req=req,
                    origen="CACHE_BD",
                    aviso=None,
                )

        # ==============================================================================
        # 2. Consulta al servicio SOAP de SEGIP (Cache Miss o Refresco Forzado)
        # ==============================================================================
        logger.info(
            "Consultando certificación oficial a SEGIP SOAP: doc=%s, comp=%s (forzar=%s)",
            doc,
            comp,
            req.forzar_actualizacion,
        )

        cert_soap_req = CertificacionConsultaRequest(
            numero_documento=doc,
            complemento=comp,
            nombre=req.nombre or "",
            primer_apellido=req.primer_apellido or "",
            segundo_apellido=req.segundo_apellido or "",
            fecha_nacimiento=req.fecha_nacimiento or "",
            numero_autorizacion=req.numero_autorizacion or "",
            clave_acceso_usuario_final=req.clave_acceso_usuario_final or "",
        )

        cert_data = None
        try:
            cert_data = await self.segip_service.solicitar_certificacion(cert_soap_req)
        except (
            SegipUnavailableException,
            SegipTimeoutException,
            SegipAuthException,
            SegipQuotaExceededException,
            Exception,
        ) as err:
            logger.warning("Fallo al consultar SOAP de SEGIP: %s", err)
            fallback = await self._intentar_degradacion_gracil(
                doc=doc, comp=comp, fecha_nac=fecha_nac, req=req, motivo=str(err)
            )
            if fallback:
                return fallback
            raise

        # ==============================================================================
        # 3. Validación de Respuesta SOAP (Homonimia, Cuotas, No Resultados)
        # ==============================================================================
        msg = (cert_data.mensaje or cert_data.descripcion_respuesta or "").strip()
        msg_lower = msg.lower()

        if (
            "homonim" in msg_lower
            or "duplicad" in msg_lower
            or "más de un" in msg_lower
            or "mas de un" in msg_lower
        ):
            raise PersonaDuplicadaException(
                message=f"SEGIP reporta múltiples registros u homonimia: {msg}. Especifique complemento o fecha de nacimiento.",
                details={"mensaje": msg, "codigo": cert_data.codigo_respuesta},
            )

        if "cuota" in msg_lower or "limite" in msg_lower:
            fallback = await self._intentar_degradacion_gracil(
                doc=doc, comp=comp, fecha_nac=fecha_nac, req=req, motivo=f"Cuota agotada: {msg}"
            )
            if fallback:
                return fallback
            raise SegipQuotaExceededException(
                message=f"Se ha superado la cuota diaria de consultas asignada por SEGIP: {msg}",
                details={"mensaje": msg, "codigo": cert_data.codigo_respuesta},
            )

        reporte_b64 = cert_data.reporte_certificacion_base64
        if (cert_data.es_valido is False and not reporte_b64) or not reporte_b64:
            raise SegipNoResultsException(
                message=f"La consulta no arrojó certificación en SEGIP: {msg}".strip(),
                details={"mensaje": msg, "codigo": cert_data.codigo_respuesta},
            )

        # ==============================================================================
        # 4. Extracción de Datos y Fotografía del PDF con PyMuPDF
        # ==============================================================================
        clean_b64 = reporte_b64.strip()
        if "," in clean_b64 and clean_b64.startswith("data:"):
            clean_b64 = clean_b64.split(",", 1)[1].strip()

        pdf_bytes = base64.b64decode(clean_b64)
        parsed = SegipPdfParser(pdf_bytes=pdf_bytes, extraer_fotografia=True).parse()

        # Extraer fotografía binaria si fue encontrada en el documento
        foto_bytes = None
        if parsed.persona.fotografia_base64:
            foto_b64 = parsed.persona.fotografia_base64.strip()
            if "," in foto_b64 and foto_b64.startswith("data:"):
                foto_b64 = foto_b64.split(",", 1)[1].strip()
            foto_bytes = base64.b64decode(foto_b64)

        # ==============================================================================
        # 5. Almacenamiento Inmutable en RustFS/S3
        # ==============================================================================
        # Subir el documento PDF con timestamp y hash SHA-256
        pdf_path, pdf_sha, pdf_size = await self.storage_service.guardar_pdf(
            numero_documento=doc,
            complemento=comp,
            pdf_bytes=pdf_bytes,
        )

        # Subir la fotografía con timestamp y hash si existe
        foto_path = None
        if foto_bytes:
            foto_path, _, _ = await self.storage_service.guardar_fotografia(
                numero_documento=doc,
                complemento=comp,
                foto_bytes=foto_bytes,
                content_type="image/jpeg",
            )

        # ==============================================================================
        # 6. Persistencia Relacional en PostgreSQL
        # ==============================================================================
        # Asegurar consistencia de documento y complemento normalizados
        if not parsed.persona.numero_documento:
            parsed.persona.numero_documento = doc
        if comp and not parsed.persona.complemento:
            parsed.persona.complemento = comp

        persona_guardada = await self.persona_repo.upsert_persona(
            data=parsed.persona,
            nacimiento=parsed.nacimiento,
            fotografia_path=foto_path,
        )

        cert_guardada = await self.persona_repo.registrar_certificacion(
            persona_id=persona_guardada.id,
            certificado=parsed.certificado,
            pdf_path=pdf_path,
            pdf_tamanio_bytes=pdf_size,
            pdf_sha256=pdf_sha,
            usuario_consulta=req.clave_acceso_usuario_final or "SISTEMA",
        )

        await self.persona_repo.registrar_bitacora(
            numero_documento=doc,
            complemento=comp,
            tipo_origen="SEGIP_SOAP",
            exitoso=True,
            codigo_respuesta=str(cert_data.codigo_respuesta or 200),
            mensaje=f"Certificación emitida: {parsed.certificado.numero_emision or 'S/N'}",
            usuario_operador=req.clave_acceso_usuario_final,
        )

        # ==============================================================================
        # 7. Generación de URLs Prefirmadas en RustFS
        # ==============================================================================
        archivos = self._generar_archivos_certificacion(
            pdf_path=pdf_path,
            foto_path=foto_path,
            req=req,
        )

        total_certs = await self.persona_repo.contar_certificaciones(persona_guardada.id)

        metadatos = MetadatosConsultaPersona(
            origen_datos="SEGIP_SOAP",
            es_refrescado=True,
            aviso=None,
            fecha_ultima_consulta_segip=cert_guardada.created_at,
            total_certificaciones_registradas=total_certs,
        )

        # La fotografía física se sirve vía URL prefirmada de RustFS
        parsed.persona.fotografia_base64 = None

        return PersonaCertificadaResponseData(
            persona=parsed.persona,
            nacimiento=parsed.nacimiento,
            certificado=parsed.certificado,
            archivos=archivos,
            metadatos=metadatos,
        )

    async def _intentar_degradacion_gracil(
        self,
        doc: str,
        comp: str,
        fecha_nac: str,
        req: PersonaCertificadaRequest,
        motivo: str,
    ) -> PersonaCertificadaResponseData | None:
        """Intenta retornar datos históricos de BD cuando falla la actualización forzada."""
        if not req.forzar_actualizacion:
            return None
        try:
            persona_existente = await self.persona_repo.buscar_con_desambiguacion(
                numero_documento=doc,
                complemento=comp,
                fecha_nacimiento=fecha_nac,
            )
            if persona_existente is not None:
                logger.warning(
                    "Aplicando degradación grácil: Falló SEGIP (%s), devolviendo datos históricos de BD",
                    motivo,
                )
                aviso_fallback = (
                    "No fue posible refrescar los datos desde SEGIP (servicio no disponible o cuota agotada). "
                    "Se retornan los últimos datos históricos certificados registrados en el sistema."
                )
                return await self._construir_respuesta_desde_db(
                    persona=persona_existente,
                    req=req,
                    origen="CACHE_BD_DEGRADADO",
                    aviso=aviso_fallback,
                )
        except PersonaDuplicadaException:
            pass
        return None

    def _generar_archivos_certificacion(
        self,
        pdf_path: str | None,
        foto_path: str | None,
        req: PersonaCertificadaRequest,
    ) -> ArchivosCertificacion:
        """Genera las URLs prefirmadas en RustFS con su respectiva vigencia."""
        expiracion = req.tiempo_expiracion_url_segundos
        url_pdf = None
        if req.generar_url_pdf and pdf_path:
            url_pdf = self.storage_service.generar_url_prefirmada(pdf_path, expiracion)

        url_foto = None
        if req.generar_url_imagen and foto_path:
            url_foto = self.storage_service.generar_url_prefirmada(foto_path, expiracion)

        fecha_exp_dt = datetime.now(UTC) + timedelta(seconds=expiracion)
        return ArchivosCertificacion(
            url_presignada_pdf=url_pdf,
            url_presignada_imagen=url_foto,
            vigencia_segundos=expiracion,
            fecha_expiracion=fecha_exp_dt,
        )

    @staticmethod
    def _mapear_datos_persona(persona: PersonaModel) -> DatosPersona:
        """Mapea la entidad ORM PersonaModel al esquema DatosPersona."""
        return DatosPersona(
            numero_documento=persona.numero_documento,
            complemento=persona.complemento,
            nombres=persona.nombres,
            primer_apellido=persona.primer_apellido,
            segundo_apellido=persona.segundo_apellido,
            fecha_nacimiento=persona.fecha_nacimiento.isoformat()
            if persona.fecha_nacimiento
            else None,
            sexo=persona.sexo,
            estado_civil=persona.estado_civil,
            domicilio=persona.domicilio,
            profesion_ocupacion=persona.profesion_ocupacion,
            fotografia_base64=None,
        )

    @staticmethod
    def _mapear_datos_nacimiento(persona: PersonaModel) -> DatosNacimiento:
        """Mapea la entidad ORM PersonaModel al esquema DatosNacimiento."""
        return DatosNacimiento(
            pais=persona.pais_nacimiento,
            departamento=persona.departamento_nacimiento,
            provincia=persona.provincia_nacimiento,
            localidad=persona.localidad_nacimiento,
        )

    @staticmethod
    def _mapear_datos_certificado(ultima_cert: CertificacionModel | None) -> DatosCertificadoPdf:
        """Mapea la entidad ORM CertificacionModel al esquema DatosCertificadoPdf."""
        if not ultima_cert:
            return DatosCertificadoPdf()
        return DatosCertificadoPdf(
            numero_emision=ultima_cert.numero_emision,
            codigo_segip=ultima_cert.codigo_segip,
            fecha_emision=ultima_cert.fecha_emision,
            motivo_consulta=ultima_cert.motivo_consulta,
            paginas=ultima_cert.paginas,
        )

    async def _construir_respuesta_desde_db(
        self,
        persona: PersonaModel,
        req: PersonaCertificadaRequest,
        origen: str,
        aviso: str | None,
    ) -> PersonaCertificadaResponseData:
        """Construye la respuesta consolidada a partir de los registros en PostgreSQL."""
        ultima_cert: CertificacionModel | None = await self.persona_repo.get_ultima_certificacion(
            persona.id
        )
        total_certs = await self.persona_repo.contar_certificaciones(persona.id)

        archivos = self._generar_archivos_certificacion(
            pdf_path=ultima_cert.pdf_path if ultima_cert else None,
            foto_path=persona.fotografia_path,
            req=req,
        )

        metadatos = MetadatosConsultaPersona(
            origen_datos=origen,
            es_refrescado=False,
            aviso=aviso,
            fecha_ultima_consulta_segip=ultima_cert.created_at
            if ultima_cert
            else persona.updated_at,
            total_certificaciones_registradas=total_certs,
        )

        datos_persona = self._mapear_datos_persona(persona)
        datos_nacimiento = self._mapear_datos_nacimiento(persona)
        datos_certificado = self._mapear_datos_certificado(ultima_cert)

        # Registrar bitácora de consulta por caché
        await self.persona_repo.registrar_bitacora(
            numero_documento=persona.numero_documento,
            complemento=persona.complemento,
            tipo_origen=origen,
            exitoso=True,
            codigo_respuesta="200",
            mensaje="Recuperado desde base de datos relacional (caché permanente)",
            usuario_operador=req.clave_acceso_usuario_final,
        )

        return PersonaCertificadaResponseData(
            persona=datos_persona,
            nacimiento=datos_nacimiento,
            certificado=datos_certificado,
            archivos=archivos,
            metadatos=metadatos,
        )
