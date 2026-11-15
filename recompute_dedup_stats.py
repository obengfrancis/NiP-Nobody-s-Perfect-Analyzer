#!/usr/bin/env python3
"""
recompute_dedup_stats.py

Deduplicates the NiP analyzer output to one row per repository 
Usage
-----
    python3 recompute_dedup_stats.py nip_analyzer_output.csv \
        [--mined mined_repositories.csv] [--out results_dedup]

Inputs
------
nip_analyzer_output.csv : raw NiP output (one row per analyzed URL entry; may
                          contain repeated repo_url rows).
mined_repositories.csv  : optional; source repository list (Baravkar et al.,
                          one row per repository-RapidAPI-host pair). Used only
                          for the Table 3 pipeline counts.

Deduplication rule
------------------
One row per repo_url. If a URL has rows with parser success > 0 and = 0, a row
with parser success > 0 is kept; otherwise the first occurrence (original file
order) is kept. A missing "Exception Type" on a parsed row means "None".

Outputs (written to --out)
--------------------------
nip_analyzer_output_dedup.csv   deduplicated analyzer output
table3_pipeline.csv             pipeline stage counts (unique repositories)
rq1_categories.csv              category counts and percentages (Fig. 2)
table4_language_by_category.csv repository counts by language and category
fig4_signals_by_language.csv    signal prevalence (%) per single-language group
fig6_single_vs_multi.csv        signal prevalence (%), single vs multilingual
mixed_depth.csv                 advanced-pattern depth within Mixed (Fig. 3a)
mixed_patterns.csv              advanced-pattern prevalence within Mixed (Fig. 3b)
http_libcount_strata.csv        single vs multilingual signals by HTTP-library count
summary.txt                     all headline numbers in one place
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, mannwhitneyu

CATS = ["None", "Basic", "Mixed", "Advanced"]
FLAGS = ["Has Try-Catch", "Has Timeout", "Has Retry",
         "Has Circuit Breaker", "Has Backoff", "Has Status Check"]
ADV_FLAGS = ["Has Timeout", "Has Retry", "Has Circuit Breaker", "Has Backoff"]
LANG_ORDER = ["python", "java", "javascript", "typescript", "go",
              "csharp", "ruby", "kotlin", "swift"]
NO_HTTP = "None detected"


def norm_url(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().str.rstrip("/")


def deduplicate(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df["_ord"] = np.arange(len(df))
    df["_psr"] = pd.to_numeric(
        df["Parser Success Rate"].astype(str).str.rstrip("%"), errors="coerce"
    ).fillna(0.0)
    df["_ok"] = df["_psr"] > 0
    df["_url"] = norm_url(df["repo_url"])
    kept = (df.sort_values(["_url", "_ok", "_ord"], ascending=[True, False, True])
              .drop_duplicates("_url", keep="first")
              .sort_values("_ord"))
    return kept


def pct(x: float) -> float:
    return round(100.0 * x, 2)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("nip_csv", type=Path)
    ap.add_argument("--mined", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=Path("results_dedup"))
    args = ap.parse_args()
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []

    def log(s: str = "") -> None:
        print(s)
        lines.append(s)

    # Text copy preserves the original cell formatting for the deduplicated file.
    raw_text = pd.read_csv(args.nip_csv, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    raw = pd.read_csv(args.nip_csv, encoding="utf-8-sig")
    for c in FLAGS:
        raw[c] = raw[c].astype(str).str.strip().str.lower().isin(["true", "1"])

    # ---- Deduplication -------------------------------------------------
    kept = deduplicate(raw)
    raw_text.loc[kept.index].to_csv(
        out / "nip_analyzer_output_dedup.csv", index=False, encoding="utf-8-sig")

    a = kept[kept["_ok"]].copy()
    a["cat"] = a["Exception Type"].fillna("None")
    a["single"] = ~a["Languages"].astype(str).str.contains(";")
    a["lang"] = a["Languages"].where(a["single"], "Multiple")
    n = len(a)

    log("=== Deduplication ===")
    log(f"Raw analyzer rows: {len(raw):,}")
    log(f"Unique repositories in analyzer output: {len(kept):,}")
    log(f"Repositories with parser success > 0 (analyzed): {n:,}")
    log(f"Repositories with parser success = 0: {len(kept) - n:,}")
    rows_ok = raw[pd.to_numeric(raw['Parser Success Rate'].astype(str).str.rstrip('%'),
                                errors='coerce').fillna(0) > 0]
    log(f"(Raw rows with parser success > 0: {len(rows_ok):,})")

    # ---- Table 3 -------------------------------------------------------
    stages = []
    if args.mined is not None:
        mined = pd.read_csv(args.mined)
        mined_urls = set(norm_url(mined["repo_url"]))
        out_urls = set(norm_url(kept["repo_url"]))
        stages += [("Source rows (repository-service pairs, incl. repeats)", len(mined)),
                   ("Unique repositories in source list", len(mined_urls)),
                   ("Not cloned / no analyzer output", len(mined_urls - out_urls))]
    stages += [("Cloned (unique repositories with analyzer output)", len(kept)),
               ("Parser failures (0% parser success)", len(kept) - n),
               ("Analyzed (parser success > 0)", n)]
    pd.DataFrame(stages, columns=["stage", "count"]).to_csv(out / "table3_pipeline.csv", index=False)
    log("\n=== Table 3 (unique repositories) ===")
    for s, c in stages:
        log(f"{s}: {c:,}")

    # ---- RQ1 categories ---------------------------------------------------
    vc = a["cat"].value_counts().reindex(CATS, fill_value=0)
    rq1 = pd.DataFrame({"count": vc, "percent": (vc / n * 100).round(2)})
    rq1.to_csv(out / "rq1_categories.csv")
    log("\n=== RQ1 categories (Fig. 2) ===")
    for c in CATS:
        log(f"{c}: {vc[c]:,} ({pct(vc[c] / n)}%)")
    log(f"Any explicit handling: {pct(1 - vc['None'] / n)}%")
    log(f"Mixed + Advanced: {pct((vc['Mixed'] + vc['Advanced']) / n)}%")

    # ---- HTTP client detection ------------------------------------------
    has_http = a["HTTP Libraries"].astype(str).str.strip() != NO_HTTP
    libs = a.loc[has_http, "HTTP Libraries"].astype(str).str.split("; ").explode()
    log("\n=== HTTP client library detection ===")
    log(f"Repositories with detected HTTP client usage: {has_http.sum():,} ({pct(has_http.mean())}%)")
    log(f"Distinct libraries observed: {libs.nunique()}")
    log("Most frequent: " + ", ".join(f"{k} ({v:,})" for k, v in libs.value_counts().head(3).items()))

    # ---- Within-Mixed depth (Fig. 3) -------------------------------------
    m = a[a["cat"] == "Mixed"]
    depth = m[ADV_FLAGS].sum(axis=1).value_counts().reindex(range(5), fill_value=0)
    pd.DataFrame({"repos": depth, "percent": (depth / len(m) * 100).round(1)}).rename_axis(
        "advanced_types").to_csv(out / "mixed_depth.csv")
    mp = (m[ADV_FLAGS].mean() * 100).round(1)
    mp.rename("percent_of_mixed").to_csv(out / "mixed_patterns.csv")
    log("\n=== Within-Mixed (Fig. 3) ===")
    log("Depth 0-4 (%): " + " / ".join(f"{v:.1f}" for v in depth / len(m) * 100))
    log("Timeout / retry / CB / backoff (%): " + " / ".join(f"{v:.1f}" for v in mp))
    log(f"Upper bound on retry-detected Mixed repos that also show backoff: "
        f"{round(mp['Has Backoff'] / mp['Has Retry'] * 100, 1)}%")

    # ---- Table 4 and chi-square ---------------------------------------
    t4 = pd.crosstab(a["lang"], a["cat"]).reindex(columns=CATS, fill_value=0)
    t4 = t4.reindex([l for l in LANG_ORDER if l in t4.index] + ["Multiple"])
    t4.insert(0, "Total", t4.sum(axis=1))
    t4.to_csv(out / "table4_language_by_category.csv")
    single_tab = t4.drop(index="Multiple")[CATS]
    single_tab = single_tab.loc[:, single_tab.sum() > 0]
    chi2, p, dof, _ = chi2_contingency(single_tab.values)
    ns = int(single_tab.values.sum())
    V = np.sqrt(chi2 / (ns * (min(single_tab.shape) - 1)))
    log("\n=== RQ2: Table 4 and association test (single-language) ===")
    log(t4.to_string())
    log(f"chi2({dof}) = {chi2:.2f}, p = {p:.3g}, Cramer's V = {V:.3f}, n_single = {ns:,}, "
        f"n_multi = {int(t4.loc['Multiple', 'Total']):,}")
    for L in ["ruby", "kotlin", "go"]:
        if L in t4.index:
            r = t4.loc[L]
            log(f"{L}: Mixed/Advanced {pct((r['Mixed'] + r['Advanced']) / r['Total'])}%, "
                f"Basic {pct(r['Basic'] / r['Total'])}%")

    # ---- Fig. 4 -------------------------------------------------------
    f4 = (a[a["single"]].groupby("lang")[FLAGS].mean() * 100).round(1)
    f4 = f4.reindex([l for l in LANG_ORDER if l in f4.index])
    f4.to_csv(out / "fig4_signals_by_language.csv")
    log("\n=== Fig. 4: signal prevalence by language (single-language, %) ===")
    log(f4.to_string())

    # ---- Fig. 6 -------------------------------------------------------
    s_rate = a[a["single"]][FLAGS].mean() * 100
    m_rate = a[~a["single"]][FLAGS].mean() * 100
    f6 = pd.DataFrame({"single_pct": s_rate.round(1), "multi_pct": m_rate.round(1),
                       "ratio": (m_rate / s_rate).round(1)})
    f6.to_csv(out / "fig6_single_vs_multi.csv")
    log("\n=== Fig. 6: single vs multilingual (%) ===")
    log(f6.to_string())

    # ---- HTTP library count check (Section 4.4) ---------------------------
    a["lib_count"] = a["HTTP Libraries"].astype(str).apply(
        lambda x: 0 if x.strip() == NO_HTTP else len(x.split("; ")))
    u = mannwhitneyu(a.loc[~a["single"], "lib_count"], a.loc[a["single"], "lib_count"])
    log("\n=== HTTP library count as complexity proxy ===")
    log(f"Median library count: multilingual {a.loc[~a['single'], 'lib_count'].median():.0f}, "
        f"single-language {a.loc[a['single'], 'lib_count'].median():.0f}; "
        f"Mann-Whitney U p = {u.pvalue:.3g}")
    a["lib_group"] = pd.cut(a["lib_count"], [-1, 1, 3, np.inf], labels=["0-1", "2-3", "4+"])
    rows = []
    for g, x in a.groupby("lib_group", observed=True):
        for grp_name, sub in (("single", x[x["single"]]), ("multi", x[~x["single"]])):
            rows.append({"lib_group": g, "group": grp_name, "n": len(sub),
                         **{c: round(sub[c].mean() * 100, 1) for c in FLAGS}})
    strata = pd.DataFrame(rows)
    strata.to_csv(out / "http_libcount_strata.csv", index=False)
    log(strata.to_string(index=False))

    (out / "summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nAll outputs written to {out.resolve()}")


if __name__ == "__main__":
    main()
