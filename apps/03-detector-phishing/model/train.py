import os
import torch
import pandas as pd
from datasets import Dataset
from transformers import (
    DistilBertTokenizerFast, 
    DistilBertForSequenceClassification, 
    Trainer, TrainingArguments
)
from core.db import get_conn

def load_data_from_db():
    conn = get_conn()
    try:
        # MEJORA: Usamos COALESCE para priorizar tu etiqueta manual (0 o 1)
        # Si no has etiquetado manualmente, usamos la lógica de riesgo
        query = """
            SELECT m.texto, 
                   COALESCE(a.etiqueta_real, 
                            CASE WHEN a.riesgo > 0.6 OR a.archivo_score > 0 THEN 1 ELSE 0 END
                   ) as label
            FROM mensajes m
            JOIN analisis a ON m.mensaje_id = a.mensaje_id
            WHERE m.texto IS NOT NULL AND m.texto != '';
        """
        df = pd.read_sql(query, conn)
        return df
    except Exception as e:
        print(f"❌ Error leyendo DB: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def train_model():
    print("🚀 Iniciando Re-entrenamiento con lógica de 3 motores...")
    df = load_data_from_db()
    
    if df.empty or len(df) < 5: # Subimos el mínimo para mayor calidad
        print(f"❌ Datos insuficientes ({len(df)}). Recomendamos al menos 5-10 ejemplos.")
        return

    # Balanceo rápido: Mostrar cuántos hay de cada uno
    print(f"📊 Dataset: {df['label'].value_counts().to_dict()} (0:Legit, 1:Phishing)")
    
    dataset = Dataset.from_dict(df.to_dict('list'))
    
    # Mantenemos el modelo multilingüe para soportar tus mensajes en varios idiomas
    model_name = "distilbert-base-multilingual-cased"
    tokenizer = DistilBertTokenizerFast.from_pretrained(model_name)

    def tokenize_function(batch):
        return tokenizer(batch["texto"], truncation=True, padding="max_length", max_length=128)

    tokenized_dataset = dataset.map(tokenize_function, batched=True)
    
    model = DistilBertForSequenceClassification.from_pretrained(model_name, num_labels=2)

    training_args = TrainingArguments(
        output_dir="./model_out",
        num_train_epochs=5,             # MEJORA: Bajamos a 5 para evitar que memorice (overfitting)
        per_device_train_batch_size=4,  # Lotes más pequeños para datasets pequeños
        learning_rate=2e-5,             # MEJORA: Tasa más lenta para un ajuste más fino
        weight_decay=0.01,
        save_strategy="epoch",          # Guardar al final de cada época
        logging_steps=1,
        report_to="none"
    )

    trainer = Trainer(
        model=model, 
        args=training_args, 
        train_dataset=tokenized_dataset
    )
    
    print("🧠 Entrenando... Ajustando pesos según etiqueta_real y archivo_score.")
    trainer.train()

    # Guardar versión final
    model.save_pretrained("./model_out")
    tokenizer.save_pretrained("./model_out")
    print(f"✅ ¡Modelo v3 guardado exitosamente!")

if __name__ == "__main__":
    train_model()