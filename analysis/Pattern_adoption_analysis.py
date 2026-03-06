"""
Pattern Adoption Analysis by Language
Author: Research Team
Date: February 2026
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap

# Set style
plt.style.use('seaborn-v0_8-paper')
sns.set_palette("husl")


def load_and_prepare_data(filepath):
    """Load pattern adoption data and calculate percentages"""
    print("="*70)
    print("LOADING PATTERN ADOPTION DATA")
    print("="*70)
    
    # ✅ Read CSV instead of Excel
    df = pd.read_csv(filepath)
    
    # ✅ Strip whitespace from column names (in case CSV has spaces)
    df.columns = df.columns.str.strip()
    
    # Remove the "Single-Repo Total" and NaN rows
    df = df[df['Language'].notna()]
    df = df[~df['Language'].isin(['Single-Repo Total', 'NaN', 'nan'])]
    
    print(f"\n✓ Loaded data for {len(df)} language categories")
    print(f"✓ Columns: {list(df.columns)}")
    
    # Repository counts
    repo_counts = {
        'Python': 2399,
        'Java': 301,
        'Javascript': 6320,
        'Typescript': 386,
        'Go': 147,
        'C#': 86,
        'Ruby': 164,
        'Kotlin': 146,
        'Swift': 107,
        'Multiple': 6820
    }
    
    # Add total repos column
    df['Total_Repos'] = df['Language'].map(repo_counts)
    
    # Calculate percentages for each pattern
    patterns = ['Try-Catch', 'Timeout', 'Retry', 'Circuit Breaker', 'Backoff', 'Status Check']
    
    for pattern in patterns:
        if pattern in df.columns:
            df[f'{pattern}_Pct'] = (df[pattern] / df['Total_Repos'] * 100).round(1)
        else:
            print(f"Warning: Pattern '{pattern}' not found in CSV columns")
    
    print("\nPattern Adoption Data (with percentages):")
    display_cols = ['Language', 'Total_Repos'] + [f'{p}_Pct' for p in patterns if f'{p}_Pct' in df.columns]
    print(df[display_cols].to_string(index=False))
    
    return df, patterns

def analyze_pattern_adoption(df, patterns):
    """Analyze pattern adoption statistics - CORRECTED"""
    print("\n" + "="*70)
    print("PATTERN ADOPTION ANALYSIS (CORRECTED)")
    print("="*70)
    
    # Separate single-language from multi-language
    df_single = df[df['Language'] != 'Multiple'].copy()
    df_multi = df[df['Language'] == 'Multiple'].copy()
    
    # CRITICAL: Calculate total single-language repos
    total_single_repos = df_single['Total_Repos'].sum()
    total_multi_repos = df_multi['Total_Repos'].sum()
    
    print(f"\nTotal single-language repos: {total_single_repos:,}")
    print(f"Total multi-language repos:  {total_multi_repos:,}")
    
    # CORRECTED: Weighted pattern percentages
    print("\n" + "-"*70)
    print("WEIGHTED PATTERN ADOPTION RATES")
    print("-"*70)
    print("\nFormula: (Total pattern occurrences) / (Total repos) × 100")
    print()
    
    for pattern in patterns:
        single_count = df_single[pattern].sum()
        single_pct = (single_count / total_single_repos) * 100
        
        multi_count = df_multi[pattern].sum()
        multi_pct = (multi_count / total_multi_repos) * 100
        
        diff_pct = multi_pct - single_pct
        ratio = multi_pct / single_pct if single_pct > 0 else float('inf')
        
        print(f"{pattern:<18}")
        print(f"  Single-lang: {single_count:>5.0f} / {total_single_repos:>6,} = {single_pct:>5.1f}%")
        print(f"  Multi-lang:  {multi_count:>5.0f} / {total_multi_repos:>6,} = {multi_pct:>5.1f}%")
        print(f"  Difference:  {diff_pct:>+5.1f}% ({ratio:.2f}× ratio)")
        print()
    
    # Summary statistics
    print("-"*70)
    print("SUMMARY: CROSS-POLLINATION EFFECT")
    print("-"*70)
    
    single_avg_pct = sum([df_single[p].sum() / total_single_repos * 100 for p in patterns]) / len(patterns)
    multi_avg_pct = sum([df_multi[p].sum() / total_multi_repos * 100 for p in patterns]) / len(patterns)
    
    print(f"\nAverage pattern adoption rate (across 6 patterns):")
    print(f"  Single-language: {single_avg_pct:.1f}%")
    print(f"  Multi-language:  {multi_avg_pct:.1f}%")
    print(f"  Difference:      {multi_avg_pct - single_avg_pct:+.1f}% ({(multi_avg_pct/single_avg_pct - 1)*100:.1f}% higher)")
    
    print("\n NOTE: This is the AVERAGE adoption rate across patterns,")
    print("    not 'patterns per repository' (which would require per-repo data)")
    
    return df_single, df_multi, total_single_repos, total_multi_repos


def create_pattern_comparison_corrected(df_single, df_multi, patterns, 
                                         total_single, total_multi, output_path):
    """Create CORRECTED grouped bar chart comparing single vs multi-language"""
    print("\n" + "="*70)
    print("CREATING CORRECTED SINGLE VS MULTI-LANGUAGE COMPARISON")
    print("="*70)
    
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # CORRECTED: Calculate weighted percentages
    single_vals = [(df_single[p].sum() / total_single * 100) for p in patterns]
    multi_vals = [(df_multi[p].sum() / total_multi * 100) for p in patterns]
    
    x = np.arange(len(patterns))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, single_vals, width, label='Single-Language', 
                  color='#3498db', edgecolor='black', linewidth=1.5)
    bars2 = ax.bar(x + width/2, multi_vals, width, label='Multi-Language', 
                  color="#e74c3c", edgecolor='black', linewidth=1.5)
    
    # Add value labels
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.1f}%',
                   ha='center', va='bottom', fontsize=16, weight='bold')
    
    # Labels and title
    ax.set_xlabel('Resilience Pattern', fontsize=16, weight='bold')
    ax.set_ylabel('Adoption Rate (%)', fontsize=16, weight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(patterns, rotation=45, fontsize=16, ha='right')
    ax.legend(loc='upper right', bbox_to_anchor=(1.0, 1.05), 
             frameon=True, shadow=True, fontsize=16)
    
    # Grid
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ CORRECTED comparison chart saved to: {output_path}")
    plt.close()
    
    
def create_pattern_heatmap(df_single, patterns, output_path):
    """Create heatmap - GREEN = HIGH adoption with BLACK text"""
    print("\n" + "="*70)
    print("CREATING PATTERN ADOPTION HEATMAP")
    print("="*70)
        
    languages = df_single['Language'].tolist()
        
    heatmap_data = []
    for _, row in df_single.iterrows():
        row_data = [row[f'{p}_Pct'] if f'{p}_Pct' in df_single.columns else 0 for p in patterns]
        heatmap_data.append(row_data)
    
    # ✅ Wrap long pattern names for better display
    wrapped_patterns = []
    for p in patterns:
        if p == 'Circuit Breaker':
            wrapped_patterns.append('Circuit\nBreaker')
        elif p == 'Status Check':
            wrapped_patterns.append('Status\nCheck')
        else:
            wrapped_patterns.append(p)
    
    heatmap_df = pd.DataFrame(heatmap_data, index=languages, columns=wrapped_patterns)
        
    fig, ax = plt.subplots(figsize=(12, 8))
        
    # Use RdYlGn (Red-Yellow-Green) - Green = high
    sns.heatmap(
        heatmap_df,
        annot=True,
        fmt='.1f',
        cmap='RdYlGn',  # Red-Yellow-Green
        cbar_kws={'label': 'Adoption Rate (%)'},
        linewidths=0.5,
        linecolor='gray',
        vmin=0,
        vmax=100,
        ax=ax,
        annot_kws={"size": 16, "weight": "bold", "color": "black"}  
    )
    
    #  Add percentage signs to cell annotations
    for text in ax.texts:
        current_text = text.get_text()
        if current_text and current_text != '':
            text.set_text(f'{current_text}%')
            text.set_color('black')  
        
    ax.set_xlabel('Resilience Pattern', fontsize=16, weight='bold', color='black')
    ax.set_ylabel('Programming Language', fontsize=16, weight='bold', color='black')
   
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right', fontsize=16, color='black')
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=16, color='black')
    
 
    ax.tick_params(axis='x', colors='black', labelsize=16)
    ax.tick_params(axis='y', colors='black', labelsize=16)
        
    cbar = ax.collections[0].colorbar
    cbar.ax.tick_params(labelsize=16, colors='black')  
    cbar.set_label('Adoption Rate (%)', fontsize=16, weight='bold', color='black')
        
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Pattern adoption heatmap saved to: {output_path}")
    plt.close()    
    

def generate_corrected_findings(df_single, df_multi, patterns, total_single, total_multi):
    """Generate corrected findings for the paper"""
    print("\n" + "="*70)
    print("CORRECTED FINDINGS FOR PAPER")
    print("="*70)
    
    print("\n✅ CORRECT CLAIM:")
    print("-"*70)
    print("""
