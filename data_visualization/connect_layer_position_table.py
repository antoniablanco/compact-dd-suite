import glob
import os
import re
import shutil
from datetime import datetime

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.backends.backend_pdf as pdf_backend
from matplotlib.font_manager import FontProperties


def archive_existing(folder):
    """Create 'folder' and its 'deprecated/' and move the existing outputs there
    before generating new ones, so old versions do not pile up in the root."""
    deprecated = os.path.join(folder, "deprecated")
    os.makedirs(deprecated, exist_ok=True)
    own = re.compile(r"^connect_layer_position_\d{8}_\d{6}\.pdf$")
    for path in glob.glob(os.path.join(folder, "*")):
        if os.path.isfile(path) and own.match(os.path.basename(path)):
            shutil.move(path, os.path.join(deprecated, os.path.basename(path)))


BASE     = os.path.dirname(os.path.abspath(__file__))
SEMI_DIR = os.path.join(BASE, "data", "python", "semi")
OUT_DIR  = os.path.join(BASE, "tables", "connect_layer_position")
OUT_PATH = os.path.join(OUT_DIR, f"connect_layer_position_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")

archive_existing(OUT_DIR)


def _file_datetime(path):
    """Datetime of a '..._DD_MM_YYYY_HH-MM-SS.csv' name: the day comes first, so
    the names cannot be sorted as strings."""
    m = re.search(r"(\d{2}_\d{2}_\d{4}_\d{2}-\d{2}-\d{2})", os.path.basename(path))
    if not m:
        return datetime.fromtimestamp(os.path.getmtime(path))
    return datetime.strptime(m.group(1), "%d_%m_%Y_%H-%M-%S")


# ── Configuration ──────────────────────────────────────────────────────────────
PROBLEM_ORDER = ["Knapsack", "Independent Set", "Set Cover", "SOC Knapsack", "Sequencing"]

KNAP_PI = {"1": "knapPI_1 (uncorr.)", "2": "knapPI_2 (weakly corr.)", "3": "knapPI_3 (strongly corr.)"}


def instance_family(problem, name):
    """Instance type inside each problem: the generator / benchmark family, or the
    parameter that moves k* (density for Set Cover, items for SOC Knapsack)."""
    if problem == "Knapsack":
        m = re.match(r"knapPI_(\d)_", name)
        return KNAP_PI[m.group(1)] if m else "l-d (f*_l-d)"
    if problem == "Independent Set":
        return re.match(r"\D+", name).group(0).rstrip("_-")
    if problem == "Set Cover":
        return "d = " + re.search(r"_d([\d.]+)_", name).group(1)
    if problem == "SOC Knapsack":
        return "n = " + re.search(r"_n(\d+)m", name).group(1)
    if problem == "Sequencing":
        m = re.search(r"atsp_([a-z]+\d*)_", name)
        return m.group(1) if m else "n = " + re.search(r"_n(\d+)_", name).group(1)
    return "—"


def family_sort_key(fam):
    """Numeric families (d = 0.25, n = 100) in numeric order, the rest alphabetical."""
    m = re.search(r"([\d.]+)$", fam)
    return (0, float(m.group(1)), fam) if m and "=" in fam else (1, 0.0, fam.lower())


# ── Loading ────────────────────────────────────────────────────────────────────
files = glob.glob(os.path.join(SEMI_DIR, "connect_layers_python_*.csv"))
if not files:
    raise FileNotFoundError(f"Could not find 'connect_layers_python_*.csv' in {SEMI_DIR}")
src_path = max(files, key=_file_datetime)
src = os.path.basename(src_path)
print(f"Loading k*:\n  {src_path}")

