import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- 1. CONFIG & DESIGN ---
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
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open("NSVG_CRM_Data").worksheet(sheet_name)
    except Exception as e:
        st.error(f"Sheet Error: {sheet_name} - {str(e)}")
        return None

def get_data(sheet_name):
    sh = connect_to_sheet(sheet_name)
    if sh:
        return pd.DataFrame(sh.get_all_records())
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
        if not users_df.empty:
            match = users_df[(users_df['username'].astype(str) == u_input) & (users_df['password'].astype(str) == p_input)]
            if not match.empty:
                st.session_state.update({'logged_in': True, 'user_role': match.iloc[0]['role'], 'user_id': u_input})
                add_data("Logs", [datetime.now().strftime("%d-%m-%Y %H:%M:%S"), u_input, "Login suksess", "Cloud"])
                st.rerun()
            else: st.error("Feil brukernavn eller passord!")
    st.stop()

# --- 4. DATA LOADING ---
df = get_data("MainDB")
role = st.session_state['user_role']
current_user = st.session_state['user_id']
display_df = df if role == "Admin" else df[df['Registrert_Av'] == current_user]

# --- 5. NAVIGATION ---
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
        st.dataframe(display_df.tail(10), use_container_width=True)

# --- 7. NY REGISTRERING (FULL FORM AS PER OLD CRM) ---
elif valg == "➕ Ny Registrering":
    st.header("➕ Opprett Ny Bankforespørsel")
    prod = st.selectbox("Bankprodukt", ["Boliglån", "Refinansiering", "Mellomfinansiering", "Investlån / Bedrift", "Byggelån", "Forbrukslån", "Billån"])
    is_bedrift = "Investlån" in prod
    has_medsoker = False if is_bedrift else (st.radio("Søknadstype", ["Alene søker", "Med-søker / Kausjonist"]) == "Med-søker / Kausjonist")

    with st.form("nsvg_bank_form"):
        c1, c2 = st.columns(2)
        with c1:
            navn = st.text_input("Fullt Navn (ihht ID)")
            fnr = st.text_input("Fødselsnummer (11 siffer)")
            epost = st.text_input("E-post")
            tlf = st.text_input("Telefonnummer")
            sivil = st.selectbox("Sivilstatus", ["Enslig", "Gift", "Samboer", "Skilt"])
        with c2:
            sektor = st.selectbox("Sektor", ["Privat", "Offentlig", "Statlig", "Kommunal"])
            jobb = st.selectbox("Arbeidsstatus", ["Fast ansatt", "Midlertidig", "AAP", "Uføre", "Selvstendig"])
            firma = st.text_input("Firma / Arbeidsgiver")
            lonn = st.number_input("Årslønn Brutto (kr)", min_value=0)

        st.divider()
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
                m_navn = st.text_input("Medsøker Fullt Navn")
                m_fnr = st.text_input("Medsøker Fnr")
            with m2: m_lonn = st.number_input("Medsøker Årslønn", min_value=0)

        notater_input = st.text_area("Interne notater / Kommentarer")
        st.file_uploader("Vedlegg (Cloud storage is active)")

        if st.form_submit_button("SEND SØKNAD"):
            new_row = [
                len(df)+1, datetime.now().strftime("%d-%m-%Y"), prod, navn, fnr, epost, tlf, sivil, 
                sektor, jobb, firma, lonn, barn, sfo, ek, gjeld, biler, belop_sokt, "", "", 
                m_navn, m_fnr, m_lonn, notater_input, "Cloud", current_user, "Mottatt"
            ]
            add_data("MainDB", new_row)
            st.success("✅ Søknad er registrert!")

# --- 8. ANSATTE KONTROLL ---
elif valg == "👥 Ansatte Kontroll" and role == "Admin":
    st.header("👥 Ansatte Management")
    users_list = get_data("Users")
    agents_list = get_data("Agents")
    
    workers = users_list[users_list['role'] == 'Worker']
    for _, worker in workers.iterrows():
        u = worker['username']
        agent_info = agents_list[agents_list['username'] == u]
        fname = agent_info['full_name'].iloc[0] if not agent_info.empty else u.capitalize()
        
        with st.expander(f"👤 {fname} (@{u})"):
            w_cases = df[df['Registrert_Av'] == u] if not df.empty else pd.DataFrame()
            st.metric("Antall Saker", len(w_cases))
            st.dataframe(w_cases.tail(5), use_container_width=True)
            if st.button(f"Slett {u}", key=u): st.warning("Kontakt database admin for sletting.")

# --- 9. MASTER PANEL (CREATE AGENTS) ---
elif valg == "🕵️ Master Kontrollpanel" and role == "Admin":
    st.header("🕵️ System Kontroll")
    t1, t2 = st.tabs(["👥 Agentstyring", "🛡️ Logger"])
    
    with t1:
        st.subheader("Opprett Ny Agent")
        with st.form("new_agent"):
            nu = st.text_input("Brukernavn").lower().strip()
            np = st.text_input("Passord")
            nf = st.text_input("Fullt Navn")
            nr = st.selectbox("Rank", ["Junior", "Senior", "Partner"])
            if st.form_submit_button("Aktiver"):
                add_data("Users", [nu, np, "Worker"])
                add_data("Agents", [nu, nf, nr, "N/A", "Active", "Signed"])
                st.success("Agent opprettet!")

    with t2:
        st.dataframe(get_data("Logs").sort_values("Tidspunkt", ascending=False))
