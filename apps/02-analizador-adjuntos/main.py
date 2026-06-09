import logging
import json
import os
import uuid
import shutil
import psycopg2
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form
import uvicorn
import clamd
from dotenv import load_dotenv  # Carga de variables de entorno

# --- Inicialización de Entorno ---
load_dotenv()

# --- Configuración ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
STORAGE_DIR = Path("analisis_data")
STORAGE_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Analizador de Archivos - DB Sincronizada")

# --- Función de Conexión Protegida ---
def guardar_en_db(mensaje_id, reporte, archivo_score):
    try:
        # Extraemos los datos de forma segura desde el .env
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS")
        )
        cur = conn.cursor()
        
        query = """
            INSERT INTO analisis_archivos (
                mensaje_id, status, filename, total_detections, high_risk, full_report
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (mensaje_id) DO UPDATE SET
                status = EXCLUDED.status,
                filename = EXCLUDED.filename,
                total_detections = EXCLUDED.total_detections,
                high_risk = EXCLUDED.high_risk,
                full_report = EXCLUDED.full_report;
        """
        
        cur.execute(query, (
            mensaje_id,
            reporte["veredicto_telegram"],
            reporte["archivo_nombre"],
            1 if reporte["es_malicioso"] else 0,
            1 if archivo_score >= 0.8 else 0,
            json.dumps(reporte)
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        logging.info(f"✅ DB Actualizada: Mensaje {mensaje_id}")
    except Exception as e:
        logging.error(f"❌ Error DB: {e}")

# --- Conexión ClamAV ---

def obtener_cliente_clamav():
    try:
        # 👇 SOLUCIÓN: Cambiamos UnixSocket por NetworkSocket apuntando a tu VPS
        cd = clamd.ClamdNetworkSocket(host='127.0.0.1', port=3310)
        cd.ping()
        return cd
    except Exception as e:
        logging.error(f"❌ ClamAV Offline: {e}")
        return None

# --- Endpoint ---
@app.post("/upload/")
async def upload_file(
    data: UploadFile = File(...), 
    mensaje_id: int = Form(...)
):
    cd = obtener_cliente_clamav()
    if not cd:
        return {"status": "error", "message": "ClamAV no disponible"}

    temp_path = STORAGE_DIR / f"scan_{uuid.uuid4().hex[:8]}{Path(data.filename).suffix}"
    
    try:
        with temp_path.open("wb") as buffer:
            shutil.copyfileobj(data.file, buffer)

        scan_result = cd.scan(str(temp_path.absolute()))
        # Obtener el resultado del primer archivo escaneado
        filename_key = list(scan_result.keys())[0]
        status, virus_name = scan_result[filename_key]
        es_malicioso = (status == "FOUND")
        
        # Score de riesgo
        archivo_score = 1.0 if es_malicioso else 0.0
        if not es_malicioso and data.filename.lower().endswith(('.exe', '.bat', '.js')):
            archivo_score = 0.4

        reporte = {
            "archivo_nombre": data.filename,
            "veredicto_telegram": "PELIGROSO" if es_malicioso else "LIMPIO",
            "es_malicioso": es_malicioso,
            "virus": virus_name if es_malicioso else "Ninguno",
            "score": archivo_score
        }

        guardar_en_db(mensaje_id, reporte, archivo_score)

        return {
            "status": "success",
            "analysis": {
                "veredicto": reporte["veredicto_telegram"],
                "archivo_score": archivo_score
            }
        }

    finally:
        if temp_path.exists(): 
            os.remove(temp_path)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
