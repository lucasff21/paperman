import json
import os
import math
from typing import List

# Caminhos
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTADOS_DIR = os.path.join(BASE_DIR, "..", "resultados")
AVALIACOES_FILE = os.path.join(RESULTADOS_DIR, "avaliacoes_sem_only.json")

# Funções de métricas adaptadas para aceitar notas de 1 a 5

def precision_at_k(notas: List[int], k: int, threshold: int = 4) -> float:
    """Proporção de itens relevantes nos Top K. (Relevante se nota >= threshold)"""
    rel = [1 if n >= threshold else 0 for n in notas[:k]]
    return sum(rel) / k if k > 0 else 0.0

def mrr_at_k(notas: List[int], k: int, threshold: int = 4) -> float:
    """Posição do primeiro item relevante. (Relevante se nota >= threshold)"""
    for i, n in enumerate(notas[:k]):
        if n >= threshold:
            return 1.0 / (i + 1)
    return 0.0

def ndcg_at_k(notas: List[int], k: int) -> float:
    """nDCG com relevância graduada. Mapeamento: 1->0, 2->1, 3->2, 4->3, 5->4"""
    # Mapear para ganhos (gain = nota - 1)
    gains = [max(0, n - 1) for n in notas[:k]]
    
    dcg = sum(gain / math.log2(i + 2) for i, gain in enumerate(gains))
    
    # IDCG (ordenando os ganhos do maior para o menor idealmente)
    ideal_gains = sorted(gains, reverse=True)
    idcg = sum(gain / math.log2(i + 2) for i, gain in enumerate(ideal_gains))
    
    return dcg / idcg if idcg > 0 else 0.0

def main():
    if not os.path.exists(AVALIACOES_FILE):
        print("Arquivo de avaliações ainda não existe.")
        return
        
    with open(AVALIACOES_FILE, "r", encoding="utf-8") as f:
        avaliacoes = json.load(f)
        
    if not avaliacoes:
        print("Nenhuma avaliação concluída ainda.")
        return

    print(f"=== RESULTADOS DA AVALIAÇÃO ({len(avaliacoes)} respostas) ===\n")
    
    metrics = {
        "p@5": [], "p@10": [],
        "mrr@10": [],
        "ndcg@5": [], "ndcg@10": []
    }
    
    for author, itens in avaliacoes.items():
        # Ordena pelo rank para garantir
        itens.sort(key=lambda x: x["rank"])
        notas = [item["nota"] for item in itens]
        
        # O paper original usou Threshold 4 (Relevante / Muito Relevante) para P e MRR
        p5 = precision_at_k(notas, 5, threshold=4)
        p10 = precision_at_k(notas, 10, threshold=4)
        mrr = mrr_at_k(notas, 10, threshold=4)
        ndcg5 = ndcg_at_k(notas, 5)
        ndcg10 = ndcg_at_k(notas, 10)
        
        metrics["p@5"].append(p5)
        metrics["p@10"].append(p10)
        metrics["mrr@10"].append(mrr)
        metrics["ndcg@5"].append(ndcg5)
        metrics["ndcg@10"].append(ndcg10)
        
        print(f"{author[:25]:<25} | P@5: {p5:.2f} | MRR: {mrr:.2f} | nDCG@10: {ndcg10:.2f}")

    print("\n=== MÉDIAS GERAIS ===")
    print(f"Precision@5 : {sum(metrics['p@5']) / len(metrics['p@5']):.4f}")
    print(f"Precision@10: {sum(metrics['p@10']) / len(metrics['p@10']):.4f}")
    print(f"MRR@10      : {sum(metrics['mrr@10']) / len(metrics['mrr@10']):.4f}")
    print(f"nDCG@5      : {sum(metrics['ndcg@5']) / len(metrics['ndcg@5']):.4f}")
    print(f"nDCG@10     : {sum(metrics['ndcg@10']) / len(metrics['ndcg@10']):.4f}")

if __name__ == "__main__":
    main()
