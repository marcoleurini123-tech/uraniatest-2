import pandas as pd
import numpy as np
import requests
import io
import yfinance as yf
import os
from datetime import datetime, timedelta

DB_FILE = "macro_database.csv"
GOOGLE_BRIDGE_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSeeY57SBwd6BftA2Bq8C0nyzzT3wj9WRWOihDF7QE-COPXhC4r2RN_k_BRgZke1nU2BbKT8oRlsXOX/pub?gid=1412711569&single=true&output=csv"

COLUMNS = [
    "Data", "VIX1D", "VIX9D", "VIX", "VIX3M", "VIX6M", "VIX1Y", "VVIX", "MOVE", "SKEW", 
    "DXY", "DIX", "GEX", "SPY", "RSP", "HYG", "XLY", "XLP", "TLT", "P_C", "GLD", "USO", 
    "Net_Liquidity", "M2"
]

def load_db():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
        if df['Data'].dt.tz is not None:
            df['Data'] = df['Data'].dt.tz_localize(None)
        df['Data'] = df['Data'].dt.normalize()
        
        for col in COLUMNS:
            if col not in df.columns:
                df[col] = np.nan
                
        num_cols = [c for c in COLUMNS if c != "Data"]
        for c in num_cols:
            df[c] = pd.to_numeric(df[c], errors='coerce')
                
        return df.dropna(subset=['Data']).sort_values("Data")
    return pd.DataFrame(columns=COLUMNS)

def save_db(df):
    df = df.drop_duplicates(subset=['Data'], keep='last').sort_values("Data")
    df.to_csv(DB_FILE, index=False)

def fetch_yahoo_data(days=365):
    # Mappatura rigorosa di tutti i nodi della Term Structure
    tickers = {
        "^VIX1D": "VIX1D", "^VIX9D": "VIX9D", "^VIX": "VIX", "^VIX3M": "VIX3M", 
        "^VIX6M": "VIX6M", "^VIX1Y": "VIX1Y", "^VVIX": "VVIX", "^SKEW": "SKEW", 
        "DX-Y.NYB": "DXY", "SPY": "SPY", "RSP": "RSP", "XLY": "XLY", "XLP": "XLP", 
        "HYG": "HYG", "TLT": "TLT", "GLD": "GLD", "USO": "USO"
    }
    df_list = []
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    for t, name in tickers.items():
        try:
            data = yf.download(
                t, 
                start=start_date.strftime('%Y-%m-%d'), 
                end=end_date.strftime('%Y-%m-%d'), 
                progress=False
            )
            
            if not data.empty and 'Close' in data.columns:
                temp = data['Close'].copy()
                if isinstance(temp, pd.DataFrame):
                    temp = temp.iloc[:, 0]
                
                temp.name = name
                df_list.append(temp)
        except Exception:
            pass
            
    if df_list:
        df = pd.concat(df_list, axis=1).reset_index()
        col_date = [c for c in df.columns if str(c).lower() == 'date']
        if col_date:
            df = df.rename(columns={col_date[0]: 'Data'})
            df['Data'] = pd.to_datetime(df['Data']).dt.tz_localize(None).dt.normalize()
            return df
            
    return pd.DataFrame(columns=['Data'] + list(tickers.values()))

def fetch_bridge_data():
    try:
        response = requests.get(GOOGLE_BRIDGE_URL, timeout=10)
        response.raise_for_status()
        df = pd.read_csv(io.StringIO(response.text))
        df.columns = df.columns.str.strip()
        
        col_mapping = {'Date': 'Data', 'Net_Liquidity': 'Net_Liquidity', 'M2': 'M2'}
        df = df.rename(columns=lambda x: col_mapping.get(x, x))
        
        if 'Data' not in df.columns:
            return pd.DataFrame(columns=["Data", "Net_Liquidity", "M2", "MOVE"])

        if pd.api.types.is_numeric_dtype(df['Data']):
            df['Data'] = pd.to_datetime(df['Data'], unit='D', origin='1899-12-30')
        else:
            df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
            
        df['Data'] = df['Data'].dt.normalize()
        
        for col in ['Net_Liquidity', 'M2', 'MOVE']:
            if col in df.columns: 
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
        return df.dropna(subset=['Data'])
    except Exception:
        return pd.DataFrame(columns=["Data", "Net_Liquidity", "M2", "MOVE"])

def fetch_squeezemetrics_data():
    url = "https://squeezemetrics.com/monitor/static/DIX.csv"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        df = pd.read_csv(io.StringIO(response.text))
        df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.normalize()
        df = df.dropna(subset=['date'])
        df = df.rename(columns={'date': 'Data', 'dix': 'DIX', 'gex': 'GEX'})
        df['DIX'] = df['DIX'] * 100
        return df[['Data', 'DIX', 'GEX']].sort_values('Data')
    except Exception:
        return pd.DataFrame(columns=['Data', 'DIX', 'GEX'])

def fetch_cboe_pc_ratio():
    url = "https://cdn.cboe.com/data/us/options/market_statistics/historical_data/totalpc.csv"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        df = pd.read_csv(io.StringIO(response.text), skiprows=2)
        df['DATE'] = pd.to_datetime(df['DATE'], errors='coerce').dt.normalize()
        df = df.dropna(subset=['DATE'])
        df = df.rename(columns={'DATE': 'Data', 'P/C Ratio': 'P_C'})
        return df[['Data', 'P_C']].sort_values('Data')
    except Exception:
        return pd.DataFrame(columns=['Data', 'P_C'])

def calculate_rolling_zscore(series, window=252):
    rolling_mean = series.rolling(window=window, min_periods=1).mean()
    rolling_std = series.rolling(window=window, min_periods=1).std(ddof=0)
    return np.where(rolling_std == 0, 0, (series - rolling_mean) / rolling_std)
