"""
app.py
Interfaz de chat con Streamlit. Llama directamente a rag_chain.ask()
(no necesita que la API FastAPI esté corriendo).

Correr con:
    streamlit run frontend/app.py
"""
import os
import sys
import streamlit as st

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "generation"))
from rag_chain import ask

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
                result = ask(question)
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
            except RuntimeError as e:
                st.error(str(e))

with st.sidebar:
    st.header("Info")
    st.markdown(
        "Este chatbot solo responde con información de mis 3 documentos "
        "indexados: CV, Proyectos y Sobre mí."
    )
    if st.button("Limpiar conversación"):
        st.session_state.messages = []
        st.rerun()
