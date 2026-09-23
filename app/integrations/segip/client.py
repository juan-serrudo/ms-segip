"""Cliente SOAP 1.1 explícito y seguro para el servicio IServicioExternoInstitucion de SEGIP."""

import asyncio
import logging
import xml.etree.ElementTree as ET
from typing import Any
from xml.sax.saxutils import escape

import defusedxml.ElementTree as defused_ET
import httpx

from app.core.config import Settings
from app.core.logging import mask_document_number, sanitize_sensitive_data
from app.integrations.segip.exceptions import (
    SegipAuthError,
    SegipCommunicationError,
    SegipEmptyResponseError,
    SegipSoapFaultError,
    SegipTimeoutError,
)

logger = logging.getLogger(__name__)

# Namespaces SOAP estándar utilizados por WCF ASP.NET
SOAP_ENV_NS = "http://schemas.xmlsoap.org/soap/envelope/"
TEMPURI_NS = "http://tempuri.org/"
ACTION_BASE = "http://tempuri.org/IServicioExternoInstitucion"


def _xml_escape(val: Any) -> str:
    """Escapa de forma segura cadenas para XML."""
    if val is None:
        return ""
    return escape(str(val), entities={'"': "&quot;", "'": "&apos;"})


class SegipSoapClient:
    """Cliente SOAP 1.1 asíncrono y resiliente para la integración con SEGIP."""

    def __init__(
        self,
        settings: Settings,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.settings = settings
        self.service_url = settings.SEGIP_SERVICE_URL
        self.institution_code = settings.SEGIP_INSTITUTION_CODE
        self.username = settings.SEGIP_USERNAME
        self.password = settings.SEGIP_PASSWORD
        self.max_retries = settings.SEGIP_MAX_RETRIES

        # Timeouts específicos de conexión y lectura
        self.timeout = httpx.Timeout(
            connect=settings.SEGIP_CONNECT_TIMEOUT,
            read=settings.SEGIP_READ_TIMEOUT,
            write=10.0,
            pool=5.0,
        )

        # Cliente HTTP asíncrono con verificación TLS activa
        self._client = httpx.AsyncClient(
            transport=transport,
            timeout=self.timeout,
            verify=True,  # No desactivar verificación TLS
            follow_redirects=False,
        )

    async def close(self) -> None:
        """Cierra el cliente HTTP subyacente."""
        await self._client.aclose()

    async def __aenter__(self) -> "SegipSoapClient":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    # ==========================================================================
    # Operaciones Publicadas del Servicio SOAP
    # ==========================================================================

    async def obtiene_version_sistema(self) -> str:
        """Consulta la versión del sistema SEGIP mediante ObtieneVersionSistema."""
        soap_action = f"{ACTION_BASE}/ObtieneVersionSistema"
        body = '<tem:ObtieneVersionSistema xmlns:tem="http://tempuri.org/"/>'

        result_dict = await self._send_soap_request("ObtieneVersionSistema", soap_action, body)
        version = result_dict.get("ObtieneVersionSistemaResult") or result_dict.get("value")
        if not version:
            raise SegipEmptyResponseError(
                "No se obtuvo la versión del sistema en la respuesta SOAP"
            )
        return str(version).strip()

    async def consulta_dato_persona_en_json(
        self,
        numero_documento: str,
        complemento: str = "",
        nombre: str = "",
        primer_apellido: str = "",
        segundo_apellido: str = "",
        fecha_nacimiento: str = "",
        numero_autorizacion: str = "",
        clave_acceso_usuario_final: str = "",
    ) -> dict[str, Any]:
        """Consulta datos de una persona devolviendo la estructura JSON y Fotografía."""
        logger.info(
            "Consultando persona en JSON para CI: %s complemento: '%s'",
            mask_document_number(numero_documento),
            complemento,
        )
        soap_action = f"{ACTION_BASE}/ConsultaDatoPersonaEnJson"

        body = f"""<tem:ConsultaDatoPersonaEnJson xmlns:tem="{TEMPURI_NS}">
            <tem:pCodigoInstitucion>{self.institution_code}</tem:pCodigoInstitucion>
            <tem:pUsuario>{_xml_escape(self.username)}</tem:pUsuario>
            <tem:pContrasenia>{_xml_escape(self.password)}</tem:pContrasenia>
            <tem:pClaveAccesoUsuarioFinal>{_xml_escape(clave_acceso_usuario_final)}</tem:pClaveAccesoUsuarioFinal>
            <tem:pNumeroAutorizacion>{_xml_escape(numero_autorizacion)}</tem:pNumeroAutorizacion>
            <tem:pNumeroDocumento>{_xml_escape(numero_documento)}</tem:pNumeroDocumento>
            <tem:pComplemento>{_xml_escape(complemento)}</tem:pComplemento>
            <tem:pNombre>{_xml_escape(nombre)}</tem:pNombre>
            <tem:pPrimerApellido>{_xml_escape(primer_apellido)}</tem:pPrimerApellido>
            <tem:pSegundoApellido>{_xml_escape(segundo_apellido)}</tem:pSegundoApellido>
            <tem:pFechaNacimiento>{_xml_escape(fecha_nacimiento)}</tem:pFechaNacimiento>
        </tem:ConsultaDatoPersonaEnJson>"""

        raw_result = await self._send_soap_request("ConsultaDatoPersonaEnJson", soap_action, body)
        return self._extract_result_dict(raw_result, "ConsultaDatoPersonaEnJsonResult")

    async def consulta_documento_dato_persona_en_json(
        self,
        numero_documento: str,
        complemento: str = "",
        nombre: str = "",
        primer_apellido: str = "",
        segundo_apellido: str = "",
        fecha_nacimiento: str = "",
        fecha_expiracion: str = "",
        numero_autorizacion: str = "",
        clave_acceso_usuario_final: str = "",
    ) -> dict[str, Any]:
        """Consulta documental de datos de persona incluyendo fecha de expiración."""
        logger.info(
            "Consultando documento de persona en JSON para CI: %s",
            mask_document_number(numero_documento),
        )
        soap_action = f"{ACTION_BASE}/ConsultaDocumentoDatoPersonaEnJson"

        body = f"""<tem:ConsultaDocumentoDatoPersonaEnJson xmlns:tem="{TEMPURI_NS}">
            <tem:pCodigoInstitucion>{self.institution_code}</tem:pCodigoInstitucion>
            <tem:pUsuario>{_xml_escape(self.username)}</tem:pUsuario>
            <tem:pContrasenia>{_xml_escape(self.password)}</tem:pContrasenia>
            <tem:pClaveAccesoUsuarioFinal>{_xml_escape(clave_acceso_usuario_final)}</tem:pClaveAccesoUsuarioFinal>
            <tem:pNumeroAutorizacion>{_xml_escape(numero_autorizacion)}</tem:pNumeroAutorizacion>
            <tem:pNumeroDocumento>{_xml_escape(numero_documento)}</tem:pNumeroDocumento>
            <tem:pComplemento>{_xml_escape(complemento)}</tem:pComplemento>
            <tem:pNombre>{_xml_escape(nombre)}</tem:pNombre>
            <tem:pPrimerApellido>{_xml_escape(primer_apellido)}</tem:pPrimerApellido>
            <tem:pSegundoApellido>{_xml_escape(segundo_apellido)}</tem:pSegundoApellido>
            <tem:pFechaNacimiento>{_xml_escape(fecha_nacimiento)}</tem:pFechaNacimiento>
            <tem:pFechaExpiracion>{_xml_escape(fecha_expiracion)}</tem:pFechaExpiracion>
        </tem:ConsultaDocumentoDatoPersonaEnJson>"""

        raw_result = await self._send_soap_request(
            "ConsultaDocumentoDatoPersonaEnJson", soap_action, body
        )
        return self._extract_result_dict(raw_result, "ConsultaDocumentoDatoPersonaEnJsonResult")

    async def consulta_dato_persona_certificacion(
        self,
        numero_documento: str,
        complemento: str = "",
        nombre: str = "",
        primer_apellido: str = "",
        segundo_apellido: str = "",
        fecha_nacimiento: str = "",
        numero_autorizacion: str = "",
        clave_acceso_usuario_final: str = "",
    ) -> dict[str, Any]:
        """Obtiene la certificación oficial de SEGIP en formato PDF Base64."""
        logger.info(
            "Solicitando certificación PDF para CI: %s",
            mask_document_number(numero_documento),
        )
        soap_action = f"{ACTION_BASE}/ConsultaDatoPersonaCertificacion"

        body = f"""<tem:ConsultaDatoPersonaCertificacion xmlns:tem="{TEMPURI_NS}">
            <tem:pCodigoInstitucion>{self.institution_code}</tem:pCodigoInstitucion>
            <tem:pUsuario>{_xml_escape(self.username)}</tem:pUsuario>
            <tem:pContrasenia>{_xml_escape(self.password)}</tem:pContrasenia>
            <tem:pClaveAccesoUsuarioFinal>{_xml_escape(clave_acceso_usuario_final)}</tem:pClaveAccesoUsuarioFinal>
            <tem:pNumeroAutorizacion>{_xml_escape(numero_autorizacion)}</tem:pNumeroAutorizacion>
            <tem:pNumeroDocumento>{_xml_escape(numero_documento)}</tem:pNumeroDocumento>
            <tem:pComplemento>{_xml_escape(complemento)}</tem:pComplemento>
            <tem:pNombre>{_xml_escape(nombre)}</tem:pNombre>
            <tem:pPrimerApellido>{_xml_escape(primer_apellido)}</tem:pPrimerApellido>
            <tem:pSegundoApellido>{_xml_escape(segundo_apellido)}</tem:pSegundoApellido>
            <tem:pFechaNacimiento>{_xml_escape(fecha_nacimiento)}</tem:pFechaNacimiento>
        </tem:ConsultaDatoPersonaCertificacion>"""

        raw_result = await self._send_soap_request(
            "ConsultaDatoPersonaCertificacion", soap_action, body
        )
        return self._extract_result_dict(raw_result, "ConsultaDatoPersonaCertificacionResult")

    async def consulta_verificacion_certificacion_codigo_qr(
        self,
        codigo_qr: str,
        numero_autorizacion: str = "",
        clave_acceso_usuario_final: str = "",
    ) -> dict[str, Any]:
        """Verifica una certificación mediante el texto extraído del código QR."""
        logger.info("Verificando certificación por código QR en SEGIP")
        soap_action = f"{ACTION_BASE}/ConsultaVerificacionCertificacionCodigoQr"

        # Nota de WSDL: el elemento se llama pIdInstitucion en lugar de pCodigoInstitucion
        body = f"""<tem:ConsultaVerificacionCertificacionCodigoQr xmlns:tem="{TEMPURI_NS}">
            <tem:pIdInstitucion>{self.institution_code}</tem:pIdInstitucion>
            <tem:pUsuario>{_xml_escape(self.username)}</tem:pUsuario>
            <tem:pContrasenia>{_xml_escape(self.password)}</tem:pContrasenia>
            <tem:pClaveAccesoUsuarioFinal>{_xml_escape(clave_acceso_usuario_final)}</tem:pClaveAccesoUsuarioFinal>
            <tem:pNumeroAutorizacion>{_xml_escape(numero_autorizacion)}</tem:pNumeroAutorizacion>
            <tem:pCodigoQr>{_xml_escape(codigo_qr)}</tem:pCodigoQr>
        </tem:ConsultaVerificacionCertificacionCodigoQr>"""

        raw_result = await self._send_soap_request(
            "ConsultaVerificacionCertificacionCodigoQr", soap_action, body
        )
        return self._extract_result_dict(
            raw_result, "ConsultaVerificacionCertificacionCodigoQrResult"
        )

    async def consulta_dato_persona_contrastacion(
        self,
        lista_campo: str,
        tipo_persona: int = 1,
        numero_autorizacion: str = "",
        clave_acceso_usuario_final: str = "",
    ) -> dict[str, Any]:
        """Contrasta campos de una persona contra la base de datos de SEGIP."""
        logger.info("Realizando contrastación de datos en SEGIP (tipo_persona=%s)", tipo_persona)
        soap_action = f"{ACTION_BASE}/ConsultaDatoPersonaContrastacion"

        body = f"""<tem:ConsultaDatoPersonaContrastacion xmlns:tem="{TEMPURI_NS}">
            <tem:pCodigoInstitucion>{self.institution_code}</tem:pCodigoInstitucion>
            <tem:pUsuario>{_xml_escape(self.username)}</tem:pUsuario>
            <tem:pContrasenia>{_xml_escape(self.password)}</tem:pContrasenia>
            <tem:pClaveAccesoUsuarioFinal>{_xml_escape(clave_acceso_usuario_final)}</tem:pClaveAccesoUsuarioFinal>
            <tem:pNumeroAutorizacion>{_xml_escape(numero_autorizacion)}</tem:pNumeroAutorizacion>
            <tem:pListaCampo>{_xml_escape(lista_campo)}</tem:pListaCampo>
            <tem:pTipoPersona>{tipo_persona}</tem:pTipoPersona>
        </tem:ConsultaDatoPersonaContrastacion>"""

        raw_result = await self._send_soap_request(
            "ConsultaDatoPersonaContrastacion", soap_action, body
        )
        return self._extract_result_dict(raw_result, "ConsultaDatoPersonaContrastacionResult")

    # ==========================================================================
    # Envío de Mensajes SOAP y Manejo de Respuestas
    # ==========================================================================

    async def _send_soap_request(
        self,
        operation_name: str,
        soap_action: str,
        body_xml: str,
    ) -> dict[str, Any]:
        """Envía un sobre SOAP 1.1 mediante HTTP POST con reintentos para fallos transitorios."""
        envelope = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tem="http://tempuri.org/">
    <soap:Header/>
    <soap:Body>
        {body_xml}
    </soap:Body>
</soap:Envelope>"""

        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": f'"{soap_action}"',
        }

        logger.debug(
            "Enviando sobre SOAP 1.1 [%s] a %s:\n%s",
            operation_name,
            self.service_url,
            sanitize_sensitive_data(envelope),
        )

        retries = 0
        last_exception: Exception | None = None

        while retries <= self.max_retries:
            try:
                response = await self._client.post(
                    url=self.service_url,
                    content=envelope.encode("utf-8"),
                    headers=headers,
                )

                logger.debug(
                    "Respuesta SOAP recibida [%s] HTTP %d:\n%s",
                    operation_name,
                    response.status_code,
                    sanitize_sensitive_data(response.text),
                )

                # Si es un error 500 con cuerpo SOAP Fault, procesar la falla
                if response.status_code == 500:
                    self._check_and_raise_soap_fault(response.content)
                    raise SegipCommunicationError(
                        f"Error HTTP 500 recibido desde SEGIP: {response.text}"
                    )

                # Verificar códigos de error HTTP transitorios para reintento
                if response.status_code in (502, 503, 504):
                    if retries < self.max_retries:
                        retries += 1
                        backoff = 0.5 * (2 ** (retries - 1))
                        logger.warning(
                            "Fallo transitorio HTTP %s al llamar a %s. Reintento %s/%s en %.2fs",
                            response.status_code,
                            operation_name,
                            retries,
                            self.max_retries,
                            backoff,
                        )
                        await asyncio.sleep(backoff)
                        continue
                    raise SegipCommunicationError(
                        f"Servicio SEGIP no disponible temporalmente (HTTP {response.status_code})"
                    )

                if response.status_code == 401 or response.status_code == 403:
                    raise SegipAuthError("Acceso no autorizado al servicio institucional de SEGIP")

                response.raise_for_status()
                return self._parse_soap_response(response.content, operation_name)

            except httpx.ConnectTimeout as err:
                last_exception = SegipTimeoutError(f"Timeout de conexión hacia SEGIP: {err}")
                if retries < self.max_retries:
                    retries += 1
                    await asyncio.sleep(0.5 * retries)
                    continue
                raise last_exception from err

            except httpx.ReadTimeout as err:
                last_exception = SegipTimeoutError(
                    f"Timeout de lectura esperando respuesta de SEGIP: {err}"
                )
                if retries < self.max_retries:
                    retries += 1
                    await asyncio.sleep(0.5 * retries)
                    continue
                raise last_exception from err

            except (httpx.ConnectError, httpx.NetworkError) as err:
                last_exception = SegipCommunicationError(
                    f"Error de red al conectar con SEGIP: {err}"
                )
                if retries < self.max_retries:
                    retries += 1
                    await asyncio.sleep(0.5 * retries)
                    continue
                raise last_exception from err

        if last_exception:
            raise last_exception
        raise SegipCommunicationError("No se pudo completar la llamada al servicio SEGIP")

    def _check_and_raise_soap_fault(self, content_bytes: bytes) -> None:
        """Verifica si el contenido XML devuelto corresponde a un SOAP Fault y levanta la excepción."""
        try:
            root = defused_ET.fromstring(content_bytes)
            # Buscar Fault en el namespace SOAP
            fault = root.find(".//{http://schemas.xmlsoap.org/soap/envelope/}Fault")
            if fault is not None:
                fault_code_el = fault.find("faultcode")
                fault_string_el = fault.find("faultstring")
                detail_el = fault.find("detail")

                code = (
                    fault_code_el.text
                    if fault_code_el is not None and fault_code_el.text
                    else "Unknown"
                )
                string = (
                    fault_string_el.text
                    if fault_string_el is not None and fault_string_el.text
                    else "SOAP Error"
                )
                detail = detail_el.text if detail_el is not None and detail_el.text else ""

                logger.error("SOAP Fault detectado: code=%s, string=%s", code, string)
                raise SegipSoapFaultError(fault_code=code, fault_string=string, detail=detail)
        except ET.ParseError:
            pass

    def _parse_soap_response(self, content_bytes: bytes, operation_name: str) -> dict[str, Any]:
        """Parsea el cuerpo de la respuesta SOAP en un diccionario de claves y valores."""
        try:
            root = defused_ET.fromstring(content_bytes)
        except Exception as err:
            raise SegipCommunicationError(
                f"Error al parsear el XML devuelto por SEGIP: {err}"
            ) from err

        # Verificar si hay SOAP Fault
        fault = root.find(".//{http://schemas.xmlsoap.org/soap/envelope/}Fault")
        if fault is not None:
            fault_code = fault.findtext("faultcode") or "Unknown"
            fault_string = fault.findtext("faultstring") or "Fault"
            raise SegipSoapFaultError(fault_code=fault_code, fault_string=fault_string)

        body = root.find(".//{http://schemas.xmlsoap.org/soap/envelope/}Body")
        if body is None:
            raise SegipEmptyResponseError("La respuesta no contiene el elemento SOAP Body")

        response_node = None
        for child in body:
            # Buscar nodo tipo <OperationNameResponse>
            tag_name = child.tag.split("}")[-1]
            if tag_name.lower().startswith(operation_name.lower()):
                response_node = child
                break

        if response_node is None:
            # Si no coincide exactamente, usar el primer elemento del Body
            if len(body) > 0:
                response_node = body[0]
            else:
                raise SegipEmptyResponseError("El SOAP Body se encuentra vacío")

        return self._element_to_dict(response_node)

    def _element_to_dict(self, element: ET.Element) -> dict[str, Any]:
        """Convierte recursivamente un elemento XML en un diccionario Python."""
        result: dict[str, Any] = {}
        if element.text and element.text.strip() and len(element) == 0:
            return {"value": element.text.strip()}

        for child in element:
            tag = child.tag.split("}")[-1]
            if len(child) > 0:
                child_data = self._element_to_dict(child)
            else:
                child_data = child.text.strip() if child.text else None

            if tag in result:
                if not isinstance(result[tag], list):
                    result[tag] = [result[tag]]
                result[tag].append(child_data)
            else:
                result[tag] = child_data

        return result

    def _extract_result_dict(self, raw_result: dict[str, Any], result_key: str) -> dict[str, Any]:
        """Extrae el diccionario específico del resultado dentro del envelope analizado."""
        if result_key in raw_result:
            val = raw_result[result_key]
            if isinstance(val, dict):
                return val
        # Si la respuesta ya es el diccionario desglosado
        return raw_result
