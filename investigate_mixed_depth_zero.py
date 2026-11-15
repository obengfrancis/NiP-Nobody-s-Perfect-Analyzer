#!/usr/bin/env python3
"""
Investigate why repositories classified as Mixed may have advanced-pattern depth 0.

Run from the NiP project root:

    python3 investigate_mixed_depth_zero.py

Optional:
    python3 investigate_mixed_depth_zero.py --root .
    python3 investigate_mixed_depth_zero.py --csv path/to/results.csv
    python3 investigate_mixed_depth_zero.py --show 50

Outputs:
    analysis/mixed_depth_zero_investigation/

The script is read-only with respect to existing project files.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

CATEGORY_CANDIDATES = [
    "category", "strategy_category", "strategy", "exception_type",
    "exception_category", "handling_category", "fault_handling_category",
    "repo_category", "repository_category", "classification", "label",
]

REPO_ID_CANDIDATES = [
    "repo_url", "repository_url", "url", "repo", "repository",
    "full_name", "name", "repo_name",
]

ADVANCED_PATTERNS = {
    "timeout": ["timeout", "timeouts", "has_timeout", "timeout_detected", "uses_timeout", "detected_timeout"],
    "retry": ["retry", "retries", "has_retry", "retry_detected", "uses_retry", "detected_retry"],
    "backoff": ["backoff", "exponential_backoff", "has_backoff", "backoff_detected", "uses_backoff", "detected_backoff"],
    "circuit_breaker": ["circuit_breaker", "circuitbreaker", "circuit_breakers", "has_circuit_breaker", "circuit_breaker_detected", "uses_circuit_breaker", "detected_circuit_breaker"],
}

SKIP_DIRS = {
    ".git", ".idea", ".vscode", "__pycache__", "node_modules", "target",
    "build", "dist", ".venv", "venv", "env",
}

SOURCE_SUFFIXES = {
    ".py", ".java", ".js", ".ts", ".go", ".cs", ".rb", ".kt", ".kts",
    ".swift", ".sh", ".md", ".txt", ".json", ".yaml", ".yml",
}

TRUE_VALUES = {"1", "true", "t", "yes", "y", "on", "present", "detected"}
FALSE_VALUES = {"0", "false", "f", "no", "n", "off", "absent", "none", "", "nan", "null", "na", "n/a"}


def norm(s: str) -> str:
    s = str(s).strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return re.sub(r"_+", "_", s).strip("_")


def parse_bool(value) -> Optional[bool]:
    if value is None:
        return None
    s = str(value).strip().lower()
    if s in TRUE_VALUES:
        return True
    if s in FALSE_VALUES:
        return False
    try:
        return float(s) > 0
    except Exception:
        pass
    if s in {"[]", "{}", "()"}:
        return False
    return None


def find_column(columns: Sequence[str], candidates: Sequence[str]) -> Optional[str]:
    by_norm = {norm(c): c for c in columns}
    for cand in candidates:
        if norm(cand) in by_norm:
            return by_norm[norm(cand)]
    return None


def fuzzy_pattern_columns(columns: Sequence[str], aliases: Sequence[str], canonical: str) -> List[str]:
    found = []
    alias_norms = list(dict.fromkeys([norm(a) for a in aliases] + [norm(canonical)]))
    for col in columns:
        n = norm(col)
        exact = any(a == n for a in alias_norms)
        token_match = any(
            len(a) >= 5 and re.search(rf"(^|_){re.escape(a)}($|_)", n)
            for a in alias_norms
        )
        if not (exact or token_match):
            continue
        if any(tok in n for tok in [
            "keyword", "example", "description", "rationale", "reason",
            "file_path", "filename", "source", "library_name", "rule"
        ]):
            continue
        found.append(col)
    out = []
    seen = set()
    for c in found:
        if c not in seen:
            out.append(c)
            seen.add(c)
    return out


def mechanism_present(row: Dict[str, str], cols: Sequence[str]):
    details = []
    known = []
    for c in cols:
        raw = row.get(c, "")
        b = parse_bool(raw)
        details.append((c, raw, b))
        if b is not None:
            known.append(b)
    if not cols or not known:
        return None, details
    return any(known), details


def discover_csvs(root: Path) -> List[Path]:
    files = []
    for p in root.rglob("*.csv"):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        try:
            if p.stat().st_size == 0:
                continue
        except OSError:
            continue
        files.append(p)
    return sorted(files)


def read_header(path: Path) -> List[str]:
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            with path.open("r", encoding=enc, newline="") as f:
                return next(csv.reader(f), [])
        except Exception:
            continue
    return []


def candidate_score(path: Path, header: Sequence[str]):
    cat = find_column(header, CATEGORY_CANDIDATES)
    repo = find_column(header, REPO_ID_CANDIDATES)
    pattern_map = {k: fuzzy_pattern_columns(header, aliases, k) for k, aliases in ADVANCED_PATTERNS.items()}
    n_patterns = sum(bool(v) for v in pattern_map.values())
    score = (10 if cat else 0) + (2 if repo else 0) + 4 * n_patterns
    if any(t in norm(path.name) for t in ["output", "result", "analysis", "repo", "exception"]):
        score += 2
    return score, {"category_column": cat, "repo_column": repo, "advanced_columns": pattern_map}


def load_csv_rows(path: Path):
    last_error = None
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            with path.open("r", encoding=enc, newline="") as f:
                reader = csv.DictReader(f)
                return reader.fieldnames or [], list(reader), enc
        except Exception as e:
            last_error = e
    raise RuntimeError(f"Could not read {path}: {last_error}")


def canonical_category(value: str) -> str:
    n = norm(value)
    if n in {"mixed", "mix"} or "mixed" in n:
        return "mixed"
    if n in {"advanced", "advanced_only"} or n.startswith("advanced"):
        return "advanced"
    if n in {"basic", "basic_only"} or n.startswith("basic"):
        return "basic"
    if n in {"none", "no_handling", "no_exception_handling"} or n.startswith("none"):
        return "none"
    return n


def analyze_csv(path: Path, meta: Dict, outdir: Path, show: int) -> Dict:
    header, rows, enc = load_csv_rows(path)
    cat_col = meta["category_column"]
    repo_col = meta["repo_column"]
    adv_cols = meta["advanced_columns"]

    result = {
        "path": str(path), "encoding": enc, "row_count": len(rows),
        "category_column": cat_col, "repo_column": repo_col,
        "advanced_columns": adv_cols, "category_counts": {},
        "mixed_count": 0, "mixed_depth_distribution": {},
        "mixed_depth_zero_count": 0, "mixed_unknown_depth_count": 0,
        "anomalies": {},
    }
    if not cat_col:
        return result

    result["category_counts"] = dict(Counter(canonical_category(r.get(cat_col, "")) for r in rows))
    depth_counter = Counter()
    depth0_rows = []
    unknown_depth_rows = []
    anomaly_counter = Counter()
    mixed_count = 0

    for idx, row in enumerate(rows, start=2):
        category = canonical_category(row.get(cat_col, ""))
        signals, detail = {}, {}
        for mech, cols in adv_cols.items():
            present, raw_detail = mechanism_present(row, cols)
            signals[mech] = present
            detail[mech] = raw_detail

        depth = len([m for m, v in signals.items() if v is True]) if all(signals[m] is not None for m in ADVANCED_PATTERNS) else None

        if category == "mixed":
            mixed_count += 1
            if depth is None:
                unknown_depth_rows.append((idx, row, signals, detail))
            else:
                depth_counter[depth] += 1
                if depth == 0:
                    depth0_rows.append((idx, row, signals, detail))

        if depth is not None:
            if category == "mixed" and depth == 0:
                anomaly_counter["mixed_with_zero_advanced"] += 1
            if category == "advanced" and depth == 0:
                anomaly_counter["advanced_with_zero_advanced"] += 1
            if category == "basic" and depth > 0:
                anomaly_counter["basic_with_advanced_signal"] += 1
            if category == "none" and depth > 0:
                anomaly_counter["none_with_advanced_signal"] += 1

    result["mixed_count"] = mixed_count
    result["mixed_depth_distribution"] = dict(sorted(depth_counter.items()))
    result["mixed_depth_zero_count"] = len(depth0_rows)
    result["mixed_unknown_depth_count"] = len(unknown_depth_rows)
    result["anomalies"] = dict(anomaly_counter)

    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", path.stem)
    depth0_path = outdir / f"{safe_name}__mixed_depth0.csv"
    extra_cols = [
        "__source_csv", "__source_line", "__category_column", "__category_value", "__repo_id",
        "__timeout_present", "__retry_present", "__backoff_present", "__circuit_breaker_present",
        "__matched_signal_columns",
    ]
    with depth0_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=extra_cols + header, extrasaction="ignore")
        writer.writeheader()
        for idx, row, signals, detail in depth0_rows:
            matched = {
                mech: [{"column": c, "raw": raw, "parsed": parsed} for c, raw, parsed in details]
                for mech, details in detail.items()
            }
            audit = {
                "__source_csv": str(path), "__source_line": idx,
                "__category_column": cat_col, "__category_value": row.get(cat_col, ""),
                "__repo_id": row.get(repo_col, "") if repo_col else "",
                "__timeout_present": signals["timeout"], "__retry_present": signals["retry"],
                "__backoff_present": signals["backoff"], "__circuit_breaker_present": signals["circuit_breaker"],
                "__matched_signal_columns": json.dumps(matched, ensure_ascii=False),
            }
            writer.writerow({**audit, **row})
    result["mixed_depth_zero_csv"] = str(depth0_path)

    if depth0_rows:
        print(f"\n>>> MIXED + DEPTH 0 examples from {path} (showing up to {show})")
        for idx, row, signals, _ in depth0_rows[:show]:
            rid = row.get(repo_col, "") if repo_col else ""
            print(f"  line={idx} repo={rid!r} category={row.get(cat_col)!r}")
            for mech in ADVANCED_PATTERNS:
                vals = [(c, row.get(c, "")) for c in adv_cols[mech]]
                print(f"    {mech:16s}: parsed={signals[mech]!r} raw={vals}")

    return result


def search_source_logic(root: Path, outdir: Path):
    hits = []
    for p in root.rglob("*"):
        if not p.is_file() or any(part in SKIP_DIRS for part in p.parts) or p.suffix.lower() not in SOURCE_SUFFIXES:
            continue
        try:
            if p.stat().st_size > 5_000_000:
                continue
            lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            continue

        for i, line in enumerate(lines, start=1):
            n = line.lower()
            logicish = (
                ("mixed" in n and ("advanced" in n or "basic" in n))
                or ("category" in n and ("mixed" in n or "advanced" in n))
                or "exception_type" in n
                or "strategy_category" in n
                or ("timeout" in n and ("retry" in n or "backoff" in n or "circuit" in n))
                or ("advanced" in n and ("timeout" in n or "retry" in n or "backoff" in n or "circuit" in n))
            )
            if logicish:
                start, end = max(1, i - 3), min(len(lines), i + 3)
                context = "\n".join(f"{j:6d}: {lines[j-1]}" for j in range(start, end + 1))
                hits.append({"file": str(p), "line": i, "context": context})

    report_path = outdir / "classification_logic_hits.txt"
    with report_path.open("w", encoding="utf-8") as f:
        for h in hits:
            f.write("=" * 100 + "\n")
            f.write(f"{h['file']}:{h['line']}\n")
            f.write(h["context"] + "\n\n")
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(description="Investigate Mixed repositories with advanced-pattern depth 0.")
    ap.add_argument("--root", default=".", help="Project root (default: current directory)")
    ap.add_argument("--csv", action="append", default=[], help="Specific CSV to inspect; may be supplied multiple times")
    ap.add_argument("--show", type=int, default=20, help="Number of depth-0 examples to print per CSV")
    ap.add_argument("--min-score", type=int, default=22, help="Minimum score for auto-discovered candidate CSVs")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        print(f"ERROR: root does not exist: {root}", file=sys.stderr)
        return 2

    outdir = root / "analysis" / "mixed_depth_zero_investigation"
    outdir.mkdir(parents=True, exist_ok=True)

    print("=" * 88)
    print("NiP Mixed-depth-zero investigation")
    print("=" * 88)
    print(f"Project root: {root}")
    print(f"Output dir  : {outdir}")

    candidates = []
    if args.csv:
        for s in args.csv:
            p = Path(s)
            if not p.is_absolute():
                p = root / p
            p = p.resolve()
            if not p.exists():
                print(f"[warning] specified CSV not found: {p}")
                continue
            header = read_header(p)
            score, meta = candidate_score(p, header)
            candidates.append((score, p, meta, header))
    else:
        csvs = discover_csvs(root)
        print(f"\nDiscovered {len(csvs)} CSV files.")
        for p in csvs:
            header = read_header(p)
            score, meta = candidate_score(p, header)
            if score >= args.min_score:
                candidates.append((score, p, meta, header))

    candidates.sort(key=lambda x: (-x[0], str(x[1])))

    if not candidates:
        print("\nNo candidate result CSV was auto-detected.")
        print("Try: python3 investigate_mixed_depth_zero.py --csv path/to/results.csv")
        print("\nCSV headers found:")
        for p in discover_csvs(root)[:50]:
            print(f"  {p}: {read_header(p)}")
        return 1

    print("\nCandidate result CSVs:")
    for score, p, meta, _ in candidates:
        print(f"  score={score:2d}  {p}")
        print(f"      category={meta['category_column']!r} repo={meta['repo_column']!r}")
        for mech, cols in meta["advanced_columns"].items():
            print(f"      {mech:16s}: {cols}")

    summaries = []
    for score, p, meta, _ in candidates:
        try:
            summary = analyze_csv(p, meta, outdir, args.show)
            summary["auto_discovery_score"] = score
            summaries.append(summary)
        except Exception as e:
            print(f"\n[error] failed analyzing {p}: {e}", file=sys.stderr)

    print("\nSearching source files for category-aggregation and advanced-signal logic...")
    logic_hits = search_source_logic(root, outdir)
    print(f"Found {len(logic_hits)} likely source/documentation hits.")
    print(f"Saved contexts to: {outdir / 'classification_logic_hits.txt'}")

    report = {
        "project_root": str(root),
        "csv_summaries": summaries,
        "classification_logic_hit_count": len(logic_hits),
        "classification_logic_report": str(outdir / "classification_logic_hits.txt"),
    }
    report_path = outdir / "investigation_summary.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n" + "=" * 88)
    print("SUMMARY")
    print("=" * 88)
    any_depth0 = False
    for s in summaries:
        print(f"\n{s['path']}")
        print(f"  rows                     : {s['row_count']}")
        print(f"  category column          : {s['category_column']}")
        print(f"  category counts          : {s['category_counts']}")
        print(f"  Mixed rows               : {s['mixed_count']}")
        print(f"  Mixed depth distribution : {s['mixed_depth_distribution']}")
        print(f"  Mixed depth 0            : {s['mixed_depth_zero_count']}")
        print(f"  Mixed depth unknown      : {s['mixed_unknown_depth_count']}")
        print(f"  cross-category anomalies : {s['anomalies']}")
        if s["mixed_depth_zero_count"] > 0:
            any_depth0 = True
            print(f"  depth-0 audit CSV        : {s['mixed_depth_zero_csv']}")

    print("\nInterpretation guide:")
    if any_depth0:
        print("  * Mixed + depth 0 is reproducible from at least one result CSV.")
        print("  * Inspect the depth-0 audit CSV plus classification_logic_hits.txt.")
        print("  * Check whether repository classification uses an alternate/fifth advanced")
        print("    detector, legacy field, per-file label, or stale category not used by the")
        print("    four-pattern depth calculation.")
    else:
        print("  * Mixed + depth 0 was not reproduced from the candidate CSVs.")
        print("  * The 1.6% likely came from a different/stale artifact or figure-generation")
        print("    script; search analysis code for 'depth', 'within_mixed', '61.9', or '1.6'.")

    print(f"\nFull JSON summary: {report_path}")
    print("\nUseful follow-up commands:")
    print("  grep -RniE 'depth|within.?mixed|61\\.9|1\\.6' analysis . --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=target")
    print("  grep -RniE 'Mixed|Advanced|timeout|retry|backoff|circuit' WebServFH.py analysis --exclude-dir=.git 2>/dev/null | head -n 200")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
