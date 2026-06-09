import torch
# Cambiamos AutoModel por el nombre específico o usamos el Auto correctamente
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from langdetect import detect
from core.memory import check_memory, save_analysis
from core.rules import apply_rules
from core.preprocessor import clean_text

# 👇 CAMBIO: Usamos una ruta relativa inteligente para que funcione en cualquier lugar
model_path = "model_out/checkpoint-75"
# 1. Cargamos el TOKENIZADOR desde el checkpoint
tokenizer = AutoTokenizer.from_pretrained(model_path)

# 2. Cargamos el MODELO usando la clase Auto que ya importaste
model = AutoModelForSequenceClassification.from_pretrained(model_path)

# (Opcional) Si el servidor tiene GPU, muévelo a CUDA
# device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
# model.to(device)
def analyze(text, cliente_id=None, mensaje_id=None):
    # Lógica de limpieza
    texto_limpio = clean_text(text)
    
    # DETECCIÓN DE IDIOMA (Tu requerimiento principal)
    try:
        idioma_real = detect(text)
    except:
        idioma_real = "es"

    # Tu lógica original de reglas y memoria
    exists, _ = check_memory(texto_limpio)
    puntos_reglas, indicadores = apply_rules(texto_limpio)
    
    # Inferencia
    inputs = tokenizer(texto_limpio, return_tensors="pt", truncation=True, padding=True, max_length=128)
    with torch.no_grad():
        outputs = model(**inputs)
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        confianza, label_idx = torch.max(probs, dim=1)
    
    # Mantenemos exactamente tu formato de respuesta original
    riesgo_ia = 0.5 if label_idx.item() == 1 else 0.1
    riesgo_total = min(1.0, riesgo_ia + puntos_reglas)

    res = {
        "clasificacion": "phishing" if riesgo_total > 0.6 else "legit",
        "riesgo": round(float(riesgo_total), 2),
        "ia_clase": f"LABEL_{label_idx.item()}",
        "indicadores": indicadores,
        "recurrente": exists
    }
    
    # Guardado: Aquí se actualiza el idioma en la DB
    save_analysis(texto_limpio, res, cliente_id, mensaje_id, idioma_real)
    
    return res
