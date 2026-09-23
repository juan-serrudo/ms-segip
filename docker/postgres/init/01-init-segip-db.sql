-- ==============================================================================
-- Microservicio ms-segip: Script de Inicialización de Base de Datos
-- ==============================================================================
-- Este script se ejecuta automáticamente en el primer arranque del contenedor
-- PostgreSQL o puede ejecutarse manualmente en el servidor PostgreSQL de producción.
-- ==============================================================================

-- Habilitar extensión pgcrypto para generación de UUIDs y funciones criptográficas si se requieren
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ==============================================================================
-- 1. Tabla de Personas
-- Almacena los datos normalizados de identidad y lugar de nacimiento.
-- Los binarios pesados (fotografía) se almacenan en RustFS y aquí solo se referencia su ruta/clave S3.
-- ==============================================================================
CREATE TABLE IF NOT EXISTS personas (
    id BIGSERIAL PRIMARY KEY,
    numero_documento VARCHAR(20) NOT NULL,
    complemento VARCHAR(10) DEFAULT '',
    nombres VARCHAR(100) NOT NULL,
    primer_apellido VARCHAR(100) NOT NULL,
    segundo_apellido VARCHAR(100) DEFAULT '',
    fecha_nacimiento DATE NULL,
    sexo VARCHAR(20) NULL,
    estado_civil VARCHAR(30) NULL,
    domicilio TEXT NULL,
    profesion_ocupacion VARCHAR(150) NULL,

    -- Datos de nacimiento
    pais_nacimiento VARCHAR(100) DEFAULT 'BOLIVIA',
    departamento_nacimiento VARCHAR(100) NULL,
    provincia_nacimiento VARCHAR(100) NULL,
    localidad_nacimiento VARCHAR(150) NULL,

    -- Referencia a almacenamiento de objetos (RustFS / S3)
    -- Ejemplo: "personas/1146351/foto.jpg"
    fotografia_path VARCHAR(500) NULL,
    fotografia_content_type VARCHAR(50) DEFAULT 'image/jpeg',

    -- Trazabilidad y auditoría
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Índices para búsqueda rápida e integridad
CREATE UNIQUE INDEX IF NOT EXISTS idx_personas_doc_complemento
    ON personas (numero_documento, COALESCE(complemento, ''));

CREATE INDEX IF NOT EXISTS idx_personas_apellidos_nombres
    ON personas (primer_apellido, segundo_apellido, nombres);

COMMENT ON TABLE personas IS 'Registro consolidado de datos de personas consultadas en SEGIP';
COMMENT ON COLUMN personas.fotografia_path IS 'Ruta o clave del objeto almacenado en RustFS/S3';


-- ==============================================================================
-- 2. Tabla de Certificaciones SEGIP
-- Registra cada emisión de certificación PDF obtenida para una persona.
-- El documento PDF completo se almacena en RustFS y aquí se guarda su referencia y hash.
-- ==============================================================================
CREATE TABLE IF NOT EXISTS certificaciones_segip (
    id BIGSERIAL PRIMARY KEY,
    persona_id BIGINT NOT NULL REFERENCES personas(id) ON DELETE CASCADE,
    numero_emision VARCHAR(50) NOT NULL,
    codigo_segip VARCHAR(50) NULL,
    fecha_emision VARCHAR(50) NULL,
    motivo_consulta TEXT NULL,
    paginas INT NOT NULL DEFAULT 1,

    -- Referencia al archivo PDF en RustFS (S3)
    -- Ejemplo: "certificados/c4CAXTej-4774047.pdf"
    pdf_path VARCHAR(500) NOT NULL,
    pdf_tamanio_bytes BIGINT NULL,
    pdf_sha256 VARCHAR(64) NULL,

    -- Metadatos de auditoría
    usuario_consulta VARCHAR(100) NULL,
    ip_origen VARCHAR(45) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_certificaciones_persona_id
    ON certificaciones_segip (persona_id);

CREATE INDEX IF NOT EXISTS idx_certificaciones_numero_emision
    ON certificaciones_segip (numero_emision);

CREATE INDEX IF NOT EXISTS idx_certificaciones_codigo_segip
    ON certificaciones_segip (codigo_segip);

COMMENT ON TABLE certificaciones_segip IS 'Historial de certificaciones oficiales en PDF emitidas por SEGIP';
COMMENT ON COLUMN certificaciones_segip.pdf_path IS 'Ruta o clave del archivo PDF almacenado en RustFS/S3';
COMMENT ON COLUMN certificaciones_segip.pdf_sha256 IS 'Hash SHA-256 para verificación de integridad del PDF';


-- ==============================================================================
-- 3. Tabla de Bitácora / Auditoría de Consultas
-- Trazabilidad de cada solicitud procesada por el microservicio.
-- ==============================================================================
CREATE TABLE IF NOT EXISTS bitacora_consultas (
    id BIGSERIAL PRIMARY KEY,
    numero_documento VARCHAR(20) NOT NULL,
    complemento VARCHAR(10) DEFAULT '',
    tipo_origen VARCHAR(30) NOT NULL, -- 'SOAP_JSON', 'PDF_EXTRACT', 'PDF_BASE64', 'QR_VERIFY'
    exitoso BOOLEAN NOT NULL DEFAULT TRUE,
    codigo_respuesta VARCHAR(50) NULL,
    mensaje TEXT NULL,
    usuario_operador VARCHAR(100) NULL,
    duracion_ms INT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_bitacora_documento
    ON bitacora_consultas (numero_documento, created_at DESC);

COMMENT ON TABLE bitacora_consultas IS 'Registro de auditoría de todas las consultas realizadas al microservicio';
