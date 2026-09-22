"""Respuestas SOAP simuladas para pruebas unitarias de SEGIP."""

import json

# ==============================================================================
# ObtieneVersionSistema
# ==============================================================================

MOCK_VERSION_RESPONSE_XML = """<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
    <s:Body>
        <ObtieneVersionSistemaResponse xmlns="http://tempuri.org/">
            <ObtieneVersionSistemaResult>8.0.0.0</ObtieneVersionSistemaResult>
        </ObtieneVersionSistemaResponse>
    </s:Body>
</s:Envelope>"""


# ==============================================================================
# ConsultaDatoPersonaEnJson
# ==============================================================================

MOCK_PERSONA_JSON = {
    "NumeroDocumento": "4892341",
    "Complemento": "1A",
    "Nombres": "CARLOS ANDRES",
    "PrimerApellido": "MAMANI",
    "SegundoApellido": "QUISPE",
    "FechaNacimiento": "15/05/1990",
    "LugarNacimientoPais": "BOLIVIA",
    "LugarNacimientoDepartamento": "LA PAZ",
    "LugarNacimientoProvincia": "MURILLO",
    "LugarNacimientoLocalidad": "NUESTRA SEÑORA DE LA PAZ",
    "Genero": "MASCULINO",
    "EstadoCivil": "SOLTERO",
    "Profesion": "LICENCIADO EN DERECHO",
    "Domicilio": "AV. MARISCAL SANTA CRUZ #123",
}

# Imagen PNG mínima válida en Base64 (1x1 transparente o pequeña imagen)
MOCK_FOTO_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

MOCK_PERSONA_RESPONSE_XML = f"""<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
    <s:Body>
        <ConsultaDatoPersonaEnJsonResponse xmlns="http://tempuri.org/">
            <ConsultaDatoPersonaEnJsonResult xmlns:a="http://schemas.datacontract.org/2004/07/Segip.Servicio.Entidades" xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
                <CodigoRespuesta>1</CodigoRespuesta>
                <CodigoUnico>UNIQ-123456789</CodigoUnico>
                <DescripcionRespuesta>CONSULTA EXITOSA</DescripcionRespuesta>
                <EsValido>true</EsValido>
                <Mensaje>DATOS ENCONTRADOS</Mensaje>
                <TipoMensaje>INFO</TipoMensaje>
                <DatosPersonaEnFormatoJson><![CDATA[{json.dumps(MOCK_PERSONA_JSON)}]]></DatosPersonaEnFormatoJson>
                <Fotografia>{MOCK_FOTO_BASE64}</Fotografia>
            </ConsultaDatoPersonaEnJsonResult>
        </ConsultaDatoPersonaEnJsonResponse>
    </s:Body>
</s:Envelope>"""


# ==============================================================================
# ConsultaDatoPersonaCertificacion
# ==============================================================================

MOCK_PDF_BASE64 = "JVBERi0xLjQKJcTl8uXrp/Og0MTGCjQgMCBvYmoKPDwgL0xlbmd0aCA1IDAgUiAvRmlsdGVyIC9GbGF0ZURlY29kZSA+PgpzdHJlYW0KeAEr5HIK0DMyUDCy0DM0NDUwMLTQBQAcxgPAZW5kc3RyZWFtCmVuZG9iago1IDAgb2JqCjI4CmVuZG9iag=="

MOCK_CERTIFICACION_RESPONSE_XML = f"""<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
    <s:Body>
        <ConsultaDatoPersonaCertificacionResponse xmlns="http://tempuri.org/">
            <ConsultaDatoPersonaCertificacionResult xmlns:a="http://schemas.datacontract.org/2004/07/Segip.Servicio.Entidades" xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
                <CodigoRespuesta>1</CodigoRespuesta>
                <CodigoUnico>CERT-987654321</CodigoUnico>
                <DescripcionRespuesta>REPORTE GENERADO</DescripcionRespuesta>
                <EsValido>true</EsValido>
                <Mensaje>CERTIFICACION EMITIDA CON EXITO</Mensaje>
                <TipoMensaje>INFO</TipoMensaje>
                <ReporteCertificacion>{MOCK_PDF_BASE64}</ReporteCertificacion>
            </ConsultaDatoPersonaCertificacionResult>
        </ConsultaDatoPersonaCertificacionResponse>
    </s:Body>
</s:Envelope>"""


# ==============================================================================
# ConsultaVerificacionCertificacionCodigoQr
# ==============================================================================

