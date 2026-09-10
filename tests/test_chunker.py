"""
test_chunker.py
Tests para la función chunk_text de ingestion/chunker.py
"""
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "ingestion"))
from chunker import chunk_text


def test_texto_corto_no_se_divide():
    """Un texto más corto que chunk_size debe devolverse como un solo chunk."""
    texto = "Esto es un texto corto de prueba."
    resultado = chunk_text(texto, chunk_size=300, overlap=50)
    assert len(resultado) == 1
    assert resultado[0] == texto


def test_texto_largo_se_divide_en_varios_chunks():
    """Un texto más largo que chunk_size debe dividirse en más de un chunk."""
    texto = "palabra " * 1000  # texto largo repetitivo, fácil de generar
    resultado = chunk_text(texto, chunk_size=300, overlap=50)
    assert len(resultado) > 1


def test_chunks_no_estan_vacios():
    """Ningún chunk generado debe quedar vacío."""
    texto = "palabra " * 1000
    resultado = chunk_text(texto, chunk_size=300, overlap=50)
    for chunk in resultado:
        assert chunk.strip() != ""