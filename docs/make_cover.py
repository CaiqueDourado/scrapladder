"""Cover and logo: a ladder of fetch methods with a per-domain memory."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, FancyArrowPatch
from pathlib import Path

OUT = Path(__file__).parent / "img"
INK, MUTED, LINE, BG = "#111111", "#555555", "#d9dde3", "#fdfdfc"
BLUE, ORANGE, AQUA, GRAY = "#2a78d6", "#eb6834", "#1baf7a", "#8a94a3"
RUNG_COLORS = ["#9cc2ef", "#5e9be2", "#2a78d6", "#1d5aa6"]
for fam in ("Inter", "DejaVu Sans"):
    try:
        matplotlib.font_manager.findfont(fam, fallback_to_default=False); plt.rcParams["font.family"] = fam; break
    except ValueError:
        pass


def ladder_mark(ax, x, y, w, h, lw=6, rungs=4, top_accent=True):
    """Two rails and rungs; the top rung in orange (the one that worked)."""
    ax.plot([x, x], [y, y + h], color=INK, lw=lw, solid_capstyle="round")
    ax.plot([x + w, x + w], [y, y + h], color=INK, lw=lw, solid_capstyle="round")
    for i in range(rungs):
        yy = y + h * (i + 0.6) / (rungs + 0.2)
        c = ORANGE if (top_accent and i == 2) else BLUE
        ax.plot([x, x + w], [yy, yy], color=c, lw=lw * 0.9, solid_capstyle="round")


TEXT = {
    "": dict(tag="Fetch any page by climbing\na ladder of methods",
             sub="and remember, per site,\nwhich rung worked",
             rungs=[("requests · httpx", "plain HTTP"), ("curl_cffi", "browser TLS fingerprint"),
                    ("Playwright · Camoufox · Scrapling", "real browser, runs JavaScript"),
                    ("scraping APIs", "paid, last resort")],
             cost="time and cost", mem="memory", memrows=[("loja-a.com.br", "curl_cffi"), ("loja-b.com.br", "playwright"),
                                                          ("blog-c.com", "httpx")],
             foot="blocks detected: Cloudflare · Akamai · DataDome · PerimeterX · AWS WAF · CAPTCHA · 429"),
    ".pt-BR": dict(tag="Baixe qualquer página subindo\numa escada de métodos",
                   sub="e lembre, por site,\nqual degrau funcionou",
                   rungs=[("requests · httpx", "HTTP comum"), ("curl_cffi", "TLS de navegador"),
                          ("Playwright · Camoufox · Scrapling", "navegador de verdade, roda JS"),
                          ("APIs de scraping", "pagas, último recurso")],
                   cost="tempo e custo", mem="memória", memrows=[("loja-a.com.br", "curl_cffi"), ("loja-b.com.br", "playwright"),
                                                                ("blog-c.com", "httpx")],
                   foot="bloqueios detectados: Cloudflare · Akamai · DataDome · PerimeterX · AWS WAF · CAPTCHA · 429"),
}

OUT.mkdir(parents=True, exist_ok=True)
for suf, t in TEXT.items():
    fig = plt.figure(figsize=(11, 5.6), dpi=110)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 110); ax.set_ylim(0, 56); ax.axis("off")
    # brand
    ladder_mark(ax, 5, 39.5, 4.2, 11, lw=5)
    ax.text(12, 45, "scrapladder", fontsize=30, weight="bold", color=INK, va="center")
    ax.text(5, 32.5, t["tag"], fontsize=15.5, color=INK, va="center", linespacing=1.25)
    ax.text(5, 24.8, t["sub"], fontsize=11.5, color=MUTED, va="center", linespacing=1.3)
    # ladder diagram
    x0, w = 44, 34
    ax.add_patch(Rectangle((x0 - 0.6, 6), 0.9, 44, color=INK))
    ax.add_patch(Rectangle((x0 + w - 0.3, 6), 0.9, 44, color=INK))
    for i, (name, desc) in enumerate(t["rungs"]):
        y = 9 + i * 10.5
        ax.add_patch(FancyBboxPatch((x0 + 1.2, y), w - 2.4, 6.4, boxstyle="round,pad=0,rounding_size=1.2",
                                    fc=RUNG_COLORS[i] if i < 3 else "#e9edf2", ec="none"))
        col = "white" if 0 < i < 3 else INK
        ax.text(x0 + 3, y + 4.3, name, fontsize=10.5, weight="bold", color=col, va="center")
        ax.text(x0 + 3, y + 1.9, desc, fontsize=8.8, color=col if i in (1, 2) else MUTED, va="center")
    ax.add_patch(FancyArrowPatch((x0 - 4, 9), (x0 - 4, 49), arrowstyle="-|>", mutation_scale=14, color=GRAY, lw=1.4))
    ax.text(x0 - 5.6, 29, t["cost"], fontsize=9, color=GRAY, rotation=90, va="center", ha="center")
    # memory card
    mx, my = 83, 22
    ax.add_patch(FancyBboxPatch((mx, my), 23, 21, boxstyle="round,pad=0,rounding_size=1.4", fc="white", ec=LINE, lw=1.2))
    ax.text(mx + 2, my + 18, t["mem"], fontsize=11, weight="bold", color=INK)
    ax.text(mx + 2, my + 15.6, "scrapladder.json", fontsize=8, color=MUTED, family="monospace")
    for j, (dom, meth) in enumerate(t["memrows"]):
        yy = my + 11.5 - j * 3.8
        ax.text(mx + 2, yy, dom, fontsize=8.6, color=INK)
        ax.text(mx + 21, yy, meth, fontsize=8.6, color=AQUA, weight="bold", ha="right")
    ax.add_patch(FancyArrowPatch((x0 + w + 1.5, 26), (mx - 0.5, 30), arrowstyle="-|>", mutation_scale=12,
                                 color=GRAY, lw=1.2, connectionstyle="arc3,rad=-0.2", linestyle=(0, (3, 2))))
    ax.text(5, 3.2, t["foot"], fontsize=8.6, color=MUTED)
    ax.text(105, 3.2, "github.com/CaiqueDourado", fontsize=8.6, color=MUTED, ha="right")
    fig.savefig(OUT / f"cover{suf}.png", facecolor=BG)
    plt.close(fig)

# logo (square, transparent-free light background) for social preview / avatar
fig = plt.figure(figsize=(4, 4), dpi=128); fig.patch.set_facecolor(BG)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 40); ax.set_ylim(0, 40); ax.axis("off")
ladder_mark(ax, 13, 8, 14, 24, lw=14)
fig.savefig(OUT / "logo.png", facecolor=BG); plt.close(fig)
print("ok")
