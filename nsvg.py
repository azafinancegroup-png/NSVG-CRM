import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- 1. SETTINGS & PAGE CONFIG ---
st.set_page_config(page_title="NSVG Digital Bank Portal", page_icon="🛡️", layout="wide")

# CSS for better look
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e0e0e0; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. GOOGLE SHEETS ENGINE ---
def connect_to_sheet(sheet_name):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open("NSVG_CRM_Data").worksheet(sheet_name)
    except:
        st.error(f"Kunne ikke koble til Google Sheet: {sheet_name}")
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

def delete_user_completely(username):
    # Dono sheets (Users aur Agents) se delete karne ke liye
    success = False
    for s_name in ["Users", "Agents"]:
        sh = connect_to_sheet(s_name)
        if sh:
            try:
                cell = sh.find(username.lower().strip())
                if cell:
                    sh.delete_rows(cell.row)
                    success = True
            except:
                continue
    return success

# --- 3. LOGIN SYSTEM ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user_role': None, 'user_id': None})

if not st.session_state['logged_in']:
    st.title("🛡️ NSVG - Sikker Digital Portal")
    with st.container():
        u_input = st.text_input("Brukernavn").lower().strip()
        p_input = st.text_input("Passord", type="password")
        if st.button("Logg inn"):
            users_df = get_data("Users")
            if not users_df.empty and 'username' in users_df.columns:
                match = users_df[(users_df['username'].astype(str).str.lower() == u_input) & (users_df['password'].astype(str) == p_input)]
                if not match.empty:
                    st.session_state.update({'logged_in': True, 'user_role': match.iloc[0]['role'], 'user_id': u_input})
                    st.rerun()
                else: st.error("Feil brukernavn eller passord!")
            else: st.error("Systemfeil: Users-tabellen ble ikke funnet.")
    st.stop()

# --- 4. GLOBAL DATA LOAD ---
df = get_data("MainDB")
role = st.session_state['user_role']
current_user = st.session_state['user_id']

# --- 5. SIDEBAR NAVIGATION ---
st.sidebar.title(f"👤 {current_user.capitalize()}")
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
    c2.metric("Total Volum (kr)", f"{volum:,.0f} kr")
    c3.metric("Estimert Provisjon (1%)", f"{volum * 0.01:,.0f} kr")
    
    st.divider()
    st.subheader("Siste Registreringer")
    if not user_data.empty:
        st.dataframe(user_data.tail(15), use_container_width=True)
    else:
        st.info("Ingen saker er registrert ennå.")

# --- 7. NY REGISTRERING (PRIVAT & BEDRIFT) ---
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
        st.subheader("🏠 Finansiell Informasjon")
        k1, k2 = st.columns(2)
        ek = k1.number_input("Egenkapital (kr)", 0)
        gjeld = k1.number_input("Annen Gjeld (kr)", 0)
        barn = k1.number_input("Barn under 18 år", 0)
        belop = k2.number_input("Søknadsbeløp (kr)", 0)
        biler = k2.number_input("Antall Biler", 0)
        sfo = k2.selectbox("SFO / Barnehage?", ["Nei", "Ja"])

        st.info("👥 Med-søker (Hvis aktuelt)")
        m_navn = st.text_input("Medsøker Navn")
        m_fnr = st.text_input("Medsøker Fødselsnummer")

        notater = st.text_area("Interne Notater / Kommentarer")
        st.file_uploader("Last opp Vedlegg (PDF/Bilder)")

        if st.form_submit_button("SEND SØKNAD"):
            # Prepare row for MainDB (27 items)
            new_row = [
                len(df)+1, datetime.now().strftime("%d-%m-%Y"), prod, navn, fnr, epost, tlf, sivil, 
                "Bedrift" if is_bedrift else "Privat", "Active", f_navn if is_bedrift else "", lonn, 
                barn, sfo, ek, gjeld, biler, belop, f_org if is_bedrift else "", 
                f_navn if is_bedrift else "", f_eier if is_bedrift else "", 
                m_navn, 0, notater, "Cloud", current_user, "Mottatt"
            ]
            add_data("MainDB", new_row)
            st.success("✅ Søknaden er registrert og lagret i skyen!")

# --- 8. MASTER KONTROLLPANEL (ADMIN) ---
elif valg == "🕵️ Master Kontrollpanel" and role == "Admin":
    st.header("🕵️ System Kontroll - Admin")
    st.subheader("➕ Opprett Ny Agent (Bruker-ID)")
    
    with st.form("agent_creation_form"):
        new_u = st.text_input("Brukernavn (Login ID)").lower().strip()
        new_p = st.text_input("Passord")
        new_fn = st.text_input("Fullt Navn på Agent")
        new_r = st.selectbox("Rank", ["Junior", "Senior", "Partner"])
        
        if st.form_submit_button("AKTIVER AGENT"):
            if new_u and new_p:
                add_data("Users", [new_u, new_p, "Worker"])
                add_data("Agents", [new_u, new_fn, new_r, "09-17", "Aktiv", "Signert"])
                st.success(f"✅ Bruker '{new_u}' er nå opprettet og aktiv!")
                st.rerun()
            else:
                st.error("Du må fylle ut både brukernavn og passord!")

# --- 9. ANSATTE KONTROLL (WITH DELETE) ---
elif valg == "👥 Ansatte Kontroll" and role == "Admin":
    st.header("👥 Ansatte Management & Oversikt")
    u_list = get_data("Users")
    
    if not u_list.empty:
        workers = u_list[u_list['role'] == 'Worker']
        for _, w in workers.iterrows():
            u_id = str(w['username'])
            with st.expander(f"👤 Agent: {u_id.upper()}"):
                col_info, col_del = st.columns([3, 1])
                
                with col_info:
                    w_cases = df[df['Registrert_Av'].astype(str).str.lower() == u_id.lower()] if not df.empty and 'Registrert_Av' in df.columns else pd.DataFrame()
                    w_volum = pd.to_numeric(w_cases['Beløp'], errors='coerce').sum() if not w_cases.empty else 0
                    st.write(f"**Antall Saker:** {len(w_cases)} | **Generert Volum:** {w_volum:,.0f} kr")
                    st.dataframe(w_cases.tail(5), use_container_width=True)
                
                with col_del:
                    st.write("---")
                    if st.button(f"🗑️ Slette {u_id}", key=f"del_{u_id}"):
                        if delete_user_completely(u_id):
                            st.success(f"Agent {u_id} er slettet!")
                            st.rerun()

# --- 10. KUNDE ARKIV ---
elif valg == "📂 Kunde Arkiv":
    st.header("📂 Kunde Arkiv")
    sok = st.text_input("Søk på Navn, Fnr eller Agent...")
    if not df.empty:
        filtered = df[df.astype(str).apply(lambda x: x.str.contains(sok, case=False)).any(axis=1)] if sok else df
        st.dataframe(filtered, use_container_width=True)
