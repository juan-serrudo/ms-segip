"""Mapeo y normalización de respuestas SOAP de SEGIP hacia esquemas Pydantic."""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from app.core.exceptions import SegipInvalidJsonException
from app.schemas.segip import (
    CertificacionResponseData,
    ContrastacionResponseData,
    DatosConsultaMetadata,
    DatosNacimiento,
    DatosPersona,
    PersonaNormalizada,
    QrVerificacionResponseData,
)
from app.utils.text import clean_string, normalize_date, normalize_gender, normalize_marital_status

logger = logging.getLogger(__name__)


def _find_field(data: dict[str, Any], *candidates: str) -> Any:
    """Busca insensible a mayúsculas y guiones bajos el primer campo coincidente en el diccionario."""
    normalized_keys = {k.lower().replace("_", ""): v for k, v in data.items()}
    for candidate in candidates:
        key_norm = candidate.lower().replace("_", "")
        if key_norm in normalized_keys:
            return normalized_keys[key_norm]
    return None


class SegipResponseMapper:
    """Transformador de respuestas crudas del servicio SOAP de SEGIP a modelos Pydantic."""

    @staticmethod
    def map_to_persona_normalizada(raw_result: dict[str, Any]) -> PersonaNormalizada:
        """Mapea una respuesta de ConsultaDatoPersonaEnJson / ConsultaDocumentoDatoPersonaEnJson."""
        # 1. Extraer metadatos de la consulta
        raw_code = raw_result.get("CodigoRespuesta")
        try:
            codigo_respuesta = int(raw_code) if raw_code is not None else None
        except (ValueError, TypeError):
            codigo_respuesta = None

        metadata = DatosConsultaMetadata(
            codigo_unico=clean_string(raw_result.get("CodigoUnico")),
            codigo_respuesta=codigo_respuesta,
            descripcion=clean_string(raw_result.get("DescripcionRespuesta")),
            fecha_consulta=datetime.now(UTC).isoformat(),
        )

        # 2. Parsear el JSON interno contenido en DatosPersonaEnFormatoJson
        json_str = raw_result.get("DatosPersonaEnFormatoJson")
        internal_data: dict[str, Any] = {}

        if json_str:
            if isinstance(json_str, dict):
                internal_data = json_str
            elif isinstance(json_str, str) and json_str.strip():
                try:
                    parsed = json.loads(json_str.strip())
                    if isinstance(parsed, dict):
                        internal_data = parsed
                    elif (
                        isinstance(parsed, list) and len(parsed) > 0 and isinstance(parsed[0], dict)
                    ):
                        internal_data = parsed[0]
                except Exception as err:
                    logger.warning("Fallo al parsear JSON interno de SEGIP: %s", err)
                    raise SegipInvalidJsonException(details=str(err)) from err

        # 3. Extraer y mapear datos personales
        foto_base64 = clean_string(raw_result.get("Fotografia")) or clean_string(
            _find_field(internal_data, "Fotografia", "Foto", "FotografiaBase64")
        )

        raw_fecha_nac = _find_field(
            internal_data, "FechaNacimiento", "Fecha_Nacimiento", "FecNacimiento", "FecNac"
        )

        persona = DatosPersona(
            numero_documento=clean_string(
                _find_field(
                    internal_data, "NumeroDocumento", "Numero_Documento", "NumeroDoc", "Doc"
                )
            ),
            complemento=clean_string(
                _find_field(internal_data, "Complemento", "ComplementoVisible", "Comp")
            ),
            nombres=clean_string(_find_field(internal_data, "Nombres", "Nombre")),
            primer_apellido=clean_string(
                _find_field(internal_data, "PrimerApellido", "Primer_Apellido", "Paterno")
            ),
            segundo_apellido=clean_string(
                _find_field(internal_data, "SegundoApellido", "Segundo_Apellido", "Materno")
            ),
            fecha_nacimiento=normalize_date(str(raw_fecha_nac)) if raw_fecha_nac else None,
            sexo=normalize_gender(str(_find_field(internal_data, "Genero", "Sexo"))),
            estado_civil=normalize_marital_status(
                str(_find_field(internal_data, "EstadoCivil", "Estado_Civil"))
            ),
            domicilio=clean_string(_find_field(internal_data, "Domicilio", "Direccion")),
            profesion_ocupacion=clean_string(
                _find_field(internal_data, "Profesion", "Ocupacion", "ProfesionOcupacion")
            ),
            fotografia_base64=foto_base64,
        )

        # 4. Extraer lugar de nacimiento
        nacimiento = DatosNacimiento(
            pais=clean_string(
                _find_field(internal_data, "LugarNacimientoPais", "PaisNacimiento", "Pais")
            ),
            departamento=clean_string(
                _find_field(
                    internal_data,
                    "LugarNacimientoDepartamento",
                    "DepartamentoNacimiento",
                    "Departamento",
                )
            ),
            provincia=clean_string(
                _find_field(
                    internal_data, "LugarNacimientoProvincia", "ProvinciaNacimiento", "Provincia"
                )
            ),
            localidad=clean_string(
                _find_field(
                    internal_data, "LugarNacimientoLocalidad", "LocalidadNacimiento", "Localidad"
                )
            ),
        )

        return PersonaNormalizada(persona=persona, nacimiento=nacimiento, consulta=metadata)

    @staticmethod
    def map_to_certificacion(raw_result: dict[str, Any]) -> CertificacionResponseData:
        """Mapea la respuesta de ConsultaDatoPersonaCertificacion a CertificacionResponseData."""
        raw_code = raw_result.get("CodigoRespuesta")
        try:
            codigo_respuesta = int(raw_code) if raw_code is not None else None
        except (ValueError, TypeError):
            codigo_respuesta = None

        es_valido = False
        val_es_valido = raw_result.get("EsValido")
        if isinstance(val_es_valido, bool):
            es_valido = val_es_valido
        elif isinstance(val_es_valido, str):
            es_valido = val_es_valido.lower() in ("true", "1", "si", "yes")

        return CertificacionResponseData(
            es_valido=es_valido,
            mensaje=clean_string(raw_result.get("Mensaje")),
            codigo_unico=clean_string(raw_result.get("CodigoUnico")),
            codigo_respuesta=codigo_respuesta,
            descripcion_respuesta=clean_string(raw_result.get("DescripcionRespuesta")),
            reporte_certificacion_base64=clean_string(raw_result.get("ReporteCertificacion")),
        )

    @staticmethod
    def map_to_qr_verificacion(raw_result: dict[str, Any]) -> QrVerificacionResponseData:
        """Mapea la respuesta de ConsultaVerificacionCertificacionCodigoQr."""
        raw_code = raw_result.get("CodigoRespuesta")
        try:
            codigo_respuesta = int(raw_code) if raw_code is not None else None
        except (ValueError, TypeError):
            codigo_respuesta = None

        es_valido = False
        val_es_valido = raw_result.get("EsValido")
        if isinstance(val_es_valido, bool):
            es_valido = val_es_valido
        elif isinstance(val_es_valido, str):
            es_valido = val_es_valido.lower() in ("true", "1", "si", "yes")

        return QrVerificacionResponseData(
            es_valido=es_valido,
            mensaje=clean_string(raw_result.get("Mensaje")),
            codigo_unico=clean_string(raw_result.get("CodigoUnico")),
            codigo_respuesta=codigo_respuesta,
            descripcion_respuesta=clean_string(raw_result.get("DescripcionRespuesta")),
            reporte_certificacion_base64=clean_string(raw_result.get("ReporteCertificacion")),
        )

    @staticmethod
    def map_to_contrastacion(raw_result: dict[str, Any]) -> ContrastacionResponseData:
        """Mapea la respuesta de ConsultaDatoPersonaContrastacion."""
        raw_code = raw_result.get("CodigoRespuesta")
        try:
            codigo_respuesta = int(raw_code) if raw_code is not None else None
        except (ValueError, TypeError):
            codigo_respuesta = None

        es_valido = False
        val_es_valido = raw_result.get("EsValido")
        if isinstance(val_es_valido, bool):
            es_valido = val_es_valido
        elif isinstance(val_es_valido, str):
            es_valido = val_es_valido.lower() in ("true", "1", "si", "yes")

        contrastacion_json = raw_result.get("ContrastacionEnFormatoJson")
        if isinstance(contrastacion_json, dict):
            contrastacion_json = json.dumps(contrastacion_json)

        return ContrastacionResponseData(
            es_valido=es_valido,
            mensaje=clean_string(raw_result.get("Mensaje")),
            codigo_unico=clean_string(raw_result.get("CodigoUnico")),
            codigo_respuesta=codigo_respuesta,
            descripcion_respuesta=clean_string(raw_result.get("DescripcionRespuesta")),
            contrastacion_json=clean_string(contrastacion_json),
        )
