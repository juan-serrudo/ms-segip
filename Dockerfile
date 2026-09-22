# ==============================================================================
# Etapa 1: Builder
# ==============================================================================
FROM python:3.12-slim AS builder

WORKDIR /build

# Instalar dependencias del sistema requeridas para construcción si aplica
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivos de definición de dependencias
COPY pyproject.toml README.md ./

# Crear entorno virtual e instalar dependencias de producción
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir .

# ==============================================================================
# Etapa 2: Runtime
# ==============================================================================
FROM python:3.12-slim AS runner

WORKDIR /app

# Instalar curl para el HEALTHCHECK y limpiar caché
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Variables de entorno de ejecución en Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Crear usuario no privilegiado para ejecutar la aplicación
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

# Copiar el entorno virtual con paquetes instalados desde el builder
COPY --from=builder /opt/venv /opt/venv

# Copiar el código fuente de la aplicación
COPY --chown=appuser:appgroup app /app/app
COPY --chown=appuser:appgroup pyproject.toml README.md /app/

# Cambiar al usuario sin privilegios
USER appuser

# Exponer el puerto de la aplicación
EXPOSE 8000

# Healthcheck de Docker
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Comando de inicio
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