MOCK_QR_RESPONSE_XML = f"""<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
    <s:Body>
        <ConsultaVerificacionCertificacionCodigoQrResponse xmlns="http://tempuri.org/">
            <ConsultaVerificacionCertificacionCodigoQrResult xmlns:a="http://schemas.datacontract.org/2004/07/Segip.Servicio.Entidades" xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
                <CodigoRespuesta>1</CodigoRespuesta>
                <CodigoUnico>QR-VERIF-112233</CodigoUnico>
                <DescripcionRespuesta>CERTIFICADO VALIDO Y AUTENTICO</DescripcionRespuesta>
                <EsValido>true</EsValido>
                <Mensaje>CERTIFICACION QR VERIFICADA</Mensaje>
                <TipoMensaje>INFO</TipoMensaje>
                <ReporteCertificacion>{MOCK_PDF_BASE64}</ReporteCertificacion>
            </ConsultaVerificacionCertificacionCodigoQrResult>
        </ConsultaVerificacionCertificacionCodigoQrResponse>
    </s:Body>
</s:Envelope>"""


# ==============================================================================
# ConsultaDatoPersonaContrastacion
# ==============================================================================

MOCK_CONTRASTACION_JSON = {
    "NumeroDocumento": "COINCIDE",
    "Nombres": "COINCIDE",
    "PrimerApellido": "COINCIDE",
}

MOCK_CONTRASTACION_RESPONSE_XML = f"""<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
    <s:Body>
        <ConsultaDatoPersonaContrastacionResponse xmlns="http://tempuri.org/">
            <ConsultaDatoPersonaContrastacionResult xmlns:a="http://schemas.datacontract.org/2004/07/Segip.Servicio.Entidades" xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
                <CodigoRespuesta>1</CodigoRespuesta>
                <CodigoUnico>CONTRAST-445566</CodigoUnico>
                <DescripcionRespuesta>CONTRASTACION FINALIZADA</DescripcionRespuesta>
                <EsValido>true</EsValido>
                <Mensaje>DATOS CONTRASTADOS</Mensaje>
                <TipoMensaje>INFO</TipoMensaje>
                <ContrastacionEnFormatoJson><![CDATA[{json.dumps(MOCK_CONTRASTACION_JSON)}]]></ContrastacionEnFormatoJson>
            </ConsultaDatoPersonaContrastacionResult>
        </ConsultaDatoPersonaContrastacionResponse>
    </s:Body>
</s:Envelope>"""


# ==============================================================================
# Errores y SOAP Faults
# ==============================================================================

MOCK_SOAP_FAULT_XML = """<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
    <s:Body>
        <s:Fault>
            <faultcode xmlns:a="http://schemas.microsoft.com/net/2005/12/windowscommunicationfoundation/dispatcher">a:InternalServiceFault</faultcode>
            <faultstring xml:lang="es-BO">Error interno del servidor en el servicio SEGIP</faultstring>
            <detail>
                <ExceptionDetail xmlns="http://schemas.datacontract.org/2004/07/System.ServiceModel" xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
                    <HelpLink i:nil="true"/>
                    <InnerException i:nil="true"/>
                    <Message>Error al conectar a la base de datos de SEGIP</Message>
                    <StackTrace>at Segip.Servicio.Metodos.Procesar()</StackTrace>
                    <Type>System.Data.SqlClient.SqlException</Type>
                </ExceptionDetail>
            </detail>
        </s:Fault>
    </s:Body>
</s:Envelope>"""

MOCK_NO_RESULTS_XML = """<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
    <s:Body>
        <ConsultaDatoPersonaEnJsonResponse xmlns="http://tempuri.org/">
            <ConsultaDatoPersonaEnJsonResult>
                <CodigoRespuesta>0</CodigoRespuesta>
                <CodigoUnico i:nil="true" xmlns:i="http://www.w3.org/2001/XMLSchema-instance"/>
                <DescripcionRespuesta>NO SE ENCONTRARON REGISTROS</DescripcionRespuesta>
                <EsValido>false</EsValido>
                <Mensaje>LA PERSONA NO EXISTE EN LA BASE DE DATOS</Mensaje>
                <TipoMensaje>ERROR</TipoMensaje>
                <DatosPersonaEnFormatoJson i:nil="true" xmlns:i="http://www.w3.org/2001/XMLSchema-instance"/>
                <Fotografia i:nil="true" xmlns:i="http://www.w3.org/2001/XMLSchema-instance"/>
            </ConsultaDatoPersonaEnJsonResult>
        </ConsultaDatoPersonaEnJsonResponse>
    </s:Body>
</s:Envelope>"""

MOCK_INVALID_JSON_RESPONSE_XML = """<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
    <s:Body>
        <ConsultaDatoPersonaEnJsonResponse xmlns="http://tempuri.org/">
            <ConsultaDatoPersonaEnJsonResult>
                <CodigoRespuesta>1</CodigoRespuesta>
                <CodigoUnico>UNIQ-ERR-JSON</CodigoUnico>
                <DescripcionRespuesta>OK</DescripcionRespuesta>
                <EsValido>true</EsValido>
                <Mensaje>DATOS</Mensaje>
                <TipoMensaje>INFO</TipoMensaje>
                <DatosPersonaEnFormatoJson>{ESTO NO ES UN JSON VALIDO</DatosPersonaEnFormatoJson>
            </ConsultaDatoPersonaEnJsonResult>
        </ConsultaDatoPersonaEnJsonResponse>
    </s:Body>
</s:Envelope>"""
