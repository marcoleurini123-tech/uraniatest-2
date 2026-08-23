import pandas as pd
import numpy as np
import requests
import io
import yfinance as yf
import os

DB_FILE = "macro_database.csv"

def load_db():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        df['Data'] = pd.to_datetime(df['Data'])
        return df
    return pd.DataFrame(columns=['Data'])

def save_db(df):
    df.to_csv(DB_FILE, index=False)

def fetch_yahoo_data(days=365):
    tickers = {"^VIX": "VIX", "DX-Y.NYB": "DXY"}
    df_list = []
    
    for t, name in tickers.items():
        try:
            data = yf.download(t, period=f"{days}d", progress=False)
            if not data.empty:
                if isinstance(data.columns, pd.MultiIndex):
                    temp = data['Close'].copy()
                    temp.name = name
                else:
                    temp = data['Close'].rename(name)
                df_list.append(temp)
        except Exception as e:
            print(f"Errore Yahoo Finance per {t}: {e}")
            pass
            
    if df_list:
        df = pd.concat(df_list, axis=1).reset_index()
        df = df.rename(columns={'Date': 'Data'})
        df['Data'] = pd.to_datetime(df['Data']).dt.tz_localize(None)
        return df
        
    return pd.DataFrame(columns=['Data', 'VIX', 'DXY'])

def fetch_bridge_data():
    # Placeholder per dati MOVE. Nessun dato fittizio. Restituisce frame vuoto.
    return pd.DataFrame(columns=['Data', 'MOVE'])

def fetch_squeezemetrics_data():
    url = "https://squeezemetrics.com/monitor/static/DIX.csv"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        df = pd.read_csv(io.StringIO(response.text))
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df = df.dropna(subset=['date'])
        df = df.rename(columns={'date': 'Data', 'dix': 'DIX', 'gex': 'GEX'})
        df['DIX'] = df['DIX'] * 100
        return df[['Data', 'DIX', 'GEX']].sort_values('Data')
    except Exception as e:
        print(f"Errore SqueezeMetrics: {e}")
        return pd.DataFrame(columns=['Data', 'DIX', 'GEX'])

def fetch_cboe_pc_ratio():
    url = "https://cdn.cboe.com/data/us/options/market_statistics/historical_data/totalpc.csv"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        df = pd.read_csv(io.StringIO(response.text), skiprows=2)
        df['DATE'] = pd.to_datetime(df['DATE'], errors='coerce')
        df = df.dropna(subset=['DATE'])
        df = df.rename(columns={'DATE': 'Data', 'P/C Ratio': 'P_C'})
        return df[['Data', 'P_C']].sort_values('Data')
    except Exception as e:
        print(f"Errore CBOE: {e}")
        return pd.DataFrame(columns=['Data', 'P_C'])

def calculate_rolling_zscore(series, window=252):
    rolling_mean = series.rolling(window=window, min_periods=1).mean()
    rolling_std = series.rolling(window=window, min_periods=1).std(ddof=0)
    return np.where(rolling_std == 0, 0, (series - rolling_mean) / rolling_std)
