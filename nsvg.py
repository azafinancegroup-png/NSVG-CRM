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
        background-color: transparent !important; color: #0000FF !important; border: 2px solid #0000FF !important; border-radius: 8px; transition: 0.3s;
    }
    .stButton > button:hover { background-color: #0000FF !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABASE & SESSION LOGIC ---
DB_FILE = "nsvg_database_pro.csv"
LOG_FILE = "nsvg_security_logs.csv"
DOCS_DIR = "nsvg_vedlegg"
USER_FILE = "nsvg_users.csv"

if not os.path.exists(DOCS_DIR): os.makedirs(DOCS_DIR)

# Initialize Users if file doesn't exist
if not os.path.exists(USER_FILE):
    pd.DataFrame([
        {"username": "amina", "password": "aminaaz0207"},
        {"username": "umer", "password": "Umer2026"},
        {"username": "ali", "password": "AliPass123"}
    ]).to_csv(USER_FILE, index=False)

def get_users():
    return pd.read_csv(USER_FILE).set_index("username")["password"].to_dict()

def save_user_password(username, new_password):
    u_df = pd.read_csv(USER_FILE)
    u_df.loc[u_df['username'] == username, 'password'] = new_password
    u_df.to_csv(USER_FILE, index=False)

def record_log(user, loc_data, action):
    try:
        lat = loc_data['coords']['latitude'] if loc_data else "N/A"
        lon = loc_data['coords']['longitude'] if loc_data else "N/A"
    except: lat, lon = "N/A", "N/A"
    
    maps_url = f"https://www.google.com/maps?q={lat},{lon}" if lat != "N/A" else "No Location"
    new_log = {"Timestamp": datetime.now().strftime("%d-%m-%Y %H:%M:%S"), "Bruker": user, "Handling": action, "Maps Link": maps_url}
    
    log_df = pd.DataFrame([new_log])
    if not os.path.exists(LOG_FILE): log_df.to_csv(LOG_FILE, index=False)
    else: log_df.to_csv(LOG_FILE, mode='a', header=False, index=False)

# --- 3. LOGIN SYSTEM ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user_role': None, 'user_id': None})

if not st.session_state['logged_in']:
    st.title("🛡️ NSVG - Sikker Digital Portal")
    st.info("⚠️ **Security Update:** Klikk **'Allow/Tillat'** på posisjonsforespørselen øverst i nettleseren.")
    
    loc = get_geolocation() # Location Popup
    
    u_input = st.text_input("Brukernavn (User ID)").lower().strip()
    p_input = st.text_input("Passord", type="password")
    
    if st.button("Logg inn"):
        USERS_DB = get_users()
        if u_input == "admin" and p_input == "NSVG2026":
            st.session_state.update({'logged_in': True, 'user_role': "Admin", 'user_id': "Admin"})
            record_log("Admin", loc, "Innlogging suksess")
            st.rerun()
        elif u_input in USERS_DB and p_input == USERS_DB[u_input]:
            st.session_state.update({'logged_in': True, 'user_role': "Worker", 'user_id': u_input.capitalize()})
            record_log(u_input, loc, "Innlogging suksess")
            st.rerun()
        else:
            record_log(u_input if u_input else "Unknown", loc, "Feilet innlogging")
            st.error("Feil brukernavn eller passord!")
    st.stop()

# --- 4. MAIN APP LOGIC ---
if not os.path.exists(DB_FILE):
    pd.DataFrame(columns=["ID", "Dato", "Produkt", "Hovedsøker", "Fnr", "Beløp", "Status", "Notater", "Vedlegg_Sti", "Registrert_Av"]).to_csv(DB_FILE, index=False)

df = pd.read_csv(DB_FILE)
role = st.session_state['user_role']
current_user = st.session_state['user_id']
display_df = df[df['Registrert_Av'] == current_user] if role == "Worker" else df

st.sidebar.title(f"👤 {current_user}")
options = ["📊 Dashbord", "➕ Registrer ny søknad", "📂 Kunde Arkiv"]
if role == "Admin": options.append("🕵️ Master Kontrollpanel")
valg = st.sidebar.radio("Hovedmeny", options)

if st.sidebar.button("🔴 Logg ut"):
    st.session_state.clear()
    st.rerun()

# --- SECTION 1: MASTER KONTROLLPANEL ---
if valg == "🕵️ Master Kontrollpanel":
    st.header("🕵️ Master Kontrollpanel")
    t1, t2 = st.tabs(["Sikkerhetslogger", "Brukerinnstillinger"])
    with t1:
        if os.path.exists(LOG_FILE): st.dataframe(pd.read_csv(LOG_FILE).sort_values("Timestamp", ascending=False), use_container_width=True)
    with t2:
        st.subheader("Endre Passord")
        target = st.selectbox("Velg Bruker", list(get_users().keys()))
        new_p = st.text_input("Nytt Passord", type="password")
        if st.button("Lagre Nytt Passord"):
            save_user_password(target, new_p)
            st.success("Passord oppdatert!")

# --- SECTION 2: DASHBORD ---
elif valg == "📊 Dashbord":
    st.header(f"📊 Dashboard - {current_user}")
    c1, c2 = st.columns(2)
    vol = pd.to_numeric(display_df['Beløp'], errors='coerce').sum()
    c1.metric("Ditt Volum (kr)", f"{vol:,} kr")
    c2.metric("Aktive saker", len(display_df))
    st.divider()
    st.dataframe(display_df.tail(15), use_container_width=True)

# --- SECTION 3: REGISTRER NY SØKNAD (Detailed Form) ---
elif valg == "➕ Registrer ny søknad":
    st.header("➕ Opprett Ny Bankforespørsel")
    prod = st.selectbox("Velg bankprodukt", ["1. Boliglån", "2. Boliglån Refinansiering", "3. Mellomfinansiering", "4. Investlån", "5. Byggelån", "6. Forbrukslån", "7. Billån"])
    is_bedrift = "Investlån" in prod
    has_medsoker = False
    if not is_bedrift:
        has_medsoker = st.radio("Søknadstype", ["Alene søker", "Med-søker / Kausjonist"]) == "Med-søker / Kausjonist"

    with st.form("nsvg_bank_skjema"):
        st.subheader("👤 Hovedsøker")
        c1, c2 = st.columns(2)
        with c1:
            navn = st.text_input("Fullt Navn")
            fnr = st.text_input("Fødselsnummer (11 siffer)")
            epost = st.text_input("E-post")
            tlf = st.text_input("Telefon")
        with c2:
            sivil = st.selectbox("Sivilstatus", ["Gift", "Samboer", "Enslig", "Skilt"])
            jobb = st.selectbox("Arbeid", ["Fast ansatt", "AAP", "Uføre", "Selvstendig"])
            firma = st.text_input("Arbeidsgiver")
            lonn = st.number_input("Årslønn (Brutto)", min_value=0)

        if "Boliglån" in prod or "Mellomfinansiering" in prod:
            st.divider()
            k1, k2 = st.columns(2)
            with k1:
                barn = st.number_input("Antall barn", min_value=0)
                ek = st.number_input("Egenkapital", min_value=0)
            with k2:
                gjeld = st.number_input("Annen gjeld", min_value=0)
                utleie = st.selectbox("Utleiedel?", ["Nei", "Ja"])

        if has_medsoker:
            st.divider()
            st.subheader("👥 Med-søker")
            m1, m2 = st.columns(2)
            with m1: m_navn = st.text_input("Medsøker Navn"); m_fnr = st.text_input("Medsøker Fnr")
            with m2: m_lonn = st.number_input("Medsøker Lønn", min_value=0); m_gjeld = st.number_input("Medsøker Gjeld", min_value=0)

        st.divider()
        notat = st.text_area("Interne notater")
        filer = st.file_uploader("Last opp dokumenter", accept_multiple_files=True)
        belop = st.number_input("Søknadsbeløp (kr)", min_value=0)

        if st.form_submit_button("SEND INN SØKNAD"):
            fil_list = []
            if filer:
                for f in filer:
                    f_path = os.path.join(DOCS_DIR, f"{fnr}_{f.name}")
                    with open(f_path, "wb") as save_f: save_f.write(f.getbuffer())
                    fil_list.append(f.name)
            
            new_data = {
                "ID": len(df)+1, "Dato": datetime.now().strftime("%d-%m-%Y"),
                "Produkt": prod, "Hovedsøker": navn, "Fnr": fnr, "Beløp": belop,
                "Status": "Til vurdering", "Notater": notat, 
                "Vedlegg_Sti": ",".join(fil_list), "Registrert_Av": current_user
            }
            df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
            df.to_csv(DB_FILE, index=False)
            st.success("Søknad Arkivert!")

# --- SECTION 4: ARKIV ---
elif valg == "📂 Kunde Arkiv":
    st.header("📂 Arkiv")
    sok = st.text_input("Søk i arkivet")
    res = display_df[display_df.astype(str).apply(lambda x: x.str.contains(sok, case=False)).any(axis=1)] if sok else display_df
    
    for i, rad in res.iterrows():
        with st.expander(f"📁 {rad['Hovedsøker']} - {rad['Produkt']}"):
            st.write(f"**Beløp:** {rad['Beløp']:,} kr | **Dato:** {rad['Dato']} | **Status:** {rad['Status']}")
            st.info(f"**Notater:** {rad['Notater']}")
            vedlegg = str(rad['Vedlegg_Sti'])
            if vedlegg and vedlegg != "nan":
                for f_name in vedlegg.split(","):
                    f_path = os.path.join(DOCS_DIR, f"{rad['Fnr']}_{f_name}")
                    if os.path.exists(f_path):
                        with open(f_path, "rb") as d_f:
                            st.download_button(f"📥 {f_name}", d_f, file_name=f_name, key=f"{f_name}_{i}")
