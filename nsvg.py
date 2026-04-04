import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime
import requests
from streamlit_js_eval import get_geolocation

# --- 1. CONFIG & STYLE ---
st.set_page_config(page_title="NSVG Digital Bank Portal", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e0e0e0; }
    [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] label, [data-testid="stSidebar"] .stSelectbox div {
        color: #002366 !important; font-weight: bold !important;
    }
    .stButton > button {
        background-color: transparent !important; color: #0000FF !important; border: 2px solid #0000FF !important; border-radius: 8px; transition: 0.3s;
    }
    .stButton > button:hover { background-color: #0000FF !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. AUTO-LOGOUT & DATABASE LOGIC ---
if 'last_activity' not in st.session_state:
    st.session_state.last_activity = time.time()

if st.session_state.get('logged_in'):
    if time.time() - st.session_state.last_activity > 300: # 5 Minutes
        st.session_state.clear()
        st.warning("Security Timeout: Inactivity ki wajah se logout kar diya gaya hai.")
        st.rerun()
st.session_state.last_activity = time.time()

DB_FILE = "nsvg_database_pro.csv"
LOG_FILE = "nsvg_security_logs.csv"
DOCS_DIR = "nsvg_vedlegg"

if not os.path.exists(DOCS_DIR): os.makedirs(DOCS_DIR)

if 'users_db' not in st.session_state:
    st.session_state.users_db = {
        "amina": "aminaaz0207",
        "umer": "Umer2026",
        "ali": "AliPass123"
    }

def record_log(user, loc_data, action):
    device = st.context.headers.get("User-Agent", "Unknown")
    lat = loc_data['coords']['latitude'] if loc_data else "N/A"
    lon = loc_data['coords']['longitude'] if loc_data else "N/A"
    new_log = {
        "Timestamp": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
        "User": user, "Action": action, "Lat/Lon": f"{lat}, {lon}",
        "Map": f"https://www.google.com/maps?q={lat},{lon}" if lat != "N/A" else "N/A",
        "Device": device
    }
    log_df = pd.DataFrame([new_log])
    if not os.path.exists(LOG_FILE): log_df.to_csv(LOG_FILE, index=False)
    else: log_df.to_csv(LOG_FILE, mode='a', header=False, index=False)

def last_data():
    cols = ["ID", "Dato", "Produkt", "Hovedsøker", "Fnr", "Beløp", "Status", "Notater", "Vedlegg_Sti", "Registrert_Av"]
    if not os.path.exists(DB_FILE):
        df = pd.DataFrame(columns=cols)
        df.to_csv(DB_FILE, index=False)
        return df
    return pd.read_csv(DB_FILE)

# --- 3. LOGIN SYSTEM ---
if not st.session_state.get('logged_in'):
    st.title("🛡️ NSVG - Sikker Digital Portal")
    st.info("⚠️ **Security Update:** System ki hifazat ke liye 'Location Access' lazmi hai. Baraye meherbani 'Allow' par click karein.")
    
    loc = get_geolocation()
    input_user = st.text_input("Brukernavn").lower().strip()
    input_pw = st.text_input("Passord", type="password")
    
    if st.button("Logg inn"):
        if input_user == "admin" and input_pw == "NSVG2026":
            st.session_state.update({"logged_in": True, "user_role": "Admin", "user_id": "Admin"})
            record_log("Admin", loc, "Login Success")
            st.rerun()
        elif input_user in st.session_state.users_db and input_pw == st.session_state.users_db[input_user]:
            st.session_state.update({"logged_in": True, "user_role": "Worker", "user_id": input_user.capitalize()})
            record_log(input_user, loc, "Login Success")
            st.rerun()
        else:
            record_log(input_user if input_user else "Unknown", loc, "Failed Attempt")
            st.error("Feil brukernavn eller passord!")
    st.stop()

# --- 4. MAIN APP ---
df = last_data()
role = st.session_state['user_role']
current_user = st.session_state['user_id']
display_df = df[df['Registrert_Av'] == current_user] if role == "Worker" else df

st.sidebar.title(f"👤 {current_user}")
menu = ["📊 Dashbord", "➕ Registrer ny søknad", "📂 Kunde Arkiv"]
if role == "Admin": menu.append("🚨 Admin Control")
valg = st.sidebar.radio("Hovedmeny", menu)

if st.sidebar.button("🔴 Logg ut"):
    st.session_state.clear()
    st.rerun()

# --- SECTION: ADMIN CONTROL ---
if valg == "🚨 Admin Control":
    st.header("🕵️ Master Control Panel")
    t1, t2 = st.tabs(["User Management", "Security Logs"])
    with t1:
        edit_u = st.selectbox("Velg bruker", list(st.session_state.users_db.keys()))
        new_p = st.text_input("Nytt Passord", type="password")
        if st.button("Oppdater Passord"):
            st.session_state.users_db[edit_u] = new_p
            st.success(f"Passord for {edit_u} oppdatert!")
    with t2:
        if os.path.exists(LOG_FILE): st.dataframe(pd.read_csv(LOG_FILE))
        else: st.info("Ingen logger funnet.")

# --- SECTION: DASHBOARD ---
elif valg == "📊 Dashbord":
    st.header(f"📊 Dashboard - {current_user}")
    col1, col2 = st.columns(2)
    total_volum = pd.to_numeric(display_df['Beløp'], errors='coerce').sum()
    col1.metric("Volum (kr)", f"{total_volum:,} kr")
    col2.metric("Aktive saker", len(display_df))
    st.divider()
    st.dataframe(display_df.tail(15), use_container_width=True)

# --- SECTION: REGISTRER NY SØKNAD ---
elif valg == "➕ Registrer ny søknad":
    st.header("➕ Opprett Ny Bankforespørsel")
    prod = st.selectbox("Velg ønsket bankprodukt", ["1. Boliglån", "2. Boliglån Refinansiering", "3. Mellomfinansiering", "4. Investlån / Bedriftslån / Leasing", "5. Byggelån", "6. Forbrukslån", "7. Billån"])
    is_bedrift = "Investlån" in prod
    has_medsoker = False
    if not is_bedrift:
        has_medsoker = st.radio("Søknadstype", ["Alene søker", "Med-søker / Kausjonist"]) == "Med-søker / Kausjonist"

    with st.form("nsvg_bank_skjema"):
        st.subheader("👤 Informasjon om Hovedsøker")
        c1, c2 = st.columns(2)
        with c1:
            navn = st.text_input("Fullt Navn (ihht ID)")
            fnr = st.text_input("Fødselsnummer (11 siffer)")
            epost = st.text_input("E-postadresse")
            tlf = st.text_input("Telefonnummer")
        with c2:
            sivil = st.selectbox("Sivilstatus", ["Gift", "Samboer", "Enslig", "Skilt/Separert"])
            jobb = st.selectbox("Arbeidsstatus", ["Fast ansatt", "Midlertidig", "AAP", "Uføretrygd", "Arbeidsledig", "Selvstendig næringsdrivende"])
            sektor = st.selectbox("Arbeidssektor", ["Privat sektor", "Offentlig/Statlig", "Kommunal"])
            firma = st.text_input("Navn på arbeidsgiver / Firma")
            ansatt_tid = st.text_input("Hvor lenge har du jobbet der?")
            lonn = st.number_input("Årslønn før skatt (Brutto)", min_value=0)

        st.divider()
        if "Boliglån" in prod or "Mellomfinansiering" in prod:
            k1, k2 = st.columns(2)
            with k1:
                barn = st.number_input("Antall barn under 18 år", min_value=0)
                sfo = st.selectbox("Går barn i SFO/Barnehage?", ["Nei", "Ja"])
                ek = st.number_input("Egenkapital (kr)", min_value=0)
                ek_kilde = st.text_input("Kilde til egenkapital")
                omrade = st.text_input("Ønsket område")
            with k2:
                gjeld = st.number_input("Annen gjeld", min_value=0)
                ramme = st.number_input("Samlet kredittramme", min_value=0)
                biler = st.number_input("Antall biler", min_value=0)
                billan = st.number_input("Restgjeld billån", min_value=0)
                utleie = st.selectbox("Skal boligen ha utleiedel?", ["Nei", "Ja"])
            if "Refinansiering" in prod:
                takst = st.number_input("Siste verdivurdering / E-takst", min_value=0)

        elif is_bedrift:
            st.warning("Firmadetaljer (Bedrift)")
            orgnr = st.text_input("Organisasjonsnummer")
            plan = st.text_area("Formål / Investeringsplan")

        if has_medsoker:
            st.divider()
            st.subheader("👥 Med-søker")
            m1, m2 = st.columns(2)
            with m1: m_navn = st.text_input("Medsøker Navn"); m_fnr = st.text_input("Medsøker Fnr")
            with m2: m_lonn = st.number_input("Medsøker Årslønn", min_value=0); m_gjeld = st.number_input("Medsøker gjeld", min_value=0)

        st.divider()
        notater_input = st.text_area("Interne notater")
        opplastede_filer = st.file_uploader("Last opp dokumenter", accept_multiple_files=True)
        total_belop = st.number_input("Endelig søknadsbeløp (kr)", min_value=0)
