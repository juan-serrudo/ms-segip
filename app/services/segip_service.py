import base64
import logging
from typing import Any

from app.core.config import Settings
from app.core.exceptions import (
    SegipAuthException,
    SegipNoResultsException,
    SegipTimeoutException,
    SegipUnavailableException,
)
from app.integrations.segip.client import SegipSoapClient
from app.integrations.segip.exceptions import (
    SegipAuthError,
    SegipCommunicationError,
    SegipSoapFaultError,
    SegipTimeoutError,
)
from app.integrations.segip.mapper import SegipResponseMapper
from app.parsers.segip_pdf_parser import SegipPdfParser
from app.schemas.segip import (
    CertificacionConsultaRequest,
    CertificacionQrRequest,
    CertificacionResponseData,
    ContrastacionRequest,
    ContrastacionResponseData,
    PersonaConsultaRequest,
    PersonaNormalizada,
    QrVerificacionResponseData,
    VersionResponseData,
)

logger = logging.getLogger(__name__)


class SegipService:
    """Servicio de dominio para coordinar consultas y transformaciones con SEGIP."""

    def __init__(self, client: SegipSoapClient, settings: Settings) -> None:
        self.client = client
        self.settings = settings

    async def get_version(self) -> VersionResponseData:
        """Obtiene la versión del sistema SEGIP desde el servicio SOAP."""
        try:
            version_str = await self.client.obtiene_version_sistema()
            return VersionResponseData(
                version=version_str,
                servicio_url=self.settings.SEGIP_SERVICE_URL,
            )
        except SegipTimeoutError as err:
            raise SegipTimeoutException(details=str(err)) from err
        except SegipCommunicationError as err:
            raise SegipUnavailableException(details=str(err)) from err

    async def check_readiness(self) -> tuple[bool, str]:
        """Comprueba conectividad contra SEGIP mediante ObtieneVersionSistema."""
        try:
            version = await self.client.obtiene_version_sistema()
            return True, f"Conexión exitosa con SEGIP (versión {version})"
        except Exception as err:
            logger.warning("Fallo al verificar readiness contra SEGIP: %s", err)
            return False, f"SEGIP no responde: {err}"

    def _resolve_usuario_final(self, usuario_final: str | None) -> str:
        """Obtiene la clave de usuario final solicitada o recurre a la configurada por defecto."""
        return (usuario_final or self.settings.SEGIP_USUARIO_FINAL or "").strip()

    async def consultar_persona(self, req: PersonaConsultaRequest) -> PersonaNormalizada:
        """Consulta datos de una persona mediante SOAP y retorna el esquema normalizado."""
        clave_usuario = self._resolve_usuario_final(req.clave_acceso_usuario_final)
        try:
            if req.fecha_expiracion:
                raw_response = await self.client.consulta_documento_dato_persona_en_json(
                    numero_documento=req.numero_documento,
                    complemento=req.complemento or "",
                    nombre=req.nombre or "",
                    primer_apellido=req.primer_apellido or "",
                    segundo_apellido=req.segundo_apellido or "",
                    fecha_nacimiento=req.fecha_nacimiento or "",
                    fecha_expiracion=req.fecha_expiracion,
                    numero_autorizacion=req.numero_autorizacion or "",
                    clave_acceso_usuario_final=clave_usuario,
                )
                self._validate_consulta_result(raw_response)
                return SegipResponseMapper.map_to_persona_normalizada(raw_response)

            raw_response = await self.client.consulta_dato_persona_en_json(
                numero_documento=req.numero_documento,
                complemento=req.complemento or "",
                nombre=req.nombre or "",
                primer_apellido=req.primer_apellido or "",
                segundo_apellido=req.segundo_apellido or "",
                fecha_nacimiento=req.fecha_nacimiento or "",
                numero_autorizacion=req.numero_autorizacion or "",
                clave_acceso_usuario_final=clave_usuario,
            )

            # Verificar si la consulta JSON devolvió error de recurso no asignado/definido
            es_valido = raw_response.get("EsValido")
            if isinstance(es_valido, str):
                es_valido = es_valido.lower() in ("true", "1")
            msg = raw_response.get("Mensaje") or raw_response.get("DescripcionRespuesta") or ""
            is_unassigned = (
                "no está asignado" in msg.lower()
                or "no esta asignado" in msg.lower()
                or "no está definido" in msg.lower()
                or "no esta definido" in msg.lower()
            )

            # Si el endpoint JSON no está asignado al convenio, recurrir a ConsultaDatoPersonaCertificacion
            if (not es_valido and is_unassigned) and self.settings.SEGIP_FALLBACK_TO_CERTIFICACION:
                logger.info(
                    "ConsultaDatoPersonaEnJson no disponible para el usuario (%s). Recurriendo automáticamente a ConsultaDatoPersonaCertificacion...",
                    msg,
                )
                raw_cert = await self.client.consulta_dato_persona_certificacion(
                    numero_documento=req.numero_documento,
                    complemento=req.complemento or "",
                    nombre=req.nombre or "",
                    primer_apellido=req.primer_apellido or "",
                    segundo_apellido=req.segundo_apellido or "",
                    fecha_nacimiento=req.fecha_nacimiento or "",
                    numero_autorizacion=req.numero_autorizacion or "",
                    clave_acceso_usuario_final=clave_usuario,
                )
                cert_valido = raw_cert.get("EsValido")
                if isinstance(cert_valido, str):
                    cert_valido = cert_valido.lower() in ("true", "1")
                cert_msg = raw_cert.get("Mensaje") or raw_cert.get("DescripcionRespuesta") or ""
                reporte_b64 = raw_cert.get("ReporteCertificacion")

                if cert_valido is False and not reporte_b64:
                    raise SegipNoResultsException(
                        message=f"La consulta no arrojó resultados en SEGIP: {cert_msg}".strip(),
                        details={"mensaje": cert_msg, "codigo": raw_cert.get("CodigoRespuesta")},
                    )

                if reporte_b64:
                    pdf_bytes = base64.b64decode(reporte_b64)
                    parsed_pdf = SegipPdfParser(pdf_bytes, extraer_fotografia=True).parse()
                    return SegipResponseMapper.map_pdf_extract_to_persona_normalizada(
                        parsed_pdf, raw_cert
                    )

            # Validar resultado de la consulta JSON
            self._validate_consulta_result(raw_response)
            return SegipResponseMapper.map_to_persona_normalizada(raw_response)

        except SegipAuthError as err:
            raise SegipAuthException(details=str(err)) from err
        except SegipTimeoutError as err:
            raise SegipTimeoutException(details=str(err)) from err
        except (SegipCommunicationError, SegipSoapFaultError) as err:
            raise SegipUnavailableException(details=str(err)) from err

    async def solicitar_certificacion(
        self, req: CertificacionConsultaRequest
    ) -> CertificacionResponseData:
        """Solicita la certificación PDF emitida por SEGIP."""
        clave_usuario = self._resolve_usuario_final(req.clave_acceso_usuario_final)
        try:
            raw_response = await self.client.consulta_dato_persona_certificacion(
                numero_documento=req.numero_documento,
                complemento=req.complemento or "",
                nombre=req.nombre or "",
                primer_apellido=req.primer_apellido or "",
                segundo_apellido=req.segundo_apellido or "",
                fecha_nacimiento=req.fecha_nacimiento or "",
                numero_autorizacion=req.numero_autorizacion or "",
                clave_acceso_usuario_final=clave_usuario,
            )
            return SegipResponseMapper.map_to_certificacion(raw_response)

        except SegipAuthError as err:
            raise SegipAuthException(details=str(err)) from err
        except SegipTimeoutError as err:
            raise SegipTimeoutException(details=str(err)) from err
        except (SegipCommunicationError, SegipSoapFaultError) as err:
            raise SegipUnavailableException(details=str(err)) from err

    async def verificar_qr(self, req: CertificacionQrRequest) -> QrVerificacionResponseData:
        """Verifica una certificación de SEGIP a partir de su código QR."""
        clave_usuario = self._resolve_usuario_final(req.clave_acceso_usuario_final)
        try:
            raw_response = await self.client.consulta_verificacion_certificacion_codigo_qr(
                codigo_qr=req.codigo_qr,
                numero_autorizacion=req.numero_autorizacion or "",
                clave_acceso_usuario_final=clave_usuario,
            )
            return SegipResponseMapper.map_to_qr_verificacion(raw_response)

        except SegipAuthError as err:
            raise SegipAuthException(details=str(err)) from err
        except SegipTimeoutError as err:
            raise SegipTimeoutException(details=str(err)) from err
        except (SegipCommunicationError, SegipSoapFaultError) as err:
            raise SegipUnavailableException(details=str(err)) from err

    async def contrastar(self, req: ContrastacionRequest) -> ContrastacionResponseData:
        """Ejecuta una contrastación de datos en SEGIP."""
        clave_usuario = self._resolve_usuario_final(req.clave_acceso_usuario_final)
        try:
            raw_response = await self.client.consulta_dato_persona_contrastacion(
                lista_campo=req.lista_campos,
                tipo_persona=req.tipo_persona,
                numero_autorizacion=req.numero_autorizacion or "",
                clave_acceso_usuario_final=clave_usuario,
            )
            return SegipResponseMapper.map_to_contrastacion(raw_response)

        except SegipAuthError as err:
            raise SegipAuthException(details=str(err)) from err
        except SegipTimeoutError as err:
            raise SegipTimeoutException(details=str(err)) from err
        except (SegipCommunicationError, SegipSoapFaultError) as err:
            raise SegipUnavailableException(details=str(err)) from err

    def _validate_consulta_result(self, raw_response: dict[str, Any]) -> None:
        """Valida que la respuesta de SEGIP contenga un resultado positivo."""
        es_valido = raw_response.get("EsValido")
        if isinstance(es_valido, str):
            es_valido = es_valido.lower() in ("true", "1")

        msg = raw_response.get("Mensaje") or raw_response.get("DescripcionRespuesta") or ""

        # Si SEGIP explícitamente indica que no es válido y no hay JSON devuelto
        json_content = raw_response.get("DatosPersonaEnFormatoJson")
        if es_valido is False and not json_content:
            raise SegipNoResultsException(
                message=f"La consulta no arrojó resultados en SEGIP: {msg}".strip(),
                details={"mensaje": msg, "codigo": raw_response.get("CodigoRespuesta")},
            )
