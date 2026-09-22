"""Esquemas de solicitud y respuesta para operaciones con SEGIP."""

from pydantic import BaseModel, Field

# ==============================================================================
# Modelos Normalizados de Datos de Persona
# ==============================================================================


class DatosPersona(BaseModel):
    """Información personal normalizada de la persona consultada."""

    numero_documento: str | None = Field(
        default=None, description="Número de documento de identidad"
    )
    complemento: str | None = Field(
        default=None, description="Complemento alfanumérico del documento"
    )
    nombres: str | None = Field(default=None, description="Nombres de pila")
    primer_apellido: str | None = Field(default=None, description="Primer apellido")
    segundo_apellido: str | None = Field(default=None, description="Segundo apellido")
    fecha_nacimiento: str | None = Field(
        default=None, description="Fecha de nacimiento en formato YYYY-MM-DD"
    )
    sexo: str | None = Field(default=None, description="Sexo o género registrado")
    estado_civil: str | None = Field(default=None, description="Estado civil")
    domicilio: str | None = Field(default=None, description="Domicilio o dirección registrada")
    profesion_ocupacion: str | None = Field(default=None, description="Profesión u ocupación")
    fotografia_base64: str | None = Field(
        default=None, description="Fotografía en Base64 si fue solicitada/devuelta"
    )


class DatosNacimiento(BaseModel):
    """Información de lugar de nacimiento."""

    pais: str | None = Field(default=None, description="País de nacimiento")
    departamento: str | None = Field(default=None, description="Departamento de nacimiento")
    provincia: str | None = Field(default=None, description="Provincia de nacimiento")
    localidad: str | None = Field(default=None, description="Localidad de nacimiento")


class DatosConsultaMetadata(BaseModel):
    """Metadatos técnicos devueltos por la consulta SEGIP."""

    codigo_unico: str | None = Field(
        default=None, description="Código único de la transacción en SEGIP"
    )
    codigo_respuesta: int | None = Field(
        default=None, description="Código numérico de respuesta de SEGIP"
    )
    descripcion: str | None = Field(
        default=None, description="Descripción textual del resultado devuelta por SEGIP"
    )
    fecha_consulta: str | None = Field(
        default=None, description="Marca de tiempo en la que se realizó la consulta"
    )


class PersonaNormalizada(BaseModel):
    """Estructura normalizada unificada para respuestas de persona."""

    persona: DatosPersona = Field(default_factory=DatosPersona)
    nacimiento: DatosNacimiento = Field(default_factory=DatosNacimiento)
    consulta: DatosConsultaMetadata = Field(default_factory=DatosConsultaMetadata)


# ==============================================================================
# Modelos de Solicitud (Requests)
# ==============================================================================


class PersonaConsultaRequest(BaseModel):
    """Parámetros para consultar datos de una persona en SEGIP."""

    numero_documento: str = Field(
        ..., description="Número de documento de identidad (CI)", min_length=4, max_length=15
    )
    complemento: str | None = Field(
        default="", description="Complemento de cédula si existe (ej. '1B')"
    )
    nombre: str | None = Field(default="", description="Nombres de la persona")
    primer_apellido: str | None = Field(default="", description="Primer apellido")
    segundo_apellido: str | None = Field(default="", description="Segundo apellido")
    fecha_nacimiento: str | None = Field(
        default="",
        description="Fecha de nacimiento en formato DD/MM/YYYY o YYYY-MM-DD",
    )
    fecha_expiracion: str | None = Field(
        default=None,
        description="Fecha de expiración de cédula si se realiza consulta documental",
    )
    numero_autorizacion: str | None = Field(
        default="",
        description="Número de autorización institucional opcional",
    )
    clave_acceso_usuario_final: str | None = Field(
        default="",
        description="Identificador o clave de usuario operador final para auditoría",
    )


