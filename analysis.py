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
    """Detect and classify column types with aggressive numeric conversion"""
    # Try to convert object columns to numeric if they look like numbers
    for col in df.select_dtypes(include=['object']).columns:
        try:
            # Attempt numeric conversion
            # Clean common non-numeric chars like currency symbols or commas if simple
            # But pd.to_numeric with coerce is safer for now
            # count valid numbers vs total
            converted = pd.to_numeric(df[col], errors='coerce')
            valid_ratio = converted.notna().sum() / len(df)
            
            # If more than 50% are valid numbers or if it was intended as numeric (less strict)
            if valid_ratio > 0.5 and df[col].nunique() > 5: # heuristic: low cardinality might be categorical categorical
                df[col] = converted
        except:
            pass

    num = df.select_dtypes(include=[np.number]).columns.tolist()
    datetime_cols = []
    
    for c in df.columns:
        if c in num: 
            continue
        try:
            # Check for datetime
            if df[c].dtype == 'object':
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
# ---------- Quality Score ----------
def calculate_quality_score(df):
    """
    Calculate a Data Quality Score (0-100).
    Based on: missing values, duplicates, outliers (simple detection).
    """
    try:
        score = 100.0
        row_count = len(df)
        if row_count == 0:
            return 0.0

        # 1. Missing Values (weight 40%)
        total_cells = df.size
        missing_cells = df.isna().sum().sum()
        missing_pct = (missing_cells / total_cells) * 100
        score -= (missing_pct * 0.4)

        # 2. Duplicate Rows (weight 30%)
        # Note: This might be expensive on huge datasets, but okay for this scale
        dup_count = df.duplicated().sum()
        dup_pct = (dup_count / row_count) * 100
        score -= (dup_pct * 0.3)

        # 3. Outlier "Potential" (weight 20%) - very heuristic
        # checking numeric columns for values outside 3 std devs
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            outlier_ratios = []
            for col in numeric_cols:
                # simple Z-score estimate
                col_data = df[col].dropna()
                if len(col_data) > 0:
                    z_scores = np.abs(stats.zscore(col_data))
                    outliers = (z_scores > 3).sum()
                    outlier_ratios.append(outliers / len(col_data))
            
            if outlier_ratios:
                avg_outlier_pct = np.mean(outlier_ratios) * 100
                score -= (avg_outlier_pct * 0.2)

        # 4. Column Naming Convention (weight 10%)
        # punishment for spaces or special chars in columns
        bad_col_names = sum(1 for c in df.columns if ' ' in str(c) or not str(c).isidentifier())
        bad_col_pct = (bad_col_names / len(df.columns)) * 100
        score -= (bad_col_pct * 0.1)

        return max(0.0, round(score, 1))
    except Exception as e:
        print(f"Error calculating quality score: {e}")
        return 0.0

# ---------- Main analyze function ----------
def analyze_df(df, out_dir_path):
    """
    Analyze a DataFrame and generate reports/charts.
    Returns a dictionary with comprehensive results.
    """
    out_dir = ensure_dir(out_dir_path)
    
    # 1. Quality Score
    quality_score = calculate_quality_score(df)
    
    # 2. Column Detection
    numeric_cols, categorical_cols, datetime_cols = detect_column_types(df)
    
    # 3. Generate Charts (Images)
    created_charts = []
    
    # Histograms
    try:
        chart = chart_histograms_overlay(df, numeric_cols, out_dir)
        if chart: created_charts.append(os.path.basename(chart))
    except Exception: pass
    
    try:
        charts = chart_separate_histograms(df, numeric_cols, out_dir)
        if charts: created_charts.extend([os.path.basename(c) for c in charts])
    except Exception: pass
    
    # Boxplots
    try:
        chart = chart_boxplot(df, numeric_cols, out_dir)
        if chart: created_charts.append(os.path.basename(chart))
    except Exception: pass
    
    # Correlation Heatmap
    try:
        chart = chart_correlation_heatmap(df, numeric_cols, out_dir)
        if chart: created_charts.append(os.path.basename(chart))
    except Exception: pass
    
    # Top Categories
    try:
        chart = chart_top_categories(df, categorical_cols, out_dir)
        if chart: created_charts.append(os.path.basename(chart))
    except Exception: pass
    
    # Scatter
    try:
        chart = chart_scatter_top_correlation(df, numeric_cols, out_dir)
        if chart: created_charts.append(os.path.basename(chart))
    except Exception: pass

    # 4. Generate JSON Stats (Compatible with frontend needs)
    analysis_info = {
        'dataset_shape': df.shape,
        'quality_score': quality_score,
        'missing_cells': int(df.isna().sum().sum()),
        'duplicate_rows': int(df.duplicated().sum()),
        'columns': [],
        'correlation': {},
        'charts': created_charts, # List of filenames
        'column_alerts': [] # For UI insights
    }
    
    # Compute detailed column stats
    for col in df.columns:
        col_type = 'numeric' if col in numeric_cols else 'categorical'
        if col in datetime_cols: col_type = 'datetime'
        
        col_data = {
            'name': col,
            'type': col_type,
            'missing': int(df[col].isna().sum()),
            'unique': int(df[col].nunique()),
            'dtype': str(df[col].dtype)
        }
        
        # Alerts
        if col_data['missing'] / len(df) > 0.5:
            analysis_info['column_alerts'].append({
                'column': col, 'type': 'warning', 'msg': 'High missing values (>50%)'
            })
        if col_data['unique'] == 1:
            analysis_info['column_alerts'].append({
                'column': col, 'type': 'warning', 'msg': 'Zero variance (constant value)'
            })

        if col in numeric_cols:
            stats_res = compute_numeric_stats(df[col])
            col_data.update(stats_res)
            # Add full describe() for chat/detailed view
            try:
                desc = df[col].describe().to_dict()
                col_data['describe'] = desc
            except: pass
            
            if stats_res.get('missing', 0) == 0 and stats_res.get('std', 0) == 0:
                 analysis_info['column_alerts'].append({
                    'column': col, 'type': 'warning', 'msg': 'Zero variance'
                })
            # Check skew
            if abs(stats_res.get('skew', 0) or 0) > 2:
                 analysis_info['column_alerts'].append({
                    'column': col, 'type': 'info', 'msg': f"Highly skewed ({stats_res['skew']:.2f})"
                })
        elif col in categorical_cols:
            stats_res = compute_categorical_stats(df[col])
            col_data.update(stats_res)
            try:
                desc = df[col].astype(str).describe().to_dict()
                col_data['describe'] = desc
            except: pass

            if stats_res.get('unique', 0) > 50:
                 analysis_info['column_alerts'].append({
                    'column': col, 'type': 'info', 'msg': f"High cardinality ({stats_res['unique']} unique)"
                })
        
        analysis_info['columns'].append(col_data)

    # Correlation matrix for JSON
    if len(numeric_cols) > 0:
        try:
            corr = df[numeric_cols].corr().fillna(0).round(2)
            analysis_info['correlation'] = corr.to_dict()
        except: pass

    # 5. Generate Smart Insights (AI Narrative)
    # 5. Generate Smart Insights (AI Narrative)
    analysis_info['smart_insights'] = generate_narrative_insights(df, analysis_info)

    return sanitize_for_json(analysis_info)

