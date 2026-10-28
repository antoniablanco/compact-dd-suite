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
    before generating new ones, so old versions do not pile up in the root. Only
    this script's own outputs are moved: the frozen pre-hooks table is kept."""
    deprecated = os.path.join(folder, "deprecated")
    os.makedirs(deprecated, exist_ok=True)
    own = re.compile(r"^smdd_vs_mdd_\d{8}_\d{6}\.pdf$")
    for path in glob.glob(os.path.join(folder, "*")):
        if os.path.isfile(path) and own.match(os.path.basename(path)):
            shutil.move(path, os.path.join(deprecated, os.path.basename(path)))


BASE      = os.path.dirname(os.path.abspath(__file__))
MDD_DIR   = os.path.join(BASE, "data", "python", "original")
SEMI_DIR  = os.path.join(BASE, "data", "python", "semi")
OUT_DIR   = os.path.join(BASE, "tables", "smdd_vs_mdd_table")
OUT_PATH  = os.path.join(OUT_DIR, f"smdd_vs_mdd_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")

archive_existing(OUT_DIR)


def _file_datetime(path):
    """Datetime of a '..._DD_MM_YYYY_HH-MM-SS.csv' name: the day comes first, so
    the names cannot be sorted as strings."""
    m = re.search(r"(\d{2}_\d{2}_\d{4}_\d{2}-\d{2}-\d{2})", os.path.basename(path))
    if not m:
        return datetime.fromtimestamp(os.path.getmtime(path))
    return datetime.strptime(m.group(1), "%d_%m_%Y_%H-%M-%S")


