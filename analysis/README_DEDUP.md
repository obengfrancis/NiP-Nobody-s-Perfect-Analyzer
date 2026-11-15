# Deduplicated analysis (regenerated)

`nip_analyzer_output.csv` is now the deduplicated analyzer output (one row per
repository; 7,576 repositories, 7,304 with parser success > 0). The original
analyzer output is kept as `nip_analyzer_output_raw.csv`.

Run in this order:

    python3 build_aggregate_inputs.py nip_analyzer_output.csv   # rebuilds the two count tables
    python3 Pie_chart.py                                        # Fig. 2 + category summary
    python3 ch-square_cat_by_lang_analysis.py                   # Table 4, chi-square, Fig. 4 (category) figures
    python3 Pattern_adoption_analysis.py                        # signal heatmap + single vs multi (Fig. 5/6)

Change from the earlier version: `Pattern_adoption_analysis.py` no longer uses
hardcoded repository counts; it reads them from
`exception_categories_count_by_language.csv`.

`previous_outputs_non_dedup/` holds the figures and tables generated from the
non-deduplicated data, kept for the record. The `category_signal_consistency/`
and `mixed_depth_zero_investigation/` folders were also produced from the
non-deduplicated data.
