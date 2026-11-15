#!/usr/bin/env python3
"""Build the two aggregated input tables used by ch-square_cat_by_lang_analysis.py
and Pattern_adoption_analysis.py directly from nip_analyzer_output.csv, so they
always match the (deduplicated) analyzer output.

Usage: python3 build_aggregate_inputs.py [nip_analyzer_output.csv]
Writes: exception_categories_count_by_language.csv, Pattern_Adoption_By_Language.csv
"""
import sys
import pandas as pd

src = sys.argv[1] if len(sys.argv) > 1 else "nip_analyzer_output.csv"
df = pd.read_csv(src, encoding="utf-8-sig")
df["psr"] = pd.to_numeric(df["Parser Success Rate"].astype(str).str.rstrip("%"), errors="coerce").fillna(0)
df = df[df["psr"] > 0].copy()
df["cat"] = df["Exception Type"].fillna("None")
single = ~df["Languages"].astype(str).str.contains(";")
names = {"python": "Python", "java": "Java", "javascript": "JavaScript", "typescript": "TypeScript",
         "go": "Go", "csharp": "C#", "ruby": "Ruby", "kotlin": "Kotlin", "swift": "Swift"}
df["Language"] = df["Languages"].map(names).where(single, "Multiple")
order = list(names.values()) + ["Multiple"]

cats = pd.crosstab(df["Language"], df["cat"]).reindex(index=order, columns=["None", "Basic", "Mixed", "Advanced"], fill_value=0)
cats.insert(0, "Repositories", cats.sum(axis=1))
cats.reset_index().to_csv("exception_categories_count_by_language.csv", index=False, encoding="utf-8-sig")

flags = {"Has Try-Catch": "Try-Catch", "Has Timeout": "Timeout", "Has Retry": "Retry",
         "Has Circuit Breaker": "Circuit Breaker", "Has Backoff": "Backoff", "Has Status Check": "Status Check"}
for c in flags:
    df[c] = df[c].astype(str).str.strip().str.lower().isin(["true", "1"])
pat = df.groupby("Language")[list(flags)].sum().rename(columns=flags).reindex(order, fill_value=0).astype(int)
single_total = pat.drop(index="Multiple").sum().to_frame("Single-Repo Total").T
pat = pd.concat([pat.drop(index="Multiple"), single_total, pat.loc[["Multiple"]]])
pat.index.name = "Language"
pat.reset_index().to_csv("Pattern_Adoption_By_Language.csv", index=False, encoding="utf-8-sig")

print(cats.to_string())
print()
print(pat.to_string())
