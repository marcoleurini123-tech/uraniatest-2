import pandas as pd
import numpy as np
import yfinance as yf
import os

MANUAL_DATA_FILE = "manual_metrics.csv"
CACHE_DATA_FILE = "macro_engine_data.csv"

TICKERS_MAP = {
    "VIX": "^VIX", "VVIX": "^VVIX", "SKEW": "^SKEW", 
    "DXY": "DX-Y.NYB", "SPY": "SPY", "RSP": "RSP", 
    "HYG": "HYG", "TLT": "TLT", "LQD": "LQD", "GLD": "GLD", 
    "USO": "USO", "US2Y": "^IRX", "US10Y": "^TNX"
}

def load_cached_eod_data() -> pd.DataFrame:
    """Carica istantaneamente i dati dalla cache locale per evitare blocchi di rete all'avvio."""
    if os.path.exists(CACHE_DATA_FILE):
        try:
            df = pd.read_csv(CACHE_DATA_FILE)
            df['Data'] = pd.to_datetime(df['Data']).dt.normalize()
            return df
        except Exception:
            pass
    return pd.DataFrame(columns=["Data"])

def fetch_stable_eod_data(force_update: bool = False) -> pd.DataFrame:
    """
    Estrae le serie storiche EOD con protezione anti-blocco (fail-fast).
    Conforme alla Regola 1: se la rete fallisce o va in timeout, restituisce 
    i dati in cache o un DataFrame vuoto, senza generare dati fittizi.
    """
    if not force_update:
        cached_df = load_cached_eod_data()
        if not cached_df.empty:
            return cached_df

    data_frames = {}
    for key, ticker in TICKERS_MAP.items():
        try:
            # Download singolo con periodo ridotto per garantire la risposta immediata
            df_t = yf.download(ticker, period="90d", interval="1d", progress=False, timeout=5)
            if not df_t.empty and 'Close' in df_t.columns:
                s = df_t['Close']
                if isinstance(s, pd.DataFrame):
                    s = s.iloc[:, 0]
                data_frames[key] = s.dropna()
        except Exception:
            continue

    if not data_frames:
        return load_cached_eod_data()

    data = pd.DataFrame(data_frames)
    data.index = pd.to_datetime(data.index).tz_localize(None).normalize()
    data = data.reset_index().rename(columns={'index': 'Data', 'Date': 'Data'})
    
    # Salva la cache locale per i futuri avvii istantanei
    data.to_csv(CACHE_DATA_FILE, index=False)
    return data

def calculate_rolling_zscore(series: pd.Series, window: int = 30) -> pd.Series:
    """
    Conforme alla Regola 2: Rigore Matematico e Z-Score.
    Calcolo statistico basato su deviazione standard mobile (rolling window).
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
