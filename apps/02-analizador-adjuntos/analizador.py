import clamd
import json
import os
from datetime import datetime

LOG_JSON = "reportes_seguridad.json"

def escanear_archivo_local(path_temporal, nombre_real):
    """
    Analiza el archivo con ClamAV y genera un score de riesgo.
    """
    try:
        # Conexión por red al contenedor de ClamAV
        cd = clamd.ClamdNetworkSocket(host='127.0.0.1', port=3310)
        cd.ping()

        # Escaneo mediante instream (envía el archivo por red al contenedor ClamAV)
        with open(path_temporal, 'rb') as f:
            scan_result = cd.instream(f)
        
        # Estructura de respuesta de instream: {'stream': ('STATUS', 'VIRUS_NAME')}
        status, virus_name = scan_result['stream']

        # LÓGICA DE SCORE (Sin tocar):
        # 1.0 si es virus confirmado.
        # 0.4 si es extensión peligrosa pero ClamAV no detectó firma.
        es_malicioso = (status == "FOUND")
        archivo_score = 1.0 if es_malicioso else 0.0

        extensiones_riesgo = ['.exe', '.scr', '.bat', '.vbs', '.js']
        if not es_malicioso and any(nombre_real.lower().endswith(ext) for ext in extensiones_riesgo):
            archivo_score = 0.4

        resultado = {
            "timestamp": datetime.now().isoformat(),
            "archivo": nombre_real,
            "veredicto": "INFECTADO" if es_malicioso else "LIMPIO",
            "amenaza": virus_name if virus_name else "Ninguna",
            "archivo_score": archivo_score,
            "status_raw": status
        }

        # Guardar en JSON local (historial)
        historial = []
        if os.path.exists(LOG_JSON):
            with open(LOG_JSON, "r") as f:
                try: 
                    historial = json.load(f)
                except: 
                    historial = []

        historial.append(resultado)
        with open(LOG_JSON, "w") as f:
            json.dump(historial, f, indent=4)

        return resultado

    except Exception as e:
        return {"error": f"Error ClamAV: {e}", "archivo_score": 0.0}
