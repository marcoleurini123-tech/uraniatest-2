import pandas as pd
import numpy as np
import yfinance as yf
import os
import streamlit as st

MANUAL_DATA_FILE = "manual_metrics.csv"

TICKERS_MAP = {
    "VIX": "^VIX", "VVIX": "^VVIX", "SKEW": "^SKEW", 
    "DXY": "DX-Y.NYB", "SPY": "SPY", "RSP": "RSP", 
    "HYG": "HYG", "TLT": "TLT", "LQD": "LQD", "GLD": "GLD", 
    "USO": "USO", "US2Y": "^IRX", "US10Y": "^TNX"
}

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_stable_eod_data(days: int = 90) -> pd.DataFrame:
    """
    Estrae le serie storiche EOD stabili con finestra temporale ridotta 
    per rispettare i vincoli di banda della connessione.
    Conforme alla Regola 1: zero dati fittizi, restituisce NaN in caso di errore di rete.
    """
    tickers_list = list(TICKERS_MAP.values())
    
    try:
        df_raw = yf.download(tickers_list, period=f"{days}d", interval="1d", progress=False, group_by='ticker', threads=False)
        if df_raw.empty:
            return pd.DataFrame(columns=["Data"])
        
        data_frames = {}
        for key, ticker in TICKERS_MAP.items():
            try:
                if len(tickers_list) == 1:
                    s = df_raw['Close']
                else:
                    s = df_raw[ticker]['Close']
                
                if not s.empty:
                    if isinstance(s, pd.DataFrame):
                        s = s.iloc[:, 0]
                    data_frames[key] = s.dropna()
            except Exception:
                continue

        if not data_frames:
            return pd.DataFrame(columns=["Data"])

        data = pd.DataFrame(data_frames)
        data.index = pd.to_datetime(data.index).tz_localize(None).normalize()
        return data.reset_index().rename(columns={'index': 'Data', 'Date': 'Data'})
        
    except Exception:
        return pd.DataFrame(columns=["Data"])

def calculate_rolling_zscore(series: pd.Series, window: int = 30) -> pd.Series:
    """
    Conforme alla Regola 2: Rigore Matematico e Z-Score.
    Calcolo statistico basato su deviazione standard mobile adattato alla finestra ridotta.
    """
    mean = series.rolling(window=window, min_periods=5).mean()
    std = series.rolling(window=window, min_periods=5).std()
    return (series - mean) / (std + 1e-9)

def load_manual_bridge_data() -> pd.DataFrame:
    """Gestisce il bridge di input manuale per metriche volatili o delistate."""
    if os.path.exists(MANUAL_DATA_FILE):
        try:
            df_man = pd.read_csv(MANUAL_DATA_FILE)
            df_man['Data'] = pd.to_datetime(df_man['Data']).dt.normalize()
            return df_man
        except Exception:
            pass
    return pd.DataFrame(columns=["Data", "VIX1D", "PCCR", "DIX", "GEX", "MOVE"])

def save_manual_bridge_data(new_row_dict: dict) -> pd.DataFrame:
    """Salva o aggiorna i dati manuali inseriti dall'utente nel file di bridge locale."""
    df_man = load_manual_bridge_data()
    target_date = pd.to_datetime(new_row_dict["Data"]).normalize()
    
    df_man = df_man[df_man['Data'] != target_date]
    new_row = pd.DataFrame([new_row_dict])
    new_row['Data'] = pd.to_datetime(new_row['Data']).dt.normalize()
    
    df_man = pd.concat([df_man, new_row], ignore_index=True).sort_values("Data")
    df_man.to_csv(MANUAL_DATA_FILE, index=False)
    return df_man
