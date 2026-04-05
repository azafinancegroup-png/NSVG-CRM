import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from streamlit_js_eval import get_geolocation

# --- 1. KONFIGURASJON & DESIGN ---
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

# --- 2. GOOGLE SHEETS CORE ENGINE ---
def connect_to_sheet(sheet_name):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open("NSVG_CRM_Data").worksheet(sheet_name)
    except Exception as e:
        st.error(f"Sheet Error: {e}")
        return None

def get_data(sheet_name):
    sh = connect_to_sheet(sheet_name)
    if sh:
        data = sh.get_all_records()
        return pd.DataFrame(data)
    return pd.DataFrame()

def add_data(sheet_name, row_list):
    sh = connect_to_sheet(sheet_name)
    if sh:
        sh.append_row(row_list)

# --- 3. LOGIN & SECURITY ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user_role': None, 'user_id': None})

if not st.session_state['logged_in']:
    st.title("🛡️ NSVG - Sikker Digital Portal")
    loc = get_geolocation()
    u_input = st.text_input("Brukernavn").lower().strip()
    p_input = st.text_input("Passord", type="password")
    
    if st.button("Logg inn"):
        users_df = get_data("Users")
        match = users_df[(users_df['username'] == u_input) & (users_df['password'].astype(str) == p_input)]
        if not match.empty:
            st.session_state.update({'logged_in': True, 'user_role': match.iloc[0]['role'], 'user_id': u_input})
            
            # Log record
            try:
                lat = loc['coords']['latitude'] if loc else "N/A"
                lon = loc['coords']['longitude'] if loc else "N/A"
            except: lat, lon = "N/A", "N/A"
            maps_url = f"https://www.google.com/maps?q={lat},{lon}"
            add_data("Logs", [datetime.now().strftime("%d-%m-%Y %H:%M:%S"), u_input, "Innlogging suksess", maps_url])
            st.rerun()
        else:
            st.error("Feil brukernavn eller passord!")
    st.stop()

# --- 4. NAVIGATION & DATA ---
df = get_data("MainDB")
role = st.session_state['user_role']
current_user = st.session_state['user_id']
display_df = df if role == "Admin" else df[df['Registrert_Av'] == current_user]

st.sidebar.title(f"👤 {current_user.capitalize()}")
menu = ["📊 Dashbord", "➕ Ny Registrering", "📂 Kunde Arkiv"]
if role == "Admin": 
    menu.append("🕵️ Master Kontrollpanel")
    menu.append("👥 Ansatte Kontroll")
valg = st.sidebar.selectbox("Hovedmeny", menu)

if st.sidebar.button("🔴 Logg ut"):
    st.session_state.clear()
    st.rerun()

# --- SECTION: DASHBORD ---
if valg == "📊 Dashbord":
    st.header(f"Oversikt - {current_user.capitalize()}")
    if not display_df.empty:
        c1, c2 = st.columns(2)
        with c1: st.metric("Aktive Saker", len(display_df))
        with c2:
            volum = pd.to_numeric(display_df['Beløp'], errors='coerce').sum()
            st.metric("Totalt Volum (kr)", f"{volum:,} kr")
        st.divider()
        st.subheader("Siste aktiviteter")
        st.dataframe(display_df.tail(10), use_container_width=True)
    else:
        st.info("Ingen data tilgjengelig.")

