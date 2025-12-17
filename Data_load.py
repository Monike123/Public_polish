import pandas as pd
import numpy as np
import warnings

def load_data(file_path, file_type, treat_strings_as_nan=True, delimiter=None):
    """
    Load data from various file formats with robust error handling
    """
    try:
        print(f"Loading {file_type} file: {file_path}")
        
        if file_type.lower() == 'csv':
            # Try different encodings and separators
            encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
            separators = [',', ';', '\t', '|'] if delimiter is None else [delimiter]
            
            data = None
            for encoding in encodings:
                for sep in separators:
                    try:
                        if treat_strings_as_nan:
                            data = pd.read_csv(file_path, sep=sep, encoding=encoding, engine="python")
                        else:
                            data = pd.read_csv(file_path, sep=sep, encoding=encoding, engine="python", keep_default_na=False)
                        
                        # Check if we got meaningful data
                        if data is not None and len(data.columns) > 1:
                            print(f"Successfully loaded CSV with encoding: {encoding}, separator: '{sep}'")
                            break
                    except Exception as e:
                        continue
                if data is not None and len(data.columns) > 1:
                    break
            
            if data is None:
                raise Exception("Could not read CSV file with any encoding/separator combination")
                
        elif file_type.lower() == 'json':
            try:
                data = pd.read_json(file_path)
            except Exception:
                # Try reading as lines-delimited JSON
                data = pd.read_json(file_path, lines=True)
                
        elif file_type.lower() == 'excel':
            try:
                data = pd.read_excel(file_path)
            except Exception as e:
                # Try reading first sheet explicitly
                data = pd.read_excel(file_path, sheet_name=0)
        else:
            raise ValueError("Unsupported file type. Use 'csv', 'json', or 'excel'")

        # Validate loaded data
        if data is None:
            raise Exception("Failed to load data - result is None")
            
        if data.empty:
            raise Exception("Loaded data is empty")
            
        if len(data.columns) == 0:
            raise Exception("No columns found in the data")

        # Generate info with error handling
        info = generate_data_info(data)
        
        print(f"Data loaded successfully: {data.shape}")
        return data, info
        
    except Exception as e:
        print(f"Error loading data: {str(e)}")
        raise Exception(f"Failed to load {file_type} file: {str(e)}")

def generate_data_info(data):
    """Generate comprehensive data information with error handling"""
    try:
        info = {
            "Shape": data.shape,
            "Columns": data.columns.tolist(),
            "Data types": data.dtypes,
            "Missing values by attribute": data.isnull().sum(),
            "Duplicated rows": data.duplicated().sum()
        }
        
        # Generate statistics with error handling
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                stats = data.describe(include='all')
                # Round numeric values
                numeric_cols = data.select_dtypes(include=[np.number]).columns
                for col in numeric_cols:
                    if col in stats.columns:
                        stats[col] = stats[col].round(2)
                info["Statistic summary"] = stats
        except Exception as e:
            print(f"Warning: Could not generate statistics summary: {str(e)}")
            info["Statistic summary"] = "Unable to generate summary"

        print("\n=== Basic Dataset Information ===")
        print("Shape:", info['Shape'])
        print("\nColumns:", info['Columns'][:10], "..." if len(info['Columns']) > 10 else "")
        print("\nData types:\n", info['Data types'])
        print("\nMissing values by attribute:\n", info['Missing values by attribute'])
        print("\nDuplicated rows:", info['Duplicated rows'])
        
        if isinstance(info["Statistic summary"], pd.DataFrame):
            print("\nStatistic summary (first 5 columns):")
            print(info['Statistic summary'].iloc[:, :5])
        
        return info
        
    except Exception as e:
        print(f"Error generating data info: {str(e)}")
        return {
            "Shape": data.shape,
            "Columns": data.columns.tolist() if hasattr(data, 'columns') else [],
            "Data types": {},
            "Missing values by attribute": {},
            "Duplicated rows": 0,
            "Statistic summary": "Error generating summary"
        }