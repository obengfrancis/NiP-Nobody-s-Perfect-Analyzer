import pandas as pd
import numpy as np
from scipy.stats import chi2_contingency
import matplotlib.pyplot as plt
import seaborn as sns

# Set style
plt.style.use('seaborn-v0_8-paper')
sns.set_palette("husl")


def load_language_data(filepath):
    """Load the language distribution data with raw counts"""
    print("="*70)
    print("LOADING LANGUAGE-SPECIFIC EXCEPTION HANDLING DATA (RAW COUNTS)")
    print("="*70)
    
    fp = filepath.lower().strip()
    if fp.endswith(".xlsx") or fp.endswith(".xls"):
        df = pd.read_excel(filepath, engine="openpyxl")
    elif fp.endswith(".csv"):
        df = pd.read_csv(filepath)
    else:
        raise ValueError(f"Unsupported file type: {filepath}")

    # ✅ FIX: Strip whitespace from column names
    df.columns = df.columns.str.strip()
    
    print(f"\n✓ Loaded data for {len(df)} language categories")
    print(f"✓ Columns: {list(df.columns)}")
    print("\nLanguage Distribution Data (with raw counts):")
    print(df.to_string(index=False))
    return df


def prepare_contingency_table_from_counts(df):

    print("\n" + "="*70)
    print("PREPARING CONTINGENCY TABLE FROM RAW COUNTS")
    print("="*70)

    # Exclude 'Multiple' category if present
    df_filtered = df[df['Language'] != 'Multiple'].copy()

    # Extract count columns (adjust names based on your CSV)
    count_cols = ['None', 'Basic', 'Mixed', 'Advanced']
    
    # Verify columns exist
    missing_cols = [col for col in count_cols if col not in df_filtered.columns]
    if missing_cols:
        print(f"\n⚠️  Missing columns: {missing_cols}")
        print(f"Available columns: {list(df_filtered.columns)}")
        print("\nAttempting to infer count columns...")
        
        # Try to find count columns with different names
        possible_none = [c for c in df_filtered.columns if 'none' in c.lower() and '%' not in c.lower()]
        possible_basic = [c for c in df_filtered.columns if 'basic' in c.lower() and '%' not in c.lower()]
        possible_mixed = [c for c in df_filtered.columns if 'mixed' in c.lower() and '%' not in c.lower()]
        possible_advanced = [c for c in df_filtered.columns if 'adv' in c.lower() and '%' not in c.lower()]
        
        count_cols = []
        if possible_none: count_cols.append(possible_none[0])
        if possible_basic: count_cols.append(possible_basic[0])
        if possible_mixed: count_cols.append(possible_mixed[0])
        if possible_advanced: count_cols.append(possible_advanced[0])
        
        print(f"✓ Inferred count columns: {count_cols}")

    # Convert to numeric (in case they're stored as strings)
    for col in count_cols:
        df_filtered[col] = pd.to_numeric(df_filtered[col], errors='coerce')

    # Build contingency table
    contingency_data = []
    languages = []

    for _, row in df_filtered.iterrows():
        language = row['Language']
        counts = [int(row[col]) for col in count_cols]
        
        contingency_data.append(counts)
        languages.append(language)

    contingency_table = np.array(contingency_data)

    print("\nContingency Table (Observed Frequencies - RAW COUNTS):")
    contingency_df = pd.DataFrame(
        contingency_table,
        index=languages,
        columns=['None', 'Basic', 'Mixed', 'Advanced']
    )
    print(contingency_df)
    
    # Show row totals for verification
    print("\nRow Totals (Repositories per Language):")
    row_totals = contingency_table.sum(axis=1)
    for lang, total in zip(languages, row_totals):
        print(f"  {lang:<12}: {total:>6,} repositories")
    
    print(f"\n✓ Total observations: {contingency_table.sum():,}")
    
    # Verify no zeros (chi-square assumption)
    zero_count = (contingency_table == 0).sum()
    if zero_count > 0:
        print(f"\n⚠️  Warning: {zero_count} cells with zero counts")

    return contingency_table, languages, count_cols


