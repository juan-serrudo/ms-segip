"""Repositorio de persistencia para personas, certificaciones y bitácora (UOIT 1.0)."""

import logging
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PersonaDuplicadaException
from app.models.bitacora import BitacoraConsultaModel
from app.models.certificacion import CertificacionModel
from app.models.persona import PersonaModel
from app.schemas.pdf import DatosCertificadoPdf
from app.schemas.segip import DatosNacimiento, DatosPersona

logger = logging.getLogger(__name__)


def _parse_date(date_str: str | None) -> date | None:
    """Parsea cadenas de fecha en formatos comunes ISO YYYY-MM-DD o DD/MM/YYYY a date."""
    if not date_str:
        return None
    val = date_str.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    return None


class PersonaRepository:
    """Acceso a datos y operaciones de persistencia para la entidad Persona y sus Certificaciones."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_documento(
        self, numero_documento: str, complemento: str | None = None
    ) -> PersonaModel | None:
        """Busca una persona por su número de cédula y complemento."""
        comp = (complemento or "").strip().upper()
        doc = numero_documento.strip()

        stmt = select(PersonaModel).where(
            PersonaModel.numero_documento == doc,
            PersonaModel.complemento == comp,
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def buscar_con_desambiguacion(
        self,
        numero_documento: str,
        complemento: str | None = None,
        fecha_nacimiento: str | None = None,
    ) -> PersonaModel | None:
        """Busca una persona aplicando resolución de homónimos / duplicados por documento."""
        doc = numero_documento.strip()
        comp = (complemento or "").strip().upper()
        fecha_nac = _parse_date(fecha_nacimiento) if fecha_nacimiento else None

        if comp:
            stmt = select(PersonaModel).where(
                PersonaModel.numero_documento == doc,
                PersonaModel.complemento == comp,
            )
            if fecha_nac is not None:
                stmt = stmt.where(PersonaModel.fecha_nacimiento == fecha_nac)
            result = await self.session.execute(stmt)
            return result.scalars().first()

        stmt_all = select(PersonaModel).where(PersonaModel.numero_documento == doc)
        result_all = await self.session.execute(stmt_all)
        personas = list(result_all.scalars().all())

        if not personas:
            return None

        if len(personas) == 1:
            return personas[0]

        if fecha_nac is not None:
            filtrados = [p for p in personas if p.fecha_nacimiento == fecha_nac]
            if len(filtrados) == 1:
                return filtrados[0]

        complist = [f"'{p.complemento}'" if p.complemento else "''" for p in personas]
        raise PersonaDuplicadaException(
            message=(
                f"Se encontraron múltiples registros ({len(personas)}) para la cédula {doc} "
                f"con complementos [{', '.join(complist)}]. Debe proporcionar el complemento "
                "o fecha de nacimiento para desambiguar."
            ),
            details={
                "numero_documento": doc,
                "total_coincidencias": len(personas),
                "requiere_complemento": True,
            },
        )

    async def get_ultima_certificacion(self, persona_id: int) -> CertificacionModel | None:
        """Obtiene la certificación más reciente registrada para una persona."""
        stmt = (
            select(CertificacionModel)
            .where(CertificacionModel.persona_id == persona_id)
            .order_by(CertificacionModel.created_at.desc(), CertificacionModel.id.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def contar_certificaciones(self, persona_id: int) -> int:
        """Retorna el conteo total de certificados emitidos para la persona."""
        stmt = select(func.count(CertificacionModel.id)).where(
            CertificacionModel.persona_id == persona_id
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def upsert_persona(
        self,
        data: DatosPersona,
        nacimiento: DatosNacimiento | None = None,
        fotografia_path: str | None = None,
    ) -> PersonaModel:
        """Crea o actualiza los datos consolidados de una persona en la base de datos."""
        numero_documento = (data.numero_documento or "").strip()
        complemento = (data.complemento or "").strip().upper()

        persona = await self.get_by_documento(numero_documento, complemento)
        fecha_nac = _parse_date(data.fecha_nacimiento)

        if persona is None:
            logger.debug(
                "Registrando nueva persona en BD: doc=%s, comp=%s",
                numero_documento,
                complemento,
            )
            persona = PersonaModel(
                numero_documento=numero_documento,
                complemento=complemento,
                nombres=(data.nombres or "").strip().upper(),
                primer_apellido=(data.primer_apellido or "").strip().upper(),
                segundo_apellido=(data.segundo_apellido or "").strip().upper(),
                fecha_nacimiento=fecha_nac,
                sexo=(data.sexo or "").strip().upper() if data.sexo else None,
                estado_civil=(data.estado_civil or "").strip().upper()
                if data.estado_civil
                else None,
                domicilio=(data.domicilio or "").strip().upper() if data.domicilio else None,
                profesion_ocupacion=(data.profesion_ocupacion or "").strip().upper()
                if data.profesion_ocupacion
                else None,
                pais_nacimiento=(nacimiento.pais or "BOLIVIA").strip().upper()
                if nacimiento and nacimiento.pais
                else "BOLIVIA",
                departamento_nacimiento=(nacimiento.departamento or "").strip().upper()
                if nacimiento and nacimiento.departamento
                else None,
                provincia_nacimiento=(nacimiento.provincia or "").strip().upper()
                if nacimiento and nacimiento.provincia
                else None,
                localidad_nacimiento=(nacimiento.localidad or "").strip().upper()
                if nacimiento and nacimiento.localidad
                else None,
                fotografia_path=fotografia_path,
            )
            self.session.add(persona)
        else:
            logger.debug(
                "Actualizando datos de persona existente en BD: id=%d, doc=%s",
                persona.id,
                numero_documento,
            )
            persona.nombres = (data.nombres or persona.nombres).strip().upper()
            persona.primer_apellido = (
                (data.primer_apellido or persona.primer_apellido).strip().upper()
            )
            persona.segundo_apellido = (
                (data.segundo_apellido or persona.segundo_apellido).strip().upper()
            )
            if fecha_nac is not None:
                persona.fecha_nacimiento = fecha_nac
            if data.sexo:
                persona.sexo = data.sexo.strip().upper()
            if data.estado_civil:
                persona.estado_civil = data.estado_civil.strip().upper()
            if data.domicilio:
                persona.domicilio = data.domicilio.strip().upper()
            if data.profesion_ocupacion:
                persona.profesion_ocupacion = data.profesion_ocupacion.strip().upper()

            if nacimiento:
                if nacimiento.pais:
                    persona.pais_nacimiento = nacimiento.pais.strip().upper()
                if nacimiento.departamento:
                    persona.departamento_nacimiento = nacimiento.departamento.strip().upper()
                if nacimiento.provincia:
                    persona.provincia_nacimiento = nacimiento.provincia.strip().upper()
                if nacimiento.localidad:
                    persona.localidad_nacimiento = nacimiento.localidad.strip().upper()

            if fotografia_path:
                persona.fotografia_path = fotografia_path

        await self.session.flush()
        return persona

    async def registrar_certificacion(
        self,
        persona_id: int,
        certificado: DatosCertificadoPdf,
        pdf_path: str,
        pdf_tamanio_bytes: int | None = None,
        pdf_sha256: str | None = None,
        usuario_consulta: str | None = None,
        ip_origen: str | None = None,
    ) -> CertificacionModel:
        """Registra un nuevo certificado emitido para la persona referenciando el objeto en RustFS."""
        cert = CertificacionModel(
            persona_id=persona_id,
            numero_emision=(certificado.numero_emision or "S/N").strip(),
            codigo_segip=certificado.codigo_segip.strip() if certificado.codigo_segip else None,
            fecha_emision=certificado.fecha_emision.strip() if certificado.fecha_emision else None,
            motivo_consulta=certificado.motivo_consulta.strip()
            if certificado.motivo_consulta
            else None,
            paginas=certificado.paginas if certificado.paginas > 0 else 1,
            pdf_path=pdf_path,
            pdf_tamanio_bytes=pdf_tamanio_bytes,
            pdf_sha256=pdf_sha256,
            usuario_consulta=usuario_consulta,
            ip_origen=ip_origen,
        )
        self.session.add(cert)
        await self.session.flush()
        return cert

    async def registrar_bitacora(
        self,
        numero_documento: str,
        complemento: str | None,
        tipo_origen: str,
        exitoso: bool = True,
        codigo_respuesta: str | None = None,
        mensaje: str | None = None,
        usuario_operador: str | None = None,
        duracion_ms: int | None = None,
    ) -> BitacoraConsultaModel:
        """Registra una entrada de auditoría para la consulta efectuada."""
        bitacora = BitacoraConsultaModel(
            numero_documento=numero_documento.strip(),
            complemento=(complemento or "").strip().upper(),
            tipo_origen=tipo_origen,
            exitoso=exitoso,
            codigo_respuesta=codigo_respuesta,
            mensaje=mensaje,
            usuario_operador=usuario_operador,
            duracion_ms=duracion_ms,
        )
        self.session.add(bitacora)
        await self.session.flush()
        return bitacora

    async def get_historial_certificaciones(self, persona_id: int) -> list[CertificacionModel]:
        """Obtiene el listado cronológico de certificaciones registradas para una persona."""
        stmt = (
            select(CertificacionModel)
            .where(CertificacionModel.persona_id == persona_id)
            .order_by(CertificacionModel.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
