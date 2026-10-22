"""Cover and figure for the README: which rung got the page first on 643 domains."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

OUT = Path(__file__).parent / "img"
INK, MUTED, LINE, BG, BLUE, GRAY = "#111111", "#555555", "#e6e6e6", "#fdfdfc", "#2a78d6", "#b8b8b8"
# First method in the domain memory of the author's crawler (Tudo Sobre Produtos, 2026)
DATA = [("curl_cffi (browser TLS)", 480), ("Playwright", 70), ("own logged-in browser*", 34),
        ("paid scraping APIs", 32), ("httpx", 12), ("requests", 6), ("DrissionPage", 6), ("Scrapling", 3)]
TEXT = {
    "": ("Which rung got the page first", "643 domains in the memory of a product crawler, 2026",
         "* not part of scrapladder: it reused the author's own browser session", "{n} domains"),
    ".pt-BR": ("Qual degrau pegou a página primeiro", "643 domínios na memória de um crawler de produtos, 2026",
               "* fora da scrapladder: usava a sessão do navegador do próprio autor", "{n} domínios"),
}
LABELS_PT = {"own logged-in browser*": "navegador logado do autor*", "paid scraping APIs": "APIs de scraping pagas",
             "curl_cffi (browser TLS)": "curl_cffi (TLS de navegador)"}
OUT.mkdir(parents=True, exist_ok=True)
for suffix, (title, sub, note, fmt) in TEXT.items():
    fig, ax = plt.subplots(figsize=(10, 5.2), dpi=110)
    fig.patch.set_facecolor(BG); ax.set_facecolor(BG)
    fig.subplots_adjust(left=0.27, right=0.93, top=0.8, bottom=0.12)
    fig.text(0.02, 0.92, title, fontsize=17, weight="bold", color=INK)
    fig.text(0.02, 0.86, sub, fontsize=10.5, color=MUTED)
    fig.text(0.02, 0.03, note, fontsize=8.5, color=MUTED)
    labels = [LABELS_PT.get(l, l) if suffix else l for l, _ in DATA][::-1]
    vals = [v for _, v in DATA][::-1]
    colors = [GRAY if "*" in l else BLUE for l in labels]
    ax.barh(labels, vals, color=colors, height=0.68)
    for y, v in enumerate(vals):
        ax.text(v + 4, y, f"{v}  (" + (f"{v/643:.0%}" if v/643 >= 0.01 else "<1%") + ")", va="center", fontsize=9.5, color=INK)
    for s in ("top", "right", "bottom"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color(LINE); ax.set_xticks([]); ax.tick_params(colors=INK, length=0, labelsize=10)
    ax.set_xlim(0, 560)
    fig.savefig(OUT / f"rungs{suffix}.png", facecolor=BG)
    plt.close(fig)
print("ok")
