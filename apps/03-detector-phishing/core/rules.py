import re

def apply_rules(text):
    """
    Analiza el texto buscando patrones asociados a phishing/spear phishing.

    Retorna:
        (puntos_riesgo, indicadores)
    """

    puntos = 0.0
    indicadores = []

    text_lower = text.lower()

    # Regla 1: Urgencia
    palabras_urgencia = [
        "urgente", "inmediatamente", "ahora",
        "expira", "atención", "último aviso",
        "acción requerida", "plazo"
    ]

    if any(p in text_lower for p in palabras_urgencia):
        puntos += 0.15
        indicadores.append("urgencia")

    # Regla 2: Credenciales
    palabras_credenciales = [
        "contraseña",
        "password",
        "usuario",
        "credenciales",
        "iniciar sesión",
        "login",
        "verificar cuenta"
    ]

    if any(p in text_lower for p in palabras_credenciales):
        puntos += 0.30
        indicadores.append("solicitud_credenciales")

    # Regla 3: Información sensible
    palabras_sensibles = [
        "dni",
        "tarjeta",
        "cuenta bancaria",
        "datos personales",
        "información confidencial",
        "código de verificación"
    ]

    if any(p in text_lower for p in palabras_sensibles):
        puntos += 0.25
        indicadores.append("informacion_sensible")

    # Regla 4: Temas financieros
    palabras_financieras = [
        "factura",
        "pago",
        "transferencia",
        "depósito",
        "reembolso",
        "nómina",
        "comprobante"
    ]

    if any(p in text_lower for p in palabras_financieras):
        puntos += 0.20
        indicadores.append("tema_financiero")

    # Regla 5: Acciones solicitadas
    acciones = [
        "haz clic",
        "click",
        "enlace",
        "link",
        "ingresa",
        "accede",
        "verifica",
        "descarga"
    ]

    if any(p in text_lower for p in acciones):
        puntos += 0.20
        indicadores.append("accion_requerida")

    # Regla 6: URL detectada
    if re.search(r'https?://|www\.', text_lower):
        puntos += 0.15
        indicadores.append("url_detectada")

    # Regla 7: Archivos sospechosos
    extensiones = [
        ".exe", ".zip", ".rar",
        ".scr", ".bat", ".js"
    ]

    if any(ext in text_lower for ext in extensiones):
        puntos += 0.25
        indicadores.append("archivo_sospechoso")

    # Regla 8: Suplantación de identidad
    entidades = [
        "gerente",
        "director",
        "rrhh",
        "recursos humanos",
        "administrador",
        "soporte técnico",
        "banco"
    ]

    if any(e in text_lower for e in entidades):
        puntos += 0.15
        indicadores.append("posible_suplantacion")

    # Regla 9: Recompensas o amenazas
    incentivos = [
        "premio",
        "bono",
        "beneficio",
        "suspendida",
        "bloqueada",
        "cancelada"
    ]

    if any(i in text_lower for i in incentivos):
        puntos += 0.15
        indicadores.append("manipulacion_emocional")

    # Limitar puntuación
    puntos = min(puntos, 1.0)

    return round(puntos, 2), indicadores