class CertificacionConsultaRequest(BaseModel):
    """Parámetros para solicitar el PDF de certificación de identidad a SEGIP."""

    numero_documento: str = Field(
        ..., description="Número de documento de identidad (CI)", min_length=4, max_length=15
    )
    complemento: str | None = Field(default="", description="Complemento de cédula si existe")
    nombre: str | None = Field(default="", description="Nombres de la persona")
    primer_apellido: str | None = Field(default="", description="Primer apellido")
    segundo_apellido: str | None = Field(default="", description="Segundo apellido")
    fecha_nacimiento: str | None = Field(default="", description="Fecha de nacimiento")
    numero_autorizacion: str | None = Field(
        default="", description="Número de autorización institucional"
    )
    clave_acceso_usuario_final: str | None = Field(
        default="", description="Clave de usuario operador"
    )


class CertificacionQrRequest(BaseModel):
    """Parámetros para verificar una certificación mediante código QR."""

    codigo_qr: str = Field(
        ..., description="Cadena de texto leída desde el código QR de la certificación"
    )
    numero_autorizacion: str | None = Field(
        default="", description="Número de autorización institucional"
    )
    clave_acceso_usuario_final: str | None = Field(
        default="", description="Clave de usuario operador"
    )


class ContrastacionRequest(BaseModel):
    """Parámetros para contrastar campos de una persona contra SEGIP."""

    lista_campos: str = Field(
        ...,
        description="Campos a contrastar (cadena o JSON según especificación SEGIP)",
    )
    tipo_persona: int = Field(default=1, description="Tipo de persona (1=Natural, etc.)")
    numero_autorizacion: str | None = Field(
        default="", description="Número de autorización institucional"
    )
    clave_acceso_usuario_final: str | None = Field(
        default="", description="Clave de usuario operador"
    )


# ==============================================================================
# Modelos de Respuestas Específicas
# ==============================================================================


class CertificacionResponseData(BaseModel):
    """Respuesta al solicitar una certificación PDF."""

    es_valido: bool = Field(description="Indica si la certificación es válida en SEGIP")
    mensaje: str | None = Field(default=None, description="Mensaje devuelto por SEGIP")
    codigo_unico: str | None = Field(default=None, description="Código único de la transacción")
    codigo_respuesta: int | None = Field(default=None, description="Código de respuesta")
    descripcion_respuesta: str | None = Field(
        default=None, description="Descripción técnica de respuesta"
    )
    reporte_certificacion_base64: str | None = Field(
        default=None,
        description="Documento PDF de certificación codificado en Base64",
    )


class QrVerificacionResponseData(BaseModel):
    """Respuesta a la verificación de código QR."""

    es_valido: bool = Field(description="Indica si el certificado QR es válido y auténtico")
    mensaje: str | None = Field(default=None, description="Mensaje devuelto por SEGIP")
    codigo_unico: str | None = Field(default=None, description="Código único emitido")
    codigo_respuesta: int | None = Field(default=None, description="Código de respuesta")
    descripcion_respuesta: str | None = Field(default=None, description="Descripción de respuesta")
    reporte_certificacion_base64: str | None = Field(
        default=None,
        description="PDF de certificación respaldatorio devuelto por SEGIP",
    )


class ContrastacionResponseData(BaseModel):
    """Respuesta a la operación de contrastación."""

    es_valido: bool = Field(description="Indica si el contraste fue ejecutado")
    mensaje: str | None = Field(default=None, description="Mensaje devuelto por SEGIP")
    codigo_unico: str | None = Field(default=None, description="Código único de consulta")
    codigo_respuesta: int | None = Field(default=None, description="Código de respuesta")
    descripcion_respuesta: str | None = Field(default=None, description="Descripción de respuesta")
    contrastacion_json: str | None = Field(
        default=None, description="Detalle del contraste en formato JSON"
    )


class VersionResponseData(BaseModel):
    """Respuesta de versión del sistema SEGIP."""

    version: str = Field(description="Versión del sistema informada por el servicio SOAP de SEGIP")
    servicio_url: str = Field(description="URL institucional configurada hacia la que se conecta")
