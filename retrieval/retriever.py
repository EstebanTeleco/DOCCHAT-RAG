"""
retriever.py
Dada una pregunta del usuario, la convierte en embedding y busca los
chunks más relevantes en ChromaDB.
"""
import os
from dotenv import load_dotenv
from openai import OpenAI
import chromadb

load_dotenv()

EMBEDDING_MODEL = "nomic-embed-text"
VECTOR_STORE_DIR = os.path.join(os.path.dirname(__file__), "..", "vector_store")
COLLECTION_NAME = "docchat"

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
client_openai = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
chroma_client = chromadb.PersistentClient(path=VECTOR_STORE_DIR)


def get_collection():
    try:
        return chroma_client.get_collection(COLLECTION_NAME)
    except Exception as e:
        raise RuntimeError(
            "No se encontró la colección de ChromaDB. "
            "Corre primero: python ingestion/embed_and_store.py"
        ) from e


MIN_SCORE = 0.35  # chunks por debajo de este score se descartan por no ser relevantes


def retrieve(query: str, top_k: int = 4, min_score: float = MIN_SCORE) -> list[dict]:
    """
    Devuelve los top_k chunks más relevantes para la query, descartando los que
    no superen min_score (evita meterle al LLM contexto irrelevante que lo lleve
    a "inventar" una conexión inexistente con la pregunta):
    [{"text": str, "source": str, "page": int, "score": float}, ...]
    """
    collection = get_collection()

    query_embedding = client_openai.embeddings.create(
        model=EMBEDDING_MODEL,
        input=[query],
    ).data[0].embedding

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
    )

    retrieved = []
    for i in range(len(results["ids"][0])):
        score = 1 - results["distances"][0][i]
        if score < min_score:
            continue
        retrieved.append({
            "text": results["documents"][0][i],
            "source": results["metadatas"][0][i]["source"],
            "page": results["metadatas"][0][i]["page"],
            # ChromaDB devuelve distancia (menor = más similar), la invertimos a "score"
            "score": score,
        })
    return retrieved


if __name__ == "__main__":
    results = retrieve("¿Cuál es el límite de tamaño de archivo en el plan Free?")
    for r in results:
        print(f"[{r['source']} p.{r['page']}] score={r['score']:.3f}")
        print(r["text"][:150], "...\n")
