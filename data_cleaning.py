import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder


def basic_cleaning(df):
    """Basic cleaning: remove duplicates, handle column names, basic type conversion"""
    try:
        # Create a copy to avoid modifying original
        df = df.copy()
        
        # Remove duplicates
        df = df.drop_duplicates()
        
        # Remove completely empty rows
        df = df.dropna(how='all')
        
        # Clean column names
        df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

        # Try to convert to numeric where possible, but don't force it
        for col in df.columns:
            if df[col].dtype == 'object':
                # Try numeric conversion first
                numeric_converted = pd.to_numeric(df[col], errors='coerce')
                # Only convert if we don't lose too much data (less than 50% becomes NaN)
                if numeric_converted.notna().sum() / len(df) > 0.5:
                    df[col] = numeric_converted
                else:
                    # Try datetime conversion
                    try:
                        datetime_converted = pd.to_datetime(df[col], errors='coerce')
                        # Only convert if we don't lose too much data
                        if datetime_converted.notna().sum() / len(df) > 0.5:
                            df[col] = datetime_converted
                    except:
                        pass
        
        # Optimize numeric types
        for col in df.select_dtypes(include=[np.number]).columns:
            df[col] = pd.to_numeric(df[col], downcast="float")

        return df
        
    except Exception as e:
        print(f"Error in basic_cleaning: {str(e)}")
        # Return original data if cleaning fails
        return df.copy()


def intermediate_cleaning(df, scale_numeric=True, encode_categorical=True, handle_outliers=True, preserve_datetime=True, cat_threshold=50, high_card_threshold=1000):
    """
    Intermediate cleaning with configurable options.
    Returns: (cleaned_df, cleaning_report_dict)
    """
    try:
        df = df.copy()
        cleaning_report = {
            "numeric_scaled": [],
            "categorical_encoded": [],
            "outliers_handled": False,
            "missing_strategy_numeric": "median",
            "missing_strategy_categorical": "mode",
            "datetime_columns": [],
            "original_shape": df.shape
        }

        # 1. Handle Datetime (Preservation)
        # We try to detect datetime columns first so we don't accidentally scale/encode them
        if preserve_datetime:
            for col in df.columns:
                if df[col].dtype == 'object':
                    try:
                        # rigorous check could be better, but we stick to previous logic + extra safety
                        is_datetime = pd.to_datetime(df[col], errors='coerce').notna().sum() / len(df) > 0.5
                        if is_datetime:
                            df[col] = pd.to_datetime(df[col], errors='coerce')
                            cleaning_report["datetime_columns"].append(col)
                    except:
                        pass
                elif np.issubdtype(df[col].dtype, np.datetime64):
                    cleaning_report["datetime_columns"].append(col)

        # 2. Handle missing values
        # (Always done unless requested otherwise, but let's keep it standard)
        for col in df.select_dtypes(include=[np.number]).columns:
            if df[col].isna().sum() > 0:
                df[col] = df[col].fillna(df[col].median())

        for col in df.select_dtypes(include=["object"]).columns:
            if df[col].isna().sum() > 0:
                mode_value = df[col].mode()
                if len(mode_value) > 0:
                    df[col] = df[col].fillna(mode_value[0])
                else:
                    df[col] = df[col].fillna("Unknown")

        # 3. Handle Outliers
        if handle_outliers:
            cols_with_outliers = []
            for col in df.select_dtypes(include=[np.number]).columns:
                # Skip bools or low distinct count numerics if needed, but standard IQR for now
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                
                if IQR > 0:
                    lower = Q1 - 1.5 * IQR
                    upper = Q3 + 1.5 * IQR
                    # Check if any outliers exist before capping
                    if ((df[col] < lower) | (df[col] > upper)).any():
                        cols_with_outliers.append(col)
                        df[col] = np.where(df[col] < lower, lower, df[col])
                        df[col] = np.where(df[col] > upper, upper, df[col])
            
            if cols_with_outliers:
                cleaning_report["outliers_handled"] = True

        # 4. Encode Categorical
        if encode_categorical:
            cat_cols = df.select_dtypes(include=["object"]).columns.tolist()
            # Exclude preserved datetime columns if they remained object (unlikely if converted above, but safe check)
            
            encoded_cols = []
            for col in cat_cols:
                # Skip if it's a datetime column we just converted (it wouldn't be object, but double check)
                if col in cleaning_report["datetime_columns"]:
                    continue

                nunique = df[col].nunique()
                encoded_cols.append(col)

                if nunique < cat_threshold:
                    try:
                        dummies = pd.get_dummies(df[col], prefix=col, drop_first=True)
                        df = pd.concat([df.drop(columns=[col]), dummies], axis=1)
                    except Exception:
                        le = LabelEncoder()
                        df[col] = le.fit_transform(df[col].astype(str))

                elif nunique < high_card_threshold:
                    le = LabelEncoder()
                    df[col] = le.fit_transform(df[col].astype(str))

                else:
                    # Frequency encoding
                    freq_encoding = df[col].value_counts(normalize=True)
                    df[col] = df[col].map(freq_encoding).fillna(0)
            
            cleaning_report["categorical_encoded"] = encoded_cols

        # 5. Scale Numeric
        if scale_numeric:
            # We must identify numeric cols anew because encoding might have added some
            num_cols = df.select_dtypes(include=[np.number]).columns
            # Exclude datetime-like numerics if any specific need, but usually fine.
            # However! One-hot encoded columns are numeric (0/1). StandardScaling them breaks their binary nature logic usually.
            # But the requirement says "Detect 'target-like' columns", "Detect datetime".
            # For now, we apply standard scaler to all numerics as per previous logic, 
            # OR we can be smarter and skip binary columns.
            
            to_scale = []
            for c in num_cols:
                # heuristic: don't scale binary columns (0/1)
                unique_vals = df[c].dropna().unique()
                if len(unique_vals) <= 2 and set(unique_vals).issubset({0, 1, 0.0, 1.0}):
                    continue
                to_scale.append(c)

            if to_scale:
                scaler = StandardScaler()
                df[to_scale] = scaler.fit_transform(df[to_scale])
                cleaning_report["numeric_scaled"] = list(to_scale)

        # Optimize types at the end
        for col in df.select_dtypes(include=[np.number]).columns:
            df[col] = pd.to_numeric(df[col], downcast="float")

        cleaning_report["final_shape"] = df.shape
        return df, cleaning_report
        
    except Exception as e:
        print(f"Error in intermediate_cleaning: {str(e)}")
        # Return original data and empty report if cleaning fails
        return basic_cleaning(df), {"error": str(e)}