# --- SECTION: NY REGISTRERING (YOUR EXACT FORM) ---
elif valg == "➕ Ny Registrering":
    st.header("➕ Opprett Ny Bankforespørsel")
    prod = st.selectbox("Bankprodukt", ["Boliglån", "Refinansiering", "Mellomfinansiering", "Investlån / Bedrift", "Byggelån", "Forbrukslån", "Billån"])
    
    is_bedrift = "Investlån" in prod
    has_medsoker = False if is_bedrift else (st.radio("Søknadstype", ["Alene søker", "Med-søker / Kausjonist"]) == "Med-søker / Kausjonist")

    with st.form("nsvg_bank_form"):
        st.subheader("👤 Kunde Informasjon")
        c1, c2 = st.columns(2)
        with c1:
            navn = st.text_input("Fullt Navn (ihht ID)")
            fnr = st.text_input("Fødselsnummer (11 siffer)")
            epost = st.text_input("E-post")
            tlf = st.text_input("Telefonnummer")
        with c2:
            sivil = st.selectbox("Sivilstatus", ["Enslig", "Gift", "Samboer", "Skilt"])
            sektor = st.selectbox("Sektor", ["Privat", "Offentlig", "Statlig", "Kommunal"])
            jobb = st.selectbox("Arbeidsstatus", ["Fast ansatt", "Midlertidig", "AAP", "Uføre", "Selvstendig"])
            firma = st.text_input("Firma / Arbeidsgiver")
            lonn = st.number_input("Årslønn Brutto (kr)", min_value=0)

        st.divider()
        st.subheader("🏠 Finansiell Detaljer")
        k1, k2 = st.columns(2)
        with k1:
            barn = st.number_input("Barn under 18 år", min_value=0)
            sfo = st.selectbox("SFO/Barnehage?", ["Nei", "Ja"])
            ek = st.number_input("Egenkapital (kr)", min_value=0)
        with k2:
            gjeld = st.number_input("Annen gjeld (kr)", min_value=0)
            biler = st.number_input("Antall biler", min_value=0)
            belop_sokt = st.number_input("Søknadsbeløp (kr)", min_value=0)

        if is_bedrift:
            st.info("🏢 Bedrifts Detaljer")
            orgnr = st.text_input("Organisasjonsnummer")
            plan = st.text_area("Formål med lånet")

        if has_medsoker:
            st.info("👥 Med-søker Detaljer")
            m1, m2 = st.columns(2)
            with m1:
                m_navn = st.text_input("Medsøker Fullt Navn")
                m_fnr = st.text_input("Medsøker Fnr")
            with m2:
                m_lonn = st.number_input("Medsøker Årslønn", min_value=0)

        st.divider()
        notater_input = st.text_area("Interne notater / Kommentarer")

        if st.form_submit_button("SEND SØKNAD"):
            # Prepare row for Google Sheet (12 columns to match your MainDB)
            # We bundle extra info into 'Notater' to keep sheet clean
            extra_info = f"Jobb: {jobb} | Sivil: {sivil} | {notater_input}"
            
            row = [
                len(df) + 1, 
                datetime.now().strftime("%d-%m-%Y"),
                prod, navn, fnr, belop_sokt, "Mottatt", 
                extra_info, "Cloud", current_user, "Vurderes", "Mottatt"
            ]
            add_data("MainDB", row)
            st.success("✅ Søknad er registrert i Google Sheets!")

# --- SECTION: KUNDE ARKIV ---
elif valg == "📂 Kunde Arkiv":
    st.header("📂 Kunde Arkiv")
    sok = st.text_input("Søk na Navn eller Fødselsnummer")
    if not display_df.empty:
        res_df = display_df[display_df.astype(str).apply(lambda x: x.str.contains(sok, case=False)).any(axis=1)] if sok else display_df
        st.dataframe(res_df, use_container_width=True)

# --- SECTION: ANSATTE KONTROLL ---
elif valg == "👥 Ansatte Kontroll" and role == "Admin":
    st.header("👥 Ansatte & Worker Management")
    users_list = get_data("Users")
    agents_list = get_data("Agents") # This is your AGENT_RECORDS_FILE
    logs_data = get_data("Logs")
    
    workers = users_list[users_list['role'] == 'Worker']
    
    for idx, worker in workers.iterrows():
        uname = worker['username']
        agent_row = agents_list[agents_list['username'] == uname]
        fname = agent_row['full_name'].values[0] if not agent_row.empty else uname.capitalize()
        
        with st.expander(f"👤 {fname} (@{uname})"):
            c1, c2 = st.columns(2)
            with c1:
                w_cases = df[df['Registrert_Av'] == uname]
                st.metric("Saker", len(w_cases))
            with c2:
                last_log = logs_data[logs_data['Bruker'] == uname].tail(1)
                st.write("**Siste aktivitet:**")
                st.caption(last_log['Tidspunkt'].values[0] if not last_log.empty else "Ingen logg")
            
            st.dataframe(w_cases[['Dato', 'Hovedsøker', 'Produkt', 'Beløp', 'Status']].tail(5), use_container_width=True)

# --- SECTION: MASTER KONTROLLPANEL ---
elif valg == "🕵️ Master Kontrollpanel" and role == "Admin":
    st.header("🕵️ System Kontroll")
    tab1, tab2 = st.tabs(["👥 Agentstyring", "🛡️ Logger"])

    with tab1:
        st.subheader("Registrerte Agenter")
        st.dataframe(get_data("Agents"), use_container_width=True)
        
    with tab2:
        st.dataframe(get_data("Logs").sort_values("Tidspunkt", ascending=False), use_container_width=True)
