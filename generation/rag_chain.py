"""
rag_chain.py
Une retrieval + generación: recupera chunks relevantes, arma un prompt
que obliga al modelo a citar la fuente, y devuelve la respuesta final
junto con las fuentes usadas (para mostrarlas en la UI).
"""
import os
import re
import sys
from dotenv import load_dotenv
from openai import OpenAI

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "retrieval"))
from retriever import retrieve

load_dotenv()

CHAT_MODEL = os.getenv("CHAT_MODEL", "openai/gpt-oss-120b")

GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client_openai = OpenAI(base_url=GROQ_BASE_URL, api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """Eres un asistente que responde preguntas ÚNICAMENTE basándote en el \
contexto proporcionado, extraído de documentos personales de Esteban Coveñas (CV, \
proyectos y una sección "sobre mí" con intereses personales).

Reglas:
1. Si la respuesta no está en el contexto, di explícitamente que no tienes esa información \
en los documentos disponibles. No inventes.
2. Si la pregunta no tiene relación con Esteban, su CV, sus proyectos o sus intereses \
personales, dilo claramente y no intentes forzar una respuesta con el contexto disponible.
3. Si solo una parte de la pregunta está respaldada por el contexto, responde esa parte y \
señala explícitamente qué parte no puedes responder con la información disponible.
4. Cada fragmento de contexto viene marcado con un número de referencia, por ejemplo [1], [2].
5. Cuando uses información de un fragmento, copia EXACTAMENTE ese número de referencia entre \
corchetes al final de la oración correspondiente. NO escribas el nombre del archivo ni el \
número de página tú mismo — solo copia el número de referencia tal cual aparece, por ejemplo [1].
6. Si tu respuesta indica que NO tienes la información (total o parcialmente), NO agregues \
ninguna cita de referencia a esa oración — las citas son solo para afirmaciones respaldadas \
por el contexto, no para mencionar qué documentos revisaste.
6b. NUNCA "infieras" o "deduzcas" datos que no estén escritos explícitamente en el contexto \
(por ejemplo, no asumas un nivel de habilidad a partir de que la persona use esa tecnología en \
proyectos). Si el dato exacto no aparece de forma literal en el contexto, di que no lo tienes, \
sin especular ni ofrecer una alternativa inferida.
7. Sé conciso y directo.
"""


def build_context(chunks: list[dict]) -> str:
    parts = []
    for i, c in enumerate(chunks, start=1):
        parts.append(f"[{i}]\n{c['text']}")
    return "\n\n---\n\n".join(parts)


def ask(question: str, top_k: int = 12) -> dict:
    """
    Devuelve:
    {
        "answer": str,
        "sources": [{"source": str, "page": int, "score": float}, ...]
    }
    """
    chunks = retrieve(question, top_k=top_k)

    if not chunks:
        return {"answer": "No encontré información relevante en los documentos.", "sources": []}

    context = build_context(chunks)

    response = client_openai.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Contexto:\n\n{context}\n\nPregunta: {question}"},
        ],
        temperature=0.2,
    )

    answer = response.choices[0].message.content

    # Reemplazamos cada [n] que escribió el modelo por la cita real
    # (archivo + página), tomada directamente de la metadata de ChromaDB.
    # Esto es lo que garantiza que la página citada sea siempre correcta,
    # sin depender de que el modelo la recuerde bien.
    def replace_ref(match):
        idx = int(match.group(1))
        if 1 <= idx <= len(chunks):
            c = chunks[idx - 1]
            return f"[{c['source']}, página {c['page']}]"
        return match.group(0)  # si el número no es válido, lo dejamos igual

    answer = re.sub(r"\[(\d+)\]", replace_ref, answer)

    # Fuentes únicas (sin duplicar página+archivo repetidos)
    seen = set()
    sources = []
    for c in chunks:
        key = (c["source"], c["page"])
        if key not in seen:
            seen.add(key)
            sources.append({"source": c["source"], "page": c["page"], "score": round(c["score"], 3)})

    return {"answer": answer, "sources": sources}


if __name__ == "__main__":
    result = ask("¿Qué código de error da si subo un archivo de 6GB sin usar multipart upload?")
    print("RESPUESTA:\n", result["answer"])
    print("\nFUENTES:")
    for s in result["sources"]:
        print(f"  - {s['source']} (página {s['page']}, score {s['score']})")
