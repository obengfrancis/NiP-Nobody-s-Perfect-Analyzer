"""
RQ1 Analysis Script: Exception Handling Distribution
Author: Research Team
Date: January 2026
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# Set style for publication-quality plots
plt.style.use('seaborn-v0_8-paper')
sns.set_palette("husl")


def load_and_clean_data(filepath):
    """Load and clean the dataset, separating valid and failed parsers"""
    print("Loading data...")
    df = pd.read_csv(filepath)
    print(f"✓ Loaded {len(df):,} repositories")
    
    # Convert Parser Success Rate to numeric (remove % sign)
    df['Parser Success Rate Numeric'] = (
        df['Parser Success Rate'].astype(str).str.rstrip('%').astype(float)
    )
    
    # Separate valid repos from parser failures
    valid_df = df[df['Parser Success Rate Numeric'] > 0.0].copy()
    failed_df = df[df['Parser Success Rate Numeric'] == 0.0].copy()
    
    # Fill NaN values in Exception Type
    valid_df['Exception Type'] = valid_df['Exception Type'].fillna('None')
    
    print(f"\n✓ Valid repositories (parser success > 0%): {len(valid_df):,}")
    print(f"✓ Parser failures (parser success = 0%): {len(failed_df):,}")
    
    return df, valid_df, failed_df


def analyze_exception_types(valid_df, failed_df):
    """Analyze exception types with corrected percentage rounding"""
    print("\n" + "="*70)
    print("EXCEPTION HANDLING DISTRIBUTION ANALYSIS")
    print("="*70)
    
    # Define categories and their order
    categories = ['None', 'Basic', 'Mixed', 'Advanced']
    
    # Make Exception Type categorical with defined order
    valid_df['Exception Type'] = pd.Categorical(
        valid_df['Exception Type'], 
        categories=categories
    )
    
    # Count occurrences (reindex to ensure all categories present)
    exception_counts = valid_df['Exception Type'].value_counts().reindex(
        categories, 
        fill_value=0
    )
    
    # Calculate exact percentages (full precision)
    total_valid = len(valid_df)
    exception_percentages = (exception_counts / total_valid) * 100
    
    # ✅ CORRECTED: Round percentages and fix rounding residual
    percentages_rounded = exception_percentages.round(2)
    residual = 100.00 - percentages_rounded.sum()
    percentages_rounded.loc['Mixed'] = round(
        percentages_rounded.loc['Mixed'] + residual, 2
    )
    
    # Total counts
    total_failed = len(failed_df)
    total_all = total_valid + total_failed
    
    # Create results dictionary
    results = {
        'total_repositories': total_all,
        'valid_repositories': total_valid,
        'failed_repositories': total_failed,
        'counts': exception_counts,
        'percentages': exception_percentages,           # exact
        'percentages_rounded': percentages_rounded,     # adjusted to 100.00
        'categories': categories
    }
    
    # Print results
    print(f"\n{'='*70}")
    print(f"DATASET OVERVIEW")
    print(f"{'='*70}")
    print(f"Total repositories in dataset: {total_all:,}")
    print(f"Successfully analyzed: {total_valid:,} ({total_valid/total_all*100:.1f}%)")
    print(f"Parser failures: {total_failed:,} ({total_failed/total_all*100:.1f}%)")
    
    print(f"\n{'='*70}")
    print(f"EXCEPTION HANDLING DISTRIBUTION")
    print(f"{'='*70}")
    print(f"\n{'-'*70}")
    print(f"{'Exception Type':<20} {'Count':>15} {'Percentage':>15}")
    print(f"{'-'*70}")
    
    for exc_type in categories:
        count = int(exception_counts[exc_type])
        pct = percentages_rounded[exc_type]
        print(f"{exc_type:<20} {count:>15,} {pct:>14.2f}%")
    
    print(f"{'-'*70}")
    print(f"{'TOTAL (Valid)':<20} {total_valid:>15,} {100.00:>14.2f}%")
    print(f"{'-'*70}")
    
    # Key findings
    print(f"\n{'='*70}")
    print(f"KEY FINDINGS")
    print(f"{'='*70}")
    
    none_count = int(exception_counts['None'])
    with_handling = total_valid - none_count
    
    print(f"\n✓ Repositories WITH exception handling: {with_handling:,} "
          f"({with_handling/total_valid*100:.1f}%)")
    print(f"✗ Repositories WITHOUT exception handling: {none_count:,} "
          f"({percentages_rounded['None']:.2f}%)")
    
    advanced_count = int(exception_counts['Advanced'])
    mixed_count = int(exception_counts['Mixed'])
    advanced_mixed = advanced_count + mixed_count
    
    print(f"\n✓ Repositories with Advanced only: {advanced_count:,} "
          f"({percentages_rounded['Advanced']:.2f}%)")
    print(f"✓ Repositories with Mixed: {mixed_count:,} "
          f"({percentages_rounded['Mixed']:.2f}%)")
    print(f"✓ Total Advanced/Mixed: {advanced_mixed:,} "
          f"({advanced_mixed/total_valid*100:.1f}%)")
    print(f"○ Repositories with Basic only: {int(exception_counts['Basic']):,} "
          f"({percentages_rounded['Basic']:.2f}%)")
    
    # Verify percentages sum to 100%
    print(f"\n✓ Verification: Rounded percentages sum to {percentages_rounded.sum():.2f}%")
    
    return results


def create_pie_chart(results, output_path='exception_handling_pie.pdf', dpi=300):
    """Create pie chart with corrected percentage display"""
    print(f"\n{'='*70}")
    print(f"CREATING PIE CHART")
    print(f"{'='*70}")
    
    counts = results['counts']
    pct_rounded = results['percentages_rounded']
    categories = results['categories']
    
    # ✅ Custom autopct that uses pre-computed rounded percentages
    def autopct_from_map(labels):
        idx = {'i': 0}
        def _fmt(_pct):
            label = labels[idx['i']]
            idx['i'] += 1
            return f"{pct_rounded[label]:.2f}%"
        return _fmt
    
    # Color scheme
    colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12']
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Create pie chart
    wedges, texts, autotexts = ax.pie(
        counts.values,
        labels=categories,
        autopct=autopct_from_map(categories),
        startangle=90,
        colors=colors,
        textprops={'fontsize': 12, 'weight': 'bold'},
        #explode=[0.05, 0, 0, 0]  # Explode 'None'
    )
    
    # Style the text
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontsize(14)
        autotext.set_weight('bold')
    
    for text in texts:
        text.set_fontsize(14)
        text.set_weight('bold')
    

    
    ax.axis('equal')
    plt.tight_layout()
    
    # Save
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight', format='pdf')
    print(f"\n✓ Pie chart saved to: {output_path}")
    print(f"  Resolution: {dpi} DPI")
    
    plt.close(fig)
    
    return fig


def create_bar_chart(results, output_path='exception_handling_bar.png', dpi=300):
    """Create bar chart with corrected percentages"""
    print(f"\n{'='*70}")
    print(f"CREATING BAR CHART")
    print(f"{'='*70}")
    
    counts = results['counts']
    pct_rounded = results['percentages_rounded']
    categories = results['categories']
    
    # Color scheme
    colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12']
    
    # Create figure
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Create bars
    bars = ax.bar(categories, counts.values, color=colors, 
                   edgecolor='black', linewidth=1.5)
    
    # Add value labels
    for bar, cat in zip(bars, categories):
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width()/2.,
            height,
            f'{int(counts[cat]):,}\n({pct_rounded[cat]:.2f}%)',
            ha='center',
            va='bottom',
            fontsize=11,
            weight='bold'
        )
    
    # Labels and title
    ax.set_xlabel('Exception Handling Category', fontsize=14, weight='bold')
    ax.set_ylabel('Number of Repositories', fontsize=14, weight='bold')
    ax.set_title(
        f'Distribution of Exception Handling Categories\n'
        f'(n={results["valid_repositories"]:,} repositories)',
        fontsize=16,
        weight='bold',
        pad=20
    )
    
    # Format y-axis
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))
    
    # Grid
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    
    plt.tight_layout()
    
    # Save
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
    print(f"✓ Bar chart saved to: {output_path}")
    
    plt.close(fig)
    
    return fig


def generate_summary_table(results, output_path='exception_handling_summary.txt'):
    """Generate text summary table with corrected percentages"""
    print(f"\n{'='*70}")
    print(f"GENERATING SUMMARY TABLE")
    print(f"{'='*70}")
    
    counts = results['counts']
    pct_rounded = results['percentages_rounded']
    categories = results['categories']
    total_valid = results['valid_repositories']
    total_failed = results['failed_repositories']
    total_all = results['total_repositories']
    
    # Build table
    lines = []
    lines.append("="*70)
    lines.append("TABLE 1: OVERALL EXCEPTION HANDLING DISTRIBUTION")
    lines.append("="*70)
    lines.append("")
    lines.append(f"Total repositories analyzed: {total_all:,}")
    lines.append(f"Successfully parsed: {total_valid:,} "
                 f"({total_valid/total_all*100:.1f}%)")
    lines.append(f"Parser failures (excluded): {total_failed:,} "
                 f"({total_failed/total_all*100:.1f}%)")
    lines.append("")
    lines.append(f"{'Exception Type':<20} {'Count':>15} {'Percentage':>15}")
    lines.append("-"*70)
    
    for cat in categories:
        lines.append(f"{cat:<20} {int(counts[cat]):>15,} "
                     f"{pct_rounded[cat]:>14.2f}%")
    
    lines.append("-"*70)
    lines.append(f"{'Total (Valid)':<20} {total_valid:>15,} {100.00:>14.2f}%")
    lines.append("="*70)
    lines.append("")
    lines.append("KEY FINDINGS:")
    lines.append("-"*70)
    
    none_count = int(counts['None'])
    with_handling = total_valid - none_count
    advanced_mixed = int(counts['Advanced']) + int(counts['Mixed'])
    
    lines.append(f"Repositories WITH exception handling: {with_handling:,} "
                 f"({with_handling/total_valid*100:.1f}%)")
    lines.append(f"Repositories WITHOUT exception handling: {none_count:,} "
                 f"({pct_rounded['None']:.2f}%)")
    lines.append(f"Repositories with Advanced/Mixed: {advanced_mixed:,} "
                 f"({advanced_mixed/total_valid*100:.1f}%)")
    lines.append("")
    lines.append("="*70)
    
    content = '\n'.join(lines)
    
    # Save
    with open(output_path, 'w') as f:
        f.write(content)
    
    print(f"✓ Summary table saved to: {output_path}")
    print("\nTable Preview:")
    print(content)


def main():
    """Main execution function"""
    print("\n" + "="*70)
    print("EXCEPTION HANDLING ANALYSIS - CORRECTED PERCENTAGES")
    print("="*70)
    
    csv_file = 'nip_analyzer_output.csv'
    
    try:
        # Load data
        df_all, df_valid, df_failed = load_and_clean_data(csv_file)
        
        # Analyze
        results = analyze_exception_types(df_valid, df_failed)
        
        # Verify data consistency
        assert results['counts'].sum() == results['valid_repositories'], \
            "Count sum doesn't match valid repositories"
        
        # Generate outputs
        print("\nGenerating visualizations...")
        create_pie_chart(results, output_path='exception_handling_pie.pdf')
        create_bar_chart(results, output_path='exception_handling_bar.png')
        generate_summary_table(results, output_path='exception_handling_summary.txt')
        
        print("\n" + "="*70)
        print("ANALYSIS COMPLETE!")
        print("="*70)
        print("\nOutput files:")
        print("  1. exception_handling_pie.pdf")
        print("  2. exception_handling_bar.png")
        print("  3. exception_handling_summary.txt")
        print("\n" + "="*70)
        
        print("\nVerification: Rounded percentages (sum to 100.00%):")
        print(results['percentages_rounded'])
        
    except FileNotFoundError:
        print(f"\nError: Could not find file: {csv_file}")
        print("Please ensure the file is in the current directory.")
    except Exception as e:
        print(f"\n Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()