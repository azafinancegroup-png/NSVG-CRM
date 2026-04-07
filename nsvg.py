import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- 1. SETTINGS & PAGE CONFIG ---
st.set_page_config(page_title="NSVG Digital Bank Portal", page_icon="🛡️", layout="wide")

# CSS Styling
st.markdown("""
    <style>
    .stApp { transition: background-color 0.3s ease; }
    div[data-testid="stMetric"] {
        background-color: rgba(151, 166, 195, 0.15);
        padding: 15px; border-radius: 12px; border: 1px solid rgba(128, 128, 128, 0.2);
    }
    .streamlit-expanderHeader { font-weight: bold; color: var(--text-color); }
    label { font-weight: 500 !important; color: var(--text-color) !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. GOOGLE SHEETS ENGINE ---
def connect_to_sheet(sheet_name):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        # YAHAN FILE NAME CHECK KAREIN: "NSVG_CRM_Data" ya "Kredittnova_Database"
        return client.open("NSVG_CRM_Data").worksheet(sheet_name)
    except Exception as e:
        return None

def get_data(sheet_name):
    sh = connect_to_sheet(sheet_name)
    if sh:
        data = sh.get_all_records()
        df = pd.DataFrame(data)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    return pd.DataFrame()

def add_data(sheet_name, row_list):
    sh = connect_to_sheet(sheet_name)
    if sh: sh.append_row(row_list)

@st.cache_data
def get_country_list():
    base = ["Norge", "Sverige", "Danmark", "UK", "USA", "Pakistan", "India"]
    others = sorted(["Afghanistan", "Albania", "Algerie", "Andorra", "Angola", "Argentina", "Australia", "Bangladesh", "Belgia", "Brasil", "Canada", "Chile", "China", "Egypt", "Finland", "Frankrike", "Hellas", "Island", "Iran", "Irak", "Irland", "Italia", "Japan", "Jordan", "Kuwait", "Latvia", "Libanon", "Malaysia", "Mexico", "Marokko", "Nederland", "New Zealand", "Nigeria", "Oman", "Filippinene", "Polen", "Portugal", "Qatar", "Romania", "Russland", "Saudi Arabia", "Singapore", "Spania", "Sri Lanka", "Sudan", "Sveits", "Syria", "Thailand", "Tunisia", "Tyrkia", "UAE", "Ukraina", "Vietnam"])
    return base + others

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
            match = users_df[(users_df['username'].astype(str).str.lower() == u_input) & (users_df['password'].astype(str) == p_input)]
            if not match.empty:
                st.session_state.update({'logged_in': True, 'user_role': match.iloc[0]['role'], 'user_id': u_input})
                st.rerun()
            else: st.error("Feil brukernavn eller passord!")
    st.stop()

# --- 4. GLOBAL DATA ---
df = get_data("MainDB")
role = st.session_state['user_role']
current_user = st.session_state['user_id']
countries = get_country_list()

# --- 5. SIDEBAR ---
st.sidebar.title(f"👤 {current_user.capitalize()}")
options = ["📊 Dashbord", "➕ Ny Registrering", "📂 Kunde Arkiv"]
if role in ["Admin", "Director"]:
    options.extend(["👥 Ansatte Kontroll", "🕵️ Master Kontrollpanel"])

valg = st.sidebar.selectbox("Hovedmeny", options)

if st.sidebar.button("🔴 Logg ut"):
    st.session_state.clear()
    st.rerun()

# --- 6. DASHBORD ---
if valg == "📊 Dashbord":
    st.header(f"Oversikt")
    c1, c2, c3 = st.columns(3)
    if not df.empty:
        # Filter data based on role
        view_data = df if role in ["Admin", "Director"] else df[df.get('Registrert_Av', '').astype(str).str.lower() == current_user.lower()]
        
        b_col = next((c for c in view_data.columns if c.lower() in ['beløp', 'sum']), None)
        total_v = pd.to_numeric(view_data[b_col], errors='coerce').sum() if b_col else 0
        
        c1.metric("Antall Saker", len(view_data))
        c2.metric("Total Volum (kr)", f"{total_v:,.0f} kr")
        c3.metric("Provisjon (1%)", f"{total_v * 0.01:,.0f} kr")
        st.divider()
        st.dataframe(view_data.tail(15), use_container_width=True)
    else:
        st.info("Ingen data mojud hai.")

# --- 7. NY REGISTRERING ---
elif valg == "➕ Ny Registrering":
    st.header("➕ Ny Bankforespørsel")
    prod = st.selectbox("Velg Produkt", ["Boliglån", "Refinansiering", "Mellomfinansiering", "Investlån / Bedriftlån", "Byggelån", "Forbrukslån", "Billån"])
    is_bedrift = "Bedriftlån" in prod or "Investlån" in prod
    has_med = st.checkbox("✅ JA, legg til Medsøker")

    with st.form("reg_form", clear_on_submit=True):
        if is_bedrift:
            st.subheader("🏢 Bedrift Detaljer")
            bc1, bc2 = st.columns(2)
            f_navn = bc1.text_input("Firma Navn")
            f_org = bc1.text_input("Organisasjonsnummer")
            f_eier = bc2.text_area("Eiere & Fnr")
            f_aksjer = bc2.text_input("Aksjer (%)")
        else:
            f_navn, f_org, f_eier, f_aksjer = "", "", "", ""

        st.subheader("👤 Hovedsøker")
        c1, c2 = st.columns(2)
        navn = c1.text_input("Fullt Navn")
        fnr = c1.text_input("Fødselsnummer")
        epost = c1.text_input("E-post")
        tlf = c2.text_input("Telefon")
        sivil = c2.selectbox("Sivilstatus", ["Enslig", "Gift", "Samboer", "Skilt"])
        pass_land = c1.selectbox("Statsborgerskap", countries)
        botid = c2.text_input("Botid i Norge")

        st.subheader("🏠 Økonomi")
        f1, f2 = st.columns(2)
        belop = f1.number_input("Ønsket Lånebeløp", 0)
        ek = f1.number_input("Egenkapital", 0)
        
        g_bolig = st.number_input("Eksisterende Gjeld (Totalt)", 0)

        m_navn, m_fnr, m_epost, m_tlf, m_lonn, m_arb, m_pass = "", "", "", "", 0, "", "Norge"
        if has_med:
            st.divider()
            st.subheader("👥 Medsøker")
            mc1, mc2 = st.columns(2)
            m_navn = mc1.text_input("Navn (Medsøker)")
            m_fnr = mc1.text_input("Fnr (Medsøker)")
            m_lonn = mc1.number_input("Lønn (Medsøker)", 0)
            m_pass = mc2.selectbox("Statsborgerskap (Medsøker)", countries, key="med_p")

        notater = st.text_area("Notater")

        if st.form_submit_button("🚀 SEND SØKNAD"):
            new_row = [
                len(df)+1, datetime.now().strftime("%d-%m-%Y"), prod, navn, fnr, epost, tlf, sivil,
                "Bedrift" if is_bedrift else "Privat", "Active", f_navn, 0, 0, "Nei", ek,
                g_bolig, 0, belop, f_org, f_eier, f_aksjer,
                m_navn, m_fnr, m_epost, m_tlf, m_lonn, "", notater,
                f"P1: {pass_land} | P2: {m_pass}", current_user, "Mottatt"
            ]
            add_data("MainDB", new_row)
            st.success("Søknad Registrert!")

# --- 8. KUNDE ARKIV ---
elif valg == "📂 Kunde Arkiv":
    st.header("📂 Kunde Arkiv")
    view_df = df if role in ["Admin", "Director"] else df[df.get('Registrert_Av', '').astype(str).str.lower() == current_user.lower()]
    
    if not view_df.empty:
        sok = st.text_input("🔍 Søk...")
        if sok:
            view_df = view_df[view_df.astype(str).apply(lambda x: x.str.contains(sok, case=False)).any(axis=1)]
        
        for i, r in view_df.iterrows():
            with st.expander(f"👤 {r.get('Hovedsøker', 'Kunde')} | Status: {r.get('Status', 'Mottatt')}"):
                st.write(r)

# --- 9. MASTER KONTROLLPANEL ---
elif valg == "🕵️ Master Kontrollpanel" and role in ["Admin", "Director"]:
    st.header("🕵️ Agent Kontroll")
    with st.form("new_agent"):
        u = st.text_input("Brukernavn").lower().strip()
        p = st.text_input("Passord")
        n = st.text_input("Navn")
        if st.form_submit_button("✅ Lagre Agent"):
            add_data("Users", [u, p, "Worker"])
            add_data("Agents", [u, n, "Senior Agent", "09-17", "Aktiv", "Signed"])
            st.success("Agent opprettet!")

# --- 10. ANSATTE KONTROLL ---
elif valg == "👥 Ansatte Kontroll" and role in ["Admin", "Director"]:
    st.header("👥 Ansatte Oversikt")
    agents_df = get_data("Agents")
    if not agents_df.empty:
        for i, row in agents_df.iterrows():
            # SAFE CHECK FOR COLUMN
            a_user = str(row.get('username', '')).strip()
            a_navn = row.get('navn', 'Ukjent')
            
            with st.expander(f"👤 {a_navn} ({a_user})"):
                st.write(f"Status: {row.get('status', 'Aktiv')}")
                
                # FIXING KEYERROR: Use .get() or check columns
                reg_col = 'Registrert_Av'
                if reg_col in df.columns:
                    agent_saker = df[df[reg_col].astype(str).str.lower() == a_user.lower()]
                    st.metric("Antall Saker", len(agent_saker))
                    if not agent_saker.empty:
                        st.dataframe(agent_saker)
                else:
                    st.warning(f"Column '{reg_col}' missing in MainDB sheet.")

# --- FOOTER ---
st.sidebar.markdown("---")
st.sidebar.caption("NSVG CRM v2.0 | © 2026 Iqbal Entrepreneur")
