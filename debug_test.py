#!/usr/bin/env python3
"""
Debug test script to identify issues with the data cleaning pipeline
"""

import pandas as pd
import numpy as np
import sys
import traceback
from pathlib import Path

# Import your modules
try:
    from Data_load import load_data
    from data_cleaning import basic_cleaning, intermediate_cleaning
    from analysis import analyze_csv
    print("✓ All modules imported successfully")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)

def create_test_dataset():
    """Create a simple test dataset for debugging"""
    np.random.seed(42)
    
    data = {
        'ID': range(1, 101),
        'Name': [f'Person_{i}' for i in range(1, 101)],
        'Age': np.random.randint(18, 80, 100),
        'Salary': np.random.normal(50000, 15000, 100),
        'Department': np.random.choice(['HR', 'IT', 'Finance', 'Marketing'], 100),
        'Rating': np.random.uniform(1, 5, 100)
    }
    
    # Add some missing values and duplicates
    df = pd.DataFrame(data)
    df.loc[5:10, 'Salary'] = np.nan
    df.loc[15:20, 'Age'] = np.nan
    df.loc[25, 'Name'] = np.nan
    
    # Add duplicates
    df = pd.concat([df, df.iloc[:5]], ignore_index=True)
    
    return df

def test_pipeline(test_file_path=None):
    """Test the entire data processing pipeline"""
    
    if test_file_path is None:
        print("Creating test dataset...")
        df_test = create_test_dataset()
        test_file_path = 'test_dataset.csv'
        df_test.to_csv(test_file_path, index=False)
        print(f"✓ Test dataset created: {test_file_path}")
    
    try:
        # Step 1: Load data
        print("\n1. Testing data loading...")
        df, info = load_data(test_file_path, 'csv')
        print(f"✓ Data loaded successfully: {df.shape}")
        
        # Step 2: Basic cleaning
        print("\n2. Testing basic cleaning...")
        df_basic = basic_cleaning(df.copy())
        print(f"✓ Basic cleaning completed: {df_basic.shape}")
        
        # Step 3: Intermediate cleaning
        print("\n3. Testing intermediate cleaning...")
        df_intermediate = intermediate_cleaning(df.copy())
        print(f"✓ Intermediate cleaning completed: {df_intermediate.shape}")
        
        # Save cleaned data
        basic_path = 'test_basic_cleaned.csv'
        intermediate_path = 'test_intermediate_cleaned.csv'
        
        df_basic.to_csv(basic_path, index=False)
        df_intermediate.to_csv(intermediate_path, index=False)
        print(f"✓ Cleaned datasets saved")
        
        # Step 4: Analysis
        print("\n4. Testing analysis...")
        try:
            analysis_result = analyze_csv(intermediate_path)
            print(f"✓ Analysis completed successfully")
            print(f"  - Charts created: {len(analysis_result.get('charts', []))}")
            print(f"  - Output directory: {analysis_result.get('out_dir', 'N/A')}")
        except Exception as e:
            print(f"✗ Analysis failed: {str(e)}")
            traceback.print_exc()
            analysis_result = {'error': str(e)}
        
        # Step 5: Create summary (similar to Flask app)
        print("\n5. Creating summary...")
        summary = {
            'original_shape': list(df.shape),
            'basic_clean_shape': list(df_basic.shape),
            'intermediate_clean_shape': list(df_intermediate.shape),
            'duplicates_removed': max(0, df.shape[0] - df_basic.shape[0]),
            'missing_before': int(df.isna().sum().sum()),
            'missing_after': int(df_intermediate.isna().sum().sum()),
            'columns': df.columns.tolist(),
            'data_types': {col: str(dtype) for col, dtype in df.dtypes.items()},
            'basic_clean_path': basic_path,
            'intermediate_clean_path': intermediate_path,
            'analysis': analysis_result,
            'success': True
        }
        
        print("✓ Summary created successfully")
        print(f"  - Original shape: {summary['original_shape']}")
        print(f"  - Basic clean shape: {summary['basic_clean_shape']}")
        print(f"  - Intermediate clean shape: {summary['intermediate_clean_shape']}")
        print(f"  - Duplicates removed: {summary['duplicates_removed']}")
        print(f"  - Missing values before: {summary['missing_before']}")
        print(f"  - Missing values after: {summary['missing_after']}")
        
        return summary
        
    except Exception as e:
        print(f"\n✗ Pipeline failed: {str(e)}")
        traceback.print_exc()
        return None

def test_individual_functions():
    """Test individual functions separately"""
    print("Testing individual functions...")
    
    # Create simple test data
    test_data = pd.DataFrame({
        'A': [1, 2, 3, np.nan, 5],
        'B': ['x', 'y', 'z', 'x', np.nan],
        'C': [1.1, 2.2, 3.3, 4.4, 5.5]
    })
    
    print(f"Test data shape: {test_data.shape}")
    
    try:
        basic_result = basic_cleaning(test_data.copy())
        print(f"✓ Basic cleaning: {test_data.shape} -> {basic_result.shape}")
    except Exception as e:
        print(f"✗ Basic cleaning failed: {str(e)}")
        traceback.print_exc()
    
    try:
        intermediate_result = intermediate_cleaning(test_data.copy())
        print(f"✓ Intermediate cleaning: {test_data.shape} -> {intermediate_result.shape}")
    except Exception as e:
        print(f"✗ Intermediate cleaning failed: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    print("=== Dataset Cleaner Debug Test ===\n")
    
    # Test with command line argument if provided
    test_file = sys.argv[1] if len(sys.argv) > 1 else None
    
    if test_file and not Path(test_file).exists():
        print(f"File not found: {test_file}")
        test_file = None
    
    # Run individual function tests first
    test_individual_functions()
    
    print("\n" + "="*50)
    
    # Run full pipeline test
    result = test_pipeline(test_file)
    
    if result:
        print("\n✓ All tests passed! Your pipeline should work in the Flask app.")
    else:
        print("\n✗ Pipeline test failed. Check the errors above.")
    
    print("\n=== Debug Test Complete ===")