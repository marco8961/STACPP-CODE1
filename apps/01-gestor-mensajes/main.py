import os
import ssl
import stat
import re
import uuid
import asyncio
import aiohttp
import uvicorn
import socks
import random
import asyncpg  # Drivers asíncronos para PostgreSQL RDS
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from contextlib import asynccontextmanager
import hmac
import hashlib
import json
import base64
import time

# --- CONFIGURACIÓN DE VARIABLES DE ENTORNO ---
load_dotenv()
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SECRET_TOKEN = os.getenv("SECRET_TOKEN_N8N")

# --- SISTEMA DE SESIONES PROPIO Y SEGURO ---
SECRET_KEY = os.getenv("SECRET_TOKEN_N8N", "default_secret_key_stacpp_12345").encode()

def crear_token(email: str, role: str) -> str:
    payload = {
        "email": email,
        "role": role,
        "exp": time.time() + 86400 * 7  # Expiración en 7 días
    }
    payload_str = json.dumps(payload)
    payload_b64 = base64.urlsafe_b64encode(payload_str.encode()).decode()
    signature = hmac.new(SECRET_KEY, payload_b64.encode(), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{signature}"

def verificar_token(token: str) -> dict:
    if not token or "." not in token:
        return None
    try:
        payload_b64, signature = token.split(".", 1)
        expected_sig = hmac.new(SECRET_KEY, payload_b64.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return None
        payload_str = base64.urlsafe_b64decode(payload_b64.encode()).decode()
        payload = json.loads(payload_str)
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None

def obtener_usuario_sesion(request: Request) -> dict:
    token = request.cookies.get("session_token")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
    if not token:
        return None
    return verificar_token(token)

async def es_administrador(email: str) -> bool:
    if not email:
        return False
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT 1 FROM administradores WHERE email = $1", email)
        return row is not None


# Mapeo dinámico y estricto desde tu archivo .env (AWS RDS)
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

# Directorios Locales de Trabajo
BASE_DIR = "/app/redcoon-data"
TEMP_DIR = os.path.join(BASE_DIR, "temp_files")
PROXIES_CACHE_FILE = os.path.join(BASE_DIR, "proxies_cache.txt")
os.makedirs(TEMP_DIR, exist_ok=True)

# URL de la API de Webshare para descargar Proxies SOCKS5
WEBSHARE_API_URL = os.getenv("WEBSHARE_API_URL", "https://proxy.webshare.io/api/v2/proxy/list/download/.../socks5/us/")

# --- MICROSERVICIOS EN DOCKER ---
N8N_WEBHOOK_URL = "http://n8n:5678/webhook/telegram"
ARCHIVO_ANALIZADOR_URL = "http://02-analizador-adjuntos:8006/upload/"
LIMITE_PESO_MB = 20

EXTENSIONES_PROHIBIDAS = [
    '.exe', '.msi', '.bat', '.sh', '.py', '.js', '.vbs',
    '.scr', '.cmd', '.jar', '.ps1', '.elf', '.bin', '.com'
]

# Pools globales en Memoria RAM (Compartidos estrictamente en el mismo hilo de FastAPI)
POOL_PROXIES = []
clientes_activos = {}
logueos_pendientes = {}
db_pool = None

# ==============================================================================
# 🔄 LIFESPAN: RECONEXIÓN AUTOMÁTICA DE SESIONES DESDE LA DB AL ARRANCAR
# ==============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool
    print("🚀 [Redcoon] Inicializando contenedor y conectando a AWS RDS...")
    
    # 1. Crear el pool de conexiones asíncronas a tu PostgreSQL en AWS
    db_pool = await asyncpg.create_pool(
        host=DB_HOST, port=int(DB_PORT), user=DB_USER, password=DB_PASSWORD, database=DB_NAME
    )
    
    # 2. Asegurar que la tabla estructurada exista en la nube
    # 2. Asegurar que la tabla estructurada exista en la nube
    async with db_pool.acquire() as conn:
        # Creamos la tabla base con el estándar correcto
        # Este código correrá sin errores tanto si la tabla ya fue creada por el dump,
        # como si Python tiene que crearla desde cero en una DB vacía.
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS public.usuarios_telegram (
                telegram_id INT8 NOT NULL,
                telefono VARCHAR(20) NOT NULL,
                nombre VARCHAR(100) NULL,
                session_string TEXT NOT NULL,
                fecha_registro TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NULL,
                CONSTRAINT usuarios_telegram_pkey PRIMARY KEY (telegram_id)
            );
        ''')

        # Si el dump no tenía la columna email por ser una versión vieja, esto la parchará
        await conn.execute("""
            ALTER TABLE public.usuarios_telegram 
            ADD COLUMN IF NOT EXISTS email VARCHAR(255);
        """)

        # Asegurar la creación de la tabla administradores
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS public.administradores (
                email VARCHAR(255) NOT NULL,
                password_hash VARCHAR(64) NOT NULL,
                creado TIMESTAMPTZ DEFAULT NOW() NULL,
                CONSTRAINT administradores_pkey PRIMARY KEY (email)
            );
        ''')
        
        # Parchear la tabla si ya existía sin la columna password_hash
        await conn.execute('''
            ALTER TABLE public.administradores ADD COLUMN IF NOT EXISTS password_hash VARCHAR(64);
        ''')

        # Sembrar admin maestro si no hay registros
        admins_count = await conn.fetchval("SELECT COUNT(*) FROM public.administradores;")
        if admins_count == 0:
            default_email = "admin@stacpp.com"
            default_pass = "admin12345"
            p_hash = hashlib.sha256(default_pass.encode()).hexdigest()
            await conn.execute('''
                INSERT INTO public.administradores (email, password_hash)
                VALUES ($1, $2);
            ''', default_email, p_hash)
            print(f"🔑 [Sembrado] Usuario Maestro Administrador creado: {default_email} con clave: {default_pass}")

    # 💡 Al salir del bloque "async with", la conexión se devuelve al pool limpiamente.
    print("💾 [Redcoon] Conexión exitosa a AWS RDS PostgreSQL y tablas verificadas.")
        
    # 3. Cargar proxies
    await actualizar_and_cargar_proxies()

    # 4. 🔥 RELEER LA BASE DE DATOS Y REHYDRATAR ESCUCHAS 🔥
    print("💾 [Redcoon] Escaneando sesiones existentes en la RDS para reactivar canales...")
    async with db_pool.acquire() as conn:
        registros = await conn.fetch("SELECT telegram_id, nombre, session_string FROM usuarios_telegram;")
        
        for reg in registros:
            try:
                proxy_config = obtener_proxy_aleatorio()
                # Levantamos Telethon cargando el string puro recuperado de la RDS
                c = TelegramClient(StringSession(reg['session_string']), API_ID, API_HASH, proxy=proxy_config)
                await c.connect()

                if await c.is_user_authorized():
                    # Volvemos a amarrar el interceptor perimetral de malware/enlaces
                    c.add_event_handler(filtro_central, events.NewMessage)
                    clientes_activos[reg['telegram_id']] = c
                    print(f"✅ [Restaurado] Canal de escucha activo para: {reg['nombre']} (ID: {reg['telegram_id']})")
            except Exception as e:
                print(f"❌ Error crítico rehidratando sesión remota {reg['telegram_id']}: {e}")

    # Cede el control a FastAPI para comenzar a recibir peticiones HTTP por el puerto 8007
    yield
    
    # Esto se ejecuta de forma segura cuando haces un 'docker compose down'
    print("🛑 [Redcoon] Apagando servicios, desconectando Telegram y liberando RDS...")
    for uid, cliente in clientes_activos.items():
        await cliente.disconnect()
    await db_pool.close()
    print("🔒 Recursos liberados correctamente de la memoria.")

# Vinculamos el ciclo de vida a la aplicación
app = FastAPI(title="Redcoon Security API con RDS", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if os.path.exists("/webs/redcoon/static"):
    app.mount("/static", StaticFiles(directory="/webs/redcoon/static"), name="static")

# ==============================================================================
# 🛠️ CAPA DE INFRAESTRUCTURA (PROXIES)
# ==============================================================================

async def actualizar_and_cargar_proxies():
    global POOL_PROXIES
    POOL_PROXIES = []
    texto_proxies = ""

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(WEBSHARE_API_URL, timeout=8) as resp:
                if resp.status == 200:
                    texto_proxies = await resp.text()
                    with open(PROXIES_CACHE_FILE, "w", encoding="utf-8") as f:
                        f.write(texto_proxies)
                    print("🌐 Proxies actualizados desde la API de Webshare y cacheados localmente.")
    except Exception as e:
        print(f"⚠️ Error conectando a Webshare ({e}). Usando respaldos locales.")

    if not texto_proxies and os.path.exists(PROXIES_CACHE_FILE):
        with open(PROXIES_CACHE_FILE, "r", encoding="utf-8") as f:
            texto_proxies = f.read()
        print("✅ Caché local de proxies cargado correctamente del disco.")

    if texto_proxies:
        lineas = [l.strip() for l in texto_proxies.split("\n") if l.strip()]
        for linea in lineas:
            partes = linea.split(":")
            if len(partes) == 4:
                POOL_PROXIES.append({
                    "ip": partes[0], "puerto": int(partes[1]),
                    "user": partes[2], "pass": partes[3]
                })
    print(f"🚀 Pool de Proxies listo en RAM: {len(POOL_PROXIES)} servidores SOCKS5.")

def obtener_proxy_aleatorio():
    if not POOL_PROXIES:
        return None
    p = random.choice(POOL_PROXIES)
    return (socks.SOCKS5, p["ip"], p["puerto"], True, p["user"], p["pass"])

# ==============================================================================
# 🛡️ CAPA DE PROTECCIÓN DE MENSAJES Y MALWARE
# ==============================================================================

async def filtro_central(event):
    msg = event.message
    try:
        me = await event.client.get_me()
        auth_user_id = me.id
        chat_id = event.chat_id
        sender = await event.get_sender()
        username = getattr(sender, 'username', None) or f"User_{sender.id}"
        fue_borrado = False

        # --- CAPA 1: ANÁLISIS DE MALWARE EN ADJUNTOS ---
        if msg.file:
            filename = (getattr(msg.file, 'name', None) or f"file_{uuid.uuid4().hex[:6]}").lower()
            size_mb = (msg.file.size or 0) / (1024 * 1024)
            extension = os.path.splitext(filename)[1]

            if extension in EXTENSIONES_PROHIBIDAS:
                await event.delete()
                await event.client.send_message('me', f"🚨 **Redcoon:** Borrado `{filename}` (Tipo prohibido).")
                fue_borrado = True
            elif size_mb > LIMITE_PESO_MB:
                await event.delete()
                await event.client.send_message('me', f"⚠️ **Redcoon:** Borrado `{filename}` (+{LIMITE_PESO_MB}MB).")
                fue_borrado = True
            else:
                path = await msg.download_media(file=TEMP_DIR)
                try:
                    os.chmod(path, stat.S_IRUSR)
                    loop = asyncio.get_running_loop()
                    file_bytes = await loop.run_in_executor(None, lambda: open(path, 'rb').read())

                    async with aiohttp.ClientSession() as session:
                        data = aiohttp.FormData()
                        data.add_field('data', file_bytes, filename=filename, content_type='application/octet-stream')
                        async with session.post(ARCHIVO_ANALIZADOR_URL, data=data, timeout=30) as resp:
                            if resp.status == 200:
                                res = await resp.json()
                                if res.get("analysis", {}).get("veredicto") == "PELIGROSO":
                                    await event.delete()
                                    await event.client.send_message('me', f"🚨 **Redcoon:** `{filename}` detectado como Malware.")
                                    fue_borrado = True
                finally:
                    if os.path.exists(path):
                        os.remove(path)

	 # --- CAPA 2: LINKS (n8n) ---
        if msg.text and not fue_borrado:
            links = re.findall(r'(https?://[^\s]+)', msg.text)
            payload = {
                "auth_user_id": auth_user_id,
                "chat_id": chat_id,
                "message_id": msg.id,
                "username": username,
                "contenido_texto": msg.text,
                "has_links": len(links) > 0,
                "links": links
            }
            async with aiohttp.ClientSession() as session:
                try:
                    await session.post(N8N_WEBHOOK_URL, json=payload)
                except: pass

    except Exception as e: print(f"Error en filtro: {e}")

# ==============================================================================
# 🔌 ENDPOINTS API DE FASTAPI
# ==============================================================================

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = "/webs/stackpp/static/index.html"
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Error de Ruta</h1><p>El index no se encuentra en la ruta mapeada.</p>"

@app.post("/auth/solicitar_codigo")
async def api_solicitar_codigo(request: Request):
    data = await request.json()
    phone = data.get('phone')
    if not phone: 
        return {"status": "error", "msg": "Teléfono requerido"}

    proxy_config = obtener_proxy_aleatorio()
    client = TelegramClient(StringSession(), API_ID, API_HASH, proxy=proxy_config)
    await client.connect()

    try:
        sent_code = await client.send_code_request(phone)
        logueos_pendientes[phone] = {
            "client": client,
            "hash": sent_code.phone_code_hash,
            "proxy": proxy_config
        }
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "msg": str(e)}

@app.post("/auth/verificar")
async def api_verificar(request: Request):

    data = await request.json()

    phone = data.get('phone')
    code = data.get('code')
    pwd = data.get('password') or ""

    email = data.get('email')

    temp = logueos_pendientes.get(phone)
    if not temp: 
        return {"status": "error", "msg": "Flujo de sesión no inicializado"}

    client = temp['client']
    try:
        try:
            user = await client.sign_in(phone, code)
        except SessionPasswordNeededError:
            if not pwd: 
                return {"status": "requires_password", "msg": "Se requiere la contraseña de verificación en dos pasos (2FA)."}
            user = await client.sign_in(password=pwd)

        me = await client.get_me()
        session_string = client.session.save()

        # Guardamos el string generado de manera persistente en AWS RDS
        async with db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO usuarios_telegram
                (
                    telegram_id,
                    telefono,
                    nombre,
                    email,
                    session_string
                )
                VALUES ($1,$2,$3,$4,$5)

                ON CONFLICT (telegram_id)
                DO UPDATE
                SET
                    telefono = EXCLUDED.telefono,
                    nombre = EXCLUDED.nombre,
                    email = EXCLUDED.email,
                    session_string = EXCLUDED.session_string;
            ''',
                me.id,
                phone,
                me.first_name,
                email,
                session_string
            )

            # Asegurar que exista una fila en la tabla clientes para mapear las métricas
            if email:
                await conn.execute('''
                    INSERT INTO clientes (nombre, contacto)
                    VALUES ($1, $2)
                    ON CONFLICT (contacto) DO NOTHING;
                ''',
                    me.first_name,
                    email
                )

        client.add_event_handler(filtro_central, events.NewMessage)
        clientes_activos[me.id] = client
        logueos_pendientes.pop(phone, None)

        return {"status": "success", "user": me.first_name}
    except Exception as e:
        return {"status": "error", "msg": str(e)}

@app.post("/api/borrar_mensaje")
async def api_borrar_mensaje(request: Request):
    data = await request.json()
    auth_user_id = data.get('auth_user_id')
    chat_id = data.get('chat_id')
    message_id = data.get('message_id')

    client = clientes_activos.get(int(auth_user_id))
    if not client: 
        return {"status": "error", "msg": "El cliente de este usuario no se encuentra activo en este hilo de ejecución"}

    try:
        await client.delete_messages(int(chat_id), [int(message_id)])
        return {"status": "ok", "msg": "Mensaje eliminado mediante directiva de seguridad"}
    except Exception as e:
        return {"status": "error", "msg": str(e)}
    
@app.post("/auth/check_user")
async def check_user(request: Request):

    data = await request.json()

    email = data.get("email")

    if not email:
        return {
            "telegram_linked": False
        }

    async with db_pool.acquire() as conn:

        row = await conn.fetchrow(
            """
            SELECT nombre
            FROM usuarios_telegram
            WHERE email = $1
            """,
            email
        )

    if row:

        return {
            "telegram_linked": True,
            "user": row["nombre"]
        }

    return {
        "telegram_linked": False
    }

# ==============================================================================
# 🔐 NUEVOS ENDPOINTS DE AUTENTICACIÓN Y ADMINISTRACIÓN
# ==============================================================================

async def verificar_google_token(id_token: str) -> dict:
    url = f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=5) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                if "email" in data:
                    return data
        except Exception:
            return None
    return None

@app.post("/auth/google_login")
async def api_google_login(request: Request):
    data = await request.json()
    id_token = data.get("credential")
    if not id_token:
        raise HTTPException(status_code=400, detail="Token no proporcionado")
    
    google_data = await verificar_google_token(id_token)
    if not google_data:
        raise HTTPException(status_code=401, detail="Token de Google inválido")
    
    email = google_data.get("email")
    name = google_data.get("name", "")
    
    role = "user"
    if await es_administrador(email):
        role = "admin"
        
    token = crear_token(email, role)
    
    from fastapi.responses import JSONResponse
    response = JSONResponse(content={
        "status": "success",
        "email": email,
        "name": name,
        "role": role,
        "token": token
    })
    
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        max_age=86400 * 7,
        samesite="lax"
    )
    return response

@app.post("/auth/admin_login")
async def api_admin_login(request: Request):
    data = await request.json()
    email = data.get("email")
    password = data.get("password")
    
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email y contraseña requeridos")
        
    p_hash = hashlib.sha256(password.encode()).hexdigest()
    
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT email FROM administradores WHERE email = $1 AND password_hash = $2",
            email, p_hash
        )
        
    if not row:
        raise HTTPException(status_code=401, detail="Credenciales de administrador incorrectas")
        
    token = crear_token(email, "admin")
    
    from fastapi.responses import JSONResponse
    response = JSONResponse(content={
        "status": "success",
        "email": email,
        "role": "admin",
        "token": token
    })
    
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        max_age=86400 * 7,
        samesite="lax"
    )
    return response

@app.get("/api/metricas")
async def api_metricas(request: Request):
    session = obtener_usuario_sesion(request)
    if not session:
        raise HTTPException(status_code=401, detail="Sesión no iniciada")
    
    email = session["email"]
    
    async with db_pool.acquire() as conn:
        client_row = await conn.fetchrow(
            "SELECT cliente_id FROM clientes WHERE contacto = $1", email
        )
        if not client_row:
            return {
                "status": "ok",
                "links_procesados": 0,
                "archivos_procesados": 0
            }
        
        client_id = client_row["cliente_id"]
        
        links_row = await conn.fetchrow(
            """
            SELECT COUNT(DISTINCT m.mensaje_id) as total
            FROM mensajes m
            JOIN analisis a ON m.mensaje_id = a.mensaje_id
            WHERE m.cliente_id = $1
            """,
            client_id
        )
        
        files_row = await conn.fetchrow(
            """
            SELECT COUNT(DISTINCT m.mensaje_id) as total
            FROM mensajes m
            JOIN analisis_archivos aa ON m.mensaje_id = aa.mensaje_id
            WHERE m.cliente_id = $1
            """,
            client_id
        )
        
        return {
            "status": "ok",
            "links_procesados": links_row["total"] if links_row else 0,
            "archivos_procesados": files_row["total"] if files_row else 0
        }

@app.get("/api/admin/metricas_globales")
async def api_admin_metricas_globales(request: Request):
    session = obtener_usuario_sesion(request)
    if not session or session.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Acceso denegado")
    
    async with db_pool.acquire() as conn:
        users_count = await conn.fetchval("SELECT COUNT(*) FROM usuarios_telegram")
        links_count = await conn.fetchval("SELECT COUNT(*) FROM analisis")
        malware_count = await conn.fetchval(
            "SELECT COUNT(*) FROM analisis_archivos WHERE status = 'PELIGROSO'"
        )
        
        return {
            "status": "ok",
            "total_usuarios": users_count,
            "total_links": links_count,
            "total_malware": malware_count
        }

@app.get("/api/admin/usuarios")
async def api_admin_usuarios(request: Request):
    session = obtener_usuario_sesion(request)
    if not session or session.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Acceso denegado")
    
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT telegram_id, telefono, nombre, email, fecha_registro
            FROM usuarios_telegram
            ORDER BY fecha_registro DESC
            """
        )
        
        usuarios = []
        for r in rows:
            tg_id = r["telegram_id"]
            status = "Activo" if tg_id in clientes_activos else "Inactivo"
            usuarios.append({
                "telegram_id": tg_id,
                "telefono": r["telefono"],
                "nombre": r["nombre"],
                "email": r["email"] or "No asociado",
                "fecha_registro": r["fecha_registro"].isoformat() if r["fecha_registro"] else "",
                "status": status
            })
            
        return {
            "status": "ok",
            "usuarios": usuarios
        }

@app.get("/api/admin/alertas")
async def api_admin_alertas(request: Request):
    session = obtener_usuario_sesion(request)
    if not session or session.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Acceso denegado")
    
    async with db_pool.acquire() as conn:
        files_alerts = await conn.fetch(
            """
            SELECT aa.mensaje_id, aa.filename as details, aa.status as veredicto, m.fecha, m.texto
            FROM analisis_archivos aa
            JOIN mensajes m ON aa.mensaje_id = m.mensaje_id
            WHERE aa.status = 'PELIGROSO'
            ORDER BY m.fecha DESC LIMIT 50
            """
        )
        
        links_alerts = await conn.fetch(
            """
            SELECT a.mensaje_id, a.veredicto_final as veredicto, m.fecha, m.texto
            FROM analisis a
            JOIN mensajes m ON a.mensaje_id = m.mensaje_id
            WHERE a.veredicto_final = 'PELIGROSO' OR a.riesgo >= 0.8
            ORDER BY m.fecha DESC LIMIT 50
            """
        )
        
        alertas = []
        for r in files_alerts:
            alertas.append({
                "tipo": "Malware",
                "mensaje_id": r["mensaje_id"],
                "detalle": f"Archivo: {r['details']}",
                "fecha": r["fecha"].isoformat() if r["fecha"] else "",
                "texto": r["texto"]
            })
        for r in links_alerts:
            alertas.append({
                "tipo": "Phishing",
                "mensaje_id": r["mensaje_id"],
                "detalle": "Enlace malicioso detectado",
                "fecha": r["fecha"].isoformat() if r["fecha"] else "",
                "texto": r["texto"]
            })
            
        alertas.sort(key=lambda x: x["fecha"], reverse=True)
        
        return {
            "status": "ok",
            "alertas": alertas[:50]
        }

@app.post("/api/admin/crear_administrador")
async def api_admin_crear_administrador(request: Request):
    session = obtener_usuario_sesion(request)
    if not session or session.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Acceso denegado")
    
    data = await request.json()
    new_email = data.get("email")
    new_password = data.get("password")
    if not new_email or not new_password:
        raise HTTPException(status_code=400, detail="Email y contraseña requeridos")
    
    p_hash = hashlib.sha256(new_password.encode()).hexdigest()
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO administradores (email, password_hash)
            VALUES ($1, $2)
            ON CONFLICT (email) DO UPDATE SET password_hash = EXCLUDED.password_hash
            """,
            new_email, p_hash
        )
        return {"status": "ok", "msg": f"Administrador {new_email} añadido correctamente"}


# ==============================================================================
# 🚀 ORQUESTACIÓN DE ARRANQUE (BOOTSTRAPPING)
# ==============================================================================
if __name__ == '__main__':
    # Al pasar la variable 'app' directa (en lugar de "main:app"), obligamos a Uvicorn
    # a correr en el proceso raíz y disparar el bloque de lectura 'lifespan' anterior.
    uvicorn.run(app, host="0.0.0.0", port=8000)

