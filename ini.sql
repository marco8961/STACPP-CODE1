-- ============================================================================
-- 📊 ESTRUCTURA DE BASE DE DATOS PARA PRODUCCIÓN (APPS_PROD)
-- Proyecto: Plataforma de Detección de Spearphishing y Malware
-- Optimizado para: AWS RDS PostgreSQL (Multi-AZ) + AWS EFS
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. CLIENTES
-- ----------------------------------------------------------------------------
CREATE TABLE public.clientes (
    cliente_id BIGSERIAL NOT NULL,
    nombre VARCHAR(100) NULL,
    contacto VARCHAR(100) NULL,
    creado TIMESTAMPTZ DEFAULT NOW() NULL, 
    activo BOOL DEFAULT TRUE NULL,
    CONSTRAINT clientes_pkey PRIMARY KEY (cliente_id),
    CONSTRAINT contacto_unico UNIQUE (contacto)
);
CREATE UNIQUE INDEX idx_clientes_contacto ON public.clientes USING btree (contacto);

-- ----------------------------------------------------------------------------
-- 2. USUARIOS TELEGRAM
-- ----------------------------------------------------------------------------
CREATE TABLE public.usuarios_telegram (
    telegram_id INT8 NOT NULL, -- Soporta los IDs nativos largos de Telegram
    telefono VARCHAR(20) NOT NULL,
    nombre VARCHAR(100) NULL,
    session_string TEXT NOT NULL,
    fecha_registro TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NULL,
    email VARCHAR(255) NULL,
    CONSTRAINT usuarios_telegram_pkey PRIMARY KEY (telegram_id)
);

-- ----------------------------------------------------------------------------
-- 3. MENSAJES (Eje central de la data)
-- ----------------------------------------------------------------------------
CREATE TABLE public.mensajes (
    mensaje_id BIGSERIAL NOT NULL, 
    cliente_id INT8 NULL,
    texto TEXT NOT NULL,
    hash TEXT NULL,
    fecha TIMESTAMPTZ DEFAULT NOW() NULL, 
    idioma VARCHAR(5) DEFAULT 'es'::character varying NULL,
    CONSTRAINT mensajes_pkey PRIMARY KEY (mensaje_id),
    CONSTRAINT mensajes_cliente_id_fkey FOREIGN KEY (cliente_id) REFERENCES public.clientes(cliente_id) ON DELETE SET NULL
);

-- ----------------------------------------------------------------------------
-- 4. ANÁLISIS BASE (Relación 1 a 1 con Mensajes - Capa de IA y Clasificación)
-- ----------------------------------------------------------------------------
CREATE TABLE public.analisis (
    mensaje_id INT8 NOT NULL,
    clasificacion VARCHAR(50) NULL,
    riesgo NUMERIC(3, 2) NULL,
    recurrente BOOL NULL,
    vt_score TEXT DEFAULT '0' NULL,
    veredicto_final VARCHAR(50) NULL,
    detalles JSONB NULL,
    etiqueta_real INT4 NULL,
    archivo_score INT4 DEFAULT 0 NULL,
    ia_clase VARCHAR(50) NULL,
    CONSTRAINT analisis_mensaje_id_unique UNIQUE (mensaje_id),
    CONSTRAINT analisis_pkey PRIMARY KEY (mensaje_id),
    CONSTRAINT analisis_mensaje_id_fkey FOREIGN KEY (mensaje_id) REFERENCES public.mensajes(mensaje_id) ON DELETE CASCADE
);

-- ----------------------------------------------------------------------------
-- 5. ANÁLISIS DE ARCHIVOS ADJUNTOS
-- ----------------------------------------------------------------------------
CREATE TABLE public.analisis_archivos (
    mensaje_id INT8 NOT NULL, 
    status TEXT NULL,
    filename TEXT NULL,
    total_detections INT4 NULL,
    high_risk INT4 NULL,
    full_report TEXT NULL,
    CONSTRAINT analisis_archivos_pkey PRIMARY KEY (mensaje_id),
    CONSTRAINT analisis_archivos_mensaje_id_fkey FOREIGN KEY (mensaje_id) REFERENCES public.mensajes(mensaje_id) ON DELETE CASCADE
);

-- ----------------------------------------------------------------------------
-- 6. ANÁLISIS DE URLS (Flujo Automatizado con N8N y EFS)
-- ----------------------------------------------------------------------------
-- 6. Análisis de URLs (Estructura pura de datos, las imágenes van directo a EFS)
CREATE TABLE public.analisis_urlscan (
    mensaje_id INT8 NOT NULL, 
    fecha TIMESTAMPTZ DEFAULT NOW() NULL, 
    url_original TEXT NULL,
    veredicto TEXT NULL,
    score_vt INT4 NULL,
    score_urlscan INT4 NULL,
    url_final TEXT NULL,
    us_malicioso BOOL NULL,
    us_veredicto TEXT NULL,
    status_http TEXT NULL,
    ip_servidor TEXT NULL,
    pais TEXT NULL,
    tecnologias VARCHAR(255) NULL,
    CONSTRAINT archivos_mensaje_id_fkey FOREIGN KEY (mensaje_id) REFERENCES public.mensajes(mensaje_id) ON DELETE CASCADE
);