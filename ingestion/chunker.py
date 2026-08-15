"""
chunker.py
Divide el texto de cada página en chunks de tamaño fijo (en tokens),
con solapamiento (overlap) entre chunks consecutivos para no perder
contexto en los bordes.
"""
import tiktoken

ENCODING = tiktoken.get_encoding("cl100k_base")


def chunk_text(text: str, chunk_size: int = 300, overlap: int = 50) -> list[str]:
    """
    Divide un texto en chunks de ~chunk_size tokens, con overlap tokens
    de solapamiento entre chunks consecutivos.
    """
    tokens = ENCODING.encode(text)
    if len(tokens) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(tokens):
        end = start + chunk_size
        chunk_tokens = tokens[start:end]
        chunks.append(ENCODING.decode(chunk_tokens))
        if end >= len(tokens):
            break
        start = end - overlap  # retrocede 'overlap' tokens
    return chunks


def chunk_pages(pages: list[dict], chunk_size: int = 300, overlap: int = 50) -> list[dict]:
    """
    Recibe la salida de loader.load_pdfs() y devuelve una lista de chunks:
    [{"text": str, "source": str, "page": int, "chunk_id": str}, ...]
    """
    all_chunks = []
    for page in pages:
        page_chunks = chunk_text(page["text"], chunk_size, overlap)
        for i, chunk in enumerate(page_chunks):
            all_chunks.append({
                "text": chunk,
                "source": page["source"],
                "page": page["page"],
                "chunk_id": f"{page['source']}_p{page['page']}_c{i}",
            })
    print(f"Total de chunks generados: {len(all_chunks)}")
    return all_chunks


if __name__ == "__main__":
    from loader import load_pdfs
    pages = load_pdfs("../data/raw_pdfs")
    chunks = chunk_pages(pages)
    print(chunks[0])
