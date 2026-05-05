"""
translate_subjects.py
=====================
Detecta títulos em português no candidatos_reais.json e os traduz para inglês.
Gera um arquivo `titulos_traduzidos.json` com o mapeamento: {author_name: translated_title}.

Dependências:
    pip install deep-translator langdetect
"""

import json
import os
import time

from langdetect import detect, LangDetectException
from deep_translator import GoogleTranslator

BASE_DIR    = r"c:\Users\Lucas\Documents\Paperman\paperman_back"
DATA_JSON   = os.path.join(BASE_DIR, "resultados", "candidatos_reais.json")
OUTPUT_JSON = os.path.join(BASE_DIR, "paperman", "titulos_traduzidos.json")


def extract_subject(a: dict) -> tuple[str, str]:
    """Retorna (author_name, first_title) de um registro ORCID."""
    person = a.get("person", {})
    name_obj = person.get("name", {})
    given  = (name_obj.get("given-names")  or {}).get("value", "")
    family = (name_obj.get("family-name") or {}).get("value", "")
    full_name = f"{given} {family}".strip() or a.get("path", "unknown")

    acts  = a.get("activities-summary", {})
    works = acts.get("works", {}).get("group", [])
    for group in works:
        for ws in group.get("work-summary", []):
            t = (ws.get("title", {}) or {}).get("title", {}) or {}
            val = t.get("value", "") if isinstance(t, dict) else ""
            if val:
                return full_name, val
    return full_name, ""


def main():
    print("[INFO] Lendo candidatos_reais.json...")
    with open(DATA_JSON, encoding="utf-8") as f:
        raw = json.load(f)

    translator = GoogleTranslator(source="pt", target="en")
    translations: dict[str, str] = {}

    for a in raw:
        author, title = extract_subject(a)
        if not title:
            continue

        # Detecta idioma
        try:
            lang = detect(title)
        except LangDetectException:
            lang = "en"

        if lang == "pt":
            print(f"  [PT → EN] {author}")
            print(f"            ORIGINAL : {title[:80]}")
            try:
                translated = translator.translate(title)
                time.sleep(0.3)  # respeita rate limit do Google
            except Exception as e:
                print(f"            ERRO: {e} — mantendo original")
                translated = title
            print(f"            TRADUZIDO: {translated[:80]}")
            translations[author] = translated
        else:
            print(f"  [OK - EN] {author}: {title[:70]}")

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(translations, f, ensure_ascii=False, indent=2)

    print(f"\n[DONE] {len(translations)} títulos traduzidos. Arquivo: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