def sanitize_for_json(obj):
    """
    Recursively sanitizes a Python object to ensure it is JSON serializable.
    - Converts NaN/Infinity to None
    - Converts numpy types to Python native types
    """
    import math
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(x) for x in obj]
    elif isinstance(obj, (np.integer, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64)):
        val = float(obj)
        if math.isnan(val) or math.isinf(val):
            return None
        return val
    elif isinstance(obj, np.ndarray):
        return sanitize_for_json(obj.tolist())
    return obj


def generate_narrative_insights(df, info):
    """
    Generate natural language insights mimicking an AI analyst.
    """
    insights = []
    
    # 1. Dataset Overview
    rows, cols = df.shape
    insights.append({
        "icon": "fa-database",
        "title": "Dataset Snapshot",
        "content": f"The dataset contains <strong>{rows} rows</strong> and <strong>{cols} columns</strong>. "
                   f"It has a Data Quality Score of <strong>{info['quality_score']}/100</strong>."
    })

    # 2. Key Correlations (if numeric data exists)
    if 'correlation' in info and info['correlation']:
        correlations = []
        corr_matrix = pd.DataFrame(info['correlation'])
        # Iterate to find strong correlations
        for c in corr_matrix.columns:
            for r in corr_matrix.index:
                if c != r:
                    val = corr_matrix.loc[r, c]
                    if val > 0.7:
                        correlations.append(f"Strong positive relation between <strong>{r}</strong> and <strong>{c}</strong> ({val})")
                    elif val < -0.7:
                        correlations.append(f"Strong negative relation between <strong>{r}</strong> and <strong>{c}</strong> ({val})")
        
        # Deduplicate (A-B is same as B-A) and limit
        unique_corrs = list(set([tuple(sorted(x.split(' and '))) for x in correlations])) # heuristic dedup
        # Simpler approach: usage set of frozensets
        seen = set()
        final_corrs = []
        for c in correlations:
            # extract columns for dedup
            try:
                parts = c.split(' between ')[1].split(' (')
                cols_part = parts[0]
                col_set = frozenset(pd.Index([x.replace('<strong>', '').replace('</strong>', '') for x in cols_part.split(' and ')]))
                if col_set not in seen:
                    seen.add(col_set)
                    final_corrs.append(c)
            except: final_corrs.append(c) # fallback

        if final_corrs:
            insights.append({
                "icon": "fa-project-diagram",
                "title": "Key Relationships",
                "content": "<ul>" + "".join([f"<li>{c}</li>" for c in final_corrs[:5]]) + "</ul>"
            })

    # 3. Missing Data Highlights
    missing_cols = [c for c in info['columns'] if c['missing'] > 0]
    if missing_cols:
        top_missing = sorted(missing_cols, key=lambda x: x['missing'], reverse=True)[:3]
        txt = "Key columns with specific missing data concerns:<ul>"
        for m in top_missing:
            pct = (m['missing'] / rows) * 100
            txt += f"<li><strong>{m['name']}</strong>: {pct:.1f}% missing</li>"
        txt += "</ul>"
        insights.append({
            "icon": "fa-exclamation-triangle",
            "title": "Data Quality alerts",
            "content": txt
        })

    # 4. Outlier / Skewness detection
    skewed = [c for c in info['columns'] if c['type'] == 'numeric' and abs(c.get('skew', 0)) > 2]
    if skewed:
        txt = "Significant skewness detected in distributions:<ul>"
        for s in skewed[:3]:
            direction = "right (positive)" if s.get('skew', 0) > 0 else "left (negative)"
            txt += f"<li><strong>{s['name']}</strong> is skewed to the {direction}.</li>"
        txt += "</ul>"
        insights.append({
            "icon": "fa-chart-area",
            "title": "Distribution Anomalies",
            "content": txt
        })

    return insights


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
    out_dir = p.parent / (p.stem + "_analysis_outputs")
    
    # Use new generic function
    result = analyze_df(df, out_dir)
    result['out_dir'] = str(out_dir)
    return result

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