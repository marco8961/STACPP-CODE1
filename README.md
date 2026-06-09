
# 🐳 STACPP - Production Ready Multi-AZ Architecture (AWS)

## 📖 Contexto Rápido: ¿Para qué sirve todo esto?
Este repositorio orquesta una infraestructura completa de ciberseguridad automatizada. Todo este ecosistema sirve para **capturar datos en tiempo real desde Telegram (mensajes y archivos), analizarlos en busca de malware o enlaces de phishing, y procesar su deteccion de manera automatizada**. 

Al usar Docker y AWS, el proyecto logra que los scripts de Python, la base de datos (RDS), la web de cara al público y las herramientas de automatización (n8n) trabajen de forma unificada, segura, y sin riesgo de perder información si el servidor se llega a reiniciar.

---

## 🎯 Propósito del Proyecto
**STACPP** es una plataforma automatizada de inteligencia diseñada para la **detección, análisis y mitigación de amenazas de phishing** distribuidas a través de canales de comunicación. 

El sistema intercepta flujos de información en tiempo real, procesa y analiza archivos adjuntos sospechosos mediante motores antivirus, y utiliza modelos avanzados de procesamiento de lenguaje natural (NLP / Transformers) para evaluar el riesgo de fraudes o enlaces maliciosos. Toda la actividad se consolida en paneles de monitoreo internos y flujos automatizados que permiten responder ante incidentes de manera inmediata.

---

## 🏗️ Mapa de la Arquitectura de Red

<img width="2142" height="1541" alt="Diagram" src="https://github.com/user-attachments/assets/ce83f2b4-0a85-4795-b6e1-82c214e5ce63" />

## 📂 Estructura del Repositorio Clean Code

```text
STACPP-CODE/
├── apps/                      # 🧠 Microservicios Backend (Aislados)
│   ├── 01-gestor-mensajes/    # Script Telethon (Python)
│   ├── 02-analizador-adjuntos/# Análisis de archivos
│   └── 03-detector-phishing/  # Modelo NLP Sentence-Transformers
├── infra/                     # 🛡️ Configuración de Infraestructura Fija
│   └── nginx/
│       └── conf/
│           └── default.conf   # Enrutador de reversa y balanceo interno
├── web/                       # 💻 Frontend del Proyecto
│   └── webs/stacpp/static/    # Archivos estáticos HTML/CSS servidos por Nginx
├── .env
└── docker-compose.yml         # Orquestador maestro compatible con AWS Multi-AZ

```

---

## 🚀 Requisitos Previos para el Despliegue

