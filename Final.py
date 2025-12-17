import pandas as pd
import numpy as np
from Data_load import load_data
from data_cleaning import basic_cleaning, intermediate_cleaning


pd.set_option('display.max_columns',None)
pd.set_option('display.max_colwidth', None)

df, info = load_data("Database\Online Retail.xlsx", "excel")

df_basic = basic_cleaning(df)
df_intermediate = intermediate_cleaning(df)


print(" Preprocessed data Summary !")
print(f"Original dataset size: {df.shape}")
print(f"After basic cleaning: {df_basic.shape}")
print(f"After intermediate cleaning: {df_intermediate.shape}")
print(f"Duplicate rows removed: {df.shape[0] - df_basic.shape[0]}")
print(f"Missing values before: {df.isna().sum().sum()}")
print(f"Missing values after: {df_intermediate.isna().sum().sum()}")
print("Outliers handled using IQR method")
print("Categorical variables encoded (get_dummies)")
print("Numerical variables scaled (StandardScaler)")

