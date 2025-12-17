#!/usr/bin/env python3
"""
Updated analysis.py for Flask web application

Analyzes CSV files and generates comprehensive statistics and visualizations
"""

import sys
from pathlib import Path
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
import math
import warnings
import tempfile

warnings.filterwarnings("ignore", category=UserWarning)
# Set matplotlib to use non-interactive backend for web applications
plt.switch_backend('Agg')

# ---------- Helpers ----------
def ensure_dir(p):
    """Ensure directory exists"""
    os.makedirs(p, exist_ok=True)
    return Path(p)

def safe_skew(s):
    """Safely calculate skewness"""
    try:
        return float(stats.skew(s.dropna()))
    except Exception:
        return float('nan')

def safe_kurtosis(s):
    """Safely calculate kurtosis"""
    try:
        return float(stats.kurtosis(s.dropna()))
    except Exception:
        return float('nan')

def compute_numeric_stats(s: pd.Series):
    """Compute comprehensive statistics for numeric columns"""
    s_non = s.dropna()
    cnt = int(s.count())
    missing = int(s.isna().sum())
    unique = int(s.nunique(dropna=True))
    
    if cnt == 0:
        return {
            'count': cnt, 'missing': missing, 'unique': unique,
            'mean': np.nan, 'median': np.nan, 'std': np.nan, 'var': np.nan,
            'min': np.nan, 'max': np.nan,
            'p10': np.nan, 'p25': np.nan, 'p50': np.nan, 'p75': np.nan, 'p90': np.nan,
            'iqr': np.nan, 'skew': np.nan, 'kurtosis': np.nan, 'modes': []
        }
    
    mean = float(s_non.mean())
    median = float(s_non.median())
    sd = float(s_non.std())
    var = float(s_non.var())
    mn = float(s_non.min())
    mx = float(s_non.max())
    p10 = float(s_non.quantile(0.10))
    p25 = float(s_non.quantile(0.25))
    p50 = float(s_non.quantile(0.50))
    p75 = float(s_non.quantile(0.75))
    p90 = float(s_non.quantile(0.90))
    iqr = p75 - p25
    skew = safe_skew(s_non)
    kurt = safe_kurtosis(s_non)
    
    # modes (could be multiple)
    try:
        modes = s_non.mode().tolist()
    except Exception:
        modes = []
    
    return {
        'count': cnt, 'missing': missing, 'unique': unique,
        'mean': mean, 'median': median, 'std': sd, 'var': var,
        'min': mn, 'max': mx,
        'p10': p10, 'p25': p25, 'p50': p50, 'p75': p75, 'p90': p90,
        'iqr': iqr, 'skew': skew, 'kurtosis': kurt, 'modes': modes
    }

def compute_categorical_stats(s: pd.Series):
    """Compute statistics for categorical columns"""
    cnt = int(s.count())
    missing = int(s.isna().sum())
    unique = int(s.nunique(dropna=True))
    top = []
    
    try:
        vc = s.value_counts(dropna=True)
        top = [(str(idx), int(val)) for idx, val in vc.head(10).items()]
    except Exception:
        top = []
    
    return {'count': cnt, 'missing': missing, 'unique': unique, 'top_values': top}

# ---------- Column detection ----------
def detect_column_types(df: pd.DataFrame, datetime_threshold=0.8):
    """Detect and classify column types"""
    num = df.select_dtypes(include=[np.number]).columns.tolist()
    datetime_cols = []
    
    for c in df.columns:
        if c in num: 
            continue
        try:
            parsed = pd.to_datetime(df[c], errors='coerce')
            if parsed.notna().mean() >= datetime_threshold:
                datetime_cols.append(c)
                df[c] = parsed
        except Exception:
            pass
    
    cat = [c for c in df.select_dtypes(include=['object', 'category']).columns.tolist() 
           if c not in datetime_cols]
    
    return num, cat, datetime_cols