Multi-language repositories exhibit systematically higher adoption 
across all six resilience patterns. Pattern-specific differences:

""")
    
    for pattern in patterns:
        single_count = df_single[pattern].sum()
        single_pct = (single_count / total_single) * 100
        
        multi_count = df_multi[pattern].sum()
        multi_pct = (multi_count / total_multi) * 100
        
        diff_pct = multi_pct - single_pct
        ratio = multi_pct / single_pct if single_pct > 0 else float('inf')
        
        print(f"  • {pattern}: {multi_pct:.1f}% vs {single_pct:.1f}% "
              f"({ratio:.2f}× higher, +{diff_pct:.1f} percentage points)")
    
    print("\n" + "="*70)
    print("SUGGESTED PAPER TEXT")
    print("="*70)
 

def main():
    """Main execution - CORRECTED VERSION"""
    print("\n" + "="*70)
    print("PATTERN ADOPTION ANALYSIS (CORRECTED)")
    print("="*70)
    
    # ✅ Use CSV file instead of Excel
    filepath = 'Pattern_Adoption_By_Language.csv'
    df, patterns = load_and_prepare_data(filepath)
    
    # Analyze (corrected)
    df_single, df_multi, total_single, total_multi = analyze_pattern_adoption(df, patterns)
    
    
    # Create corrected visualization
    create_pattern_comparison_corrected(
        df_single, df_multi, patterns, total_single, total_multi,
        'pattern_single_vs_multi_CORRECTED.pdf'
    )
    
    
      # This will now work because create_pattern_heatmap() is defined above
    create_pattern_heatmap(
        df_single, patterns,
        'pattern_adoption_heatmap.pdf'
    )
  
    
  
    # Generate corrected findings
    generate_corrected_findings(df_single, df_multi, patterns, total_single, total_multi)
    
    print("\n" + "="*70)
    print("CORRECTED ANALYSIS COMPLETE!")
    print("="*70)
    print("\nKey correction:")
    print(" NEW: Weighted average by repository count")
    print()
    print("Output: pattern_single_vs_multi_CORRECTED.pdf")
    print("\n" + "="*70)


if __name__ == "__main__":
    main()