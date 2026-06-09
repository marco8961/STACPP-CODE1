import os  # <--- Falta importar os
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

# Cargar las variables del archivo .env
load_dotenv()

def get_conn():
    try:
        conn = psycopg2.connect(
            # Usamos os.getenv para obtener los valores del .env
            host=os.getenv("DB_HOST"), 
            port=os.getenv("DB_PORT"),
            dbname=os.getenv("DB_NAME"), # Nombre exacto que pusiste en el .env
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS")
        )
        return conn
    except Exception as e:
        print(f"❌ Error conectando a Postgres: {e}")
        return None