# ---------- Chart functions (save only, no display for web) ----------
def save_chart(fig, out_path):
    """Save chart to file"""
    fig.tight_layout()
    try:
        fig.savefig(out_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        return str(out_path)
    except Exception as e:
        plt.close(fig)
        return None

def chart_histograms_overlay(df, numeric_cols, out_dir):
    """Create overlay histograms for numeric columns"""
    if not numeric_cols: 
        return None
    
    cols = numeric_cols[:5]  # Limit to 5 columns
    fig, ax = plt.subplots(figsize=(10, 6))
    
    colors = ['blue', 'red', 'green', 'orange', 'purple']
    
    for i, c in enumerate(cols):
        data = df[c].dropna()
        if data.empty: 
            continue
        
        ax.hist(data, bins=30, alpha=0.6, label=c, 
                color=colors[i % len(colors)], histtype='stepfilled')
    
    ax.set_title('Distribution Overlay (Top 5 Numeric Columns)', fontsize=14)
    ax.set_xlabel('Value')
    ax.set_ylabel('Frequency')
    if len(cols) > 1:
        ax.legend()
    
    fname = out_dir / 'histograms_overlay.png'
    return save_chart(fig, fname)

def chart_separate_histograms(df, numeric_cols, out_dir):
    """Create separate histograms for each numeric column"""
    created = []
    
    for c in numeric_cols[:10]:  # Limit to prevent too many files
        data = df[c].dropna()
        if data.empty: 
            continue
        
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.hist(data, bins=30, color='skyblue', edgecolor='black', alpha=0.7)
        ax.set_title(f'Distribution of {c}', fontsize=14)
        ax.set_xlabel(c)
        ax.set_ylabel('Frequency')
        ax.grid(True, alpha=0.3)
        
        fname = out_dir / f'hist_{c.replace(" ", "_").replace("/", "_")}.png'
        result = save_chart(fig, fname)
        if result:
            created.append(result)
    
    return created

def chart_boxplot(df, numeric_cols, out_dir):
    """Create boxplots for numeric columns"""
    if not numeric_cols:
        return None
    
    # Limit to 10 columns for readability
    cols_to_plot = numeric_cols[:10]
    data = []
    labels = []
    
    for c in cols_to_plot:
        col_data = df[c].dropna()
        if not col_data.empty:
            data.append(col_data)
            labels.append(c)
    
    if not data:
        return None
    
    fig, ax = plt.subplots(figsize=(12, 8))
    bp = ax.boxplot(data, labels=labels, vert=True, patch_artist=True)
    
    # Color the boxes
    colors = plt.cm.Set3(np.linspace(0, 1, len(bp['boxes'])))
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    ax.set_title('Boxplots of Numeric Columns', fontsize=14)
    ax.set_xlabel('Columns')
    ax.set_ylabel('Values')
    plt.xticks(rotation=45, ha='right')
    
    fname = out_dir / 'boxplot_numeric.png'
    return save_chart(fig, fname)

def chart_correlation_heatmap(df, numeric_cols, out_dir):
    """Create correlation heatmap"""
    if len(numeric_cols) < 2:
        return None
    
    # Limit to 15 columns for readability
    cols_to_plot = numeric_cols[:15]
    corr = df[cols_to_plot].corr()
    
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # Create heatmap
    im = ax.imshow(corr.values, cmap='RdYlBu_r', aspect='auto', 
                   vmin=-1, vmax=1, interpolation='nearest')
    
    # Add colorbar
    cbar = plt.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label('Correlation Coefficient', rotation=270, labelpad=20)
    
    # Set ticks and labels
    ax.set_xticks(range(len(corr.columns)))
    ax.set_yticks(range(len(corr.index)))
    ax.set_xticklabels(corr.columns, rotation=45, ha='right')
    ax.set_yticklabels(corr.index)
    
    # Add correlation values as text
    for i in range(corr.shape[0]):
        for j in range(corr.shape[1]):
            text_color = 'white' if abs(corr.values[i, j]) > 0.5 else 'black'
            ax.text(j, i, f'{corr.values[i,j]:.2f}', 
                   ha='center', va='center', color=text_color, fontsize=8)
    
    ax.set_title('Correlation Matrix Heatmap', fontsize=14)
    
    fname = out_dir / 'correlation_heatmap.png'
    return save_chart(fig, fname)

def chart_top_categories(df, categorical_cols, out_dir):
    """Create bar chart for top categories"""
    if not categorical_cols:
        return None
    
    # Find the categorical column with most non-null values
    best_col = max(categorical_cols, key=lambda c: df[c].notna().sum())
    vc = df[best_col].value_counts(dropna=True).head(15)
    
    if vc.empty:
        return None
    
    fig, ax = plt.subplots(figsize=(12, 8))
    bars = ax.bar(range(len(vc)), vc.values, color='lightcoral', alpha=0.8)
    
    # Add value labels on bars
    for i, (bar, value) in enumerate(zip(bars, vc.values)):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + value*0.01,
                str(value), ha='center', va='bottom', fontsize=10)
    
    ax.set_xlabel('Categories')
    ax.set_ylabel('Count')
    ax.set_title(f'Top 15 Values in "{best_col}"', fontsize=14)
    ax.set_xticks(range(len(vc)))
    ax.set_xticklabels([str(x)[:20] + '...' if len(str(x)) > 20 else str(x) 
                       for x in vc.index], rotation=45, ha='right')
    
    fname = out_dir / f'top_categories_{best_col.replace(" ", "_").replace("/", "_")}.png'
    return save_chart(fig, fname)

