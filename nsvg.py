import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- 1. CONFIG ---
st.set_page_config(page_title="NSVG Digital Bank Portal", page_icon="🛡️", layout="wide")

# --- 2. GOOGLE SHEETS CONNECTION ---
def connect_to_sheet(sheet_name):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open("NSVG_CRM_Data").worksheet(sheet_name)
    except Exception:
        return None

def get_data(sheet_name):
    sh = connect_to_sheet(sheet_name)
    if sh:
        return pd.DataFrame(sh.get_all_records())
    return pd.DataFrame()

def add_data(sheet_name, row_list):
    sh = connect_to_sheet(sheet_name)
    if sh: sh.append_row(row_list)

# --- 3. LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user_role': None, 'user_id': None})

if not st.session_state['logged_in']:
    st.title("🛡️ NSVG - Sikker Digital Portal")
    u_input = st.text_input("Brukernavn").lower().strip()
    p_input = st.text_input("Passord", type="password")
    if st.button("Logg inn"):
        users_df = get_data("Users")
        if not users_df.empty and 'username' in users_df.columns:
            match = users_df[(users_df['username'].astype(str).str.lower() == u_input) & (users_df['password'].astype(str) == p_input)]
            if not match.empty:
                st.session_state.update({'logged_in': True, 'user_role': match.iloc[0]['role'], 'user_id': u_input})
                st.rerun()
            else: st.error("Feil brukernavn!")
    st.stop()

# --- 4. DATA LOAD ---
df = get_data("MainDB")
role = st.session_state['user_role']
current_user = st.session_state['user_id']

# --- 5. NAVIGATION ---
st.sidebar.title(f"👤 {current_user.capitalize()}")
menu = ["📊 Dashbord", "➕ Ny Registrering", "📂 Kunde Arkiv"]
if role == "Admin": menu.extend(["👥 Ansatte Kontroll", "🕵️ Master Kontrollpanel"])
valg = st.sidebar.selectbox("Meny", menu)

if st.sidebar.button("🔴 Logg ut"):
    st.session_state.clear()
    st.rerun()

# --- 6. DASHBORD ---
if valg == "📊 Dashbord":
    st.header(f"Oversikt - {current_user.capitalize()}")
    # Filter data for current user
    user_data = df[df['Registrert_Av'].astype(str).str.lower() == current_user.lower()] if not df.empty and 'Registrert_Av' in df.columns else df
    
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Saker", len(user_data))
    with c2:
        volum = pd.to_numeric(user_data['Beløp'], errors='coerce').sum() if not user_data.empty else 0
        st.metric("Total Volum (kr)", f"{volum:,.0f}")
    with c3:
        st.metric("Estimert Provisjon", f"{volum * 0.01:,.0f}")
    
    st.dataframe(user_data.tail(10), use_container_width=True)

# --- 7. NY REGISTRERING (FULL FORM + UPLOAD) ---
elif valg == "➕ Ny Registrering":
    st.header("➕ Ny Bankforespørsel")
    prod = st.selectbox("Produkt", ["Boliglån", "Refinansiering", "Mellomfinansiering", "Investlån", "Byggelån", "Forbrukslån", "Billån"])
    
    with st.form("full_form"):
        c1, c2 = st.columns(2)
        with c1:
            navn = st.text_input("Fullt Navn")
            fnr = st.text_input("Fødselsnummer")
            epost = st.text_input("E-post")
            tlf = st.text_input("Telefon")
            sivil = st.selectbox("Sivilstatus", ["Enslig", "Gift", "Samboer", "Skilt"])
        with c2:
            jobb = st.selectbox("Arbeid", ["Fast", "Midlertidig", "AAP", "Uføre", "Selvstendig"])
            firma = st.text_input("Arbeidsgiver")
            lonn = st.number_input("Årslønn", 0)
            barn = st.number_input("Barn under 18", 0)
            sfo = st.selectbox("SFO?", ["Nei", "Ja"])

        st.divider()
        k1, k2 = st.columns(2)
        with k1:
            ek = st.number_input("EK", 0)
            gjeld = st.number_input("Gjeld", 0)
        with k2:
            biler = st.number_input("Biler", 0)
            belop = st.number_input("Søknadsbeløp", 0)

        st.info("👥 Med-søker (Hvis aktuelt)")
        m_navn = st.text_input("Medsøker Navn")
        m_fnr = st.text_input("Medsøker Fnr")
        
        notater = st.text_area("Notater")
        st.file_uploader("Last opp dokumenter (PDF/Bilder)")

        if st.form_submit_button("SEND SØKNAD"):
            # Ensure 27 columns for MainDB
            new_row = [len(df)+1, datetime.now().strftime("%d-%m-%Y"), prod, navn, fnr, epost, tlf, sivil, "Privat", jobb, firma, lonn, barn, sfo, ek, gjeld, biler, belop, "", "", m_navn, m_fnr, 0, notater, "Cloud_Upload", current_user, "Mottatt"]
            add_data("MainDB", new_row)
            st.success("✅ Registrert!")

# --- 8. ANSATTE KONTROLL (FIXED FOR KEYERROR) ---
elif valg == "👥 Ansatte Kontroll" and role == "Admin":
    st.header("👥 Ansatte Management")
    users_list = get_data("Users")
    agents_list = get_data("Agents")
    
    if not users_list.empty:
        workers = users_list[users_list['role'] == 'Worker']
        for _, worker in workers.iterrows():
            u = str(worker['username'])
            
            # SAFE ACCESS TO AGENTS LIST
            fname = u.capitalize()
            if not agents_list.empty and 'username' in agents_list.columns:
                agent_match = agents_list[agents_list['username'].astype(str) == u]
                if not agent_match.empty: fname = agent_match.iloc[0]['full_name']
            
            with st.expander(f"👤 {fname} (@{u})"):
                # SAFE FILTERING FOR MAINDB
                if not df.empty and 'Registrert_Av' in df.columns:
                    w_cases = df[df['Registrert_Av'].astype(str).str.lower() == u.lower()]
                    st.metric("Antall Saker", len(w_cases))
                    st.dataframe(w_cases, use_container_width=True)
                
                if st.button(f"Slett {u}", key=f"del_{u}"):
                    st.error("Sletting må gjøres manuelt i Google Sheets for sikkerhet.")

# --- 9. KUNDE ARKIV ---
elif valg == "📂 Kunde Arkiv":
    st.header("📂 Arkiv")
    sok = st.text_input("Søk her...")
    if not df.empty:
        filtered = df[df.astype(str).apply(lambda x: x.str.contains(sok, case=False)).any(axis=1)] if sok else df
        st.dataframe(filtered, use_container_width=True)