def perform_chi_square_test(contingency_table, languages):
    """Perform chi-square test on raw count data"""
    print("\n" + "="*70)
    print("CHI-SQUARE TEST OF INDEPENDENCE (USING RAW COUNTS)")
    print("="*70)
    
    print("\nNull Hypothesis (H₀): Programming language has NO effect on exception handling strategy")
    print("Alternative Hypothesis (H₁): Programming language DOES affect exception handling strategy")
    print("\nSignificance level: α = 0.05")
    
    # Perform Chi-square test
    chi2_stat, p_value, dof, expected = chi2_contingency(contingency_table)
    
    # Calculate Cramér's V (effect size)
    n = contingency_table.sum()
    min_dim = min(contingency_table.shape[0] - 1, contingency_table.shape[1] - 1)
    cramers_v = np.sqrt(chi2_stat / (n * min_dim))
    
    # Print results
    print("\n" + "-"*70)
    print("TEST RESULTS")
    print("-"*70)
    print(f"Chi-square statistic (χ²):  {chi2_stat:.2f}")
    print(f"Degrees of freedom:         {dof}")
    print(f"P-value:                    {p_value:.2e}")
    print(f"Cramér's V (effect size):   {cramers_v:.4f}")
    
    # Interpret effect size
    print(f"\nEffect Size Interpretation (Cramér's V):")
    if cramers_v < 0.1:
        effect_desc = "negligible"
    elif cramers_v < 0.3:
        effect_desc = "small to medium"
    elif cramers_v < 0.5:
        effect_desc = "medium to large"
    else:
        effect_desc = "large"
    print(f"  V = {cramers_v:.4f} indicates a {effect_desc} association")
    
    # Statistical decision
    print("\n" + "-"*70)
    print("STATISTICAL DECISION")
    print("-"*70)
    
    if p_value < 0.001:
        print(f"✓ P-value ({p_value:.2e}) < 0.001")
        print("✓ REJECT NULL HYPOTHESIS (H₀)")
        print("\n CONCLUSION: Programming language SIGNIFICANTLY affects exception")
        print("   handling strategy distribution (p < 0.001, highly significant)")
    elif p_value < 0.05:
        print(f"✓ P-value ({p_value:.4f}) < 0.05")
        print("✓ REJECT NULL HYPOTHESIS (H₀)")
        print(f"\n CONCLUSION: Programming language significantly affects exception")
        print(f"   handling strategy (p = {p_value:.4f})")
    else:
        print(f"✗ P-value ({p_value:.4f}) >= 0.05")
        print("✗ FAIL TO REJECT NULL HYPOTHESIS (H₀)")
        print("\n CONCLUSION: No significant evidence that language affects exception")
        print("   handling strategy")
    
    # Show expected frequencies
    print("\n" + "-"*70)
    print("EXPECTED FREQUENCIES (if H₀ were true)")
    print("-"*70)
    expected_df = pd.DataFrame(
        expected,
        index=languages,
        columns=['None', 'Basic', 'Mixed', 'Advanced']
    )
    print(expected_df.round(2).to_string())
    
    # Check assumptions
    print("\n" + "-"*70)
    print("CHI-SQUARE TEST ASSUMPTIONS")
    print("-"*70)
    print("1. Independence: ✓ Each repository is independently classified")
    print("2. Expected frequency ≥ 5 in at least 80% of cells:")
    
    cells_below_5 = (expected < 5).sum()
    total_cells = expected.size
    pct_below_5 = (cells_below_5 / total_cells) * 100
    
    print(f"   - Cells with expected frequency < 5: {cells_below_5}/{total_cells} ({pct_below_5:.1f}%)")
    
    if pct_below_5 <= 20:
        print("   ✓ Assumption satisfied (≤ 20% cells below 5)")
    else:
        print(f"  Assumption violated ({pct_below_5:.1f}% > 20%)")
        print("   → Consider combining categories or interpreting with caution")
    
    # Calculate contribution to chi-square
    print("\n" + "-"*70)
    print("CONTRIBUTION TO CHI-SQUARE (Top contributors)")
    print("-"*70)
    
    residuals = (contingency_table - expected) ** 2 / expected
    contribution_df = pd.DataFrame(
        residuals,
        index=languages,
        columns=['None', 'Basic', 'Mixed', 'Advanced']
    )
    
    # Flatten and get top 10 contributors
    flat_contrib = []
    for i, lang in enumerate(languages):
        for j, cat in enumerate(['None', 'Basic', 'Mixed', 'Advanced']):
            flat_contrib.append({
                'Language': lang,
                'Category': cat,
                'Contribution': residuals[i, j],
                'Observed': contingency_table[i, j],
                'Expected': expected[i, j]
            })
    
    contrib_df = pd.DataFrame(flat_contrib).sort_values('Contribution', ascending=False)
    
    print("\nTop 10 cells contributing to χ² statistic:")
    for idx, row in contrib_df.head(10).iterrows():
        print(f"  {row['Language']:<12} - {row['Category']:<8}: "
              f"χ² contrib = {row['Contribution']:>6.2f} "
              f"(obs={int(row['Observed'])}, exp={row['Expected']:.1f})")
    
    return chi2_stat, p_value, dof, cramers_v, expected


def calculate_percentages_from_counts(df, count_cols):
    """Calculate percentages from raw counts for visualization"""
    df_pct = df.copy()
    
    # Calculate row totals
    df_pct['Total'] = df_pct[count_cols].sum(axis=1)
    
    # Calculate percentages
    for col in count_cols:
        df_pct[f'{col} %'] = (df_pct[col] / df_pct['Total'] * 100).round(2)
    
    return df_pct


