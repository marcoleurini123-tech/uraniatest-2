import pandas as pd
import numpy as np
import yfinance as yf
import os

MANUAL_DATA_FILE = "manual_metrics.csv"

def fetch_stable_eod_data(days: int = 504) -> pd.DataFrame:
    """
    Estrae le serie storiche EOD stabili tramite yfinance.
    Conforme alla Regola 1: isolamento rigoroso delle eccezioni per singolo ticker.
    Se un endpoint fallisce, restituisce NaN senza generare dati fittizi.
    """
    tickers = {
        "VIX": "^VIX", "VVIX": "^VVIX", "SKEW": "^SKEW", 
        "DXY": "DX-Y.NYB", "SPY": "SPY", "RSP": "RSP", 
        "HYG": "HYG", "TLT": "TLT", "LQD": "LQD", "GLD": "GLD", 
        "USO": "USO", "US2Y": "^IRX", "US10Y": "^TNX"
    }
    
    data_frames = {}
    for key, ticker in tickers.items():
        try:
            df_t = yf.download(ticker, period=f"{days}d", interval="1d", progress=False)
            if not df_t.empty and 'Close' in df_t.columns:
                s = df_t['Close']
                if isinstance(s, pd.DataFrame):
                    s = s.iloc[:, 0]
                data_frames[key] = s
        except Exception:
            continue

    if not data_frames:
        return pd.DataFrame(columns=["Data"])

    data = pd.DataFrame(data_frames)
    data.index = pd.to_datetime(data.index).tz_localize(None).normalize()
    return data.reset_index().rename(columns={'index': 'Data', 'Date': 'Data'})

def calculate_rolling_zscore(series: pd.Series, window: int = 52) -> pd.Series:
    """
    Conforme alla Regola 2: Rigore Matematico e Z-Score.
    Calcolo statistico basato su deviazione standard mobile (rolling window).
    Nessuna soglia percentuale fissa o arbitraria.
    """
    mean = series.rolling(window=window, min_periods=10).mean()
    std = series.rolling(window=window, min_periods=10).std()
    return (series - mean) / (std + 1e-9)

def load_manual_bridge_data() -> pd.DataFrame:
    """
    Gestisce il bridge di input manuale per metriche volatili o delistate 
    (VIX1D, PCCR, DIX, GEX, MOVE).
    """
    if os.path.exists(MANUAL_DATA_FILE):
        try:
            df_man = pd.read_csv(MANUAL_DATA_FILE)
            df_man['Data'] = pd.to_datetime(df_man['Data']).dt.normalize()
            return df_man
        except Exception:
            pass
    return pd.DataFrame(columns=["Data", "VIX1D", "PCCR", "DIX", "GEX", "MOVE"])

def save_manual_bridge_data(new_row_dict: dict) -> pd.DataFrame:
    """
    Salva o aggiorna i dati manuali inseriti dall'utente nel file di bridge locale.
    """
    df_man = load_manual_bridge_data()
    target_date = pd.to_datetime(new_row_dict["Data"]).normalize()
    
    df_man = df_man[df_man['Data'] != target_date]
    new_row = pd.DataFrame([new_row_dict])
    new_row['Data'] = pd.to_datetime(new_row['Data']).dt.normalize()
    
    df_man = pd.concat([df_man, new_row], ignore_index=True).sort_values("Data")
    df_man.to_csv(MANUAL_DATA_FILE, index=False)
    return df_man