df = pd.read_csv(src_path, dtype=str)
df = df[df["File_name"] != "File_name"].copy()
for col in ["Variables number", "K Default", "K Opt", "Nodes Default", "Nodes Opt"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")
df = df.drop_duplicates(subset=["File_name", "Problem type"], keep="last")
df["Family"] = [instance_family(p, f) for p, f in zip(df["Problem type"], df["File_name"])]
df["rel"]    = df["K Opt"] / df["Variables number"]
print(f"  ({len(df)} instances)")


# ── Summary ────────────────────────────────────────────────────────────────────
def geo_ratio(num, den):
    ok = (num > 0) & (den > 0)
    return float(np.exp(np.mean(np.log(num[ok] / den[ok])))) if ok.any() else np.nan


def summarize(sub):
    """Where k* falls relative to 1, ceil(N/2) (= K Default) and N."""
    k, n, half = sub["K Opt"], sub["Variables number"], sub["K Default"]
    return {
        "n_inst": len(sub), "N": n.mean(), "k": k.mean(),
        "rel_mean": sub["rel"].mean(), "rel_median": sub["rel"].median(),
        "rel_min": sub["rel"].min(), "rel_max": sub["rel"].max(),
        "buckets": (int((k == 1).sum()),
                    int(((k > 1) & (k < half)).sum()),
                    int((k == half).sum()),
                    int(((k > half) & (k < n)).sum()),
                    int((k == n).sum())),
        "gain": geo_ratio(sub["Nodes Opt"], sub["Nodes Default"]),
    }


rows = []
for p in PROBLEM_ORDER:
    dp = df[df["Problem type"] == p]
    if dp.empty:
        continue
    for fam in sorted(dp["Family"].unique(), key=family_sort_key):
        rows.append({"problem": p, "family": fam, **summarize(dp[dp["Family"] == fam])})
    rows.append({"problem": p, "family": "All", **summarize(dp)})


# ── Rendering ──────────────────────────────────────────────────────────────────
INK, MUTED, GRID = "#1f2328", "#6e7781", "#d0d7de"
DOT, MEAN        = "#8fb3de", "#1f4e8c"   # one hue: light dots, dark mean

FN  = FontProperties(family="monospace", size=7)
FNB = FontProperties(family="monospace", size=7, weight="bold")
FH  = FontProperties(family="monospace", size=7.5, weight="bold")


def plot_page():
    """One row per (problem, family): every instance's k*/N as a dot, the mean as a
    tick. Reference lines at 1/N ≈ 0, 0.5 (default) and 1 (= MDD)."""
    fam_rows = [r for r in rows if r["family"] != "All"]
    labels, ys, y = [], [], 0.0
    sep = []
    prev = None
    for r in fam_rows:
        if prev is not None and r["problem"] != prev:
            y += 0.6
            sep.append(y - 0.8)
        labels.append(f"{r['problem']} · {r['family']}")
        ys.append(y)
        y += 1
        prev = r["problem"]

    fig, ax = plt.subplots(figsize=(8.5, 0.24 * len(fam_rows) + 1.6))
    rng = np.random.default_rng(0)
    for r, yy in zip(fam_rows, ys):
        sub = df[(df["Problem type"] == r["problem"]) & (df["Family"] == r["family"])]
        jitter = rng.uniform(-0.18, 0.18, len(sub))
        ax.scatter(sub["rel"], yy + jitter, s=12, color=DOT, edgecolor="white",
                   linewidth=0.5, zorder=2)
        ax.plot([r["rel_mean"]] * 2, [yy - 0.35, yy + 0.35], color=MEAN, lw=2,
                solid_capstyle="round", zorder=3)
    for x, txt in [(0.5, "ceil(N/2) default"), (1.0, "k = N (MDD)")]:
        ax.axvline(x, color=MUTED, lw=0.8, ls="--", zorder=1)
        ax.text(x, -1.1, txt, ha="center", va="bottom", color=MUTED, fontsize=7)
    for s in sep:
        ax.axhline(s, color=GRID, lw=0.6)
    ax.set_yticks(ys)
    ax.set_yticklabels(labels, fontsize=7, color=INK)
    ax.set_ylim(max(ys) + 0.8, -1.3)
    ax.set_xlim(-0.02, 1.04)
    ax.set_xlabel("k* / N   (k* = 1 → whole DD built backward, k* = N → plain MDD)",
                  fontsize=8, color=INK)
    ax.tick_params(axis="x", labelsize=7, colors=MUTED)
    ax.grid(axis="x", color=GRID, lw=0.5)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.set_title(f"Position of the optimal connect layer k* — dots: instances, bar: mean\n{src}",
                 loc="left", fontsize=8.5, color=INK)
    plt.tight_layout()
    return fig


def fmt(v, d=2):
    return "—" if pd.isna(v) else f"{v:.{d}f}"


HEADERS = ["Problem", "Family", "#", "N", "k*",
           "k*/N mean", "median", "min–max",
           "k=1", "<N/2", "=N/2", ">N/2", "k=N", "nodes k*/N/2"]
WIDTHS  = [1.35, 1.75, 0.4, 0.6, 0.6,
           0.85, 0.65, 1.0,
           0.45, 0.5, 0.5, 0.5, 0.45, 1.05]

table = []
for r in rows:
    table.append([r["problem"], r["family"], str(r["n_inst"]), fmt(r["N"], 1), fmt(r["k"], 1),
                  fmt(r["rel_mean"]), fmt(r["rel_median"]),
                  f"{fmt(r['rel_min'])}–{fmt(r['rel_max'])}",
                  *[str(b) for b in r["buckets"]],
                  "—" if pd.isna(r["gain"]) else f"{r['gain']:.2f}×"])


def table_page():
    row_h, hdr_h = 0.26, 0.4
    total_w = sum(WIDTHS)
    total_h = hdr_h + len(table) * row_h
    fig, ax = plt.subplots(figsize=(total_w + 0.4, total_h + 1.2))
    ax.axis("off")
    ax.set_xlim(0, total_w)
    ax.set_ylim(0, total_h)
    xs = np.concatenate([[0], np.cumsum(WIDTHS)])

    for j, h in enumerate(HEADERS):
        ax.text(xs[j] + WIDTHS[j] / 2, total_h - hdr_h / 2, h, ha="center", va="center",
                fontproperties=FH)
    ax.plot([0, total_w], [total_h - hdr_h] * 2, color="black", lw=0.8)

    prev_problem = None
    for i, (line, r) in enumerate(zip(table, rows)):
        y = total_h - hdr_h - (i + 0.5) * row_h
        if prev_problem is not None and r["problem"] != prev_problem:
            ax.plot([0, total_w], [y + row_h / 2] * 2, color="black", lw=0.5)
        if r["family"] == "All":
            ax.add_patch(plt.Rectangle((0, y - row_h / 2), total_w, row_h,
                                       color="#f0f0f0", zorder=0))
        # The bucket holding most instances, so the typical position reads at a glance.
        top = 8 + int(np.argmax(r["buckets"]))
        ax.add_patch(plt.Rectangle((xs[top], y - row_h / 2), WIDTHS[top], row_h,
                                   color="#cfe0f3", zorder=0))
        bold = r["family"] == "All"
        for j, txt in enumerate(line):
            shown = txt if (j > 0 or r["problem"] != prev_problem) else ""
            ax.text(xs[j] + WIDTHS[j] / 2, y, shown, ha="center", va="center",
                    fontproperties=FNB if (j == 0 or bold) else FN)
        prev_problem = r["problem"]

    for x in (xs[5], xs[8], xs[13]):
        ax.plot([x, x], [0, total_h], color="black", lw=0.6)

    ax.set_title(
        "Optimal connect layer k* per problem and instance family — DD Python\n"
        f"Source: {src}\n"
        "k* minimizes the exact sMDD size before reduction (Σ_{j<k} forward + Σ_{j≥k} backward widths).  "
        "N/2 = ceil(N/2), the default.\n"
        "k=1 / <N/2 / =N/2 / >N/2 / k=N: number of instances in each position (shaded: the most common).  "
        "'nodes k*/N/2': geometric mean of nodes(k*) / nodes(ceil(N/2)).",
        loc="left", fontproperties=FontProperties(family="monospace", size=7.5), pad=8)
    plt.tight_layout()
    return fig


with pdf_backend.PdfPages(OUT_PATH) as pdf:
    for fig in (plot_page(), table_page()):
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)


# ── Console ────────────────────────────────────────────────────────────────────
print(f"\nWriting PDF -> {OUT_PATH}\n")
widths = [max(len(HEADERS[j]), *(len(l[j]) for l in table)) for j in range(len(HEADERS))]
print("  ".join(h.ljust(w) for h, w in zip(HEADERS, widths)))
for line in table:
    print("  ".join(c.ljust(w) for c, w in zip(line, widths)))

print("\nDone!")