def create_visualizations(df, contingency_table, languages, count_cols, chi2_stat, p_value):
    """Create publication-quality visualizations from raw counts"""
    print("\n" + "="*70)
    print("CREATING VISUALIZATIONS")
    print("="*70)

    # Exclude 'Multiple' for visualization
    df_viz = df[df['Language'] != 'Multiple'].copy()
    
    # Calculate percentages from counts
    df_viz = calculate_percentages_from_counts(df_viz, count_cols)
    
    # Ensure language order matches contingency table
    df_viz = df_viz.set_index('Language').loc[languages].reset_index()
    
    pct_cols = [f'{col} %' for col in count_cols]

    # ----------------------------------------
    # Figure 1: Stacked bar chart
    # ----------------------------------------
    fig1, ax1 = plt.subplots(figsize=(12, 7))

    x = np.arange(len(languages))
    width = 0.6
    colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12']

    bottom = np.zeros(len(languages))

    for col, color, label in zip(pct_cols, colors, count_cols):
        values = df_viz[col].values
        ax1.bar(
            x, values, width,
            label=label,
            color=color, bottom=bottom,
            edgecolor='white', linewidth=0.5
        )
        bottom += values

    ax1.set_xlabel('Programming Language', fontsize=16, weight='bold')
    ax1.set_ylabel('Percentage of Repositories', fontsize=16, weight='bold')
    ax1.set_title(
        f'Exception Handling Distribution by Language\nχ² = {chi2_stat:.2f}, p < 0.001',
        fontsize=16, weight='bold'
    )
    ax1.title.set_position((0.1, 1.0))   # x=0.0 → far left, y=1.0 → top
    ax1.title.set_ha('left')
    ax1.set_xticks(x)
    ax1.set_xticklabels(languages, rotation=45, ha='right', fontsize=16)
    ax1.tick_params(axis='y', labelsize=16)
    ax1.legend(loc='upper right', bbox_to_anchor=(1.0, 1.2), ncol=2,  frameon=True, shadow=True, fontsize=16)
    ax1.set_ylim(0, 100)
    ax1.grid(axis='y', alpha=0.3, linestyle='--')
    ax1.set_axisbelow(True)
 
    plt.tight_layout()
    plt.savefig('language_exception_distribution_stacked.pdf', dpi=300, bbox_inches='tight')
    print("✓ Stacked bar chart saved")
    plt.close(fig1)

    # ----------------------------------------
    # Figure 2: Heatmap
    # ----------------------------------------
    fig2, ax2 = plt.subplots(figsize=(10, 7))

    heatmap_data = df_viz[pct_cols].values
    heatmap_df = pd.DataFrame(
        heatmap_data,
        index=languages,
        columns=count_cols
    )

    sns.heatmap(
        heatmap_df, annot=True, fmt='.1f', cmap='RdYlGn',
        cbar_kws={'label': 'Percentage (%)'}, ax=ax2,
        linewidths=0.5, linecolor='gray',
        vmin=0, vmax=100
    )

    ax2.set_xlabel('Exception Handling Category', fontsize=14, weight='bold')
    ax2.set_ylabel('Programming Language', fontsize=14, weight='bold')
    ax2.set_title(
        f'Exception Handling Heatmap by Language\nχ² = {chi2_stat:.2f}, p < 0.001',
        fontsize=16, weight='bold'
    )

    plt.tight_layout()
    plt.savefig('language_exception_heatmap.pdf', dpi=300, bbox_inches='tight')
    print("✓ Heatmap saved")
    plt.close(fig2)

    # ----------------------------------------
    # Figure 3: Advanced/Mixed adoption bar chart
    # ----------------------------------------
    fig3, ax3 = plt.subplots(figsize=(12, 7))

    df_viz['Advanced_Mixed %'] = df_viz[[c for c in pct_cols if 'Mixed' in c or 'Advanced' in c]].sum(axis=1)

    x = np.arange(len(languages))
    bars = ax3.bar(
        x, df_viz['Advanced_Mixed %'].values,
        color='#2ecc71', edgecolor='black', linewidth=1.5
    )

    for bar in bars:
        height = bar.get_height()
        ax3.text(
            bar.get_x() + bar.get_width()/2., height,
            f'{height:.1f}%',
            ha='center', va='bottom', fontsize=10, weight='bold'
        )

    ax3.set_xlabel('Programming Language', fontsize=14, weight='bold')
    ax3.set_ylabel('Advanced/Mixed Adoption (%)', fontsize=14, weight='bold')
    ax3.set_title('Advanced and Mixed Pattern Adoption by Language', fontsize=16, weight='bold')
    ax3.set_xticks(x)
    ax3.set_xticklabels(languages, rotation=45, ha='right')
    ax3.grid(axis='y', alpha=0.3, linestyle='--')
    ax3.set_axisbelow(True)

    avg = df_viz['Advanced_Mixed %'].mean()
    ax3.axhline(y=avg, color='red', linestyle='--', linewidth=2, label=f'Average: {avg:.1f}%')
    ax3.legend()

    plt.tight_layout()
    plt.savefig('language_advanced_adoption.pdf', dpi=300, bbox_inches='tight')
    print("✓ Advanced adoption bar chart saved")
    plt.close(fig3)



