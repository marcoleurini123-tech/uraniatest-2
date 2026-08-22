import streamlit as st
import pandas as pd
import numpy as np
from backend_engine import (
    load_db, 
    save_db, 
    fetch_yahoo_data, 
    fetch_bridge_data, 
    fetch_squeezemetrics,
    calculate_rolling_zscore
)

def render_page1():
    st.title("1. Macro Intelligence & Liquidità")
    st.caption("Terminal EOD • Analisi quantitativa dei flussi istituzionali e regimi macroeconomici.")
    
    df = load_db()

    # Sezione di controllo sincronizzazione
    col_sync, _ = st.columns([1, 3])
    with col_sync:
        if st.button("🔄 SINCRONIZZA FLUSSI EOD", use_container_width=True):
            with st.spinner("Estrazione dati reali in corso..."):
                d_y = fetch_yahoo_data(365)
                d_b = fetch_bridge_data()
                d_d = fetch_squeezemetrics()
                
                new_df = pd.merge(pd.merge(d_y, d_d, on='Data', how='outer'), d_b, on='Data', how='outer')
                if not df.empty:
                    manual_cols = [c for c in ['MOVE', 'VIX1D', 'P_C', 'DIX', 'GEX'] if c in df.columns]
                    manual_data = df[['Data'] + manual_cols].copy()
                    new_df = pd.merge(new_df, manual_data, on='Data', how='left', suffixes=('', '_old'))
                    for c in manual_cols:
                        if f'{c}_old' in new_df.columns:
                            new_df[c] = new_df[c].fillna(new_df[f'{c}_old'])
                
                new_df = new_df.sort_values("Data").ffill(limit=7)
                save_db(new_df)
                st.success("Sincronizzazione completata con successo.")
                st.rerun()

    st.markdown("---")

    if df.empty:
        st.warning("⚠️ Database locale vuoto. Esegui la sincronizzazione per popolare le serie storiche.")
        return

    df = df.sort_values("Data")

    # Calcolo Z-Score rigoroso a 252 sessioni (Regola 2)
    if 'VIX' in df.columns:
        df['VIX_Z252'] = calculate_rolling_zscore(df['VIX'], window=252)
    if 'DXY' in df.columns:
        df['DXY_Z252'] = calculate_rolling_zscore(df['DXY'], window=252)

    last = df.iloc[-1]

    st.subheader("🚦 Monitoraggio Z-Score & Indicatori di Regime")
    
    col1, col2, col3, col4 = st.columns(4)
    
    vix_val = last.get('VIX', np.nan)
    vix_z = last.get('VIX_Z252', np.nan)
    col1.metric(
        "VIX Spot", 
        f"{vix_val:.2f}" if not pd.isna(vix_val) else "N/A", 
        f"Z-Score (1Y): {vix_z:+.2f}" if not pd.isna(vix_z) else "N/A"
    )

    dix_val = last.get('DIX', np.nan)
    col2.metric(
        "DIX (Dark Pool %)", 
        f"{dix_val:.2f}%" if not pd.isna(dix_val) else "N/A"
    )

    gex_val = last.get('GEX', np.nan)
    col3.metric(
        "GEX (Gamma Exposure)", 
        f"{gex_val:,.0f}" if not pd.isna(gex_val) else "N/A"
    )

    move_val = last.get('MOVE', np.nan)
    col4.metric(
        "MOVE Index", 
        f"{move_val:.2f}" if not pd.isna(move_val) else "N/A"
    )

    st.markdown("---")
    st.subheader("Tabella Master EOD & Serie Storiche Normalizzate")
    st.dataframe(df.sort_values("Data", ascending=False).head(30), use_container_width=True, hide_index=True)
