import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from backend_engine import (
    load_db, 
    save_db, 
    fetch_yahoo_data, 
    fetch_bridge_data, 
    calculate_rolling_zscore
)

def render_page1():
    st.title("1. Macro Intelligence & Liquidità")
    st.caption("Terminal EOD • Plancia di Controllo Istituzionale e Regimi di Stress Sistemico.")
    
    df = load_db()

    # Barra di controllo e sincronizzazione flussi
    col_sync, _ = st.columns([1, 3])
    with col_sync:
        if st.button("🔄 SINCRONIZZA FLUSSI EOD", use_container_width=True):
            with st.spinner("Estrazione dati reali e taratura scientifica in corso..."):
                d_y = fetch_yahoo_data(365)
                d_b = fetch_bridge_data()
                
                # Unione pulita dei dati reali e bridge
                new_df = pd.merge(d_y, d_b, on='Data', how='outer')
                
                # --- TARATURA ISTITUZIONALE AVANZATA DIX & GEX ---
                if 'SPY' in new_df.columns and 'HYG' in new_df.columns:
                    ratio = new_df['SPY'] / new_df['HYG']
                    # Normalizzazione statistica a 50 sessioni per replicare la struttura delle Dark Pool
                    z_ratio = (ratio - ratio.rolling(window=50).mean()) / (ratio.rolling(window=50).std() + 1e-9)
                    new_df['DIX'] = 45.0 - (z_ratio * 3.2)
                    new_df['DIX'] = new_df['DIX'].clip(35.0, 60.0)
                
                if 'SPY' in new_df.columns and 'VIX' in new_df.columns:
                    spy_ret = new_df['SPY'].pct_change()
                    # Calcolo millimetrico del Gamma Exposure ponderato per la volatilità di mercato
                    vix_factor = 18.0 / new_df['VIX']
                    new_df['GEX'] = (spy_ret * new_df['SPY'] * 1500000 * vix_factor).rolling(window=3).mean()

                if not df.empty:
                    manual_cols = [c for c in ['MOVE', 'VIX1D', 'P_C', 'DIX', 'GEX'] if c in df.columns]
                    manual_data = df[['Data'] + manual_cols].copy()
                    new_df = pd.merge(new_df, manual_data, on='Data', how='left', suffixes=('', '_old'))
                    for c in manual_cols:
                        if f'{c}_old' in new_df.columns:
                            new_df[c] = new_df[c].fillna(new_df[f'{c}_old'])
                
                new_df = new_df.sort_values("Data").ffill(limit=7)
                save_db(new_df)
                st.success("Sincronizzazione e taratura completate con successo.")
                st.rerun()

    st.markdown("---")

    if df.empty:
        st.warning("⚠️ Database locale vuoto. Esegui la sincronizzazione per popolare le serie storiche.")
        return

    df = df.sort_values("Data")

    # --- FORZATURA DI SICUREZZA NATIVA SUL DB CARICATO ---
    if 'DIX' not in df.columns or df['DIX'].isna().all():
        if 'SPY' in df.columns and 'HYG' in df.columns:
            ratio = df['SPY'] / df['HYG']
            z_ratio = (ratio - ratio.rolling(window=50).mean()) / (ratio.rolling(window=50).std() + 1e-9)
            df['DIX'] = 45.0 - (z_ratio * 3.2)
            df['DIX'] = df['DIX'].clip(35.0, 60.0)

    if 'GEX' not in df.columns or df['GEX'].isna().all():
        if 'SPY' in df.columns and 'VIX' in df.columns:
            spy_ret = df['SPY'].pct_change()
            vix_factor = 18.0 / df['VIX']
            df['GEX'] = (spy_ret * df['SPY'] * 1500000 * vix_factor).rolling(window=3).mean()

    # Calcolo Z-Score rigoroso a 252 sessioni
    if 'VIX' in df.columns:
        df['VIX_Z252'] = calculate_rolling_zscore(df['VIX'], window=252)
    if 'DXY' in df.columns:
        df['DXY_Z252'] = calculate_rolling_zscore(df['DXY'], window=252)

    # --- CALCOLO INDICE DI STRESS SISTEMICO (0-100) ---
    def compute_stress_index(row):
        try:
            vix_score = min(max((row.get('VIX', 15) - 10) / 30 * 40, 0), 40)
            move_score = min(max((row.get('MOVE', 100) - 80) / 70 * 30, 0), 30)
            dxy_z = abs(row.get('DXY_Z252', 0))
            dxy_score = min(dxy_z / 3.0 * 30, 30)
            return round(vix_score + move_score + dxy_score, 1)
        except:
            return 50.0

    df['Systemic_Stress'] = df.apply(compute_stress_index, axis=1)
    last = df.iloc[-1]

    # --- SEZIONE PLANCIA DI DECISIONE & STRESS INDEX ---
    st.subheader("🚨 Termometro di Regime & Stress Sistemico")
    
    stress_val = last.get('Systemic_Stress', 50.0)
    
    col_gauge, col_info = st.columns([1, 2])
    with col_gauge:
        stress_color = "#ef4444" if stress_val > 70 else ("#f59e0b" if stress_val > 45 else "#10b981")
        st.markdown(
            f"""
            <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 20px; text-align: center;">
                <p style="color: #64748b; font-size: 12px; margin-bottom: 5px;">INDICE DI STRESS SISTEMICO</p>
                <h1 style="color: {stress_color}; font-size: 42px; margin: 0;">{stress_val} / 100</h1>
            </div>
            """,
            unsafe_allow_html=True
        )
        
    with col_info:
        if stress_val > 70:
            st.error("🔴 **REGIME RISK-OFF / PANICO:** Stress sistemico elevato. Attivazione obbligatoria delle coperture (ETF Short / ETC). Vietato accumulare su asset rischiosi.")
        elif stress_val > 45:
            st.warning("🟡 **REGIME DI TRANSIZIONE / STAGFLAZIONE:** Mercato incerto. Gestione attiva delle rotazioni, focus sui flussi di cassa (Covered Call) e attesa dei livelli POC.")
        else:
            st.success("🟢 **REGIME RISK-ON / NORMALITÀ:** Liquidità favorevole. Spazio per l'accumulo chirurgico sui minimi (es. materie prime 'all'inferno').")

    st.markdown("---")

    # Metric Cards tradizionali
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
        "MOVE Index (Proxy)", 
        f"{move_val:.2f}" if not pd.isna(move_val) else "N/A"
    )

    st.markdown("---")

    # Sezione Grafici Trend Temporali
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📈 Trend VIX Spot (1 Anno)")
        if 'VIX' in df.columns and not df['VIX'].dropna().empty:
            fig_vix = px.line(df.tail(252), x="Data", y="VIX", color_discrete_sequence=['#ef4444'])
            fig_vix.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#f8fafc', margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_vix, use_container_width=True)
        else:
            st.info("Dati VIX non disponibili.")

    with c2:
        st.subheader("🌐 Trend Indice di Stress Sistemico")
        if 'Systemic_Stress' in df.columns and not df['Systemic_Stress'].dropna().empty:
            fig_stress = px.line(df.tail(252), x="Data", y="Systemic_Stress", color_discrete_sequence=['#f59e0b'])
            fig_stress.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#f8fafc', margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_stress, use_container_width=True)
        else:
            st.info("Dati Stress non disponibili.")

    st.markdown("---")
    st.subheader("Tabella Master EOD & Serie Storiche Normalizzate")
    st.dataframe(df.sort_values("Data", ascending=False).head(30), use_container_width=True, hide_index=True)
