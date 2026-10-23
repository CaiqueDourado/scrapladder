"""Which rung got store prices, by type of store (9,847 price readings, author's crawler)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

OUT = Path(__file__).parent / "img"
INK, MUTED, BG = "#111111", "#555555", "#fdfdfc"
# price readings per (store type, rung); from product_prices grouped by store and source
DATA = {
    "global":   {"http": 307, "curl": 1800, "browser": 650, "paid": 659, "own": 1464, "other": 497},
    "br_mkt":   {"http": 17, "curl": 568, "browser": 199, "paid": 3, "own": 2280, "other": 7},
    "br_retail": {"http": 470, "curl": 0, "browser": 11, "paid": 2, "own": 503, "other": 0},
    "brand":    {"http": 154, "curl": 81, "browser": 0, "paid": 0, "own": 4, "other": 3},
    "small":    {"http": 112, "curl": 38, "browser": 0, "paid": 0, "own": 0, "other": 0},
}
STORES = {"global": 5, "br_mkt": 4, "br_retail": 9, "brand": 6, "small": 8}
COLORS = {"http": "#9cc2ef", "curl": "#2a78d6", "browser": "#1baf7a", "paid": "#eb6834", "own": "#8a94a3", "other": "#d9dde3"}
TXT = {
    "": dict(title="Which rung got store prices", sub="9,829 price readings from 32 stores, by type of store",
             groups={"global": "global marketplaces", "br_mkt": "Brazilian marketplaces", "br_retail": "Brazilian retailers",
                     "brand": "brand stores", "small": "small and niche shops"},
             keys={"http": "plain HTTP", "curl": "curl_cffi", "browser": "headless browser", "paid": "paid API",
                   "own": "author's logged-in browser*", "other": "manual / unknown"},
             n="{n} stores · {p:,} readings", note="* not part of scrapladder"),
    ".pt-BR": dict(title="Qual degrau pegou os preços das lojas", sub="9.829 leituras de preço em 32 lojas, por tipo de loja",
                   groups={"global": "marketplaces globais", "br_mkt": "marketplaces brasileiros", "br_retail": "varejistas brasileiros",
                           "brand": "lojas de fabricante", "small": "lojas pequenas e de nicho"},
                   keys={"http": "HTTP comum", "curl": "curl_cffi", "browser": "navegador headless", "paid": "API paga",
                         "own": "navegador logado do autor*", "other": "manual / desconhecido"},
                   n="{n} lojas · {p:,} leituras", note="* fora da scrapladder"),
}
for suf, t in TXT.items():
    fig, ax = plt.subplots(figsize=(11, 5.0), dpi=110); fig.patch.set_facecolor(BG); ax.set_facecolor(BG)
    fig.subplots_adjust(left=0.25, right=0.97, top=0.72, bottom=0.12)
    fig.text(0.02, 0.92, t["title"], fontsize=16, weight="bold", color=INK)
    fig.text(0.02, 0.86, t["sub"], fontsize=10, color=MUTED)
    order = list(DATA)[::-1]
    for i, g in enumerate(order):
        tot = sum(DATA[g].values()); left = 0
        for k in COLORS:
            w = DATA[g][k] / tot * 100
            ax.barh(i, w, left=left, color=COLORS[k], height=0.62, edgecolor=BG, linewidth=1)
            if w >= 7:
                ax.text(left + w / 2, i, f"{w:.0f}%", ha="center", va="center", fontsize=8.5,
                        color="white" if k in ("curl", "browser", "paid", "own") else INK)
            left += w
        lab = t["groups"][g]; sub = t["n"].format(n=STORES[g], p=tot)
        if suf: sub = sub.replace(",", ".")
        ax.text(-1.5, i + 0.12, lab, ha="right", va="center", fontsize=10, color=INK)
        ax.text(-1.5, i - 0.2, sub, ha="right", va="center", fontsize=8, color=MUTED)
    ax.set_xlim(0, 100); ax.set_yticks([]); ax.set_xticks([])
    for s in ax.spines.values(): s.set_visible(False)
    x = 0.02
    for k, c in COLORS.items():
        fig.patches.append(matplotlib.patches.Rectangle((x, 0.785), 0.012, 0.03, transform=fig.transFigure, color=c))
        fig.text(x + 0.016, 0.8, t["keys"][k], fontsize=8.6, color=INK, va="center")
        x += 0.016 + 0.0068 * len(t["keys"][k]) + 0.02
    fig.text(0.02, 0.03, t["note"], fontsize=8.5, color=MUTED)
    fig.savefig(OUT / f"store-prices{suf}.png", facecolor=BG); plt.close(fig)
print("ok")
