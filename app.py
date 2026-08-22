import streamlit as st
import hmac

# Configurazione globale e layout minimale (Tema Scuro Istituzionale)
st.set_page_config(
    page_title="URANIA QUANTITATIVE TERMINAL",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Stile visivo e iniezione immagine di sfondo (CSS Istituzionale)
BACKGROUND_IMAGE_URL = "https://images.unsplash.com/photo-1639762681485-074b7f938ba0?q=80&w=2000&auto=format&fit=crop"

st.markdown(
    f"""
    <style>
    .stApp {{
        background: linear-gradient(rgba(3, 7, 18, 0.92), rgba(3, 7, 18, 0.95)), url("{BACKGROUND_IMAGE_URL}");
        background-size: cover;
        background-position: center;
        color: #f8fafc;
    }}
    .login-box {{
        background: rgba(15, 23, 42, 0.85);
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 40px;
        text-align: center;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# Gestione della sicurezza e autenticazione (Regola 3)
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    _, col_c, _ = st.columns([1, 1.2, 1])
    with col_c:
        st.markdown(
            """
            <div class="login-box">
                <h3>🛡️ URANIA SYSTEM</h3>
                <p style="color: #64748b; font-size: 12px;">Macro Quantitative Terminal • EOD Execution Engine</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        pwd = st.text_input("Password di Accesso:", type="password", placeholder="••••••••••••")
        if st.button("SBLOCCA TERMINALE", use_container_width=True):
            try:
                if hmac.compare_digest(pwd, st.secrets["APP_PASSWORD"]):
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Credenziali non valide.")
            except KeyError:
                st.error("Errore critico: chiave 'APP_PASSWORD' mancante nel vault st.secrets.")
    st.stop()

# Sidebar di navigazione a compartimenti stagni (Regola 4)
with st.sidebar:
    st.markdown("### 🛡️ URANIA SYSTEM")
    st.caption("Engine EOD • Z-Score & Volumetric Lab")
    
    nav = st.radio(
        "Moduli di Analisi:",
        [
            "1. Macro Intelligence & Liquidità",
            "2. Z-Score & COT Lab (CFTC)",
            "3. Quant Lab (Studi Storici)",
            "4. POC Scanner & Telegram Radar"
        ]
    )
    
    st.markdown("---")
    st.markdown("● **Status:** `Secure & Isolated` ✅")
    
    if st.button("🔒 Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# Router isolato dei moduli
if nav.startswith("1."):
    try:
        from pages_modules.page1_macro import render_page1
        render_page1()
    except ImportError:
        st.title("1. Macro Intelligence & Liquidità")
        st.error("Errore critico: modulo 'page1_macro.py' non trovato nella cartella pages_modules.")
    except Exception as e:
        st.error(f"Errore di esecuzione nel Modulo 1: {str(e)}")

elif nav.startswith("2."):
    st.title("2. Z-Score & COT Lab (CFTC)")
    st.info("Compartimento stagno 2 in fase di sviluppo.")

elif nav.startswith("3."):
    st.title("3. Quant Lab (Studi Storici)")
    st.info("Compartimento stagno 3 in attesa di sviluppo.")

elif nav.startswith("4."):
    st.title("4. POC Scanner & Telegram Radar")
    st.info("Compartimento stagno 4 in attesa di sviluppo.")
