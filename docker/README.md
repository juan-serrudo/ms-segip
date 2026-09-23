# Infraestructura de Desarrollo: PostgreSQL & RustFS

Este directorio contiene la configuración y scripts para levantar el entorno de persistencia y almacenamiento de objetos para `ms-segip` en modo local/desarrollo.

---

## 1. Servicios Incluidos

| Servicio | Tecnología | Puerto Host | Descripción | Credenciales por Defecto |
| :--- | :--- | :--- | :--- | :--- |
| **Base de Datos** | PostgreSQL 16 (Alpine) | `5432` | Persistencia relacional de identidades, certificados y bitácora | Usuario: `segip_user`<br>Clave: `segip_secret_2026`<br>BD: `segip_db` |
| **API Object Storage** | RustFS | `9000` | Almacenamiento compatible S3 para PDFs y fotografías | Access Key: `rustfsadmin`<br>Secret Key: `rustfssecret2026` |
| **Consola Web RustFS** | RustFS Web UI | `9001` | Interfaz gráfica web para visualizar y gestionar buckets | Mismas credenciales de RustFS |

---

## 2. Comandos de Uso Rápido

### Iniciar la infraestructura:
```bash
docker compose -f docker/compose.infra.yaml up -d
```

### Comprobar el estado y salud de los contenedores:
```bash
docker compose -f docker/compose.infra.yaml ps
```

### Ver logs en tiempo real:
```bash
docker compose -f docker/compose.infra.yaml logs -f
```

### Detener la infraestructura:
```bash
docker compose -f docker/compose.infra.yaml down
```

> [!NOTE]
> Los datos de PostgreSQL y RustFS persisten en volúmenes nombrados de Docker (`ms_segip_postgres_data` y `ms_segip_rustfs_data`). Si deseas reiniciar la base de datos a cero y volver a ejecutar el script `01-init-segip-db.sql`, utiliza `docker compose -f docker/compose.infra.yaml down -v`.

---

## 3. Acceso a la Consola Web de RustFS

Una vez iniciado el contenedor, puedes acceder desde tu navegador a:
* **URL:** [http://localhost:9001](http://localhost:9001)
* **Access Key:** `rustfsadmin`
* **Secret Key:** `rustfssecret2026`

Desde la consola puedes explorar el bucket configurado (por ejemplo `segip-archivos`) y revisar los PDFs y fotos almacenados.

---

## 4. Conexión desde el Microservicio FastAPI

En desarrollo, puedes configurar en tu archivo `.env`:

```env
# PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_USER=segip_user
DB_PASSWORD=segip_secret_2026
DB_NAME=segip_db
DATABASE_URL=postgresql+asyncpg://segip_user:segip_secret_2026@localhost:5432/segip_db

# RustFS (S3)
RUSTFS_ENDPOINT_URL=http://localhost:9000
RUSTFS_ACCESS_KEY=rustfsadmin
RUSTFS_SECRET_KEY=rustfssecret2026
RUSTFS_BUCKET_NAME=segip-archivos
RUSTFS_REGION=us-east-1
RUSTFS_USE_SSL=false
```

---

## 5. Transición a Producción (Máquinas Virtuales Dedicadas)

En el entorno de producción institucional:
* **PostgreSQL** estará instalado directamente en una máquina virtual dedicada (ej. RHEL / Debian / Ubuntu Server bajo Systemd).
* **RustFS** estará instalado y ejecutándose como servicio binario/systemd en otra máquina virtual dedicada.

Gracias a la parametrización de variables de entorno del microservicio, **no se requiere ningún cambio de código**: únicamente se actualizan `DB_HOST`, `RUSTFS_ENDPOINT_URL` y sus credenciales en el archivo de variables del servidor productivo.
