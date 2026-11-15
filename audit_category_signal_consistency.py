#!/usr/bin/env python3
"""
Stage-2 NiP classification consistency audit.

Purpose
-------
Investigate contradictions between repository-level `Exception Type` and the
exported signal flags, especially:
  - Mixed + advanced depth 0
  - Basic + >=1 advanced signal
  - Advanced + advanced depth 0

Run from the NiP project root:

    python3 audit_category_signal_consistency.py

Optional:
    python3 audit_category_signal_consistency.py --csv "Exception_Handling _Analysis_Output /analyzed_repositories.csv"
    python3 audit_category_signal_consistency.py --source WebServFH.py

Outputs:
    analysis/category_signal_consistency/
        category_depth_crosstab.csv
        category_reconstruction_crosstab.csv   (if basic columns are found)
        category_mismatches.csv                (if reconstructable)
        source_logic_contexts.txt
        audit_summary.json
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

TRUE = {"1","true","t","yes","y","on","present","detected"}
FALSE = {"0","false","f","no","n","off","absent","none","","nan","null","na","n/a"}

CATEGORY_NAMES = ["None", "Basic", "Advanced", "Mixed"]

CATEGORY_CANDIDATES = [
    "Exception Type", "exception_type", "category", "strategy_category",
    "handling_category", "fault_handling_category", "classification", "label"
]
REPO_CANDIDATES = ["repo_url","repository_url","url","repo","repository","full_name","name"]

# Exact/common exported names first; fuzzy matching below supplements them.
ADVANCED_ALIASES = {
    "timeout": ["Has Timeout","timeout","has_timeout","timeout_detected","uses_timeout"],
    "retry": ["Has Retry","retry","has_retry","retry_detected","uses_retry"],
    "backoff": ["Has Backoff","backoff","exponential_backoff","has_backoff","backoff_detected"],
    "circuit_breaker": [
        "Has Circuit Breaker","circuit_breaker","circuitbreaker","has_circuit_breaker",
        "circuit_breaker_detected"
    ],
}

BASIC_ALIASES = {
    "try_catch": [
        "Has Try Catch","Has Try/Catch","Has Try-Catch","Has Exception Handling",
        "try_catch","trycatch","has_try_catch","exception_handling",
        "has_exception_handling","has_exception_handler","try_except","try_rescue"
    ],
    "status_error_check": [
        "Has Status Check","Has Error Check","Has Status/Error Check","Has HTTP Error Check",
        "status_check","error_check","status_error_check","http_error_check",
        "has_status_check","has_error_check","raise_for_status"
    ],
}

SKIP_DIRS = {".git","node_modules","target","build","dist",".venv","venv","env","__pycache__"}

def norm(s: str) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", str(s).strip().lower())).strip("_")

def parse_bool(v) -> Optional[bool]:
    if v is None:
        return None
    s = str(v).strip().lower()
    if s in TRUE:
        return True
    if s in FALSE:
        return False
    try:
        return float(s) > 0
    except Exception:
        return None

def canonical_category(v: str) -> str:
    n = norm(v)
    if "mixed" in n: return "Mixed"
    if n.startswith("advanced"): return "Advanced"
    if n.startswith("basic"): return "Basic"
    if n.startswith("none") or n in {"no_handling","no_exception_handling"}: return "None"
    return str(v).strip()

def find_col(columns: Sequence[str], candidates: Sequence[str]) -> Optional[str]:
    by_norm = {norm(c): c for c in columns}
    for x in candidates:
        if norm(x) in by_norm:
            return by_norm[norm(x)]
    return None

def fuzzy_cols(columns: Sequence[str], aliases: Sequence[str], canonical: str) -> List[str]:
    alias_norms = list(dict.fromkeys([norm(x) for x in aliases] + [norm(canonical)]))
    out = []
    for c in columns:
        n = norm(c)
        exact = n in alias_norms
        bounded = any(
            len(a) >= 4 and re.search(rf"(^|_){re.escape(a)}($|_)", n)
            for a in alias_norms
        )
        if exact or bounded:
            if not any(x in n for x in [
                "reason","rationale","description","example","keyword",
                "filename","file_path","rule_name","library_name"
            ]):
                out.append(c)
    return list(dict.fromkeys(out))

def mech_value(row: Dict[str,str], cols: Sequence[str]) -> Tuple[Optional[bool], Dict[str,object]]:
    parsed = []
    raw = {}
    for c in cols:
        b = parse_bool(row.get(c,""))
        raw[c] = row.get(c,"")
        if b is not None:
            parsed.append(b)
    if not cols or not parsed:
        return None, raw
    return any(parsed), raw

def read_csv(path: Path):
    last = None
    for enc in ("utf-8-sig","utf-8","latin-1"):
        try:
            with path.open("r",encoding=enc,newline="") as f:
                r = csv.DictReader(f)
                return r.fieldnames or [], list(r), enc
        except Exception as e:
            last = e
    raise RuntimeError(f"Cannot read {path}: {last}")

def auto_csv(root: Path) -> Optional[Path]:
    preferred = [
        root / "Exception_Handling _Analysis_Output " / "analyzed_repositories.csv",
        root / "Exception_Handling _Analysis_Output" / "analyzed_repositories.csv",
        root / "analysis" / "analyzed_repositories.csv",
    ]
    for p in preferred:
        if p.exists():
            return p

    best = None
    best_score = -1
    for p in root.rglob("*.csv"):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        try:
            with p.open("r",encoding="utf-8-sig",newline="") as f:
                hdr = next(csv.reader(f),[])
        except Exception:
            continue
        score = 0
        if find_col(hdr,CATEGORY_CANDIDATES): score += 10
        for mech, aliases in ADVANCED_ALIASES.items():
            if fuzzy_cols(hdr,aliases,mech): score += 4
        try:
            if p.stat().st_size > 0: score += 1
        except OSError:
            pass
        if score > best_score:
            best_score, best = score, p
    return best

def source_contexts(root: Path, out: Path, source_hint: Optional[str]) -> Dict[str,int]:
    if source_hint:
        files = [Path(source_hint)]
        if not files[0].is_absolute():
            files = [root / files[0]]
    else:
        files = []
        for p in root.rglob("*"):
            if not p.is_file() or any(part in SKIP_DIRS for part in p.parts):
                continue
            if p.suffix.lower() in {".py",".java",".js",".ts",".go",".cs",".rb",".kt",".swift",".md",".txt"}:
                try:
                    if p.stat().st_size <= 4_000_000:
                        files.append(p)
                except OSError:
                    pass

    needles = [
        r"Exception Type", r"exception_type",
        r"Has Timeout", r"Has Retry", r"Has Backoff", r"Has Circuit Breaker",
        r"\bMixed\b", r"\bAdvanced\b", r"\bBasic\b",
        r"has_timeout", r"has_retry", r"has_backoff", r"circuit.?breaker",
    ]
    regs = [re.compile(x,re.I) for x in needles]
    hit_count = 0
    file_counts = Counter()
    blocks = []
    seen = set()

    for p in files:
        try:
            lines = p.read_text(encoding="utf-8",errors="ignore").splitlines()
        except Exception:
            continue
        for i,line in enumerate(lines,1):
            if not any(r.search(line) for r in regs):
                continue
            low = line.lower()
            logicish = (
                "exception type" in low or "exception_type" in low
                or "has timeout" in low or "has retry" in low
                or "has backoff" in low or "has circuit breaker" in low
                or ("mixed" in low and ("basic" in low or "advanced" in low))
                or ("advanced" in low and any(x in low for x in ["timeout","retry","backoff","circuit"]))
            )
            if not logicish:
                continue
            start,end=max(1,i-6),min(len(lines),i+8)
            key=(str(p),start,end)
            if key in seen: continue
            seen.add(key)
            block="\n".join(f"{j:6d}: {lines[j-1]}" for j in range(start,end+1))
            blocks.append(f"{'='*100}\n{p}:{i}\n{block}\n")
            hit_count += 1
            file_counts[str(p)] += 1

    out.write_text("\n".join(blocks),encoding="utf-8")
    return {"hit_count": hit_count, "files_with_hits": len(file_counts), "top_files": file_counts.most_common(20)}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=".")
    ap.add_argument("--csv",default=None)
    ap.add_argument("--source",default=None,help="Optional source file to focus source search, e.g. WebServFH.py")
    ap.add_argument("--show",type=int,default=20)
    args=ap.parse_args()

    root=Path(args.root).resolve()
    outdir=root/"analysis"/"category_signal_consistency"
    outdir.mkdir(parents=True,exist_ok=True)

    csv_path=(root/args.csv).resolve() if args.csv and not Path(args.csv).is_absolute() else (Path(args.csv).resolve() if args.csv else auto_csv(root))
    if not csv_path or not csv_path.exists():
        print("ERROR: Could not locate result CSV. Use --csv path/to/analyzed_repositories.csv",file=sys.stderr)
        return 2

    cols,rows,enc=read_csv(csv_path)
    cat_col=find_col(cols,CATEGORY_CANDIDATES)
    repo_col=find_col(cols,REPO_CANDIDATES)

    adv_map={m:fuzzy_cols(cols,a,m) for m,a in ADVANCED_ALIASES.items()}
    basic_map={m:fuzzy_cols(cols,a,m) for m,a in BASIC_ALIASES.items()}

    print("="*92)
    print("NiP category ↔ signal consistency audit")
    print("="*92)
    print(f"CSV      : {csv_path}")
    print(f"Rows     : {len(rows)}")
    print(f"Encoding : {enc}")
    print(f"Category : {cat_col!r}")
    print(f"Repo id  : {repo_col!r}")
    print("\nMatched advanced columns:")
    for k,v in adv_map.items(): print(f"  {k:18s}: {v}")
    print("Matched basic columns:")
    for k,v in basic_map.items(): print(f"  {k:18s}: {v}")

    # Print potentially relevant unclaimed boolean-looking headers.
    claimed=set(sum(adv_map.values(),[])+sum(basic_map.values(),[]))
    interesting=[c for c in cols if c not in claimed and any(x in norm(c) for x in [
        "has","exception","error","status","handler","advanced","basic","mixed","timeout","retry","backoff","circuit"
    ])]
    print("\nOther potentially relevant columns:")
    for c in interesting: print(f"  {c}")

    if not cat_col:
        print("\nERROR: category column not found.",file=sys.stderr)
        return 2

    # Category x advanced-depth cross-tab.
    cross=defaultdict(Counter)
    detailed=[]
    reconstructable = all(adv_map[m] for m in ADVANCED_ALIASES) and any(basic_map[m] for m in BASIC_ALIASES)

    for line,row in enumerate(rows,2):
        cat=canonical_category(row.get(cat_col,""))
        adv_vals={}
        adv_raw={}
        for m,cs in adv_map.items():
            adv_vals[m],adv_raw[m]=mech_value(row,cs)

        if all(v is not None for v in adv_vals.values()):
            depth=sum(v is True for v in adv_vals.values())
        else:
            depth=None
        cross[cat][depth] += 1

        basic_vals={}
        basic_raw={}
        for m,cs in basic_map.items():
            basic_vals[m],basic_raw[m]=mech_value(row,cs)

        expected=None
        if reconstructable and all(v is not None for v in adv_vals.values()):
            known_basic=[v for v in basic_vals.values() if v is not None]
            if known_basic:
                has_basic=any(known_basic)
                has_adv=any(v is True for v in adv_vals.values())
                if has_basic and has_adv: expected="Mixed"
                elif has_adv: expected="Advanced"
                elif has_basic: expected="Basic"
                else: expected="None"

        detailed.append({
            "line":line,
            "row":row,
            "category":cat,
            "depth":depth,
            "adv_vals":adv_vals,
            "adv_raw":adv_raw,
            "basic_vals":basic_vals,
            "basic_raw":basic_raw,
            "expected":expected,
        })

    depths=[0,1,2,3,4,None]
    print("\nCATEGORY × FOUR-ADVANCED-SIGNAL DEPTH")
    header=["Category","0","1","2","3","4","Unknown","Total"]
    print("  " + " | ".join(f"{x:>10}" for x in header))
    print("  " + "-"*104)
    for cat in CATEGORY_NAMES:
        vals=[cross[cat][d] for d in [0,1,2,3,4,None]]
        print("  " + " | ".join([f"{cat:>10}"]+[f"{x:10d}" for x in vals]+[f"{sum(vals):10d}"]))

    crosstab_path=outdir/"category_depth_crosstab.csv"
    with crosstab_path.open("w",encoding="utf-8",newline="") as f:
        w=csv.writer(f)
        w.writerow(header)
        for cat in CATEGORY_NAMES:
            vals=[cross[cat][d] for d in [0,1,2,3,4,None]]
            w.writerow([cat]+vals+[sum(vals)])

    # Reconstructed-category audit if basic signals can be observed.
    reconstruction=Counter()
    mismatches=[]
    if reconstructable:
        for d in detailed:
            if d["expected"] is not None:
                reconstruction[(d["category"],d["expected"])] += 1
                if d["category"] != d["expected"]:
                    mismatches.append(d)

        print("\nSTORED CATEGORY × RECONSTRUCTED CATEGORY FROM EXPORTED SIGNALS")
        print("  " + " | ".join(f"{x:>10}" for x in ["Stored"]+CATEGORY_NAMES+["Total"]))
        print("  " + "-"*85)
        for stored in CATEGORY_NAMES:
            vals=[reconstruction[(stored,exp)] for exp in CATEGORY_NAMES]
            print("  " + " | ".join([f"{stored:>10}"]+[f"{x:10d}" for x in vals]+[f"{sum(vals):10d}"]))
        print(f"\nTotal stored-vs-reconstructed mismatches: {len(mismatches)}")

        recon_path=outdir/"category_reconstruction_crosstab.csv"
        with recon_path.open("w",encoding="utf-8",newline="") as f:
            w=csv.writer(f)
            w.writerow(["Stored"]+CATEGORY_NAMES+["Total"])
            for stored in CATEGORY_NAMES:
                vals=[reconstruction[(stored,exp)] for exp in CATEGORY_NAMES]
                w.writerow([stored]+vals+[sum(vals)])

        mismatch_path=outdir/"category_mismatches.csv"
        audit_cols=[
            "__source_line","__repo_id","__stored_category","__expected_from_exported_signals",
            "__advanced_depth","__advanced_values","__basic_values"
        ]
        with mismatch_path.open("w",encoding="utf-8",newline="") as f:
            w=csv.DictWriter(f,fieldnames=audit_cols+cols,extrasaction="ignore")
            w.writeheader()
            for d in mismatches:
                row=d["row"]
                w.writerow({
                    "__source_line":d["line"],
                    "__repo_id":row.get(repo_col,"") if repo_col else "",
                    "__stored_category":d["category"],
                    "__expected_from_exported_signals":d["expected"],
                    "__advanced_depth":d["depth"],
                    "__advanced_values":json.dumps(d["adv_vals"]),
                    "__basic_values":json.dumps(d["basic_vals"]),
                    **row
                })

        print(f"Mismatch CSV: {mismatch_path}")
    else:
        print("\n[NOTE] Could not reconstruct the full four-way category because the exported CSV")
        print("       does not expose enough recognizable basic-signal columns.")
        print("       The category × advanced-depth table is still definitive for the anomalies.")

    # Specific anomaly samples.
    anomaly_specs=[
        ("Mixed + depth 0", lambda d: d["category"]=="Mixed" and d["depth"]==0),
        ("Basic + advanced depth >0", lambda d: d["category"]=="Basic" and d["depth"] is not None and d["depth"]>0),
        ("Advanced + depth 0", lambda d: d["category"]=="Advanced" and d["depth"]==0),
    ]
    for title,pred in anomaly_specs:
        subset=[d for d in detailed if pred(d)]
        print(f"\n{title}: {len(subset)}")
        for d in subset[:args.show]:
            rid=d["row"].get(repo_col,"") if repo_col else ""
            print(f"  line={d['line']} repo={rid} adv={d['adv_vals']} basic={d['basic_vals']}")

    # Source-code contexts.
    logic_path=outdir/"source_logic_contexts.txt"
    src_summary=source_contexts(root,logic_path,args.source)
    print(f"\nSource logic contexts: {logic_path}")
    print(f"Source hits: {src_summary['hit_count']} across {src_summary['files_with_hits']} files")
    print("Top files:")
    for p,n in src_summary["top_files"][:10]:
        print(f"  {n:4d}  {p}")

    summary={
        "csv":str(csv_path),
        "rows":len(rows),
        "category_column":cat_col,
        "repo_column":repo_col,
        "advanced_columns":adv_map,
        "basic_columns":basic_map,
        "other_potentially_relevant_columns":interesting,
        "category_depth":{cat:{str(k):v for k,v in cross[cat].items()} for cat in cross},
        "reconstructable":reconstructable,
        "stored_vs_reconstructed":{f"{a}->{b}":n for (a,b),n in reconstruction.items()},
        "mismatch_count":len(mismatches),
        "source_search":src_summary,
    }
    (outdir/"audit_summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")

    print("\n" + "="*92)
    print("WHAT TO PASTE BACK")
    print("="*92)
    print("1. The 'Matched basic columns' section")
    print("2. The 'CATEGORY × FOUR-ADVANCED-SIGNAL DEPTH' table")
    print("3. The 'STORED CATEGORY × RECONSTRUCTED CATEGORY' table, if produced")
    print("4. The top relevant block(s) from analysis/category_signal_consistency/source_logic_contexts.txt")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