> 💡 **NOTA:** Se recomienda revisar detalladamente la sección de [📚 Documentación y Manuales a Seguir](#-documentación-y-manuales-a-seguir). En caso de realizar un despliegue en entorno local, asegúrese de modificar las variables y rutas según corresponda.

Antes de levantar el entorno en la instancia **AWS EC2**, asegúrate de contar con la siguiente infraestructura ya aprovisionada en tu consola de AWS.

1. **AWS RDS (PostgreSQL):** Instancia activa con una base de datos.
2. **AWS EFS (Elastic File System):** Sistema de archivos creado y accesible mediante *Mount Targets* en las mismas subredes que la EC2.
3. **AWS ALB (Application Load Balancer):** Configurado para redirigir el tráfico HTTP de los dominios hacia el puerto `80` de tu instancia EC2.
4. **DOMINIO:** Tener un dominio activo, de preferencia de proveedores de confianza.P ero que si tenga compatibilidad para que sea administrado por cloudflared.

---

## 🛠️ Guía de Despliegue Rápido (Paso a Paso)

### 1. Clonar el repositorio en la instancia EC2

```bash
git clone https://github.com/marco8961/STACPP-CODE1.git
cd STACPP-CODE1

```

### 2. Configurar Variables de Entorno

Crea un archivo `.env` en la raíz basado en las variables del proyecto:

```bash
touch .env
nano .env

```
Variables a copiar

```bash
# ==============================================================================
# 🔐 CONFIGURACIÓN DE TELEGRAM (01-gestor-mensajes)
# ==============================================================================
API_ID=32....
API_HASH=<api_hash>
BOT_TOKEN=<bot_token>
SECRET_TOKEN_N8N=<secret_token_n8n>

# ==============================================================================
# 💾 CONFIGURACIÓN DE BASE DE DATOS (AWS RDS POSTGRESQL)
# ==============================================================================
DB_HOST=<db_host>
DB_PORT=45...
DB_NAME=ejemplo1
DB_USER=ejemplo2
DB_PASSWORD=<db_password>

# ==============================================================================
# 🌐 CONFIGURACIÓN DE N8N (ORQUESTADOR)
# ==============================================================================
N8N_PROTOCOL=https
N8N_HOST=n8n.tu.dominio.com
WEBHOOK_URL=https://n8n.tu_dominio.com/
NODE_ENV=production

# ==============================================================================
# 📊 CONFIGURACIÓN DE GRAFANA
# ==============================================================================
GRAFANA_PASS=<grafana_password>

# ==============================================================================
# 🛡️ CONFIGURACIÓN DE PROXIES
# ==============================================================================
WEBSHARE_API_URL=https://tu_api

# ==============================================================================
# 🔐 CONFIGURACIÓN DE HOMARR (DASHBOARD SOC)
# ==============================================================================
HOMARR_AUTH_SECRET=
HOMARR_CRYPT_KEY=

# ==============================================================================
# 🌐 CONFIGURACIÓN GLOBAL DE DOMINIO
# ==============================================================================
DOMAIN_NAME=tu_dominio.com

# 📦 CONFIGURACIÓN DE ALMACENAMIENTO AWS EFS
EFS_VOLUME_ID=fs......
```

### 3. Ejecutar las Tablas Estructurales en la Base de Datos

Antes de encender los contenedores, ejecuta el archivo SQL de mi dump estructural utilizando tu cliente de confianza (**DBeaver** o **pgAdmin**) conectado al endpoint de **AWS RDS**.

### 4. Encender la Arquitectura con Docker Compose

```bash
docker compose up -d

```

---

## 💾 Gestión de Almacenamiento Compartido (AWS EFS)

El volumen de datos de `n8n` y la carpeta compartida con el microservicio `01-gestor-mensajes` están mapeados directamente a la raíz de tu **AWS EFS** usando el controlador nativo NFSv4 de Docker. Esto garantiza que si la instancia EC2 se reinicia o escala, los archivos `.png` y flujos **nunca se perderán**.

---

## 📚 Documentación y Manuales a Seguir

Para operar, mantener o expandir el sistema correctamente, se deben seguir los siguientes manuales de procedimientos internos:

* **📖 Manual de Credenciales y API Keys:** Documento guía para la obtención de tokens de Telegram (`API_ID`, `API_HASH`), configuración de accesos de AWS y rotación de llaves del panel de Homarr.
* **📖 Guía de Mantenimiento de Base de Datos (Postgres):** Pasos para ejecutar respaldos preventivos desde DBeaver, monitoreo de conexiones activas en AWS RDS y validación de tipos de datos masivos `INT8`.
* **📖 Manual de Flujos en N8N:** Estructura de los Webhooks activos, reglas para la generación de alertas en Discord/Slack y ruta del volumen compartido para la lectura de imágenes `.png`.
* **📖 Procedimiento de Escalabilidad de Microservicios:** Instrucciones para modificar las imágenes de Docker de los analizadores de Phishing (Transformers) y recarga limpia de Nginx mediante `docker compose exec nginx nginx -s reload`.

---

## 👥 Creadores y Desarrolladores

Este proyecto ha sido diseñado y desarrollado por:

* **Marco Pillaca** — *Core Architecture, DevOps & Backend Infrastructure* 
* **Paolo Pineda** — *Core Developer / Integrations*
