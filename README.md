# DocChat RAG

![Tests](https://github.com/EstebanTeleco/DOCCHAT-RAG/actions/workflows/tests.yml/badge.svg)

Chatbot que responde preguntas sobre mí (Esteban Coveñas) citando la fuente exacta (archivo y página). Indexa 3 documentos: mi CV, un detalle de mis proyectos y una sección "sobre mí" con intereses personales (3 PDFs incluidos en `data/raw_pdfs`).

Está corriendo en vivo en mi página personal, en el botón **"Pregúntale a mi IA"**.

## Cómo funciona

1. Los PDFs se cargan y se dividen en chunks (por tokens, con overlap para no perder contexto en los bordes).
2. Cada chunk se convierte en embedding con Ollama (`nomic-embed-text`) y se guarda en ChromaDB.
3. Cuando llega una pregunta, se busca por similitud los chunks más relevantes.
4. Esos chunks se meten en el prompt junto con la pregunta y se le pasan al LLM (vía Groq, modelo `gpt-oss-120b`), que tiene que citar de dónde sacó cada dato.
5. Antes de mostrar la respuesta, las citas `[1]`, `[2]`, etc. se reemplazan por el archivo y la página real, tomados directo de la metadata de ChromaDB (no confío en que el modelo la escriba bien).
6. El frontend de Streamlit no llama directo a la lógica del RAG: le pega por HTTP al endpoint `POST /chat` de la API, igual que lo haría cualquier otro cliente (Postman, otro frontend, etc.).

Los embeddings se generan en local con Ollama porque es un modelo chico y corre bien hasta en una máquina sin GPU. La generación de la respuesta sí necesita un modelo más grande, así que esa parte va por la API de Groq — es gratis para este volumen de uso y la latencia es bastante mejor que intentar correr algo similar en una instancia chica.

## Estructura

```
docchat/
├── data/raw_pdfs/          CV, Proyectos y Sobre mí (3 PDFs)
├── ingestion/
│   ├── loader.py           extrae texto de los PDFs, página por página
│   ├── chunker.py          divide en chunks con overlap (tiktoken)
│   └── embed_and_store.py  genera embeddings (Ollama) y los guarda en ChromaDB
├── retrieval/
│   └── retriever.py        búsqueda semántica top-k
├── generation/
│   └── rag_chain.py        arma el prompt final y llama al LLM (Groq)
├── api/
│   └── main.py             FastAPI, expone GET /health y POST /chat
├── frontend/
│   └── app.py              interfaz de chat con Streamlit, consume la API por HTTP
├── evaluation/
│   ├── test_questions.json dataset de preguntas de prueba
│   └── evaluate.py         mide retrieval accuracy y keyword accuracy
├── tests/
│   ├── test_chunker.py     tests unitarios del chunking
│   └── test_api.py         tests del endpoint /health
├── vector_store/           se genera al correr embed_and_store.py
└── requirements.txt
```

## Instalación

```bash
cd docchat
python -m venv venv
source venv/bin/activate       # en Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Copiar `.env.example` a `.env` y completar la `GROQ_API_KEY` (se saca gratis en [console.groq.com](https://console.groq.com)). Si vas a correr los scripts fuera de Docker, dejá `OLLAMA_BASE_URL` apuntando a tu Ollama local (por defecto `http://localhost:11434/v1`). `API_URL` le dice a Streamlit dónde encontrar la API (por defecto `http://localhost:8000`; en Docker se sobreescribe solo).

```bash
cp .env.example .env
```

Ollama tiene que estar corriendo local con el modelo de embeddings descargado:

```bash
ollama pull nomic-embed-text
```

## Uso

Primero hay que indexar los documentos (una sola vez, o cada vez que cambien los PDFs):

```bash
python ingestion/embed_and_store.py
```

Para probar rápido por consola:

```bash
python generation/rag_chain.py
```

Levantar la API (tiene que estar corriendo antes que Streamlit, porque el frontend le pega por HTTP):

```bash
uvicorn api.main:app --reload --port 8000
```

La documentación queda en `http://localhost:8000/docs`.

Levantar la interfaz de chat (con la API ya corriendo):

```bash
streamlit run frontend/app.py
```

Se abre en `http://localhost:8501`.

Correr la evaluación (mide, sobre un set de preguntas de prueba, si el documento correcto aparece entre los recuperados y si la respuesta contiene la info esperada):

```bash
python evaluation/evaluate.py
```

Los resultados detallados quedan en `evaluation/eval_results.json`.

## Tests

Tests unitarios para el chunker y el endpoint `/health` (no necesitan Ollama ni Groq corriendo):

```bash
pytest tests/
```

## Con Docker

Requiere tener Docker Desktop corriendo. Con esto se levanta Ollama (para embeddings), la API y el frontend sin instalar nada más en la máquina. La generación de respuestas de todas formas sale a internet a la API de Groq, así que hace falta la `GROQ_API_KEY` en el `.env` igual.

```bash
cp .env.example .env

# descarga el modelo de embeddings dentro del volumen de Ollama (una sola vez)
docker compose run --rm ollama-init

# indexa los documentos (una sola vez, o cuando cambien los PDFs)
docker compose run --rm ingest

# levanta la API y el frontend
docker compose up --build
```

API en `http://localhost:8000/docs`, frontend en `http://localhost:8501`. El vector store se monta como volumen así que no se pierde al bajar los contenedores (`docker compose down`).

## Despliegue

Corriendo en vivo en una instancia EC2 de AWS (Free Tier), enlazada desde mi página personal.

- **Instancia:** `t3.micro` (Ubuntu 24.04), Free Tier, con IP pública.
- **Memoria:** el t3.micro solo trae 1GB de RAM, así que le agregué 2GB de swap para que no se caigan los contenedores al levantar todo junto.
- **LLM:** la generación va por la API de Groq en vez de un modelo local — no hay forma de correr un LLM decente en una instancia de este tamaño. Los embeddings sí siguen siendo locales con Ollama, corriendo dentro de la misma instancia.
- **SSL/HTTPS:** [Caddy](https://caddyserver.com/) corre como reverse proxy delante de la API y se encarga del certificado SSL automáticamente (Let's Encrypt), así el servicio queda expuesto por HTTPS sin tener que renovar nada a mano.
- **Acceso:** el botón "Pregúntale a mi IA" en mi página redirige a este servicio.

Es un despliegue simple, pensado para portafolio y no para producción real:

- Una sola instancia, sin autoscaling ni balanceo de carga.
- La API no tiene autenticación (ver más abajo).
- No usa Elastic IP, así que si la instancia se reinicia la IP pública puede cambiar.

## Por qué lo armé así

Usé chunking por tokens en vez de por caracteres porque con `tiktoken` mido el tamaño real que va a ver el modelo, y evito cortar oraciones a la mitad de forma rara. 220 tokens por chunk con 60 de overlap me funcionó bien para este tamaño de documentos.

ChromaDB porque es una vector DB embebida, no necesita infraestructura aparte, y para un proyecto de este tamaño no tenía sentido levantar Pinecone o algo así. Para producción probablemente migraría a otra cosa.

Separé embeddings de generación a propósito: los embeddings los dejé en Ollama local porque el modelo es chico y no tiene sentido pagar o depender de una API externa solo para eso. La generación sí necesita un modelo grande, y ahí no compite: correrlo local en una instancia sin GPU daba respuestas lentas, así que terminé usando Groq.

Las citas son obligatorias en el prompt, y además se muestran las fuentes recuperadas por separado en la UI. La idea es poder comparar lo que el modelo dice que citó contra lo que realmente se recuperó, para detectar si está alucinando la cita.

El retriever descarta chunks con score de similitud por debajo de `MIN_SCORE` (en `retrieval/retriever.py`). Sin esto, cualquier pregunta fuera de tema (que no tiene nada que ver con mi CV/proyectos/hobbies) igual recibía los chunks "menos malos", y el modelo terminaba forzando una respuesta con contexto irrelevante. Después de correr `evaluation/evaluate.py` con preguntas dentro y fuera de alcance, terminé bajando `MIN_SCORE` a 0.35 — con 0.5 estaba descartando de más algunas preguntas válidas.

## Cosas que sé que le faltan

- No hace OCR, así que un PDF escaneado como imagen no va a extraer texto (pdfplumber solo lee texto nativo).
- No maneja tablas complejas más allá del texto plano que se puede extraer.
- El chunking es por página + tokens, no es semantic chunking. Dividir por encabezados sería una mejora natural.
- La API no tiene autenticación, y ya está expuesta a internet en el despliegue de AWS — es el próximo problema a resolver ahí.
- No hay Elastic IP en el despliegue, así que la URL pública no es 100% estable si la instancia se reinicia.
- Cobertura de tests todavía parcial: cubre chunking y el endpoint `/health`, pero falta testear `rag_chain.ask()` y `/chat` con mocking de las llamadas a Ollama/Groq.

Ideas para seguir mejorando: comparar distintos tamaños de chunk, métricas más serias con RAGAS en vez de solo keyword matching, y streaming de la respuesta en vez de esperar a que termine todo el mensaje.
