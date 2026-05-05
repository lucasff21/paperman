"""
xlsx_to_translations.py
=======================
Lê resultados/CANDIDATOS.xlsx e gera paperman/titulos_traduzidos.json
com o mapeamento { author_name: translated_title }.
O arquivo não tem cabeçalho: coluna 0 = nome, coluna 1 = título traduzido.
"""
import json
import os
import pandas as pd

BASE_DIR    = r"c:\Users\Lucas\Documents\Paperman\paperman_back"
XLSX_FILE   = os.path.join(BASE_DIR, "resultados", "CANDIDATOS.xlsx")
OUTPUT_JSON = os.path.join(BASE_DIR, "paperman", "titulos_traduzidos.json")

def main():
    print(f"Lendo: {XLSX_FILE}")
    # header=None porque a primeira linha já é dado (sem cabeçalho)
    df = pd.read_excel(XLSX_FILE, header=None)
    df.columns = ["nome", "titulo"]

    print(f"Total de linhas: {len(df)}")
    print(df.head(5).to_string())
    print()

    translations = {}
    for _, row in df.iterrows():
        nome   = str(row["nome"]).strip()
        titulo = str(row["titulo"]).strip()
        if nome and titulo and titulo.lower() not in ["nan", "", "none"]:
            translations[nome] = titulo
            print(f"  {nome[:40]:<40} -> {titulo[:60]}")

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(translations, f, ensure_ascii=False, indent=2)

    print(f"\n[DONE] {len(translations)} entradas salvas em: {OUTPUT_JSON}")

if __name__ == "__main__":
    main()

