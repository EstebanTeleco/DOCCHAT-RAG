"""
app.py
Interfaz de chat con Streamlit. Llama a la API de FastAPI vía HTTP
(la API FastAPI debe estar corriendo en API_URL).

Correr con:
    streamlit run frontend/app.py
"""
import os
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="DocChat - Esteban Coveñas", layout="centered")
st.title("DocChat - Pregúntame sobre Esteban Coveñas")
st.caption("RAG con citas: pregunta sobre mi CV, proyectos o intereses personales y te respondo citando la fuente exacta.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("sources"):
            with st.expander("Fuentes usadas"):
                for s in msg["sources"]:
                    st.markdown(f"- **{s['source']}** — página {s['page']} (score: {s['score']})")

question = st.chat_input("Pregunta sobre mi CV, proyectos o hobbies...")

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Buscando en los documentos..."):
            try:
                response = requests.post(
                    f"{API_URL}/chat",
                    json={"question": question},
                    timeout=60,
                )
                response.raise_for_status()
                result = response.json()

                st.markdown(result["answer"])
                if result["sources"]:
                    with st.expander("Fuentes usadas"):
                        for s in result["sources"]:
                            st.markdown(f"- **{s['source']}** — página {s['page']} (score: {s['score']})")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result["answer"],
                    "sources": result["sources"],
                })
            except requests.exceptions.ConnectionError:
                st.error(
                    f"No se pudo conectar con la API en {API_URL}. "
                    "¿Está corriendo FastAPI? (uvicorn api.main:app)"
                )
            except requests.exceptions.Timeout:
                st.error("La API tardó demasiado en responder (timeout).")
            except requests.exceptions.RequestException as e:
                st.error(f"Error al llamar a la API: {e}")

with st.sidebar:
    st.header("Info")
    st.markdown(
        "Este chatbot solo responde con información de mis 3 documentos "
        "indexados: CV, Proyectos y Sobre mí."
    )
    if st.button("Limpiar conversación"):
        st.session_state.messages = []
        st.rerun()