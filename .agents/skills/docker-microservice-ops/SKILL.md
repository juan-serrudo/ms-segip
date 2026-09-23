---
name: docker-microservice-ops
description: >-
  Use this skill when configuring, building, running, or troubleshooting Docker containers, docker compose hot-reload, Kubernetes health probes, or intranet DNS for ms-segip.
---

# Docker & Microservice Operations — ms-segip Runbook

Este manual establece los procedimientos para el empaquetado, ejecución local en contenedores y despliegue del microservicio `ms-segip`.

---

## 1. Arquitectura de la Imagen Docker (Multi-Stage & Rootless)

El [Dockerfile](Dockerfile) utiliza una arquitectura multi-stage optimizada para producción y seguridad:

* **Etapa 1 (Builder)**: Utiliza `python:3.12-slim` con `build-essential` para compilar dependencias en `/opt/venv`.
* **Etapa 2 (Runner)**: Copia `/opt/venv`, descarta herramientas de compilación, instala `curl` para el healthcheck y corre bajo un usuario no privilegiado:
  - Usuario: `appuser` (UID 10001).
  - Grupo: `appgroup` (GID 10001).
* **Seguridad de Archivos**: Todo el código se copia con permisos restringidos (`--chown=appuser:appgroup`).

---

## 2. Desarrollo con Recarga Automática (Compose Dev)

Para trabajar localmente con recarga automática (*hot-reload*):

```bash
# Iniciar contenedor montando la carpeta ./app en vivo
docker compose -f compose.dev.yaml up --build

# Ver logs en tiempo real
docker compose -f compose.dev.yaml logs -f ms-segip

# Detener el contenedor
docker compose -f compose.dev.yaml down
```

### Configuración del montaje:
El archivo `compose.dev.yaml` vincula `./app:/app/app` y sobrescribe el comando de inicio para incluir `--reload`. Cada vez que se modifica un archivo en la máquina anfitriona, Uvicorn reinicia el proceso dentro del contenedor.

---

## 3. Resolución de DNS Intranet en Contenedores

Si el contenedor Docker no puede resolver el dominio `segip-api.fiscalia.gob.bo` durante pruebas con la red institucional:

1. Editar `compose.dev.yaml` (o `compose.yaml`).
2. Descomentar la directiva de DNS:
   ```yaml
   dns:
     - 192.168.20.2
   ```
3. Reiniciar el contenedor:
   ```bash
   docker compose -f compose.dev.yaml up -d
   ```

---

## 4. Diagnóstico de Sondas de Salud (Health Checks)

Comprobar que las sondas respondan adecuadamente desde el host:

```bash
# Liveness Probe (Sonda de vida del proceso FastAPI)
curl -i http://localhost:8000/health/live

# Readiness Probe (Sonda de disponibilidad frente al servicio externo)
curl -i http://localhost:8000/health/ready
```

Si el contenedor se reinicia inesperadamente en Docker o Kubernetes, verificar que la sonda configurada en el orquestador apunte a `/health/live` (que no contacta a SEGIP) y no a `/health/ready`, para evitar el antipatrón de reinicio en bucle (*Death Spiral*).

---

## 5. Permisos y Volúmenes de Usuario `appuser`

Al ejecutar el contenedor con volúmenes montados en Linux, si se presentan errores de permisos al crear archivos temporales o caché, recordar que el contenedor corre con UID `10001`:
```bash
# El entorno virtual ya cuenta con PYTHONDONTWRITEBYTECODE=1 para evitar problemas con __pycache__
docker run --rm -it -v $(pwd)/app:/app/app --user 10001:10001 ms-segip:latest uvicorn app.main:app --host 0.0.0.0 --port 8000
```
