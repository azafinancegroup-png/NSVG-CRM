import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- 1. SETTINGS ---
st.set_page_config(page_title="NSVG Digital Bank Portal", page_icon="🛡️", layout="wide")

# --- 2. GOOGLE SHEETS ENGINE ---
def connect_to_sheet(sheet_name):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open("NSVG_CRM_Data").worksheet(sheet_name)
    except:
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
        if not users_df.empty and 'username' in users_df.columns:
            match = users_df[(users_df['username'].astype(str).str.lower() == u_input) & (users_df['password'].astype(str) == p_input)]
            if not match.empty:
                st.session_state.update({'logged_in': True, 'user_role': match.iloc[0]['role'], 'user_id': u_input})
                st.rerun()
            else: st.error("Feil brukernavn!")
    st.stop()

# --- 4. GLOBAL DATA ---
df = get_data("MainDB")
role = st.session_state['user_role']
current_user = st.session_state['user_id']

# --- 5. SIDEBAR NAVIGATION ---
st.sidebar.title(f"👤 {current_user.capitalize()}")
# Sidebar Menu Options
options = ["📊 Dashbord", "➕ Ny Registrering", "📂 Kunde Arkiv"]
if role == "Admin":
    options.append("👥 Ansatte Kontroll")
    options.append("🕵️ Master Kontrollpanel")

valg = st.sidebar.selectbox("Hovedmeny", options)

if st.sidebar.button("🔴 Logg ut"):
    st.session_state.clear()
    st.rerun()

# --- 6. DASHBORD ---
if valg == "📊 Dashbord":
    st.header(f"Oversikt - {current_user.capitalize()}")
    user_data = df[df['Registrert_Av'].astype(str).str.lower() == current_user.lower()] if not df.empty and 'Registrert_Av' in df.columns else df
    
    c1, c2, c3 = st.columns(3)
    volum = pd.to_numeric(user_data['Beløp'], errors='coerce').sum() if not user_data.empty else 0
    c1.metric("Antall Saker", len(user_data))
    c2.metric("Total Volum (kr)", f"{volum:,.0f}")
    c3.metric("Estimert Provisjon (1%)", f"{volum * 0.01:,.0f}")
    
    st.divider()
    st.subheader("Siste aktiviteter")
    st.dataframe(user_data.tail(10), use_container_width=True)

# --- 7. NY REGISTRERING (BEDRIFTLÅN FORM) ---
elif valg == "➕ Ny Registrering":
    st.header("➕ Ny Bankforespørsel")
    prod = st.selectbox("Velg Produkt", ["Boliglån", "Refinansiering", "Investlån / Bedriftlån", "Byggelån", "Forbrukslån", "Billån"])
    
    is_bedrift = "Bedriftlån" in prod or "Investlån" in prod

    with st.form("form_reg"):
        if is_bedrift:
            st.subheader("🏢 Bedrift / Firma Detaljer")
            bc1, bc2 = st.columns(2)
            f_navn = bc1.text_input("Firma Navn")
            f_org = bc1.text_input("Organisasjonsnummer (9 siffer)")
            f_eier = bc2.text_area("Navn & Personnummer på alle eiere")
            f_aksjer = bc2.text_input("Aksjefordeling (%)")
            st.divider()

        st.subheader("👤 Kontaktperson / Hovedsøker")
        c1, c2 = st.columns(2)
        navn = c1.text_input("Fullt Navn")
        fnr = c1.text_input("Fødselsnummer (11 siffer)")
        epost = c1.text_input("E-post")
        tlf = c2.text_input("Telefon")
        sivil = c2.selectbox("Sivilstatus", ["Enslig", "Gift", "Samboer", "Skilt"])
        lonn = c2.number_input("Årslønn Brutto (kr)", 0)

        st.divider()
        st.subheader("🏠 Finansiell Info")
        k1, k2 = st.columns(2)
        ek = k1.number_input("Egenkapital", 0)
        gjeld = k1.number_input("Annen Gjeld", 0)
        barn = k1.number_input("Barn under 18", 0)
        belop = k2.number_input("Søknadsbeløp", 0)
        biler = k2.number_input("Antall Biler", 0)
        sfo = k2.selectbox("SFO/Barnehage?", ["Nei", "Ja"])

        notater = st.text_area("Interne Notater / Kommentarer")
        st.file_uploader("Last opp Vedlegg (PDF/Bilder)")

        if st.form_submit_button("SEND SØKNAD"):
            # Row mapping (27 columns)
            new_row = [len(df)+1, datetime.now().strftime("%d-%m-%Y"), prod, navn, fnr, epost, tlf, sivil, "Bedrift" if is_bedrift else "Privat", "Active", f_navn if is_bedrift else "", lonn, barn, sfo, ek, gjeld, biler, belop, f_org if is_bedrift else "", f_navn if is_bedrift else "", f_eier if is_bedrift else "", f_aksjer if is_bedrift else 0, 0, notater, "Cloud", current_user, "Mottatt"]
            add_data("MainDB", new_row)
            st.success("✅ Søknad registrert!")

# --- 8. MASTER KONTROLLPANEL (AGENT CREATOR) ---
elif valg == "🕵️ Master Kontrollpanel" and role == "Admin":
    st.header("🕵️ System Kontroll - Admin")
    st.subheader("➕ Opprett Ny Bruker-ID")
    
    with st.form("agent_creation_form"):
        new_u = st.text_input("Brukernavn (Login ID)").lower().strip()
        new_p = st.text_input("Passord")
        new_fn = st.text_input("Fullt Navn på Agent")
        new_r = st.selectbox("Rank", ["Junior", "Senior", "Partner"])
        
        if st.form_submit_button("AKTIVER AGENT"):
            if new_u and new_p:
                add_data("Users", [new_u, new_p, "Worker"])
                add_data("Agents", [new_u, new_fn, new_r, "09-17", "Active", "Signed"])
                st.success(f"✅ Bruker '{new_u}' er nå opprettet!")
                st.rerun()
            else:
                st.error("Fyll ut brukernavn og passord!")

# --- 9. ANSATTE KONTROLL ---
elif valg == "👥 Ansatte Kontroll" and role == "Admin":
    st.header("👥 Ansatte Management")
    u_list = get_data("Users")
    if not u_list.empty:
        workers = u_list[u_list['role'] == 'Worker']
        for _, w in workers.iterrows():
            u_id = str(w['username'])
            with st.expander(f"Agent Profil: {u_id}"):
                w_cases = df[df['Registrert_Av'].astype(str).str.lower() == u_id.lower()] if not df.empty else pd.DataFrame()
                st.metric("Antall Saker", len(w_cases))
                st.dataframe(w_cases, use_container_width=True)