def chart_scatter_top_correlation(df, numeric_cols, out_dir):
    """Create scatter plot of most correlated variables"""
    if len(numeric_cols) < 2:
        return None
    
    # Calculate correlation matrix and find highest correlation
    corr = df[numeric_cols].corr().abs()
    
    # Remove diagonal elements
    corr_vals = corr.where(~np.eye(corr.shape[0], dtype=bool))
    
    try:
        # Find the pair with highest correlation
        max_corr_idx = np.unravel_index(np.nanargmax(corr_vals.values), corr_vals.shape)
        col1 = corr_vals.index[max_corr_idx[0]]
        col2 = corr_vals.columns[max_corr_idx[1]]
        corr_value = corr.loc[col1, col2]
        
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Create scatter plot
        ax.scatter(df[col1], df[col2], alpha=0.6, s=50, color='steelblue')
        
        # Add trend line
        try:
            z = np.polyfit(df[col1].dropna(), df[col2].dropna(), 1)
            p = np.poly1d(z)
            ax.plot(df[col1], p(df[col1]), "r--", alpha=0.8, linewidth=2)
        except:
            pass
        
        ax.set_xlabel(col1)
        ax.set_ylabel(col2)
        ax.set_title(f'Scatter Plot: {col1} vs {col2}\n(Correlation: {corr_value:.3f})', fontsize=14)
        ax.grid(True, alpha=0.3)
        
        fname = out_dir / f'scatter_{col1.replace(" ", "_")}_{col2.replace(" ", "_")}.png'
        return save_chart(fig, fname)
    
    except Exception:
        return None

