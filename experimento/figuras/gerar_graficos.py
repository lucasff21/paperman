# -*- coding: utf-8 -*-
"""
Gera as figuras do Capitulo 6 (Avaliacao) da dissertacao Recademy.
Substituem as Tabelas 6.3 (offline), 6.5 (online ranking) e 6.6 (online subjetivo).

Estilo:
- barras verticais agrupadas, valor escrito em cima de cada barra
- sem eixo vertical (spine/ticks/label removidos) -> pedido do Prof. Danilo
- paleta Okabe-Ito (colorblind-safe); consistencia entre figuras:
  Multiplicativo = azul, Baseline Semantico = laranja
- rotulos numericos em padrao brasileiro (virgula decimal)
Saida: PNG (300 dpi) + PDF vetorial em resultados/figuras/
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

OUT = os.path.dirname(os.path.abspath(__file__))

# ---- Paleta (Okabe-Ito) ------------------------------------------------------
AZUL      = "#0072B2"  # Multiplicativo / Lista 1
LARANJA   = "#E69F00"  # Baseline Semantico / Lista 2
CINZA     = "#999999"  # Baseline Aleatorio
VERMELHAO = "#D55E00"  # Aditivo

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.edgecolor": "#444444",
    "figure.dpi": 100,
})

def br(v, dec=3):
    """Formata numero em padrao brasileiro (virgula)."""
    return f"{v:.{dec}f}".replace(".", ",")

def limpar_eixo(ax):
    """Remove eixo vertical: spine esquerda/direita/topo, ticks e label de y."""
    for s in ("left", "right", "top"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", left=False, labelleft=False)
    ax.tick_params(axis="x", bottom=False)
    ax.set_ylabel("")

def rotular(ax, rects, dec=3, fs=8):
    for r in rects:
        h = r.get_height()
        ax.annotate(br(h, dec),
                    xy=(r.get_x() + r.get_width() / 2, h),
                    xytext=(0, 2), textcoords="offset points",
                    ha="center", va="bottom", fontsize=fs, color="#222222")

def salvar(fig, nome):
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(OUT, f"{nome}.{ext}"),
                    bbox_inches="tight", dpi=300)
    plt.close(fig)
    print("gerado:", nome)

# =============================================================================
# G1 - OFFLINE (Tabela 6.3, N=49)  -> 4 modelos x 6 metricas
# =============================================================================
metr_off = ["P@3", "MRR@3", "P@5", "MRR@5", "P@10", "nDCG@10"]
modelos = [
    ("Baseline Aleatório",  CINZA,     [0.231, 0.374, 0.216, 0.416, 0.198, 0.556]),
    ("Baseline Semântico",  LARANJA,   [0.265, 0.449, 0.224, 0.483, 0.192, 0.568]),
    ("Multiplicativo",      AZUL,      [0.197, 0.371, 0.180, 0.403, 0.135, 0.446]),
    ("Aditivo",             VERMELHAO, [0.163, 0.296, 0.135, 0.320, 0.112, 0.392]),
]
import numpy as np
x = np.arange(len(metr_off))
n = len(modelos)
largura = 0.20
fig, ax = plt.subplots(figsize=(11, 4.8))
for i, (nome, cor, vals) in enumerate(modelos):
    off = (i - (n - 1) / 2) * largura
    rects = ax.bar(x + off, vals, largura, label=nome, color=cor, edgecolor="white", linewidth=0.4)
    rotular(ax, rects, dec=3, fs=7)
ax.set_xticks(x)
ax.set_xticklabels(metr_off, fontsize=11)
ax.set_ylim(0, 0.66)
limpar_eixo(ax)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.14), ncol=4,
          frameon=False, fontsize=10, columnspacing=1.2, handlelength=1.2)
salvar(fig, "fig_offline_metricas")

# =============================================================================
# G2 - ONLINE ranking (Tabela 6.5, n=27) -> Lista 1 x Lista 2
# =============================================================================
metr_on = ["MRR", "MAP", "nDCG", "P@5", "P@10"]
lista1 = [0.6355, 0.5890, 0.8485, 0.4889, 0.5185]
lista2 = [0.5948, 0.5080, 0.8930, 0.3481, 0.3815]
x = np.arange(len(metr_on))
largura = 0.36
fig, ax = plt.subplots(figsize=(8.5, 4.6))
r1 = ax.bar(x - largura/2, lista1, largura, label="Lista 1 — Multiplicativo", color=AZUL, edgecolor="white", linewidth=0.5)
r2 = ax.bar(x + largura/2, lista2, largura, label="Lista 2 — Baseline Semântico", color=LARANJA, edgecolor="white", linewidth=0.5)
rotular(ax, r1, dec=3, fs=9); rotular(ax, r2, dec=3, fs=9)
ax.set_xticks(x); ax.set_xticklabels(metr_on, fontsize=12)
ax.set_ylim(0, 1.0)
limpar_eixo(ax)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.12), ncol=2, frameon=False, fontsize=10)
salvar(fig, "fig_online_ranking")

# =============================================================================
# G3 - ONLINE subjetivo (Tabela 6.6, n=27) -> 5 dimensoes, escala 1-5
# =============================================================================
dims = ["Relevância", "Diversidade", "Precisão", "Atualidade", "Surpresa"]
sub1 = [2.96, 2.89, 2.52, 3.33, 2.70]
sub2 = [2.44, 2.70, 1.89, 2.48, 2.07]
x = np.arange(len(dims))
largura = 0.36
fig, ax = plt.subplots(figsize=(8.8, 4.6))
r1 = ax.bar(x - largura/2, sub1, largura, label="Lista 1 — Multiplicativo", color=AZUL, edgecolor="white", linewidth=0.5)
r2 = ax.bar(x + largura/2, sub2, largura, label="Lista 2 — Baseline Semântico", color=LARANJA, edgecolor="white", linewidth=0.5)
rotular(ax, r1, dec=2, fs=9); rotular(ax, r2, dec=2, fs=9)
ax.axhline(3, color="#888888", linestyle="--", linewidth=0.8, zorder=0)
ax.annotate("limiar de relevância (3)", xy=(len(dims)-1, 3), xytext=(0, 3),
            textcoords="offset points", ha="right", va="bottom", fontsize=8, color="#666666")
ax.set_xticks(x); ax.set_xticklabels(dims, fontsize=11)
ax.set_ylim(0, 3.7)
limpar_eixo(ax)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.12), ncol=2, frameon=False, fontsize=10)
salvar(fig, "fig_online_subjetivo")

print("OK - figuras em", OUT)
