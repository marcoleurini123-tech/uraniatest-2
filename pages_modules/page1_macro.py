import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from backend_engine import (
    load_db, 
    save_db, 
    fetch_yahoo_data, 
    fetch_bridge_data, 
    fetch_squeezemetrics_data,
    fetch_cboe_pc_ratio,
    calculate_rolling_zscore
)

def render_manual_institutional_override(df):
    st.markdown("### ⚙️ Immissione Manuale Dati Istituzionali")
    st.caption("Inserire i dati EOD prima della sincronizzazione. I valori immessi non verranno sovrascritti dalle API.")
    
    with st.form("override_istituzionale"):
        c1, c2, c3, c4, c5 = st.columns(5)
        
        with c1:
            target_date = st.date_input("Data Riferimento", pd.Timestamp.today())
        with c2:
            dix_input = st.number_input("DIX (%)", min_value=0.0, max_value=100.0, step=0.1, format="%.1f")
        with c3:
            gex_input = st.number_input("GEX (Val Assoluto)", step=1000000.0, format="%.0f")
        with c4:
            pc_input = st.number_input("P/C Ratio", min_value=0.0, max_value=5.0, step=0.01, format="%.2f")
        with c5:
            move_input = st.number_input("MOVE Index", min_value=0.0, max_value=300.0, step=0.1, format="%.2f")
            
        submit = st.form_submit_button("1. Salva nel Database Locale")
        
        if submit:
            target_ts = pd.to_datetime(target_date).normalize()
            
            if not df.empty and target_ts in df['Data'].values:
                idx = df.index[df['Data'] == target_ts].tolist()[0]
            else:
                new_row = pd.DataFrame({'Data': [target_ts]})
                df = pd.concat([df, new_row], ignore_index=True)
                idx = df.index[-1]
            
            if dix_input > 0: df.at[idx, 'DIX'] = dix_input
            if gex_input != 0: df.at[idx, 'GEX'] = gex_input
            if pc_input > 0: df.at[idx, 'P_C'] = pc_input
            if move_input > 0: df.at[idx, 'MOVE'] = move_input
            
            df = df.sort_values("Data").reset_index(drop=True)
            save_db(df)
            st.success(f"Dati blindati nel DB per la sessione {target_ts.strftime('%Y-%m-%d')}.")
            st.rerun()

