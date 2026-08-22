import pandas as pd
import numpy as np
import yfinance as yf
import requests
import io
import os

DB_FILE = "macro_data.csv"
GOOGLE_BRIDGE_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSeeY57SBwd6BftA2Bq8C0nyzzT3wj9WRWOihDF7QE-COPXhC4r2RN_k_BRgZke1nU2BbKT8oRlsXOX/pub?gid=1412711569&single=true&output=csv"

COLUMNS = [
    "Data", "VIX1D", "VIX9D", "VIX", "VIX3M", "VIX6M", "VIX1Y", "VVIX", "MOVE", "SKEW", 
    "DXY", "DIX", "GEX", "SPY", "RSP", "HYG", "XLY", "XLP", "TLT", "P_C", "GLD", "USO", "Net_Liquidity", "M2"
]

def load_db() -> pd.DataFrame:
    """Carica istantaneamente il database locale per azzerare i tempi di avvio."""
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE)
            df['Data'] = pd.to_datetime(df['Data']).dt.normalize()
            for col in COLUMNS:
                if col not in df.columns: 
                    df[col] = 0.0
            return df.sort_values("Data")
        except Exception:
            pass
    return pd.DataFrame(columns=COLUMNS)

def save_db(df: pd.DataFrame):
    """Salva il database consolidato su disco."""
    df = df.drop_duplicates(subset=['Data'], keep='last').sort_values("Data")
    df.to_csv(DB_FILE, index=False)

def fetch_bridge_data() -> pd.DataFrame:
    """Estrae i dati macro da Google Bridge con gestione rigorosa delle eccezioni."""
    try:
        response = requests.get(GOOGLE_BRIDGE_URL, timeout=10)
        response.raise_for_status()
        df_bridge = pd.read_csv(io.StringIO(response.text))
        df_bridge.columns = df_bridge.columns.str.strip()
        df_bridge = df_bridge.rename(columns={'Data': 'Data', 'Date': 'Data', 'Net_Liquidity': 'Net_Liquidity', 'M2': 'M2'})
        
        if pd.api.types.is_numeric_dtype(df_bridge['Data']):
            df_bridge['Data'] = pd.to_datetime(df_bridge['Data'], unit='D', origin='1899-12-30')
        else:
            df_bridge['Data'] = pd.to_datetime(df_bridge['Data'], errors='coerce')
            
        df_bridge['Data'] = df_bridge['Data'].dt.normalize()
        for col in ['Net_Liquidity', 'M2']:
            if col in df_bridge.columns: 
                df_bridge[col] = pd.to_numeric(df_bridge[col], errors='coerce')
                
        return df_bridge.dropna(subset=['Data', 'Net_Liquidity'])
    except Exception:
        return pd.DataFrame(columns=["Data", "Net_Liquidity", "M2"])

def fetch_yahoo_data(days: int = 60) -> pd.DataFrame:
    """Estrae in blocco (bulk) i dati da Yahoo Finance in un'unica chiamata di rete."""
    tickers = {
        "VIX9D": "^VIX9D", "VIX": "^VIX", "VIX3M": "^VIX3M", "VIX6M": "^VIX6M", 
        "VIX1Y": "^VIX1Y", "VVIX": "^VVIX", "SKEW": "^SKEW", "DXY": "DX-Y.NYB", 
        "SPY": "SPY", "RSP": "RSP", "XLY": "XLY", "XLP": "XLP", "HYG": "HYG", 
        "TLT": "TLT", "P_C": "^PCCR", "GLD": "GLD", "USO": "USO"
    }
    try:
        raw_data = yf.download(list(tickers.values()), period=f"{days}d", interval="1d", progress=False)
        if raw_data.empty or 'Close' not in raw_data.columns:
            return pd.DataFrame(columns=["Data"])
            
        data = raw_data['Close']
        data = data.rename(columns={v: k for k, v in tickers.items()})
        data.index = pd.to_datetime(data.index).tz_localize(None).normalize()
        return data.reset_index().rename(columns={'Date': 'Data', 'index': 'Data'})
    except Exception:
        return pd.DataFrame(columns=["Data"])

def fetch_squeezemetrics() -> pd.DataFrame:
    """Estrae DIX e GEX reali da SqueezeMetrics."""
    try:
        url = "https://squeezemetrics.com/monitor/static/DIX.csv"
        df_d = pd.read_csv(url, timeout=10).tail(31).rename(columns={'date': 'Data', 'dix': 'DIX', 'gex': 'GEX'})
        df_d['Data'] = pd.to_datetime(df_d['Data']).dt.normalize()
        df_d['DIX'] = df_d['DIX'] * 100
        return df_d
    except Exception:
        return pd.DataFrame(columns=["Data", "DIX", "GEX"])
