import streamlit as st
import pandas as pd
import numpy as np
from datetime import date
from backend_engine import (
    fetch_stable_eod_data, 
    calculate_rolling_zscore, 
    load_manual_bridge_data, 
    save_manual_bridge_data
)

def render_page1():
    st.title("🛡️ Macro Intelligence & Liquidità Fed")
    st.caption("Terminal EOD • Monitoraggio flussi istituzionali e regimi macroeconomici.")

    st.markdown("---")

    # Sezione 1: Bridge Manuale Unificato per Metriche Instabili / Delistate
    with st.expander("📥 Inserimento Manuale Unificato (VIX1D, PCCR, DIX, GEX, MOVE)", expanded=False):
        st.markdown("Inserisci i valori di chiusura giornaliera per le metriche non disponibili via API diretta. Nessun dato fittizio ammesso.")
        
        with st.form("manual_bridge_form"):
            col_d, col_v1, col_pccr = st.columns(3)
            with col_d:
                m_date = st.date_input("Data di Riferimento", value=date.today())
            with col_v1:
                val_vix1d = st.number_input("VIX1D", value=0.0, format="%.2f", step=0.1)
            with col_pccr:
                val_pccr = st.number_input("Put/Call Ratio (PCCR)", value=0.0, format="%.4f", step=0.01)

            col_dix, col_gex, col_move = st.columns(3)
            with col_dix:
                val_dix = st.number_input("DIX (Dark Pool %)", value=0.0, format="%.2f", step=0.1)
            with col_gex:
                val_gex = st.number_input("GEX (Gamma Exposure)", value=0.0, format="%.2f", step=1.0)
            with col_move:
                val_move = st.number_input("MOVE Index", value=0.0, format="%.2f", step=0.1)

            submitted = st.form_submit_button("REGISTRA DATI NEL BRIDGE")
            if submitted:
                row_data = {
                    "Data": m_date.strftime("%Y-%m-%d"),
                    "VIX1D": val_vix1d if val_vix1d > 0 else np.nan,
                    "PCCR": val_pccr if val_pccr > 0 else np.nan,
                    "DIX": val_dix if val_dix > 0 else np.nan,
                    "GEX": val_gex if val_gex != 0 else np.nan,
                    "MOVE": val_move if val_move > 0 else np.nan
                }
                save_manual_bridge_data(row_data)
                st.success("Dati manuali registrati con successo nel database locale.")

    st.markdown("### 📊 Quadro EOD & Normalizzazione Statistica")

    # Caricamento dati automatici
    df_auto = fetch_stable_eod_data(days=504)
    df_man = load_manual_bridge_data()

    if df_auto.empty:
        st.warning("⚠️ Impossibile recuperare le serie storiche automatiche da yfinance. Conforme alla Regola 1: nessuna simulazione attiva.")
        return

    # Unione blindata tra dati automatici e bridge manuale
    if not df_man.empty:
        df_auto['Data'] = pd.to_datetime(df_auto['Data']).dt.normalize()
        df_man['Data'] = pd.to_datetime(df_man['Data']).dt.normalize()
        df_master = pd.merge(df_auto, df_man, on="Data", how="left")
    else:
        df_master = df_auto.copy()
        for col in ["VIX1D", "PCCR", "DIX", "GEX", "MOVE"]:
            df_master[col] = np.nan

    df_master = df_master.sort_values("Data").reset_index(drop=True)

    # Calcolo Z-Score rigoroso (Regola 2) su finestre standard (52 settimane)
    if 'VIX' in df_master.columns:
        df_master['VIX_Z52'] = calculate_rolling_zscore(df_master['VIX'], window=52)

    # Visualizzazione metriche chiave con rigore matematico
    col1, col2, col3, col4 = st.columns(4)

    if 'VIX' in df_master.columns and not df_master['VIX'].dropna().empty:
        last_vix = df_master['VIX'].iloc[-1]
        last_vix_z = df_master['VIX_Z52'].iloc[-1] if 'VIX_Z52' in df_master.columns else np.nan
        col1.metric("VIX Spot", f"{last_vix:.2f}", f"Z-Score 1Y: {last_vix_z:+.2f}")

    if 'SPY' in df_master.columns and not df_master['SPY'].dropna().empty:
        last_spy = df_master['SPY'].iloc[-1]
        prev_spy = df_master['SPY'].iloc[-2] if len(df_master) > 1 else last_spy
        pct_change = ((last_spy - prev_spy) / prev_spy) * 100
        col2.metric("SPY Close", f"${last_spy:.2f}", f"{pct_change:+.2f}%")

    if 'MOVE' in df_master.columns and not df_master['MOVE'].dropna().empty:
        last_move = df_master['MOVE'].iloc[-1]
        col3.metric("MOVE Index", f"{last_move:.2f}" if not pd.isna(last_move) else "N/A (Manuale)")

    if 'PCCR' in df_master.columns and not df_master['PCCR'].dropna().empty:
        last_pccr = df_master['PCCR'].iloc[-1]
        col4.metric("Put/Call Ratio", f"{last_pccr:.4f}" if not pd.isna(last_pccr) else "N/A (Manuale)")

    st.markdown("---")
    st.subheader("Tabella Master EOD (Dati Reali & Bridge)")
    st.dataframe(df_master.tail(30), use_container_width=True, hide_index=True)
