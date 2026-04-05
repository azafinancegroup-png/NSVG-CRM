import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- 1. CONFIG & STYLING ---
st.set_page_config(page_title="NSVG Digital Bank Portal", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e0e0e0; }
    [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] label { color: #002366 !important; font-weight: bold !important; }
    .stButton > button { background-color: transparent !important; color: #0000FF !important; border: 2px solid #0000FF !important; border-radius: 8px; }
    .stButton > button:hover { background-color: #0000FF !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. GOOGLE SHEETS CONNECTION ---
def connect_to_sheet(sheet_name):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        # Streamlit Cloud ke 'Secrets' se credentials uthayega
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open("NSVG_CRM_Data").worksheet(sheet_name)
    except Exception as e:
        return None

def get_data(sheet_name):
    sh = connect_to_sheet(sheet_name)
    if sh:
        data = sh.get_all_records()
        return pd.DataFrame(data)
    return pd.DataFrame()

def add_data(sheet_name, row_list):
    sh = connect_to_sheet(sheet_name)
    if sh: sh.append_row(row_list)

# --- 3. LOGIN SYSTEM ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user_role': None, 'user_id': None})

if not st.session_state['logged_in']:
    st.title("🛡️ NSVG - Sikker Digital Portal")
    u_input = st.text_input("Brukernavn").lower().strip()
    p_input = st.text_input("Passord", type="password")
    
    if st.button("Logg inn"):
        users_df = get_data("Users")
        if not users_df.empty and 'username' in users_df.columns:
            # Match user credentials
            match = users_df[(users_df['username'].astype(str) == u_input) & (users_df['password'].astype(str) == p_input)]
            if not match.empty:
                st.session_state.update({
                    'logged_in': True, 
                    'user_role': match.iloc[0]['role'], 
                    'user_id': u_input
                })
                # Log current activity
                add_data("Logs", [datetime.now().strftime("%d-%m-%Y %H:%M:%S"), u_input, "Login suksess", "Cloud"])
                st.rerun()
            else:
                st.error("Feil brukernavn eller passord!")
        else:
            st.error("Sheet 'Users' mein 'username' column nahi mila!")
    st.stop()

# --- 4. DATA LOADING & FILTERING ---
df = get_data("MainDB")
role = st.session_state['user_role']
current_user = st.session_state['user_id']

# Safety Filter for Agents/Workers
if not df.empty and 'Registrert_Av' in df.columns:
    display_df = df if role == "Admin" else df[df['Registrert_Av'].astype(str) == current_user]
else:
    display_df = df # Fallback: agar column missing ho to sara data dikhaye taake crash na ho

# --- 5. SIDEBAR NAVIGATION ---
st.sidebar.title(f"👤 {current_user.capitalize()}")
menu = ["📊 Dashbord", "➕ Ny Registrering", "📂 Kunde Arkiv"]
if role == "Admin": 
    menu.extend(["🕵️ Master Kontrollpanel", "👥 Ansatte Kontroll"])
valg = st.sidebar.selectbox("Hovedmeny", menu)

if st.sidebar.button("🔴 Logg ut"):
    st.session_state.clear()
    st.rerun()

# --- 6. DASHBORD ---
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
        st.info("Ingen saker funnet i databasen.")

# --- 7. NY REGISTRERING (FULL FORM) ---
elif valg == "➕ Ny Registrering":
    st.header("➕ Opprett Ny Bankforespørsel")
    prod = st.selectbox("Bankprodukt", ["Boliglån", "Refinansiering", "Mellomfinansiering", "Investlån / Bedrift", "Byggelån", "Forbrukslån", "Billån"])
    
    is_bedrift = "Investlån" in prod
    has_medsoker = False if is_bedrift else (st.radio("Søknadstype", ["Alene søker", "Med-søker / Kausjonist"]) == "Med-søker / Kausjonist")

    with st.form("nsvg_bank_form"):
        st.subheader("👤 Kunde Informasjon")
        c1, c2 = st.columns(2)
        with c1:
            navn = st.text_input("Fullt Navn")
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

        m_navn, m_fnr, m_lonn = "", "", 0
        if has_medsoker:
            st.info("👥 Med-søker Detaljer")
            m1, m2 = st.columns(2)
            with m1:
                m_navn = st.text_input("Medsøker Navn")
                m_fnr = st.text_input("Medsøker Fnr")
            with m2: m_lonn = st.number_input("Medsøker Årslønn", min_value=0)

        notater_input = st.text_area("Interne notater")

        if st.form_submit_button("SEND SØKNAD"):
            # Row mapping for MainDB (ID, Dato, Produkt, ..., Registrert_Av, Status)
            new_row = [
                len(df)+1, datetime.now().strftime("%d-%m-%Y"), prod, navn, fnr, epost, tlf, sivil,
                sektor, jobb, firma, lonn, barn, sfo, ek, gjeld, biler, belop_sokt, "", "",
                m_navn, m_fnr, m_lonn, notater_input, "Cloud", current_user, "Mottatt"
            ]
            add_data("MainDB", new_row)
            st.success("✅ Søknad er registrert!")

# --- 8. KUNDE ARKIV ---
elif valg == "📂 Kunde Arkiv":
    st.header("📂 Kunde Arkiv")
    sok = st.text_input("Søk på Navn eller Fødselsnummer")
    if not display_df.empty:
        res_df = display_df[display_df.astype(str).apply(lambda x: x.str.contains(sok, case=False)).any(axis=1)] if sok else display_df
        st.dataframe(res_df, use_container_width=True)

# --- 9. ANSATTE KONTROLL (ADMIN ONLY - FIXED) ---
elif valg == "👥 Ansatte Kontroll" and role == "Admin":
    st.header("👥 Ansatte Management")
    users_list = get_data("Users")
    agents_list = get_data("Agents")
    
    if not users_list.empty and 'role' in users_list.columns:
        workers = users_list[users_list['role'] == 'Worker']
        for _, worker in workers.iterrows():
            u = worker['username']
            # Safety check for Agents data
            fname = u.capitalize()
            if not agents_list.empty and 'username' in agents_list.columns:
                agent_info = agents_list[agents_list['username'].astype(str) == u]
                if not agent_info.empty and 'full_name' in agents_list.columns:
                    fname = agent_info.iloc[0]['full_name']

            with st.expander(f"👤 {fname} (@{u})"):
                if not df.empty and 'Registrert_Av' in df.columns:
                    w_cases = df[df['Registrert_Av'].astype(str) == u]
                    st.metric("Totalt Saker", len(w_cases))
                    st.dataframe(w_cases, use_container_width=True)
                else:
                    st.warning("Ingen saker funnet for denne agenten.")

# --- 10. MASTER KONTROLLPANEL (ADMIN ONLY) ---
elif valg == "🕵️ Master Kontrollpanel" and role == "Admin":
    st.header("🕵️ System Kontroll")
    tab1, tab2 = st.tabs(["👥 Agentstyring", "🛡️ Logger"])
    
    with tab1:
        st.subheader("Opprett Ny Agent (Worker)")
        with st.form("new_agent_form"):
            nu = st.text_input("Loginn-ID (Brukernavn)").lower().strip()
            np = st.text_input("Passord")
            nf = st.text_input("Fullt Navn")
            nr = st.selectbox("Rank", ["Junior Agent", "Senior Agent", "Partner"])
            if st.form_submit_button("AKTIVER AGENT"):
                add_data("Users", [nu, np, "Worker"])
                add_data("Agents", [nu, nf, nr, "N/A", "Active", "Signed"])
                st.success(f"Agent {nf} er opprettet!")
                st.rerun()

    with tab2:
        logs = get_data("Logs")
        if not logs.empty:
            st.dataframe(logs.sort_values(by=logs.columns[0], ascending=False), use_container_width=True)