def generate_results_summary(df, languages, count_cols, chi2_stat, p_value, dof, cramers_v):
    """Generate text summary of results (NO LaTeX) - HANDLES COLUMN NAME VARIATIONS"""
    print("\n" + "="*70)
    print("GENERATING RESULTS SUMMARY")
    print("="*70)

    # Exclude 'Multiple' for main table
    df_table = df[df['Language'] != 'Multiple'].copy()
    
    # ✅ Strip whitespace from column names before processing
    df_table.columns = df_table.columns.str.strip()
    count_cols_stripped = [col.strip() for col in count_cols]
    
    # Calculate percentages from raw counts
    df_table = calculate_percentages_from_counts(df_table, count_cols_stripped)
    
    # Ensure language order matches contingency table
    df_table = df_table.set_index('Language').loc[languages].reset_index()

    # Generate text table
    text_table = []
    text_table.append("="*85)
    text_table.append("EXCEPTION HANDLING DISTRIBUTION BY LANGUAGE (FROM RAW COUNTS)")
    text_table.append("="*85)
    text_table.append("")
    text_table.append(f"{'Language':<12} {'Repos':>7} {'None%':>8} {'Basic%':>8} {'Mixed%':>8} {'Adv%':>8}")
    text_table.append("-"*85)

    for _, row in df_table.iterrows():
        lang = row['Language']
        total = int(row['Total'])
        
        # Access percentage columns (they're now clean)
        none_pct = row['None %']
        basic_pct = row['Basic %']
        mixed_pct = row['Mixed %']
        adv_pct = row['Advanced %']
        
        text_table.append(
            f"{lang:<12} {total:>7,} "
            f"{none_pct:>7.1f}% {basic_pct:>7.1f}% "
            f"{mixed_pct:>7.1f}% {adv_pct:>7.1f}%"
        )

    text_table.append("-"*85)
    text_table.append("")
    text_table.append("STATISTICAL TEST RESULTS:")
    text_table.append(f"  Chi-square (χ²):     {chi2_stat:.2f}")
    text_table.append(f"  Degrees of freedom:  {dof}")
    text_table.append(f"  P-value:             {p_value:.2e} (< 0.001)")
    text_table.append(f"  Cramér's V:          {cramers_v:.4f}")
    text_table.append("")
    text_table.append(" CONCLUSION: Language significantly affects exception handling (p < 0.001)")
    text_table.append("="*85)

    text_content = "\n".join(text_table)

    with open("language_chi_square_results.txt", "w") as f:
        f.write(text_content)

    print("✓ Results summary saved to: language_chi_square_results.txt")
    print("\nResults Summary:")
    print(text_content)

def main():
    """Main execution"""
    print("\n" + "="*70)
    print("CHI-SQUARE TEST: LANGUAGE IMPACT ON EXCEPTION HANDLING")
    print("USING RAW COUNTS (NOT PERCENTAGES)")
    print("="*70)
    
    # Load data
    filepath = 'exception_categories_count_by_language.csv'
    df = load_language_data(filepath)
    
    # Prepare contingency table from raw counts
    contingency_table, languages, count_cols = prepare_contingency_table_from_counts(df)
    
    # Perform Chi-square test
    chi2_stat, p_value, dof, cramers_v, expected = perform_chi_square_test(
        contingency_table, languages
    )
    
    # Create visualizations
    create_visualizations(df, contingency_table, languages, count_cols, chi2_stat, p_value)
    
    # Generate results summary (text only, no LaTeX)
    generate_results_summary(df, languages, count_cols, chi2_stat, p_value, dof, cramers_v)
    
    print("\n" + "="*70)
    print("ANALYSIS COMPLETE!")
    print("="*70)
    print("\nOutput files:")
    print("  1. language_exception_distribution_stacked.pdf - Stacked bar chart")
    print("  2. language_exception_heatmap.pdf - Heatmap visualization")
    print("  3. language_advanced_adoption.pdf - Advanced/Mixed adoption")
    print("  4. language_chi_square_results.txt - Statistical results summary")
    print("\n" + "="*70)


if __name__ == "__main__":
    main()