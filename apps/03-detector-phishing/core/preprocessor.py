import re
import unicodedata
from core.db import get_conn

def clean_text(text):
    """
    Limpia el texto para el análisis de la IA:
    1. Convierte a minúsculas.
    2. Reemplaza URLs por el token [url].
    3. Normaliza acentos y caracteres especiales.
    4. Elimina caracteres no deseados manteniendo la estructura básica.
    """
    if not text:
        return ""
    
    # 1. Pasar a minúsculas
    text = text.lower()
    
    # 2. Reemplazar URLs por [url]
    # Detecta http, https y www
    text = re.sub(r"http\S+|www\S+|https\S+", "[url]", text, flags=re.MULTILINE)
    
    # 3. Normalización de caracteres (Quitar acentos/tildes)
    # Ejemplo: 'á' -> 'a', 'ñ' -> 'n'
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8', 'ignore')
    
    # 4. Limpieza de símbolos (Mantenemos letras, espacios y los corchetes del token url)
    text = re.sub(r"[^a-z\s\[\]]", "", text)
    
    # 5. Eliminar espacios en blanco extra
    text = " ".join(text.split())
    
    return text.strip()

def normalizar_mensajes_db():
    """
    Función de mantenimiento para limpiar mensajes antiguos 
    que no pasaron por el preprocesador.
    """
    conn = get_conn()
    if not conn:
        print("❌ No se pudo conectar a la base de datos para normalizar.")
        return
    
    cur = conn.cursor()
    try:
        # Buscamos mensajes que no tengan el token [url] pero sí contengan http
        cur.execute("SELECT mensaje_id, texto FROM mensajes WHERE texto LIKE '%http%'")
        rows = cur.fetchall()
        
        for mid, txt in rows:
            limpio = clean_text(txt)
            cur.execute("UPDATE mensajes SET texto = %s WHERE mensaje_id = %s", (limpio, mid))
        
        conn.commit()
        print(f"✅ Se normalizaron {len(rows)} mensajes en la base de datos.")
    except Exception as e:
        print(f"❌ Error en la normalización de DB: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()