# ---------- Main analyze function ----------
def analyze_csv(path_csv):
    """Main function to analyze CSV and generate comprehensive report"""
    p = Path(path_csv)
    if not p.exists():
        raise FileNotFoundError(f"{p} not found")
    
    # Read the CSV file
    try:
        df = pd.read_csv(p)
    except Exception as e:
        raise Exception(f"Error reading CSV file: {str(e)}")
    
    if df.empty:
        raise Exception("The CSV file is empty")
    
    # Create output directory
    out_dir = ensure_dir(p.parent / (p.stem + "_analysis_outputs"))
    
    # Detect column types
    numeric_cols, categorical_cols, datetime_cols = detect_column_types(df.copy())
    
    print(f"Detected {len(numeric_cols)} numeric, {len(categorical_cols)} categorical, {len(datetime_cols)} datetime columns")
    
    # Compute statistics
    rows = []
    
    # Process numeric columns
    for c in numeric_cols:
        stats_dict = compute_numeric_stats(df[c])
        stats_dict_flat = {f"num_{k}": v if k != 'modes' else ','.join(map(str, v)) 
                          for k, v in stats_dict.items()}
        stats_dict_flat['column'] = c
        stats_dict_flat['dtype'] = str(df[c].dtype)
        stats_dict_flat['column_type'] = 'numeric'
        rows.append(stats_dict_flat)
    
    # Process categorical columns
    for c in categorical_cols:
        stats_dict = compute_categorical_stats(df[c])
        flat = {'column': c, 'dtype': str(df[c].dtype), 'column_type': 'categorical',
                'cat_count': stats_dict['count'], 'cat_missing': stats_dict['missing'],
                'cat_unique': stats_dict['unique']}
        
        # Add top values
        for i, (val, cnt) in enumerate(stats_dict['top_values'][:5], start=1):
            flat[f'top{i}_value'] = val
            flat[f'top{i}_count'] = cnt
        
        rows.append(flat)
    
    # Save summary statistics
    if rows:
        summary_df = pd.DataFrame(rows)
        summary_csv = out_dir / 'summary_statistics.csv'
        summary_df.to_csv(summary_csv, index=False)
        print(f"✓ Saved summary statistics to: {summary_csv}")
    
    # Generate visualizations
    created_charts = []
    
    # 1. Histogram overlay
    try:
        chart = chart_histograms_overlay(df, numeric_cols, out_dir)
        if chart: created_charts.append(chart)
    except Exception as e:
        print(f"Failed to create histogram overlay: {e}")
    
    # 2. Individual histograms
    try:
        charts = chart_separate_histograms(df, numeric_cols, out_dir)
        created_charts.extend(charts)
    except Exception as e:
        print(f"Failed to create individual histograms: {e}")
    
    # 3. Boxplots
    try:
        chart = chart_boxplot(df, numeric_cols, out_dir)
        if chart: created_charts.append(chart)
    except Exception as e:
        print(f"Failed to create boxplots: {e}")
    
    # 4. Correlation heatmap
    try:
        chart = chart_correlation_heatmap(df, numeric_cols, out_dir)
        if chart: created_charts.append(chart)
    except Exception as e:
        print(f"Failed to create correlation heatmap: {e}")
    
    # 5. Top categories
    try:
        chart = chart_top_categories(df, categorical_cols, out_dir)
        if chart: created_charts.append(chart)
    except Exception as e:
        print(f"Failed to create category chart: {e}")
    
    # 6. Scatter plot of most correlated variables
    try:
        chart = chart_scatter_top_correlation(df, numeric_cols, out_dir)
        if chart: created_charts.append(chart)
    except Exception as e:
        print(f"Failed to create scatter plot: {e}")
    
    # Print summary
    print(f"\n=== Analysis Complete ===")
    print(f"Dataset: {len(df)} rows × {len(df.columns)} columns")
    print(f"Numeric columns: {len(numeric_cols)}")
    print(f"Categorical columns: {len(categorical_cols)}")
    print(f"DateTime columns: {len(datetime_cols)}")
    print(f"Charts created: {len(created_charts)}")
    
    return {
        'summary_csv': str(summary_csv) if rows else None,
        'charts': created_charts,
        'out_dir': str(out_dir),
        'dataset_info': {
            'rows': len(df),
            'columns': len(df.columns),
            'numeric_cols': len(numeric_cols),
            'categorical_cols': len(categorical_cols),
            'datetime_cols': len(datetime_cols)
        }
    }

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python analysis.py <csv_file_path>")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    try:
        result = analyze_csv(csv_path)
        print(f"\nAnalysis completed successfully!")
        print(f"Results saved to: {result['out_dir']}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)