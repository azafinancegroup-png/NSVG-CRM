import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- 1. SETTINGS & PAGE CONFIG ---
st.set_page_config(page_title="NSVG Digital Bank Portal", page_icon="🛡️", layout="wide")

# CSS for Dark & Light Mode Compatibility
st.markdown("""
    <style>
    div[data-testid="stMetric"] {
        background-color: rgba(151, 166, 195, 0.15);
        padding: 15px;
        border-radius: 12px;
        border: 1px solid rgba(128, 128, 128, 0.2);
    }
    .streamlit-expanderHeader {
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SPEED CACHING ---
@st.cache_data
def get_country_list():
    base = ["Norge", "Sverige", "Danmark", "UK", "USA", "Pakistan", "India"]
    others = sorted(["Afghanistan", "Albania", "Algerie", "Andorra", "Angola", "Argentina", "Australia", "Bangladesh", "Belgia", "Brasil", "Canada", "Chile", "China", "Egypt", "Finland", "Frankrike", "Hellas", "Island", "Iran", "Irak", "Irland", "Italia", "Japan", "Jordan", "Kuwait", "Latvia", "Libanon", "Malaysia", "Mexico", "Marokko", "Nederland", "New Zealand", "Nigeria", "Oman", "Filippinene", "Polen", "Portugal", "Qatar", "Romania", "Russland", "Saudi Arabia", "Singapore", "Spania", "Sri Lanka", "Sudan", "Sveits", "Syria", "Thailand", "Tunisia", "Tyrkia", "UAE", "Ukraina", "Vietnam"])
    return base + others

# --- 3. GOOGLE SHEETS ENGINE ---
def connect_to_sheet(sheet_name):
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        # Yahan apni Google Sheet ka sahi naam likhein
        return client.open("NSVG_CRM_Data").worksheet(sheet_name)
    except Exception as e:
        st.error(f"Tilkoblingsfeil: {e}")
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
    if sh: 
        sh.append_row(row_list)
        return True
    return False

# --- 4. LOGIN SYSTEM ---
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

# --- 5. GLOBAL DATA LOAD ---
df = get_data("MainDB")
role = st.session_state['user_role']
current_user = st.session_state['user_id']
countries = get_country_list()

# --- 6. SIDEBAR NAVIGATION ---
st.sidebar.title(f"👤 {current_user.capitalize()}")
options = ["📊 Dashbord", "➕ Ny Registrering", "📂 Kunde Arkiv"]

if role in ["Admin", "Director"]:
    options.extend(["👥 Ansatte Kontroll", "🕵️ Master Kontrollpanel"])

valg = st.sidebar.selectbox("Hovedmeny", options)

if st.sidebar.button("🔴 Logg ut"):
    st.session_state.clear()
    st.rerun()

# --- 7. DASHBORD ---
if valg == "📊 Dashbord":
    st.header(f"Oversikt - {current_user.capitalize()}")
    c1, c2, c3 = st.columns(3)

    if not df.empty:
        # Filter data based on role
        if role in ["Admin", "Director"]:
            view_data = df
        else:
            reg_col = next((c for c in df.columns if c.lower() in ['saksbehandler', 'registrert_av', 'agent']), 'Saksbehandler')
            view_data = df[df[reg_col].astype(str).str.lower() == current_user.lower()] if reg_col in df.columns else df

        # Calculations
        b_col = next((c for c in view_data.columns if c.lower() in ['lånebeløp', 'beløp', 'sum']), 'Lånebeløp')
        total_v = pd.to_numeric(view_data[b_col], errors='coerce').sum() if b_col in view_data.columns else 0
        
        c1.metric("Antall Saker", len(view_data))
        c2.metric("Total Volum (kr)", f"{total_v:,.0f} kr")
        c3.metric("Provisjon (1%)", f"{total_v * 0.01:,.0f} kr")
        
        st.divider()
        st.subheader("Siste Registrerte Saker")
        st.dataframe(view_data.tail(15), use_container_width=True)
    else:
        st.info("📭 Dashbordet er tomt.")

# --- 8. NY REGISTRERING (FIXED SECTION 7) ---
elif valg == "➕ Ny Registrering":
    st.header("➕ Ny Bankforespørsel")
    
    prod = st.selectbox("Velg Produkt", ["Boliglån", "Refinansiering", "Mellomfinansiering", "Investlån / Bedriftlån", "Byggelån", "Forbrukslån", "Billån"])
    is_bedrift = "Bedriftlån" in prod or "Investlån" in prod

    st.info("Har kunden en Medsøker?")
    has_med = st.checkbox("✅ JA, legg til Medsøker")

    with st.form("main_bank_form", clear_on_submit=True):
        # Bedrift Section
        f_navn, f_org, f_eier, f_aksjer = "", "", "", ""
        if is_bedrift:
            st.subheader("🏢 Bedriftsdetaljer")
            bc1, bc2 = st.columns(2)
            f_navn = bc1.text_input("Firma Navn")
            f_org = bc1.text_input("OrgNr")
            f_eier = bc2.text_area("Eiere (Navn & Fnr)")
            f_aksjer = bc2.text_input("Aksjer %")
            st.divider()

        # Hovedsøker
        st.subheader("👤 Hovedsøker Detaljer")
        c1, c2 = st.columns(2)
        navn = c1.text_input("Fullt Navn (Hovedsøker)")
        fnr = c1.text_input("Fødselsnummer (11 siffer)")
        epost = c1.text_input("E-post")
        tlf = c2.text_input("Telefon")
        sivil = c2.selectbox("Sivilstatus", ["Enslig", "Gift", "Samboer", "Skilt"])
        pass_land = c1.selectbox("Statsborgerskap", countries)
        botid = c2.text_input("Botid i Norge")

        st.markdown("#### 💼 Inntekt & Finans")
        l1, l2, l3 = st.columns(3)
        lonn = l1.number_input("Årslønn Brutto", 0)
        arb = l2.text_input("Arbeidsgiver")
        tid = l3.text_input("Ansettelsestid")
        
        f1, f2 = st.columns(2)
        belop = f1.number_input("Ønsket Lånebeløp", 0)
        ek = f1.number_input("Egenkapital", 0)
        barn = f2.number_input("Antall Barn", 0)
        biler = f2.number_input("Antall Biler", 0)
        sfo = f2.selectbox("SFO/Barnehage?", ["Nei", "Ja"])

        st.markdown("#### 💳 Gjeld")
        g1, g2, g3 = st.columns(3)
        g_bolig = g1.number_input("Boliglån", 0)
        g_bil = g2.number_input("Billån", 0)
        g_forbruk = g3.number_input("Forbrukslån", 0)
        g_kort = g1.number_input("Kredittkort", 0)
        g_studie = g2.number_input("Studielån", 0)

        # Medsøker
        m_navn, m_fnr, m_epost, m_tlf, m_lonn, m_arb = "", "", "", "", 0, ""
        if has_med:
            st.divider()
            st.subheader("👥 Medsøker Detaljer")
            mc1, mc2 = st.columns(2)
            m_navn = mc1.text_input("Fullt Navn (Medsøker)")
            m_fnr = mc1.text_input("Fødselsnummer (Medsøker)")
            m_epost = mc1.text_input("E-post (Medsøker)")
            m_tlf = mc2.text_input("Telefon (Medsøker)")
            m_lonn = mc1.number_input("Årslønn (Medsøker)", 0)
            m_arb = mc2.text_input("Arbeidsgiver (Medsøker)")

        st.divider()
        notater = st.text_area("Notater")

        if st.form_submit_button("🚀 SEND SØKNAD"):
            tot_gjeld = g_bolig + g_bil + g_forbruk + g_kort + g_studie
            # Match Sheet Column Sequence
            new_row = [
                len(df)+1, datetime.now().strftime("%d-%m-%Y"), prod, navn, fnr, epost, tlf, sivil, 
                "Bedrift" if is_bedrift else "Privat", "Active", f_navn, lonn, barn, sfo, ek, 
                tot_gjeld, biler, belop, f_org, f_eier, f_aksjer, 
                m_navn, m_fnr, m_epost, m_tlf, m_lonn, m_arb, notater, 
                f"P1: {pass_land}", current_user, "Mottatt"
            ]
            if add_data("MainDB", new_row):
                st.success("✅ Søknad Registrert!")
                st.balloons()
                st.rerun()

# --- 9. KUNDE ARKIV ---
elif valg == "📂 Kunde Arkiv":
    st.header("📂 Kunde Arkiv")
    if not df.empty:
        sok = st.text_input("🔍 Søk (Navn, Tlf, E-post)...")
        view_df = df if role in ["Admin", "Director"] else df[df['Saksbehandler'].astype(str).str.lower() == current_user.lower()]
        
        if sok:
            mask = view_df.astype(str).apply(lambda x: x.str.contains(sok, case=False)).any(axis=1)
            view_df = view_df[mask]
        
        st.dataframe(view_df, use_container_width=True)
    else:
        st.info("Arkivet er tomt.")

# --- 10. MASTER & AGENT KONTROLL ---
elif valg == "🕵️ Master Kontrollpanel" and role in ["Admin", "Director"]:
    st.header("🕵️ Agent Kontroll")
    with st.form("agent_reg"):
        u = st.text_input("Brukernavn").lower().strip()
        p = st.text_input("Passord")
        n = st.text_input("Fullt Navn")
        role_type = st.selectbox("Rolle", ["Worker", "Admin"])
        if st.form_submit_button("Aktiver Agent"):
            add_data("Users", [u, p, role_type])
            add_data("Agents", [u, n, "Aktiv", datetime.now().strftime("%d-%m-%Y")])
            st.success("Agent er opprettet!")

elif valg == "👥 Ansatte Kontroll" and role in ["Admin", "Director"]:
    st.header("👥 Ansatte Oversikt")
    agents = get_data("Agents")
    st.table(agents)

# --- FOOTER ---
st.sidebar.markdown("---")
st.sidebar.caption(f"NSVG CRM v2.0 | {datetime.now().year}")
