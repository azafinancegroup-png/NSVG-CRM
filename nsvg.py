import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from streamlit_js_eval import get_geolocation

# --- 1. CONFIG & DESIGN ---
st.set_page_config(page_title="NSVG Digital Bank Portal", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e0e0e0; }
    .stButton > button {
        background-color: transparent !important; color: #0000FF !important; border: 2px solid #0000FF !important; border-radius: 8px;
    }
    .stButton > button:hover { background-color: #0000FF !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. GOOGLE SHEETS CORE ---
def connect_to_sheet(sheet_name):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open("NSVG_CRM_Data").worksheet(sheet_name)
    except: return None

def get_data(sheet_name):
    sh = connect_to_sheet(sheet_name)
    return pd.DataFrame(sh.get_all_records()) if sh else pd.DataFrame()

def add_data(sheet_name, row_list):
    sh = connect_to_sheet(sheet_name)
    if sh: sh.append_row(row_list)

def delete_user_row(username):
    sh = connect_to_sheet("Users")
    if sh:
        cells = sh.find(username)
        if cells: sh.delete_rows(cells.row)

# --- 3. LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user_role': None, 'user_id': None})

if not st.session_state['logged_in']:
    st.title("🛡️ NSVG - Sikker Digital Portal")
    u_input = st.text_input("Brukernavn").lower().strip()
    p_input = st.text_input("Passord", type="password")
    if st.button("Logg inn"):
        users_df = get_data("Users")
        match = users_df[(users_df['username'].astype(str) == u_input) & (users_df['password'].astype(str) == p_input)]
        if not match.empty:
            st.session_state.update({'logged_in': True, 'user_role': match.iloc[0]['role'], 'user_id': u_input})
            st.rerun()
        else: st.error("Feil!")
    st.stop()

# --- 4. NAVIGATION ---
df = get_data("MainDB")
role = st.session_state['user_role']
current_user = st.session_state['user_id']
display_df = df if role == "Admin" else df[df['Registrert_Av'] == current_user]

st.sidebar.title(f"👤 {current_user.capitalize()}")
menu = ["📊 Dashbord", "➕ Ny Registrering", "📂 Kunde Arkiv"]
if role == "Admin": menu.extend(["🕵️ Master Kontrollpanel", "👥 Ansatte Kontroll"])
valg = st.sidebar.selectbox("Hovedmeny", menu)

# --- 5. NY REGISTRERING (FULL DETAILED FORM) ---
if valg == "➕ Ny Registrering":
    st.header("➕ Ny Bankforespørsel")
    prod = st.selectbox("Produkt", ["Boliglån", "Refinansiering", "Mellomfinansiering", "Investlån", "Forbrukslån"])
    has_medsoker = st.radio("Søknadstype", ["Alene", "Med-søker"]) == "Med-søker"

    with st.form("full_form"):
        c1, c2 = st.columns(2)
        with c1:
            navn = st.text_input("Kunde Navn")
            fnr = st.text_input("Fødselsnummer")
            sivil = st.selectbox("Sivilstatus", ["Enslig", "Gift", "Samboer", "Skilt"])
            barn = st.number_input("Barn under 18", 0)
            sfo = st.selectbox("Har SFO/Barnehage?", ["Nei", "Ja"])
        with c2:
            jobb = st.selectbox("Jobb", ["Fast", "Midlertidig", "AAP", "Selvstendig"])
            lonn = st.number_input("Årslønn Brutto", 0)
            gjeld = st.number_input("Annen Gjeld", 0)
            biler = st.number_input("Antall Biler", 0)
            belop = st.number_input("Søknadsbeløp", 0)

        if has_medsoker:
            st.info("👥 Med-søker")
            m_navn = st.text_input("Medsøker Navn")
            m_lonn = st.number_input("Medsøker Lønn", 0)

        notater = st.text_area("Kommentarer")
        if st.form_submit_button("SEND SØKNAD"):
            row = [len(df)+1, datetime.now().strftime("%d-%m-%Y"), prod, navn, fnr, belop, "Mottatt", notater, "Cloud", current_user, "Vurderes", "Mottatt"]
            add_data("MainDB", row)
            st.success("✅ Registrert!")

# --- 6. ANSATTE KONTROLL (WITH DELETE OPTION) ---
elif valg == "👥 Ansatte Kontroll" and role == "Admin":
    st.header("👥 Ansatte Management")
    users = get_data("Users")
    workers = users[users['role'] == 'Worker']
    
    for _, w in workers.iterrows():
        uname = w['username']
        with st.expander(f"👤 {uname.capitalize()}"):
            w_cases = df[df['Registrert_Av'] == uname] if not df.empty else pd.DataFrame()
            st.metric("Saker", len(w_cases))
            if st.button(f"Slette Tilgang: {uname}", key=f"del_{uname}"):
                delete_user_row(uname)
                st.rerun()
            st.write("Siste Saker:")
            if not w_cases.empty: st.dataframe(w_cases.tail(5))
            else: st.write("Ingen saker")

# --- 7. MASTER KONTROLLPANEL (CREATE NEW AGENTS) ---
elif valg == "🕵️ Master Kontrollpanel" and role == "Admin":
    st.header("🕵️ System Kontroll")
    st.subheader("Opprett Ny Agent / Bruker")
    with st.form("new_user"):
        new_u = st.text_input("Nytt Brukernavn").lower().strip()
        new_p = st.text_input("Nytt Passord")
        new_r = st.selectbox("Rolle", ["Worker", "Admin"])
        if st.form_submit_button("AKTIVER BRUKER"):
            add_data("Users", [new_u, new_p, new_r])
            st.success(f"Bruker {new_u} er opprettet!")
            st.rerun()

# --- 8. OTHER SECTIONS ---
elif valg == "📊 Dashbord":
    st.header(f"Oversikt - {current_user.capitalize()}")
    if not display_df.empty:
        st.metric("Aktive Saker", len(display_df))
        st.dataframe(display_df.tail(10))

elif valg == "📂 Kunde Arkiv":
    st.header("📂 Kunde Arkiv")
    sok = st.text_input("Søk")
    if not display_df.empty:
        res = display_df[display_df.astype(str).apply(lambda x: x.str.contains(sok, case=False)).any(axis=1)]
        st.dataframe(res)
