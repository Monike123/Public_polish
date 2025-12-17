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


def intermediate_cleaning(df, cat_threshold=50, high_card_threshold=1000):
    """Intermediate cleaning: handle missing values, outliers, encoding, scaling"""
    try:
        df = df.copy()

        # Handle missing values
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

        # Handle outliers using IQR method
        for col in df.select_dtypes(include=[np.number]).columns:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            
            if IQR > 0:  # Only apply if there's variation
                lower = Q1 - 1.5 * IQR
                upper = Q3 + 1.5 * IQR
                df[col] = np.where(df[col] < lower, lower, df[col])
                df[col] = np.where(df[col] > upper, upper, df[col])

        # Encode categorical variables
        cat_cols = df.select_dtypes(include=["object"]).columns.tolist()
        
        for col in cat_cols:
            nunique = df[col].nunique()

            if nunique < cat_threshold:
                # One-hot encoding for low cardinality
                try:
                    dummies = pd.get_dummies(df[col], prefix=col, drop_first=True)
                    df = pd.concat([df.drop(columns=[col]), dummies], axis=1)
                except Exception:
                    # If get_dummies fails, use label encoding
                    le = LabelEncoder()
                    df[col] = le.fit_transform(df[col].astype(str))

            elif nunique < high_card_threshold:
                # Label encoding for medium cardinality
                le = LabelEncoder()
                df[col] = le.fit_transform(df[col].astype(str))

            else:
                # Frequency encoding for high cardinality
                freq_encoding = df[col].value_counts(normalize=True)
                df[col] = df[col].map(freq_encoding).fillna(0)

        # Scale numerical features
        num_cols = df.select_dtypes(include=[np.number]).columns
        if len(num_cols) > 0:
            scaler = StandardScaler()
            df[num_cols] = scaler.fit_transform(df[num_cols])

        # Optimize data types
        for col in df.select_dtypes(include=[np.number]).columns:
            df[col] = pd.to_numeric(df[col], downcast="float")

        return df
        
    except Exception as e:
        print(f"Error in intermediate_cleaning: {str(e)}")
        # Fall back to basic cleaning if intermediate fails
        return basic_cleaning(df)