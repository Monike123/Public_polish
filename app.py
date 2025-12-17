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

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

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
            try:
                df = pd.read_csv(file_path, sep=None, engine='python')
            except:
                # Fallback to default if python engine fails or for edge cases
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

import analysis  # Import the analysis module

# ... (Previous imports kept if needed, but create_simple_analysis is removed)

@app.route('/')
def index():
    datasets = get_public_datasets()
    return render_template('index.html', datasets=datasets)

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
        
        # Get configuration from form (default to True)
        config = {
            'scale_numeric': request.form.get('scale_numeric', 'true') == 'true',
            'encode_categorical': request.form.get('encode_categorical', 'true') == 'true',
            'handle_outliers': request.form.get('handle_outliers', 'true') == 'true'
        }
        
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
        result = process_dataset_organized(
            str(filepath), filename, cleaned_path, analysis_path, 
            folder_name, config
        )
        
        return jsonify(result)
    
    except Exception as e:
        app.logger.error(f"Upload error: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500

@app.route('/process_public', methods=['POST'])
def process_public_dataset():
    try:
        data = request.json
        if not data or 'filename' not in data:
            return jsonify({'error': 'No filename provided'}), 400
            
        filename = data['filename']
        public_path = Path(PUBLIC_DATASETS_FOLDER) / filename
        
        if not public_path.exists():
            return jsonify({'error': 'Dataset not found'}), 404
            
        # Get configuration
        config = {
            'scale_numeric': data.get('scale_numeric', True),
            'encode_categorical': data.get('encode_categorical', True),
            'handle_outliers': data.get('handle_outliers', True)
        }
        
        # Create unique folder structure
        folder_name = create_unique_folder_name(filename)
        
        # Create folders for this processing session
        session_folder = BASE_DIR / folder_name
        upload_path = UPLOAD_FOLDER / folder_name
        cleaned_path = CLEANED_DATASETS_FOLDER / folder_name
        analysis_path = ANALYSIS_FOLDER / folder_name
        
        for folder in [session_folder, upload_path, cleaned_path, analysis_path]:
            os.makedirs(folder, exist_ok=True)
            
        # Copy public file to session upload folder
        filepath = upload_path / filename
        shutil.copy2(public_path, filepath)
        app.logger.info(f"Public file copied to: {filepath}")
        
        # Process the file
        result = process_dataset_organized(
            str(filepath), filename, cleaned_path, analysis_path, 
            folder_name, config
        )
        
        return jsonify(result)

    except Exception as e:
        app.logger.error(f"Public dataset processing error: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500

def process_dataset_organized(file_path, original_filename, cleaned_folder, analysis_folder, session_id, config=None):
    """Process dataset with organized folder structure and configuration"""
    try:
        if config is None:
            config = {'scale_numeric': True, 'encode_categorical': True, 'handle_outliers': True}

        app.logger.info(f"Processing file: {file_path} with config: {config}")
        
        # Determine file type
        file_type = get_file_type(original_filename)
        
        # Load data
        df = load_data_simple(file_path, file_type)
        
        # Validate data
        if df.empty:
            raise Exception("The dataset is empty")
        
        if len(df.columns) == 0:
            raise Exception("No columns found in dataset")
        
        # Clean data
        # 1. Basic Cleaning
        df_basic = basic_cleaning_simple(df.copy()) # Using simple logic within app.py or from data_cleaning? 
        # Ideally we should use data_cleaning.basic_cleaning too, but let's stick to what's available or import it.
        # The user file 'data_cleaning.py' has 'basic_cleaning'. 'app.py' has 'basic_cleaning_simple'.
        # Let's switch to using the imported data_cleaning module for consistency if possible, but
        # basic_cleaning_simple is defined in app.py. I'll stick to basic_cleaning_simple for now to minimize risk errors,
        # OR better: use data_cleaning.intermediate_cleaning which I JUST REFACTORED.
        
        # Wait, I need to call the NEW intermediate_cleaning from data_cleaning.py
        from data_cleaning import intermediate_cleaning
        
        # 2. Intermediate Cleaning (Advanced)
        # It returns tuple (df, report)
        df_intermediate, cleaning_report = intermediate_cleaning(
            df_basic.copy(),
            scale_numeric=config['scale_numeric'],
            encode_categorical=config['encode_categorical'],
            handle_outliers=config['handle_outliers']
        )
        
        # Save cleaned datasets
        base_name = Path(original_filename).stem
        basic_clean_path = cleaned_folder / f"basic_cleaned_{base_name}.csv"
        intermediate_clean_path = cleaned_folder / f"advanced_cleaned_{base_name}.csv"
        
        df_basic.to_csv(basic_clean_path, index=False)
        df_intermediate.to_csv(intermediate_clean_path, index=False)
        app.logger.info("Cleaned datasets saved")
        
        # Create analysis using the NEW analysis module
        app.logger.info("Starting analysis...")
        analysis_result = analysis.analyze_df(df_intermediate, analysis_folder)

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
            'analysis': analysis_result, 
            'cleaning_report': cleaning_report, # Return the report to frontend
            'download_ids': { # Logical IDs as requested
                'basic': f"{session_id}/{basic_clean_path.name}",
                'advanced': f"{session_id}/{intermediate_clean_path.name}",
                'analysis': f"{session_id}"
            },
            'download_urls': {
                'basic': f"/download/cleaned/{session_id}/{basic_clean_path.name}",
                'advanced': f"/download/cleaned/{session_id}/{intermediate_clean_path.name}",
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

@app.route('/analysis/images/<session_id>/<filename>')
def serve_analysis_image(session_id, filename):
    """Serve individual analysis images for the frontend"""
    try:
        file_path = ANALYSIS_FOLDER / session_id / filename
        if file_path.exists():
            return send_file(str(file_path))
        else:
            return jsonify({'error': 'Image not found'}), 404
    except Exception as e:
        app.logger.error(f"Image serve error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 50MB.'}), 413

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(Exception)
def handle_exception(e):
    # pass through HTTP errors
    if hasattr(e, 'code') and e.code is not None:
         return jsonify({'error': str(e)}), e.code
         
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