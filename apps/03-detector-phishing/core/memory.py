import hashlib
from core.db import get_conn

def _hash(txt):
    return hashlib.sha256(txt.encode()).hexdigest()

def check_memory(txt):
    h = _hash(txt)
    conn = get_conn()
    if not conn: return False, 0.0
    cur = conn.cursor()
    try:
        cur.execute("SELECT a.riesgo FROM mensajes m JOIN analisis a ON m.mensaje_id = a.mensaje_id WHERE m.hash = %s", (h,))
        row = cur.fetchone()
        return (True, float(row[0])) if row else (False, 0.0)
    except:
        return False, 0.0
    finally:
        cur.close()
        conn.close()

def save_analysis(txt, res, cliente_id=None, mensaje_id=None, idioma="es"):
    """Solo actualiza el idioma y guarda el análisis sin cambiar tu estructura de resultados"""
    if mensaje_id is None: return
    h = _hash(txt)
    conn = get_conn()
    if not conn: return
    cur = conn.cursor()
    try:
        # 1. Actualizamos el idioma y el hash en la tabla mensajes que creó n8n
        cur.execute("""
            UPDATE mensajes 
            SET idioma = %s, hash = %s, texto = %s
            WHERE mensaje_id = %s
        """, (idioma, h, txt, mensaje_id))

        # 2. Insertamos el resultado del análisis (IA)
        cur.execute("""
            INSERT INTO analisis (mensaje_id, riesgo, clasificacion, ia_clase)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (mensaje_id) DO UPDATE SET 
                riesgo = EXCLUDED.riesgo, 
                clasificacion = EXCLUDED.clasificacion,
                ia_clase = EXCLUDED.ia_clase
        """, (mensaje_id, res.get('riesgo'), res.get('clasificacion'), res.get('ia_clase')))
        conn.commit()
    except Exception as e:
        print(f"Error DB: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()