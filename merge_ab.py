import json
import os

BASE_DIR = r"c:\Users\Lucas\Documents\Paperman\paperman_back"
FILE_A = os.path.join(BASE_DIR, "resultados", "recomendacoes_sem_only.json")
FILE_B = os.path.join(BASE_DIR, "resultados", "recomendacoes_multiplicative.json")
FILE_OUT = os.path.join(BASE_DIR, "paperman", "offline_evaluation", "recomendacoes_ab.json")

def main():
    print("Lendo Lista A (sem_only)...")
    with open(FILE_A, "r", encoding="utf-8") as fa:
        data_a = json.load(fa)

    print("Lendo Lista B (multiplicative)...")
    with open(FILE_B, "r", encoding="utf-8") as fb:
        data_b = json.load(fb)

    # Cria dicionário da lista B para busca rápida por autor
    dict_b = {item["author"]: item for item in data_b}

    merged = []
    
    for item_a in data_a:
        author = item_a["author"]
        base_title = item_a["base_title"]
        
        item_b = dict_b.get(author)
        if not item_b:
            print(f"Aviso: Autor {author} não encontrado na Lista B!")
            continue

        merged.append({
            "author": author,
            "base_title": base_title,
            "lista_a": item_a["recommendations"],
            "lista_b": item_b["recommendations"]
        })

    with open(FILE_OUT, "w", encoding="utf-8") as fout:
        json.dump(merged, fout, ensure_ascii=False, indent=2)

    print(f"SUCESSO! {len(merged)} autores combinados no arquivo: {FILE_OUT}")

if __name__ == "__main__":
    main()
