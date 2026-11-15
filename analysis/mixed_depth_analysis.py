#!/usr/bin/env python3
"""
mixed_depth_analysis.py

Within-Mixed advanced-pattern analysis (paper Fig. 3).

  (a) Advanced pattern depth: number of distinct advanced pattern types
      (timeout, retry, circuit breaker, backoff) detected per Mixed repository.
  (b) Prevalence of each advanced pattern type within Mixed repositories.

Usage:
    python3 mixed_depth_analysis.py [nip_analyzer_output.csv]

Input: analyzer output (deduplicated, one row per repository). Repositories
with 0% parser success are excluded; a missing Exception Type means "None".

Outputs:
    mixed_depth_figure.pdf / .png   two-panel figure
    mixed_depth.csv                 depth counts and percentages
    mixed_patterns.csv              per-pattern counts and percentages
    mixed_depth_summary.txt         numbers for the paper text
"""
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

SRC = sys.argv[1] if len(sys.argv) > 1 else "nip_analyzer_output.csv"

ADVANCED = [("Has Timeout", "Timeout"), ("Has Retry", "Retry"),
            ("Has Circuit Breaker", "Circuit\nBreaker"), ("Has Backoff", "Backoff")]
DEPTH_LABELS = ["0\n(edge case)", "1\n(shallow)", "2\n(moderate)", "3\n(broad)", "4\n(comprehensive)"]
DEPTH_COLORS = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#1a1a2e"]
PATTERN_COLORS = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12"]


def load_mixed(path: str) -> tuple[pd.DataFrame, int]:
    df = pd.read_csv(path, encoding="utf-8-sig")
    psr = pd.to_numeric(df["Parser Success Rate"].astype(str).str.rstrip("%"), errors="coerce").fillna(0)
    df = df[psr > 0].copy()
    df["Exception Type"] = df["Exception Type"].fillna("None")
    if df["repo_url"].duplicated().any():
        print(f"WARNING: {df['repo_url'].duplicated().sum()} repeated repo_url rows; "
              "run on the deduplicated CSV.")
    for col, _ in ADVANCED:
        df[col] = df[col].astype(str).str.strip().str.lower().isin(["true", "1"])
    return df[df["Exception Type"] == "Mixed"].copy(), len(df)


def main() -> None:
    mixed, n_analyzed = load_mixed(SRC)
    n = len(mixed)
    cols = [c for c, _ in ADVANCED]

    depth = mixed[cols].sum(axis=1).value_counts().reindex(range(5), fill_value=0)
    depth_pct = depth / n * 100
    pd.DataFrame({"advanced_types": range(5), "repositories": depth.values,
                  "percent": depth_pct.round(1).values}).to_csv("mixed_depth.csv", index=False)

    counts = mixed[cols].sum()
    prev = counts / n * 100
    pd.DataFrame({"pattern": [lbl.replace("\n", " ") for _, lbl in ADVANCED],
                  "repositories": counts.values, "percent": prev.round(1).values}
                 ).to_csv("mixed_patterns.csv", index=False)

    # ---- Figure --------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.2))

    bars = ax1.bar(range(5), depth.values, color=DEPTH_COLORS, edgecolor="black", linewidth=0.8)
    for b, p in zip(bars, depth_pct):
        ax1.text(b.get_x() + b.get_width() / 2, b.get_height() + n * 0.01, f"{p:.1f}%",
                 ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax1.set_xticks(range(5))
    ax1.set_xticklabels(DEPTH_LABELS, fontsize=9)
    ax1.set_xlabel("Number of advanced pattern types detected", fontsize=11)
    ax1.set_ylabel("Number of Mixed repositories", fontsize=11)
    ax1.set_title("(a) Advanced pattern depth in Mixed repos", fontsize=12)
    ax1.set_ylim(0, depth.max() * 1.18)
    ax1.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
    ax1.grid(axis="y", linestyle=":", alpha=0.6)
    ax1.set_axisbelow(True)
    ax1.annotate(f"{depth_pct[1]:.1f}% of Mixed repos\nhave only 1 advanced\npattern type",
                 xy=(1, depth[1]), xytext=(2.15, depth.max() * 1.02),
                 fontsize=9, color="#1f4e79",
                 bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#1f4e79"),
                 arrowprops=dict(arrowstyle="-", color="#1f4e79"))
    handles = [plt.Rectangle((0, 0), 1, 1, fc=c, ec="black") for c in DEPTH_COLORS]
    ax1.legend(handles, [f"Depth {i}" for i in range(5)], fontsize=8, loc="upper right")

    labels = [lbl for _, lbl in ADVANCED]
    y = range(len(labels))[::-1]
    hb = ax2.barh(list(y), prev.values, color=PATTERN_COLORS, edgecolor="black", linewidth=0.8)
    for b, p in zip(hb, prev.values):
        ax2.text(b.get_width() + 1, b.get_y() + b.get_height() / 2, f"{p:.1f}%",
                 va="center", fontsize=10, fontweight="bold")
    ax2.set_yticks(list(y))
    ax2.set_yticklabels(labels, fontsize=10)
    ax2.set_xlim(0, 100)
    ax2.set_xlabel("Prevalence within Mixed repositories (%)", fontsize=11)
    ax2.set_title("(b) Which patterns appear in Mixed repos", fontsize=12)
    ax2.grid(axis="x", linestyle=":", alpha=0.6)
    ax2.set_axisbelow(True)

    plt.tight_layout()
    plt.savefig("mixed_depth_figure.pdf", dpi=300, bbox_inches="tight")
    plt.savefig("mixed_depth_figure.png", dpi=300, bbox_inches="tight")
    plt.close()

    # ---- Summary ------------------------------------------------------
    t, r = prev["Has Timeout"], prev["Has Retry"]
    cb, bo = prev["Has Circuit Breaker"], prev["Has Backoff"]
    lines = [
        f"Input: {SRC}",
        f"Analyzed repositories (parser success > 0): {n_analyzed:,}",
        f"Mixed repositories: {n:,} ({n / n_analyzed * 100:.2f}%)",
        "",
        "Advanced pattern depth within Mixed:",
        *[f"  {i} types: {depth[i]:,} ({depth_pct[i]:.1f}%)" for i in range(5)],
        "",
        "Pattern prevalence within Mixed:",
        f"  Timeout {t:.1f}%, Retry {r:.1f}%, Circuit breaker {cb:.1f}%, Backoff {bo:.1f}%",
        f"  At most {bo / r * 100:.1f}% of retry-detected Mixed repos can also show backoff "
        f"(backoff {bo:.1f}% / retry {r:.1f}%).",
    ]
    if depth[0]:
        lines += ["", f"Note: {depth[0]:,} Mixed repositories have no advanced flag "
                      "(category and flags come from different detection paths)."]
    text = "\n".join(lines)
    open("mixed_depth_summary.txt", "w", encoding="utf-8").write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
