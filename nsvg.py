import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime
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
        background-color: transparent !important; color: #002366 !important; border: 2px solid #002366 !important; border-radius: 8px; transition: 0.3s;
    }
    .stButton > button:hover { background-color: #002366 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. AUTO-LOGOUT & DATABASE LOGIC ---
if 'last_activity' not in st.session_state:
    st.session_state.last_activity = time.time()

if st.session_state.get('logged_in'):
    if time.time() - st.session_state.last_activity > 300: # 5 Minutes
        st.session_state.clear()
        st.warning("Sikkerhetstidsavbrudd: Du har blitt logget ut pga inaktivitet.")
        st.rerun()
st.session_state.last_activity = time.time()

DB_FILE = "nsvg_database_pro.csv"
LOG_FILE = "nsvg_security_logs.csv"
DOCS_DIR = "nsvg_vedlegg"
if not os.path.exists(DOCS_DIR): os.makedirs(DOCS_DIR)

# IDs aur Passwords ka database
USERS_DB = {
    "amina": "aminaaz0207",
    "umer": "Umer2026",
    "ali": "AliPass123"
}

def record_log(user, loc_data, action):
    try:
        lat = loc_data.get('coords', {}).get('latitude', "N/A") if loc_data else "N/A"
        lon = loc_data.get('coords', {}).get('longitude', "N/A") if loc_data else "N/A"
    except:
        lat, lon = "N/A", "N/A"
    new_log = {
        "Timestamp": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
        "Bruker": user, "Handling": action, "Position": f"{lat}, {lon}",
        "Kart": f"https://www.google.com/maps?q={lat},{lon}" if lat != "N/A" else "N/A"
    }
    log_df = pd.DataFrame([new_log])
    if not os.path.exists(LOG_FILE): log_df.to_csv(LOG_FILE, index=False)
    else: log_df.to_csv(LOG_FILE, mode='a', header=False, index=False)

def last_data():
    if not os.path.exists(DB_FILE):
        cols = ["ID", "Dato", "Produkt", "Hovedsøker", "Fnr", "Beløp", "Status", "Notater", "Vedlegg_Sti", "Registrert_Av"]
        df = pd.DataFrame(columns=cols)
        df.to_csv(DB_FILE, index=False)
        return df
    return pd.read_csv(DB_FILE)

# --- 3. LOGIN SYSTEM ---
if not st.session_state.get('logged_in'):
    st.title("🛡️ NSVG - Sikker Digital Portal")
    st.info("⚠️ **Sikkerhetsoppdatering:** For å beskytte systemet er 'Stedstilgang' obligatorisk. Klikk 'Tillat' (Allow).")
    
    loc = get_geolocation()
    input_user = st.text_input("Brukernavn (User ID)").lower().strip()
    input_pw = st.text_input("Passord", type="password")
    
    if st.button("Logg inn"):
        if input_user == "admin" and input_pw == "NSVG2026":
            st.session_state.update({"logged_in": True, "user_role": "Admin", "user_id": "Admin"})
            record_log("Admin", loc, "Innlogging suksess")
            st.rerun()
        elif input_user in USERS_DB and input_pw == USERS_DB[input_user]:
            st.session_state.update({"logged_in": True, "user_role": "Worker", "user_id": input_user.capitalize()})
            record_log(input_user, loc, "Innlogging suksess")
            st.rerun()
        else:
            st.error("Feil brukernavn eller passord!")
    st.stop()

# --- 4. MAIN APP ---
df = last_data()
role = st.session_state['user_role']
current_user = st.session_state['user_id']
display_df = df[df['Registrert_Av'] == current_user] if role == "Worker" else df

st.sidebar.title(f"👤 {current_user}")
menu = ["📊 Dashbord", "➕ Registrer ny søknad", "📂 Kunde Arkiv"]
if role == "Admin": menu.append("🚨 Admin Kontroll")
valg = st.sidebar.radio("Hovedmeny", menu)

if st.sidebar.button("🔴 Logg ut"):
    st.session_state.clear()
    st.rerun()

# --- ADMIN SECTION ---
if valg == "🚨 Admin Kontroll":
    st.header("🕵️ Master Kontrollpanel")
    if os.path.exists(LOG_FILE): st.dataframe(pd.read_csv(LOG_FILE), use_container_width=True)
    else: st.info("Ingen logger funnet.")

# --- DASHBOARD ---
elif valg == "📊 Dashbord":
    st.header(f"📊 Dashboard - {current_user}")
    col1, col2 = st.columns(2)
    total_volum = pd.to_numeric(display_df['Beløp'], errors='coerce').sum()
    col1.metric("Volum (kr)", f"{total_volum:,} kr")
    col2.metric("Aktive saker", len(display_df))
    st.divider()
    st.dataframe(display_df.tail(15), use_container_width=True)

# --- REGISTRER NY SØKNAD (Detailed Form) ---
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
            jobb = st.selectbox("Arbeidsstatus", ["Fast ansatt", "Midlertidig", "AAP", "Uføretrygd", "Arbeidsledig", "Selvstendig"])
            firma = st.text_input("Navn på arbeidsgiver / Firma")
            lonn = st.number_input("Årslønn før skatt (Brutto)", min_value=0)

        if "Boliglån" in prod or "Mellomfinansiering" in prod:
            st.divider()
            k1, k2 = st.columns(2)
            with k1:
                barn = st.number_input("Antall barn under 18 år", min_value=0)
                ek = st.number_input("Egenkapital (kr)", min_value=0)
            with k2:
                gjeld = st.number_input("Annen gjeld", min_value=0)
                utleie = st.selectbox("Skal boligen ha utleiedel?", ["Nei", "Ja"])

        if has_medsoker:
            st.divider()
            st.subheader("👥 Med-søker")
            m1, m2 = st.columns(2)
            with m1: m_navn = st.text_input("Medsøker Navn"); m_fnr = st.text_input("Medsøker Fnr")
            with m2: m_lonn = st.number_input("Medsøker Årslønn", min_value=0); m_gjeld = st.number_input("Medsøker gjeld", min_value=0)

        st.divider()
        notater_input = st.text_area("Interne notater")
        opplastede_filer = st.file_uploader("Last opp dokumenter", accept_multiple_files=True)
        total_belop = st.number_input("Søknadsbeløp (kr)", min_value=0)

        if st.form_submit_button("SEND INN SØKNAD TIL VAULT"):
            fil_liste = []
            if opplastede_filer:
                for fil in opplastede_filer:
                    ren_filnavn = f"{fnr}_{fil.name}".replace(" ", "_")
                    with open(os.path.join(DOCS_DIR, ren_filnavn), "wb") as f: f.write(fil.getbuffer())
                    fil_liste.append(ren_filnavn)
            
            ny_kunde = {
                "ID": len(df) + 1, "Dato": datetime.now().strftime("%d-%m-%Y"),
                "Produkt": prod, "Hovedsøker": navn, "Fnr": fnr, "Beløp": total_belop,
                "Status": "Til vurdering", "Notater": notater_input, 
                "Vedlegg_Sti": ",".join(fil_liste), "Registrert_Av": current_user
            }
            df = pd.concat([df, pd.DataFrame([ny_kunde])], ignore_index=True)
            df.to_csv(DB_FILE, index=False)
            st.success(f"✅ Søknad arkivert av {current_user}!")

# --- KUNDE ARKIV ---
elif valg == "📂 Kunde Arkiv":
    st.header(f"📂 Arkiv - {current_user}")
    sok = st.text_input("Søk i arkivet (Navn eller Fnr)")
    res_df = display_df[display_df.astype(str).apply(lambda x: x.str.contains(sok, case=False)).any(axis=1)] if sok else display_df
    for i, rad in res_df.iterrows():
        with st.expander(f"📁 {rad['Hovedsøker']} - {rad['Produkt']}"):
            st.write(f"**Beløp:** {rad['Beløp']:,} kr | **Dato:** {rad['Dato']} | **Status:** {rad['Status']}")
            st.info(f"**Notater:** {rad['Notater']}")
            vedlegg = str(rad['Vedlegg_Sti'])
            if vedlegg and vedlegg != "nan" and vedlegg != "":
                for f_name in vedlegg.split(","):
                    f_path = os.path.join(DOCS_DIR, f_name)
                    if os.path.exists(f_path):
                        with open(f_path, "rb") as d_file:
                            st.download_button(f"📥 {f_name}", d_file, file_name=f_name, key=f"{f_name}_{i}")
