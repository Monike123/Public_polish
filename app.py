from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
import os
import pandas as pd
import numpy as np
from pathlib import Path
import zipfile
from werkzeug.utils import secure_filename
from datetime import datetime
import traceback
import logging
import shutil

# Setup logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Configuration - organized folder structure
BASE_DIR = Path('results')
UPLOAD_FOLDER = BASE_DIR / 'uploads'
CLEANED_DATASETS_FOLDER = BASE_DIR / 'cleaned_datasets'
ANALYSIS_FOLDER = BASE_DIR / 'analysis'
PUBLIC_DATASETS_FOLDER = 'dataset'

ALLOWED_EXTENSIONS = {'csv', 'json', 'xlsx', 'xls'}

# Ensure directories exist
for folder in [BASE_DIR, UPLOAD_FOLDER, CLEANED_DATASETS_FOLDER, ANALYSIS_FOLDER]:
    os.makedirs(folder, exist_ok=True)
os.makedirs(PUBLIC_DATASETS_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_type(filename):
    ext = filename.rsplit('.', 1)[1].lower()
    if ext == 'csv':
        return 'csv'
    elif ext == 'json':
        return 'json'
    elif ext in ['xlsx', 'xls']:
        return 'excel'
    return None

def get_public_datasets():
    """Get list of public datasets"""
    datasets = []
    try:
        if os.path.exists(PUBLIC_DATASETS_FOLDER):
            for item in os.listdir(PUBLIC_DATASETS_FOLDER):
                item_path = os.path.join(PUBLIC_DATASETS_FOLDER, item)
                if (item != 'dataset_by_user' and 
                    os.path.isfile(item_path) and 
                    allowed_file(item)):
                    datasets.append({
                        'name': item,
                        'size': os.path.getsize(item_path),
                        'path': item_path
                    })
    except Exception as e:
        app.logger.error(f"Error getting public datasets: {str(e)}")
    return datasets

def create_unique_folder_name(filename):
    """Create a unique folder name based on filename and timestamp"""
    base_name = Path(filename).stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{timestamp}_{base_name}"

def load_data_simple(file_path, file_type):
    """Simplified data loading"""
    try:
        app.logger.info(f"Loading {file_type} file: {file_path}")
        
        if file_type.lower() == 'csv':
            df = pd.read_csv(file_path)
        elif file_type.lower() == 'json':
            df = pd.read_json(file_path)
        elif file_type.lower() == 'excel':
            df = pd.read_excel(file_path)
        else:
            raise ValueError("Unsupported file type")
        
        app.logger.info(f"Data loaded successfully: {df.shape}")
        return df
        
    except Exception as e:
        app.logger.error(f"Error loading data: {str(e)}")
        raise

def basic_cleaning_simple(df):
    """Simplified basic cleaning"""
    try:
        app.logger.info("Starting basic cleaning...")
        df = df.copy()
        
        # Remove duplicates
        df = df.drop_duplicates()
        
        # Remove completely empty rows
        df = df.dropna(how='all')
        
        # Clean column names
        df.columns = [str(col).strip().lower().replace(" ", "_") for col in df.columns]
        
        app.logger.info(f"Basic cleaning completed: {df.shape}")
        return df
        
    except Exception as e:
        app.logger.error(f"Error in basic cleaning: {str(e)}")
        raise

def intermediate_cleaning_simple(df):
    """Simplified intermediate cleaning"""
    try:
        app.logger.info("Starting intermediate cleaning...")
        df = df.copy()
        
        # Handle missing values
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if df[col].isna().any():
                median_val = df[col].median()
                df[col] = df[col].fillna(median_val)
                app.logger.info(f"Filled {col} missing values with {median_val}")
        
        categorical_cols = df.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            if df[col].isna().any():
                mode_val = df[col].mode()
                fill_val = mode_val[0] if len(mode_val) > 0 else "Unknown"
                df[col] = df[col].fillna(fill_val)
                app.logger.info(f"Filled {col} missing values with {fill_val}")
        
        app.logger.info(f"Intermediate cleaning completed: {df.shape}")
        return df
        
    except Exception as e:
        app.logger.error(f"Error in intermediate cleaning: {str(e)}")
        raise

# app.py - replace create_simple_analysis with this
import pandas as pd
import numpy as np
import math
from scipy import stats as _stats  # if scipy available; optional fallback below

def create_simple_analysis(df, analysis_folder):
    """Create robust analysis JSON including descriptive stats, histograms, correlation, and sample rows."""
    try:
        analysis_info = {
            'dataset_shape': df.shape,
            'column_info': {},       # per-column: type, stats, histogram, top_values
            'summary_stats': {},     # optional aggregates
            'data_quality': {
                'missing_values': df.isnull().sum().to_dict(),
                'duplicate_rows': int(df.duplicated().sum()),
                'data_types': df.dtypes.astype(str).to_dict()
            },
            'correlation': {},       # numeric correlation matrix
            'sample_rows': []        # small sample for scatter plots
        }

        # compute column_info
        for col in df.columns:
            series = df[col]
            col_info = {
                'type': str(series.dtype),
                'non_null_count': int(series.count()),
                'null_count': int(series.isnull().sum()),
                'unique_values': int(series.nunique())
            }

            # numeric columns: stats + histogram
            if pd.api.types.is_numeric_dtype(series):
                non_null = series.dropna()
                cnt = int(non_null.count())
                col_info['stats'] = {
                    'count': cnt,
                    'mean': float(non_null.mean()) if cnt > 0 else None,
                    'std': float(non_null.std()) if cnt > 0 else None,
                    'min': float(non_null.min()) if cnt > 0 else None,
                    'q1': float(non_null.quantile(0.25)) if cnt > 0 else None,
                    'median': float(non_null.median()) if cnt > 0 else None,
                    'q3': float(non_null.quantile(0.75)) if cnt > 0 else None,
                    'max': float(non_null.max()) if cnt > 0 else None,
                    'skew': float(non_null.skew()) if cnt > 0 else None,
                    'kurtosis': float(non_null.kurtosis()) if cnt > 0 else None
                }
                # histogram: try 12 bins (only values)
                try:
                    arr = non_null.to_numpy()
                    if arr.size > 0:
                        counts, bins = np.histogram(arr, bins=12)
                        col_info['histogram'] = {
                            'bins': [float(x) for x in bins],       # length n+1
                            'counts': [int(x) for x in counts]      # length n
                        }
                except Exception:
                    col_info['histogram'] = None

            else:
                # categorical / object: top values for pie/donut
                try:
                    top = series.dropna().value_counts().head(10)
                    col_info['top_values'] = top.to_dict()
                except Exception:
                    col_info['top_values'] = {}

            analysis_info['column_info'][col] = col_info

        # correlation matrix for numeric columns
        try:
            numeric_df = df.select_dtypes(include=[np.number])
            if numeric_df.shape[1] > 0:
                corr = numeric_df.corr().fillna(0)
                # convert to nested mapping of floats
                analysis_info['correlation'] = corr.round(4).to_dict()
            else:
                analysis_info['correlation'] = {}
        except Exception:
            analysis_info['correlation'] = {}

        # sample rows for scatter plots (limit to 500 rows to keep payload small)
        try:
            sample = df.select_dtypes(include=[np.number]).head(500)
            analysis_info['sample_rows'] = sample.to_dict(orient='records')
        except Exception:
            analysis_info['sample_rows'] = []

        # save textual report as before (optional)
        report_path = analysis_folder / 'analysis_report.txt'
        try:
            with open(report_path, 'w') as f:
                f.write("DATASET ANALYSIS REPORT\n")
                f.write("=" * 60 + "\n\n")
                f.write(f"Dataset Shape: {analysis_info['dataset_shape']}\n")
                f.write(f"Total Missing Values: {sum(analysis_info['data_quality']['missing_values'].values())}\n")
                f.write(f"Duplicate Rows: {analysis_info['data_quality']['duplicate_rows']}\n\n")
                f.write("COLUMN DETAILS:\n")
                f.write("-" * 40 + "\n")
                for col, info in analysis_info['column_info'].items():
                    f.write(f"\n{col} ({info['type']}):\n")
                    f.write(f"  Non-null: {info['non_null_count']}\n")
                    f.write(f"  Unique: {info['unique_values']}\n")
                    if 'stats' in info:
                        s = info['stats']
                        f.write(f"  Count: {s['count']}\n  Mean: {s['mean']}\n  Std: {s['std']}\n")
                        f.write(f"  Min/Q1/Median/Q3/Max: {s['min']}/{s['q1']}/{s['median']}/{s['q3']}/{s['max']}\n")
                    if 'top_values' in info and info['top_values']:
                        f.write(f"  Top values: {info['top_values']}\n")
        except Exception:
            pass

        return analysis_info

    except Exception as e:
        app.logger.error(f"Error creating analysis: {str(e)}")
        return {'error': str(e)}


@app.route('/')
def index():
    try:
        public_datasets = get_public_datasets()
        app.logger.info(f"Found {len(public_datasets)} public datasets")
        return render_template('index.html', datasets=public_datasets)
    except Exception as e:
        app.logger.error(f"Error in index route: {str(e)}")
        return render_template('index.html', datasets=[])

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        app.logger.info("Upload request received")
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file selected'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Please upload CSV, JSON, XLS, or XLSX files.'}), 400
        
        # Create unique folder structure
        folder_name = create_unique_folder_name(file.filename)
        
        # Create folders for this processing session
        session_folder = BASE_DIR / folder_name
        upload_path = UPLOAD_FOLDER / folder_name
        cleaned_path = CLEANED_DATASETS_FOLDER / folder_name
        analysis_path = ANALYSIS_FOLDER / folder_name
        
        for folder in [session_folder, upload_path, cleaned_path, analysis_path]:
            os.makedirs(folder, exist_ok=True)
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        filepath = upload_path / filename
        file.save(str(filepath))
        app.logger.info(f"File saved: {filepath}")
        
        # Process the file
        result = process_dataset_organized(str(filepath), filename, cleaned_path, analysis_path, folder_name)
        
        return jsonify(result)
    
    except Exception as e:
        app.logger.error(f"Upload error: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500

def process_dataset_organized(file_path, original_filename, cleaned_folder, analysis_folder, session_id):
    """Process dataset with organized folder structure"""
    try:
        app.logger.info(f"Processing file: {file_path}")
        
        # Determine file type
        file_type = get_file_type(original_filename)
        app.logger.info(f"File type: {file_type}")
        
        # Load data
        df = load_data_simple(file_path, file_type)
        
        # Validate data
        if df.empty:
            raise Exception("The dataset is empty")
        
        if len(df.columns) == 0:
            raise Exception("No columns found in dataset")
        
        # Clean data
        df_basic = basic_cleaning_simple(df.copy())
        df_intermediate = intermediate_cleaning_simple(df.copy())
        
        # Save cleaned datasets
        base_name = Path(original_filename).stem
        basic_clean_path = cleaned_folder / f"basic_cleaned_{base_name}.csv"
        intermediate_clean_path = cleaned_folder / f"advanced_cleaned_{base_name}.csv"
        
        df_basic.to_csv(basic_clean_path, index=False)
        df_intermediate.to_csv(intermediate_clean_path, index=False)
        app.logger.info("Cleaned datasets saved")
        
        # Create analysis
        analysis_result = create_simple_analysis(df_intermediate, analysis_folder)

        summary = {
            'success': True,
            'session_id': session_id,
            'original_shape': list(df.shape),
            'basic_clean_shape': list(df_basic.shape),
            'intermediate_clean_shape': list(df_intermediate.shape),
            'duplicates_removed': max(0, df.shape[0] - df_basic.shape[0]),
            'missing_before': int(df.isna().sum().sum()),
            'missing_after': int(df_intermediate.isna().sum().sum()),
            'columns': df.columns.tolist(),
            'data_types': {col: str(dtype) for col, dtype in df.dtypes.items()},
            'basic_clean_path': str(basic_clean_path),
            'intermediate_clean_path': str(intermediate_clean_path),
            'analysis_folder': str(analysis_folder),
            'analysis': analysis_result,   # <-- added here
            'download_urls': {
                'basic': f"/download/cleaned/{session_id}/basic_cleaned_{base_name}.csv",
                'advanced': f"/download/cleaned/{session_id}/advanced_cleaned_{base_name}.csv",
                'analysis': f"/download/analysis/{session_id}"
            }
        }
        
        app.logger.info("Dataset processing completed successfully")
        return summary
        
    except Exception as e:
        app.logger.error(f"Processing error: {str(e)}")
        app.logger.error(traceback.format_exc())
        return {
            'success': False,
            'error': str(e)
        }

@app.route('/download/cleaned/<session_id>/<filename>')
def download_cleaned_file(session_id, filename):
    """Download cleaned dataset file"""
    try:
        file_path = CLEANED_DATASETS_FOLDER / session_id / filename
        if file_path.exists():
            return send_file(str(file_path), as_attachment=True)
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        app.logger.error(f"Download error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/download/analysis/<session_id>')
def download_analysis_zip(session_id):
    """Download analysis results as zip"""
    try:
        analysis_path = ANALYSIS_FOLDER / session_id
        if not analysis_path.exists():
            return jsonify({'error': 'Analysis not found'}), 404
        
        # Create zip file
        zip_path = BASE_DIR / f"analysis_{session_id}.zip"
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for file in analysis_path.glob('**/*'):
                if file.is_file():
                    zipf.write(file, file.relative_to(analysis_path))
        
        return send_file(str(zip_path), as_attachment=True, download_name=f'analysis_{session_id}.zip')
    
    except Exception as e:
        app.logger.error(f"Analysis download error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 50MB.'}), 413

@app.errorhandler(Exception)
def handle_exception(e):
    app.logger.error(f"Unhandled exception: {str(e)}")
    app.logger.error(traceback.format_exc())
    return jsonify({'error': 'An unexpected error occurred'}), 500

if __name__ == '__main__':
    print("Starting organized Flask application...")
    print(f"Base directory: {BASE_DIR}")
    print(f"Upload folder: {UPLOAD_FOLDER}")
    print(f"Cleaned datasets folder: {CLEANED_DATASETS_FOLDER}")
    print(f"Analysis folder: {ANALYSIS_FOLDER}")
    app.run(debug=True, host='0.0.0.0', port=5000)