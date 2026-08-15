"""
loader.py
Extrae texto de todos los PDFs en data/raw_pdfs, página por página,
conservando metadata (nombre de archivo, número de página).
"""
import os
import pdfplumber

def load_pdfs(pdf_dir: str) -> list[dict]:
    """
    Devuelve una lista de dicts:
    [{"text": str, "source": str, "page": int}, ...]
    Un elemento por cada página con texto no vacío.
    """
    pages = []
    pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith(".pdf")]

    if not pdf_files:
        raise FileNotFoundError(f"No se encontraron PDFs en {pdf_dir}")

    for filename in sorted(pdf_files):
        filepath = os.path.join(pdf_dir, filename)
        print(f"Leyendo: {filename}")
        with pdfplumber.open(filepath) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                if text and text.strip():
                    pages.append({
                        "text": text.strip(),
                        "source": filename,
                        "page": page_num,
                    })
    print(f"Total de páginas con texto extraído: {len(pages)}")
    return pages


if __name__ == "__main__":
    pages = load_pdfs("../data/raw_pdfs")
    print(pages[0])
