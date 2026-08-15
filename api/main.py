"""
main.py
API FastAPI que expone el sistema RAG.

Correr con:
    uvicorn api.main:app --reload --port 8000

Luego probar en: http://localhost:8000/docs
"""
import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "generation"))
from rag_chain import ask

app = FastAPI(title="DocChat API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # en producción, restringir a tu dominio
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str
    top_k: int = 4


class SourceItem(BaseModel):
    source: str
    page: int
    score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceItem]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="La pregunta no puede estar vacía.")
    try:
        result = ask(req.question, top_k=req.top_k)
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