def render_page1():
    st.title("1. Macro Intelligence & Liquidità")
    st.caption("Terminal EOD • Plancia di Controllo Istituzionale e Regimi di Stress Sistemico.")
    
    df = load_db()

    render_manual_institutional_override(df)
    
    st.markdown("---")
    
    col_sync, _ = st.columns([1, 3])
    with col_sync:
        if st.button("🔄 2. SINCRONIZZA FLUSSI EOD", use_container_width=True):
            with st.spinner("Estrazione dati dalle API e allineamento database..."):
                d_y = fetch_yahoo_data(365)
                d_b = fetch_bridge_data()
                d_sq = fetch_squeezemetrics_data()
                d_pc = fetch_cboe_pc_ratio()
                
                fetched_df = pd.merge(d_y, d_b, on='Data', how='outer')
                if not d_sq.empty:
                    fetched_df = pd.merge(fetched_df, d_sq, on='Data', how='outer')
                if not d_pc.empty:
                    fetched_df = pd.merge(fetched_df, d_pc, on='Data', how='outer')

                if not df.empty:
                    fetched_df = fetched_df.set_index('Data')
                    local_df = df.set_index('Data')
                    final_df = local_df.combine_first(fetched_df).reset_index()
                else:
                    final_df = fetched_df

                final_df = final_df.sort_values("Data").ffill(limit=7).dropna(subset=['Data'])
                save_db(final_df)
                st.success("Sincronizzazione completata: i dati manuali sono stati preservati.")
                st.rerun()

    st.markdown("---")

    if df.empty:
        st.warning("⚠️ Database locale vuoto. Esegui la sincronizzazione.")
        return

    # ---------------------------------------------------------
    # NORMALIZZAZIONE VETTORIALE RUNTIME
    # ---------------------------------------------------------
    df = df.sort_values("Data").reset_index(drop=True)
    
    # Propaga gli ultimi dati validi su weekend o giornate vuote
    num_cols = ['VIX', 'DXY', 'MOVE', 'DIX', 'GEX', 'P_C']
    market_cols = [c for c in num_cols if c in df.columns]
    if market_cols:
        df[market_cols] = df[market_cols].ffill(limit=7)

    if 'VIX' in df.columns:
        df['VIX_Z252'] = calculate_rolling_zscore(df['VIX'], window=252)
    if 'DXY' in df.columns:
        df['DXY_Z252'] = calculate_rolling_zscore(df['DXY'], window=252)

    def compute_stress_index(row):
        try:
            vix_score = min(max((row.get('VIX', 15) - 10) / 30 * 40, 0), 40)
            
            move_val = row.get('MOVE', 100)
            if pd.isna(move_val):
                move_val = 100
            move_score = min(max((move_val - 80) / 70 * 30, 0), 30)
            
            dxy_z = abs(row.get('DXY_Z252', 0)) if not pd.isna(row.get('DXY_Z252')) else 0
            dxy_score = min(dxy_z / 3.0 * 30, 30)
            
            return round(vix_score + move_score + dxy_score, 1)
        except Exception:
            return 50.0

    df['Systemic_Stress'] = df.apply(compute_stress_index, axis=1)
    last = df.iloc[-1]

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
            st.error("🔴 **REGIME RISK-OFF / PANICO:** Stress sistemico elevato. Attivazione obbligatoria coperture. Vietato accumulare su asset rischiosi.")
        elif stress_val > 45:
            st.warning("🟡 **REGIME DI TRANSIZIONE / STAGFLAZIONE:** Mercato incerto. Gestione attiva delle rotazioni e attesa dei livelli POC.")
        else:
            st.success("🟢 **REGIME RISK-ON / NORMALITÀ:** Liquidità favorevole. Spazio per accumulo chirurgico sui minimi.")

    st.markdown("---")

    col1, col2, col3, col4, col5 = st.columns(5)
    vix_val = last.get('VIX', np.nan)
    vix_z = last.get('VIX_Z252', np.nan)
    col1.metric("VIX Spot", f"{vix_val:.2f}" if not pd.isna(vix_val) else "N/A", f"Z-Score(1Y): {vix_z:+.2f}" if not pd.isna(vix_z) else "N/A")

    dix_val = last.get('DIX', np.nan)
    col2.metric("DIX (Dark Pool %)", f"{dix_val:.2f}%" if not pd.isna(dix_val) else "N/A")

    gex_val = last.get('GEX', np.nan)
    col3.metric("GEX (Gamma Exp)", f"{gex_val:,.0f}" if not pd.isna(gex_val) else "N/A")

    pc_val = last.get('P_C', np.nan)
    col4.metric("Total P/C", f"{pc_val:.2f}" if not pd.isna(pc_val) else "N/A")

    move_val = last.get('MOVE', np.nan)
    col5.metric("MOVE Index", f"{move_val:.2f}" if not pd.isna(move_val) else "N/A")

    st.markdown("---")

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📈 Trend VIX Spot (1 Anno)")
        if 'VIX' in df.columns and not df['VIX'].dropna().empty:
            fig_vix = px.line(df.dropna(subset=['VIX']).tail(252), x="Data", y="VIX", color_discrete_sequence=['#ef4444'], template='plotly_dark')
            fig_vix.update_traces(connectgaps=True)
            fig_vix.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_vix, use_container_width=True)
        else:
            st.info("Dati VIX non disponibili.")

    with c2:
        st.subheader("🌐 Trend Indice di Stress Sistemico")
        if 'Systemic_Stress' in df.columns and not df['Systemic_Stress'].dropna().empty:
            fig_stress = px.line(df.dropna(subset=['Systemic_Stress']).tail(252), x="Data", y="Systemic_Stress", color_discrete_sequence=['#f59e0b'], template='plotly_dark')
            fig_stress.update_traces(connectgaps=True)
            fig_stress.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_stress, use_container_width=True)
        else:
            st.info("Dati Stress non disponibili.")

    st.markdown("---")
    st.subheader("Tabella Master EOD & Serie Storiche Normalizzate")
    
    display_df = df.sort_values("Data", ascending=False).head(30).copy()
    display_df['Data'] = display_df['Data'].dt.strftime('%Y-%m-%d')
    st.dataframe(display_df, use_container_width=True, hide_index=True)
