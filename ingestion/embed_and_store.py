"""
embed_and_store.py
Genera embeddings de cada chunk con la API de OpenAI y los persiste
en una colección de ChromaDB en disco (vector_store/).

Ejecutar una sola vez (o cada vez que cambien los PDFs de origen):
    python embed_and_store.py
"""
import os
import sys
from dotenv import load_dotenv
from openai import OpenAI
import chromadb

sys.path.append(os.path.dirname(__file__))
from loader import load_pdfs
from chunker import chunk_pages

load_dotenv()

EMBEDDING_MODEL = "nomic-embed-text"
PDF_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw_pdfs")
VECTOR_STORE_DIR = os.path.join(os.path.dirname(__file__), "..", "vector_store")
COLLECTION_NAME = "docchat"

# Ollama expone una API compatible con la de OpenAI.
# No hace falta una API key real, cualquier string sirve.
# OLLAMA_BASE_URL permite apuntar a Ollama corriendo en el host cuando este
# script se ejecuta dentro de un contenedor Docker (ver .env / docker-compose.yml).
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
client_openai = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Genera embeddings en batch (la API de OpenAI acepta listas)."""
    response = client_openai.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
    )
    return [item.embedding for item in response.data]


def build_vector_store():
    print("1/4 - Cargando PDFs...")
    pages = load_pdfs(PDF_DIR)

    print("2/4 - Generando chunks...")
    chunks = chunk_pages(pages, chunk_size=220, overlap=60)

    print("3/4 - Generando embeddings (esto usa Ollama en local)...")
    batch_size = 10
    all_embeddings = []
    for i in range(0, len(chunks), batch_size):
        batch = [c["text"] for c in chunks[i:i + batch_size]]
        embeddings = embed_texts(batch)
        all_embeddings.extend(embeddings)
        print(f"   Embeddings generados: {min(i + batch_size, len(chunks))}/{len(chunks)}")

    print("4/4 - Guardando en ChromaDB...")
    chroma_client = chromadb.PersistentClient(path=VECTOR_STORE_DIR)
    # Si la colección ya existe (de una corrida previa), la reseteamos
    try:
        chroma_client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = chroma_client.create_collection(COLLECTION_NAME, metadata={"hnsw:space": "cosine"})
    collection.add(
        ids=[c["chunk_id"] for c in chunks],
        embeddings=all_embeddings,
        documents=[c["text"] for c in chunks],
        metadatas=[{"source": c["source"], "page": c["page"]} for c in chunks],
    )

    print(f"Listo. {len(chunks)} chunks indexados en '{VECTOR_STORE_DIR}'.")


if __name__ == "__main__":
    build_vector_store()
