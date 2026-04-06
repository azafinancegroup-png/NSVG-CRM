import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- 1. SETTINGS & PAGE CONFIG ---
st.set_page_config(page_title="NSVG Digital Bank Portal", page_icon="🛡️", layout="wide")

# CSS for Dark & Light Mode Compatibility
st.markdown("""
    <style>
    /* Main Background color adaptation */
    .stApp {
        transition: background-color 0.3s ease;
    }
    
    /* Metrics Box styling (Dono modes mein readable rahega) */
    div[data-testid="stMetric"] {
        background-color: rgba(151, 166, 195, 0.15); /* Light transparent grey */
        padding: 15px;
        border-radius: 12px;
        border: 1px solid rgba(128, 128, 128, 0.2);
    }

    /* Expander styling fix for visibility */
    .streamlit-expanderHeader {
        font-weight: bold;
        color: var(--text-color); /* Automatically picks theme text color */
    }

    /* Table/Dataframe adjustment for dark mode */
    .stDataFrame {
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 8px;
    }
    
    /* Label and Input visibility */
    label {
        font-weight: 500 !important;
        color: var(--text-color) !important;
    }
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

def update_status(row_index, new_status):
    sh = connect_to_sheet("MainDB")
    if sh:
        # Row index in Sheets is 1-based + 1 for header
        sh.update_cell(row_index + 1, 27, new_status)
        return True
    return False

def delete_user_completely(username):
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

# --- 4. GLOBAL DATA LOAD ---
df = get_data("MainDB")
role = st.session_state['user_role']
current_user = st.session_state['user_id']

# --- 5. SIDEBAR NAVIGATION ---
st.sidebar.title(f"👤 {current_user.capitalize()}")
options = ["📊 Dashbord", "➕ Ny Registrering", "📂 Kunde Arkiv"]
if role == "Admin":
    options.extend(["👥 Ansatte Kontroll", "🕵️ Master Kontrollpanel"])

valg = st.sidebar.selectbox("Hovedmeny", options)

if st.sidebar.button("🔴 Logg ut"):
    st.session_state.clear()
    st.rerun()

if valg == "📊 Dashbord":
    st.header(f"Oversikt - {current_user.capitalize()}")
    
    # 1. Sab se pehle 'user_data' ko define karna zaroori hai
    if not df.empty:
        # Columns saaf karein
        df.columns = [str(c).strip() for c in df.columns]
        
        # Admin aur Worker ka filter lagana
        if 'Registrert_Av' in df.columns:
            user_data = df if role == "Admin" else df[df['Registrert_Av'].astype(str).str.lower() == current_user.lower()]
        else:
            user_data = df # Agar column na mile to saara data dikhao (safety)
    else:
        user_data = pd.DataFrame() # Agar sheet bilkul khali ho

    # 2. Ab Metrics dikhana (Ab error nahi aayega kyunke user_data define ho chuka hai)
    c1, c2, c3 = st.columns(3)
    
    volum = 0
    if not user_data.empty and 'Beløp' in user_data.columns:
        volum = pd.to_numeric(user_data['Beløp'], errors='coerce').sum()
    
    c1.metric("Antall Saker", len(user_data))
    c2.metric("Total Volum (kr)", f"{volum:,.0f} kr")
    c3.metric("Estimert Provisjon (1%)", f"{volum * 0.01:,.0f} kr")
    
    st.divider()
    st.subheader("Siste Saker & Status")
    if not user_data.empty:
        st.dataframe(user_data.tail(15), use_container_width=True)
    else:
        st.info("Ingen saker funnet.")            
    c1, c2, c3 = st.columns(3)
    # Check if 'Beløp' column exists before summing
    volum = 0
    if not user_data.empty and 'Beløp' in user_data.columns:
        volum = pd.to_numeric(user_data['Beløp'], errors='coerce').sum()
    
    c1.metric("Antall Saker", len(user_data))
    c2.metric("Total Volum (kr)", f"{volum:,.0f} kr")
    c3.metric("Estimert Provisjon (1%)", f"{volum * 0.01:,.0f} kr")
    
    st.divider()
    st.subheader("Siste Saker & Status")
    st.dataframe(user_data.tail(15), use_container_width=True)
    
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
            new_row = [
                len(df)+1, datetime.now().strftime("%d-%m-%Y"), prod, navn, fnr, epost, tlf, sivil, 
                "Bedrift" if is_bedrift else "Privat", "Active", f_navn if is_bedrift else "", lonn, 
                barn, sfo, ek, gjeld, biler, belop, f_org if is_bedrift else "", 
                f_navn if is_bedrift else "", f_eier if is_bedrift else "", 
                m_navn, 0, notater, "Cloud", current_user, "Mottatt"
            ]
            add_data("MainDB", new_row)
            st.success("✅ Søknad registrert!")

# --- 8. KUNDE ARKIV (WITH ADMIN STATUS CONTROL) ---
elif valg == "📂 Kunde Arkiv":
    st.header("📂 Kunde Arkiv & Behandling")
    sok = st.text_input("Søk på Navn, Fnr, Agent or Status...")
    
    view_df = df if role == "Admin" else df[df['Registrert_Av'].astype(str).str.lower() == current_user.lower()]
    
    if not view_df.empty:
        if sok:
            view_df = view_df[view_df.astype(str).apply(lambda x: x.str.contains(sok, case=False)).any(axis=1)]
        
        for i, r in view_df.iterrows():
            with st.expander(f"📄 {r['Dato']} - {r['Hovedsøker']} | Status: {r['Status']}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Produkt:** {r['Produkt']}")
                    st.write(f"**Fødselsnr:** {r['Fødselsnummer']}")
                    st.write(f"**Beløp:** {r['Beløp']:,} kr")
                    st.write(f"**Agent:** {r['Registrert_Av']}")
                with col2:
                    if role == "Admin":
                        new_st = st.selectbox("Oppdater Status", ["Mottatt", "Under Behandling", "Mangelfull", "Godkjent", "Avslått", "Utbetalt"], index=0, key=f"status_{i}")
                        if st.button("Lagre Status", key=f"btn_{i}"):
                            if update_status(i + 1, new_st):
                                st.success(f"Status endret til {new_st}")
                                st.rerun()
                    else:
                        st.info(f"Gjeldende Status: {r['Status']}")

# --- 9. ANSATTE KONTROLL (WITH DELETE) ---
elif valg == "👥 Ansatte Kontroll" and role == "Admin":
    st.header("👥 Ansatte Management")
    u_list = get_data("Users")
    if not u_list.empty:
        workers = u_list[u_list['role'] == 'Worker']
        for _, w in workers.iterrows():
            u_id = str(w['username'])
            with st.expander(f"👤 Agent: {u_id.upper()}"):
                c1, c2 = st.columns([3, 1])
                with c1:
                    w_cases = df[df['Registrert_Av'].astype(str).str.lower() == u_id.lower()] if not df.empty else pd.DataFrame()
                    st.write(f"Saker: {len(w_cases)}")
                    st.dataframe(w_cases.tail(3), use_container_width=True)
                with c2:
                    if st.button(f"🗑️ Slette {u_id}", key=f"del_{u_id}"):
                        if delete_user_completely(u_id):
                            st.success(f"{u_id} slettet!")
                            st.rerun()

# --- 10. MASTER KONTROLLPANEL ---
elif valg == "🕵️ Master Kontrollpanel" and role == "Admin":
    st.header("🕵️ System Admin")
    with st.form("new_user_form"):
        new_u = st.text_input("Ny Bruker-ID").lower().strip()
        new_p = st.text_input("Passord")
        new_fn = st.text_input("Agent Navn")
        if st.form_submit_button("AKTIVER AGENT"):
            if new_u and new_p:
                add_data("Users", [new_u, new_p, "Worker"])
                add_data("Agents", [new_u, new_fn, "Senior", "09-17", "Aktiv", "Signed"])
                st.success("✅ Agent opprettet!")
                st.rerun()
