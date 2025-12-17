#!/usr/bin/env python3
"""
Minimal debug version of Flask app to isolate the issue
"""

from flask import Flask, render_template, request, jsonify, send_file
import os
import pandas as pd
import numpy as np
import tempfile
from datetime import datetime
import traceback
import json

app = Flask(__name__)
app.secret_key = 'debug-key'

UPLOAD_FOLDER = 'debug_uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Debug Dataset Cleaner</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .section { margin: 20px 0; padding: 20px; border: 1px solid #ccc; }
            .error { color: red; background: #ffe6e6; padding: 10px; }
            .success { color: green; background: #e6ffe6; padding: 10px; }
            button { padding: 10px 20px; margin: 5px; }
            pre { background: #f5f5f5; padding: 10px; overflow-x: auto; }
        </style>
    </head>
    <body>
        <h1>Debug Dataset Cleaner</h1>
        
        <div class="section">
            <h3>1. Test with Sample Data</h3>
            <button onclick="testSampleData()">Test Sample Data Processing</button>
            <div id="sampleResult"></div>
        </div>
        
        <div class="section">
            <h3>2. Upload Your File</h3>
            <form id="uploadForm" enctype="multipart/form-data">
                <input type="file" id="fileInput" accept=".csv,.json,.xlsx,.xls">
                <button type="submit">Upload & Process</button>
            </form>
            <div id="uploadResult"></div>
        </div>
        
        <div class="section">
            <h3>3. Debug Log</h3>
            <div id="debugLog"></div>
        </div>

        <script>
            function log(message, isError = false) {
                const logDiv = document.getElementById('debugLog');
                const timestamp = new Date().toLocaleTimeString();
                const className = isError ? 'error' : 'success';
                logDiv.innerHTML += `<div class="${className}">[${timestamp}] ${message}</div>`;
            }

            function testSampleData() {
                log('Testing with sample data...');
                fetch('/test_sample')
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        log(`ERROR: ${data.error}`, true);
                        document.getElementById('sampleResult').innerHTML = 
                            `<div class="error">Error: ${data.error}</div>`;
                    } else {
                        log('Sample data processing successful!');
                        document.getElementById('sampleResult').innerHTML = 
                            `<div class="success">
                                <h4>Processing Results:</h4>
                                <pre>${JSON.stringify(data, null, 2)}</pre>
                            </div>`;
                    }
                })
                .catch(error => {
                    log(`FETCH ERROR: ${error}`, true);
                });
            }

            document.getElementById('uploadForm').addEventListener('submit', function(e) {
                e.preventDefault();
                const file = document.getElementById('fileInput').files[0];
                if (!file) {
                    log('No file selected', true);
                    return;
                }

                const formData = new FormData();
                formData.append('file', file);

                log(`Uploading file: ${file.name} (${file.size} bytes)`);
                
                fetch('/debug_upload', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        log(`UPLOAD ERROR: ${data.error}`, true);
                        document.getElementById('uploadResult').innerHTML = 
                            `<div class="error">Error: ${data.error}</div>`;
                    } else {
                        log('File processing successful!');
                        document.getElementById('uploadResult').innerHTML = 
                            `<div class="success">
                                <h4>Processing Results:</h4>
                                <pre>${JSON.stringify(data, null, 2)}</pre>
                            </div>`;
                    }
                })
                .catch(error => {
                    log(`UPLOAD FETCH ERROR: ${error}`, true);
                });
            });
        </script>
    </body>
    </html>
    '''

@app.route('/test_sample')
def test_sample():
    try:
        app.logger.info("Creating sample data...")
        
        # Create sample data
        np.random.seed(42)
        sample_data = pd.DataFrame({
            'ID': range(1, 21),
            'Name': [f'Person_{i}' for i in range(1, 21)],
            'Age': np.random.randint(20, 60, 20),
            'Salary': np.random.normal(50000, 10000, 20),
            'Department': np.random.choice(['HR', 'IT', 'Finance'], 20)
        })
        
        # Add some missing values
        sample_data.loc[2, 'Age'] = np.nan
        sample_data.loc[5, 'Salary'] = np.nan
        
        app.logger.info(f"Sample data created: {sample_data.shape}")
        
        # Save to temp file
        temp_file = os.path.join(UPLOAD_FOLDER, 'sample_data.csv')
        sample_data.to_csv(temp_file, index=False)
        
        # Process it
        result = debug_process_dataset(temp_file, 'sample_data.csv')
        
        return jsonify(result)
        
    except Exception as e:
        app.logger.error(f"Sample test error: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)})

@app.route('/debug_upload', methods=['POST'])
def debug_upload():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'})
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'})
        
        # Save file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{file.filename}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        app.logger.info(f"File saved: {filepath}")
        
        # Process it
        result = debug_process_dataset(filepath, file.filename)
        
        return jsonify(result)
        
    except Exception as e:
        app.logger.error(f"Upload error: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)})

def debug_process_dataset(file_path, original_filename):
    """Simplified processing with detailed logging"""
    try:
        app.logger.info(f"Processing: {file_path}")
        
        # Step 1: Load data
        app.logger.info("Step 1: Loading data...")
        df = pd.read_csv(file_path)
        app.logger.info(f"Data loaded: {df.shape}, columns: {list(df.columns)}")
        
        if df.empty:
            raise Exception("Dataset is empty")
        
        # Step 2: Basic cleaning (simplified)
        app.logger.info("Step 2: Basic cleaning...")
        df_basic = df.drop_duplicates().dropna(how='all')
        app.logger.info(f"Basic cleaning done: {df_basic.shape}")
        
        # Step 3: Handle missing values (simplified)
        app.logger.info("Step 3: Handling missing values...")
        df_clean = df_basic.copy()
        
        # Fill numeric columns with median
        numeric_cols = df_clean.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if df_clean[col].isna().any():
                median_val = df_clean[col].median()
                df_clean[col] = df_clean[col].fillna(median_val)
                app.logger.info(f"Filled {col} missing values with {median_val}")
        
        # Fill categorical columns with mode
        cat_cols = df_clean.select_dtypes(include=['object']).columns
        for col in cat_cols:
            if df_clean[col].isna().any():
                mode_val = df_clean[col].mode()
                if len(mode_val) > 0:
                    df_clean[col] = df_clean[col].fillna(mode_val[0])
                    app.logger.info(f"Filled {col} missing values with {mode_val[0]}")
        
        app.logger.info(f"Missing value handling done: {df_clean.shape}")
        
        # Step 4: Save cleaned data
        app.logger.info("Step 4: Saving cleaned data...")
        basic_path = os.path.join(UPLOAD_FOLDER, f"basic_cleaned_{original_filename}")
        clean_path = os.path.join(UPLOAD_FOLDER, f"cleaned_{original_filename}")
        
        df_basic.to_csv(basic_path, index=False)
        df_clean.to_csv(clean_path, index=False)
        
        app.logger.info("Files saved successfully")
        
        # Create summary
        summary = {
            'success': True,
            'original_shape': list(df.shape),
            'basic_clean_shape': list(df_basic.shape),
            'final_clean_shape': list(df_clean.shape),
            'duplicates_removed': df.shape[0] - df_basic.shape[0],
            'missing_before': int(df.isna().sum().sum()),
            'missing_after': int(df_clean.isna().sum().sum()),
            'columns': df.columns.tolist(),
            'numeric_columns': numeric_cols.tolist(),
            'categorical_columns': cat_cols.tolist(),
            'basic_clean_path': basic_path,
            'final_clean_path': clean_path,
            'data_types': {col: str(dtype) for col, dtype in df.dtypes.items()}
        }
        
        app.logger.info("Processing completed successfully")
        return summary
        
    except Exception as e:
        app.logger.error(f"Processing error: {str(e)}")
        app.logger.error(traceback.format_exc())
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }

@app.route('/download/<path:filepath>')
def download_file(filepath):
    try:
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True)
        else:
            return jsonify({'error': 'File not found'})
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    print("Starting debug Flask app...")
    print("Open http://localhost:5001 in your browser")
    app.run(debug=True, host='0.0.0.0', port=5001)