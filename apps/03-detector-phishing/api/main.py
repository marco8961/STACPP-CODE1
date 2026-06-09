from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from model.infer import analyze

app = FastAPI()

class Payload(BaseModel):
    mensaje: str           
    cliente_id: Optional[str] = None
    mensaje_id: int        

@app.post("/analyze")
async def run_analysis(payload: Payload):
    # La IA recibe el ID para saber qué fila de Postgres actualizar
    return analyze(payload.mensaje, payload.cliente_id, payload.mensaje_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
