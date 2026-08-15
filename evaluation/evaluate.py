"""
evaluate.py
Corre el dataset de preguntas de prueba contra el sistema RAG y mide:
  - Retrieval accuracy: ¿el documento fuente correcto aparece entre las
    fuentes recuperadas?
  - Keyword presence: ¿la respuesta generada contiene al menos una de
    las palabras clave esperadas?

Correr con:
    python evaluation/evaluate.py
"""
import json
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "generation"))
from rag_chain import ask

TEST_FILE = os.path.join(os.path.dirname(__file__), "test_questions.json")


def run_evaluation():
    with open(TEST_FILE, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    results = []
    retrieval_hits = 0
    keyword_hits = 0

    for i, case in enumerate(test_cases, start=1):
        print(f"\n[{i}/{len(test_cases)}] {case['question']}")
        result = ask(case["question"])
        answer = result["answer"]
        sources_found = [s["source"] for s in result["sources"]]

        keyword_ok = any(
            kw.lower() in answer.lower() for kw in case["expected_keywords"]
        )

        # "__NONE__" marca preguntas fuera de alcance: lo que importa es que
        # la RESPUESTA final diga que no tiene información (ya medido en
        # keyword_ok), no si llegaron chunks de bajo score al contexto —
        # esos pueden colarse sin que el LLM termine usándolos.
        if case["expected_source"] == "__NONE__":
            retrieval_ok = keyword_ok
        else:
            retrieval_ok = case["expected_source"] in sources_found

        retrieval_hits += int(retrieval_ok)
        keyword_hits += int(keyword_ok)

        print(f"  Respuesta: {answer[:120]}...")
        print(f"  Retrieval correcto: {'si' if retrieval_ok else 'no'} (esperado: {case['expected_source']}, obtenido: {sources_found})")
        print(f"  Keyword encontrada: {'si' if keyword_ok else 'no'} (esperadas: {case['expected_keywords']})")

        results.append({
            "question": case["question"],
            "answer": answer,
            "retrieval_ok": retrieval_ok,
            "keyword_ok": keyword_ok,
            "sources_found": sources_found,
        })

    n = len(test_cases)
    print("\n" + "=" * 50)
    print(f"RESUMEN: {n} preguntas evaluadas")
    print(f"  Retrieval accuracy: {retrieval_hits}/{n} ({100*retrieval_hits/n:.1f}%)")
    print(f"  Keyword accuracy:   {keyword_hits}/{n} ({100*keyword_hits/n:.1f}%)")
    print("=" * 50)

    # Guardar resultados detallados
    output_path = os.path.join(os.path.dirname(__file__), "eval_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nResultados detallados guardados en: {output_path}")


if __name__ == "__main__":
    run_evaluation()