def read_results(path):
    """CSV with the cluster jobs concatenated: the repeated header lines are
    dropped and the numeric columns parsed."""
    df = pd.read_csv(path, dtype=str)
    df.columns = df.columns.str.strip()
    df = df[df["File_name"] != "File_name"].copy()
    for col in df.columns:
        df[col] = df[col].str.strip()
    for col in ["Max Width", "Optimization Value", "Construction Time", "Solution Time",
                "Number Node", "Number Arcs"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["Reduce Time"] = pd.to_numeric(df["Reduce Time"], errors="coerce").fillna(0.0)
    df["Is Reduced"]  = df["Is Reduced"].str.lower() == "true"
    df["Sort"]        = df["Sort"].str.lower() == "true"
    df.attrs["source_datetime"] = _file_datetime(path)
    print(f"  {path}  ({len(df)} rows)")
    return df


# ── Configuration ──────────────────────────────────────────────────────────────
PROBLEM_ORDER = ["Knapsack", "Independent Set", "Set Cover", "SOC Knapsack", "Sequencing"]
DD_ORDER      = ["Exact", "Restricted", "RelaxPriority"]

# Restricted gives a feasible (primal) solution, relaxed a bound: 'better' depends
# on the role and on the objective sense.
DD_ROLE = {"Restricted": "restricted", "RelaxPriority": "relaxed"}

KEY = ["File_name", "Problem type", "DD Type", "Max Width", "Is Reduced"]

# Times are written with 4 decimals: the floor avoids 0/0 in the time ratio.
TIME_FLOOR = 1e-4
REL_TOL    = 1e-6


# ── Loading ────────────────────────────────────────────────────────────────────
def load_latest(folder, pattern, exclude=()):
    files = [f for f in glob.glob(os.path.join(folder, pattern))
             if not any(e in os.path.basename(f) for e in exclude)]
    if not files:
        raise FileNotFoundError(f"Could not find '{pattern}' in {folder}")
    latest = max(files, key=_file_datetime)
    return read_results(latest), os.path.basename(latest)


print("Loading MDD (baseline):")
df_mdd, mdd_src = load_latest(MDD_DIR, "results_python_*.csv", exclude=("grouping", "gurobi"))

# Only the newest general run: the dedicated exact files (results_semi_exact_*)
# are not merged in, so every row comes from one code version.
print("Loading sMDD:")
df_semi, semi_src = load_latest(SEMI_DIR, "results_python_semi_*.csv")

df_mdd  = df_mdd[df_mdd["Sort"]].drop_duplicates(subset=KEY, keep="last")
df_semi = df_semi[df_semi["Sort"]].drop_duplicates(subset=KEY, keep="last")

for d in (df_mdd, df_semi):
    d["Time"] = (d["Construction Time"] + d["Reduce Time"]).clip(lower=TIME_FLOOR)

COLS  = ["Objective Type", "Time", "Solution Time", "Number Node", "Number Arcs", "Optimization Value"]
pairs = df_mdd[KEY + COLS].merge(df_semi[KEY + COLS + ["Connect Layer"]],
                                 on=KEY, suffixes=("_mdd", "_semi"))
print(f"\nPaired rows (same instance, DD type, width and reduction): {len(pairs)}")


# ── Comparison ─────────────────────────────────────────────────────────────────
def compare_bound(row):
    """+1 when the sMDD bound is better, -1 when worse, 0 when equal."""
    a, b = row["Optimization Value_mdd"], row["Optimization Value_semi"]
    if (np.isinf(a) and np.isinf(b) and a == b) or abs(a - b) <= REL_TOL * (1 + abs(a)):
        return 0
    role = DD_ROLE.get(row["DD Type"])
    if role is None:
        return 0
    higher_better = (role == "restricted") == (row["Objective Type_mdd"].lower() == "max")
    return 1 if (b > a) == higher_better else -1


pairs["_cmp"] = pairs.apply(compare_bound, axis=1)


def geo_ratio(num, den):
    """Geometric mean of the per-row ratios: the instances span several orders of
    magnitude, so a ratio of means would only reflect the largest ones."""
    ok = (num > 0) & (den > 0)
    return float(np.exp(np.mean(np.log(num[ok] / den[ok])))) if ok.any() else np.nan


rows = []
for p in PROBLEM_ORDER:
    for dd in DD_ORDER:
        for red in (False, True):
            sub = pairs[(pairs["Problem type"] == p) & (pairs["DD Type"] == dd)
                        & (pairs["Is Reduced"] == red)]
            if sub.empty:
                continue
            finite = sub[np.isfinite(sub["Optimization Value_mdd"])
                         & np.isfinite(sub["Optimization Value_semi"])]
            rows.append({
                "problem": p, "dd": dd, "reduced": red, "n": len(sub),
                "time":  (sub["Time_mdd"].mean(), sub["Time_semi"].mean(),
                          geo_ratio(sub["Time_semi"], sub["Time_mdd"])),
                "solve": (sub["Solution Time_mdd"].mean(), sub["Solution Time_semi"].mean(),
                          geo_ratio(sub["Solution Time_semi"], sub["Solution Time_mdd"])),
                "nodes": (sub["Number Node_mdd"].mean(), sub["Number Node_semi"].mean(),
                          geo_ratio(sub["Number Node_semi"], sub["Number Node_mdd"])),
                "arcs":  (sub["Number Arcs_mdd"].mean(), sub["Number Arcs_semi"].mean(),
                          geo_ratio(sub["Number Arcs_semi"], sub["Number Arcs_mdd"])),
                "bound": (finite["Optimization Value_mdd"].mean(),
                          finite["Optimization Value_semi"].mean(),
                          len(sub) - len(finite)),
                "wtl":   (int((sub["_cmp"] > 0).sum()), int((sub["_cmp"] == 0).sum()),
                          int((sub["_cmp"] < 0).sum())),
            })


# ── Rendering ──────────────────────────────────────────────────────────────────
def fmt_num(v):
    if pd.isna(v):
        return "—"
    av = abs(v)
    if av >= 1e6:
        return f"{v:.3g}"
    if av >= 100:
        return f"{v:,.0f}"
    if av >= 1:
        return f"{v:.2f}"
    return f"{v:.4f}"


def fmt_ratio(r):
    return "—" if pd.isna(r) else f"{r:.2f}×"


HEADERS = ["Problem", "DD", "Red.", "N",
           "Time MDD", "Time sMDD", "ratio",
           "Solve MDD", "Solve sMDD", "ratio",
           "Nodes MDD", "Nodes sMDD", "ratio",
           "Arcs MDD", "Arcs sMDD", "ratio",
           "Bound MDD", "Bound sMDD", "non-fin.",
           "sMDD +/=/-"]
WIDTHS  = [1.35, 1.15, 0.45, 0.5,
           0.9, 0.9, 0.6,
           0.9, 0.9, 0.6,
           0.95, 0.95, 0.6,
           0.95, 0.95, 0.6,
           0.95, 0.95, 0.6,
           1.1]

table = []
for r in rows:
    table.append([r["problem"], r["dd"], "yes" if r["reduced"] else "no", str(r["n"]),
                  fmt_num(r["time"][0]),  fmt_num(r["time"][1]),  fmt_ratio(r["time"][2]),
                  fmt_num(r["solve"][0]), fmt_num(r["solve"][1]), fmt_ratio(r["solve"][2]),
                  fmt_num(r["nodes"][0]), fmt_num(r["nodes"][1]), fmt_ratio(r["nodes"][2]),
                  fmt_num(r["arcs"][0]),  fmt_num(r["arcs"][1]),  fmt_ratio(r["arcs"][2]),
                  fmt_num(r["bound"][0]), fmt_num(r["bound"][1]), str(r["bound"][2]),
                  "{}/{}/{}".format(*r["wtl"])])

FN  = FontProperties(family="monospace", size=7)
FNB = FontProperties(family="monospace", size=7, weight="bold")
FH  = FontProperties(family="monospace", size=7.5, weight="bold")
ROW_H, HDR_H = 0.26, 0.4


def ratio_color(r):
    """Green when the sMDD is smaller/faster, red when it is larger/slower."""
    if pd.isna(r):
        return "white"
    if r <= 0.95:
        return "#c8e6c9"
    if r < 1.05:
        return "white"
    if r < 2:
        return "#ffe0b2"
    return "#ffcdd2"


def wtl_color(w, t, l):
    if w > l:
        return "#c8e6c9"
    if l > w:
        return "#ffcdd2"
    return "white"


total_w = sum(WIDTHS)
total_h = HDR_H + len(table) * ROW_H
fig, ax = plt.subplots(figsize=(total_w + 0.4, total_h + 1.4))
ax.axis("off")
ax.set_xlim(0, total_w)
ax.set_ylim(0, total_h)
xs = np.concatenate([[0], np.cumsum(WIDTHS)])

for j, h in enumerate(HEADERS):
    ax.text(xs[j] + WIDTHS[j] / 2, total_h - HDR_H / 2, h, ha="center", va="center",
            fontproperties=FH)
ax.plot([0, total_w], [total_h - HDR_H] * 2, color="black", lw=0.8)

RATIO_COLS = {6: "time", 9: "solve", 12: "nodes", 15: "arcs"}
prev_problem = None
for i, (line, r) in enumerate(zip(table, rows)):
    y = total_h - HDR_H - (i + 0.5) * ROW_H
    if prev_problem is not None and r["problem"] != prev_problem:
        ax.plot([0, total_w], [y + ROW_H / 2] * 2, color="black", lw=0.5)
    for j, txt in enumerate(line):
        color = None
        if j in RATIO_COLS:
            color = ratio_color(r[RATIO_COLS[j]][2])
        elif j == len(line) - 1:
            color = wtl_color(*r["wtl"])
        if color:
            ax.add_patch(plt.Rectangle((xs[j], y - ROW_H / 2), WIDTHS[j], ROW_H,
                                       color=color, zorder=0))
        shown = txt if (j > 0 or r["problem"] != prev_problem) else ""
        ax.text(xs[j] + WIDTHS[j] / 2, y, shown, ha="center", va="center",
                fontproperties=FNB if j == 0 else FN)
    prev_problem = r["problem"]

for x in (xs[4], xs[7], xs[10], xs[13], xs[16], xs[19]):
    ax.plot([x, x], [0, total_h], color="black", lw=0.6)

ax.set_title(
    "sMDD vs MDD — DD Python, paired rows (same instance, DD type, width and reduction)"
    "\n"
    f"MDD: {mdd_src}   |   sMDD: {semi_src}\n"
    "Columns are means over the paired rows; 'ratio' is the geometric mean of sMDD/MDD per row. "
    "Time = construction + reduction; Solve = longest/shortest path over the built diagram.\n"
    "Bound means skip rows where either value is ±inf (empty restricted / unreachable "
    "terminal), counted in 'non-fin.'.  "
    "'sMDD +/=/-': rows where the sMDD bound is better / equal / worse.",
    loc="left", fontproperties=FontProperties(family="monospace", size=7.5), pad=8)

plt.tight_layout()
with pdf_backend.PdfPages(OUT_PATH) as pdf:
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


# ── Console ────────────────────────────────────────────────────────────────────
print(f"\nWriting PDF -> {OUT_PATH}\n")
widths = [max(len(HEADERS[j]), *(len(l[j]) for l in table)) for j in range(len(HEADERS))]
print("  ".join(h.ljust(w) for h, w in zip(HEADERS, widths)))
for line in table:
    print("  ".join(c.ljust(w) for c, w in zip(line, widths)))

print("\nDone!")
