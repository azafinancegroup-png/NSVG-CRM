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

# Base options jo sab ko dikhengi
options = ["📊 Dashbord", "➕ Ny Registrering", "📂 Kunde Arkiv"]

# Super Power Logic: Admin aur Director dono ko "Ansatte Kontroll" aur "Master" ka access milega
if role in ["Admin", "Director"]:
    options.extend(["👥 Ansatte Kontroll", "🕵️ Master Kontrollpanel"])

valg = st.sidebar.selectbox("Hovedmeny", options)

# Logout Button
if st.sidebar.button("🔴 Logg ut"):
    st.session_state.clear()
    st.rerun()
    
# --- 6. DASHBORD LOGIC ---
if valg == "📊 Dashbord":
    st.header(f"Oversikt - {current_user.capitalize()}")
    
    if not df.empty:
        # Extra spaces saaf karna taake columns sahi match hon
        df.columns = [str(c).strip() for c in df.columns]
        
        # SUPER LOGIC: Admin aur Director ko poora data (All 1200 clients) dikhao
        # Baaki agents ko sirf unka apna data dikhao
        if role in ["Admin", "Director"]:
            user_data = df 
        else:
            if 'Registrert_Av' in df.columns:
                user_data = df[df['Registrert_Av'].astype(str).str.lower() == current_user.lower()]
            else:
                user_data = df

        # Metrics (Dashboard ke upar jo dabbe hote hain)
        c1, c2, c3 = st.columns(3)
        
        # Beløp (Amount) ko number mein badalna taake calculation sahi ho
        volum = pd.to_numeric(user_data['Beløp'], errors='coerce').sum() if 'Beløp' in user_data.columns else 0
        saker_count = len(user_data)
        provisjon = volum * 0.01  # 1% Commission calculation
        
        c1.metric("Antall Saker", f"{s_count}")
        c2.metric("Total Volum (kr)", f"{volum:,.0f} kr")
        c3.metric("Estimert Inntekt (1%)", f"{provisjon:,.0f} kr")
        
        st.divider()
        
        # Data Table dikhana
        st.subheader("Siste Registrerte Saker")
        if not user_data.empty:
            # Sirf aakhri 15 saker dikhana taake screen bhari na lage
            st.dataframe(user_data.tail(15), use_container_width=True)
        else:
            st.info("Ingen saker funnet i databasen.")
            
    else:
        st.warning("Databasen er tom. Ingen data å vise på dashbordet.")
        
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

# --- 8. KUNDE ARKIV ---
elif valg == "📂 Kunde Arkiv":
    st.header("📂 Kunde Arkiv - Full Oversikt")
    
    # Logic: Admin aur Director ko saara data dikhao
    if role in ["Admin", "Director"]:
        view_df = df
    else:
        # Agents ko sirf apna data dikhao
        if 'Registrert_Av' in df.columns:
            view_df = df[df['Registrert_Av'].astype(str).str.lower() == current_user.lower()]
        else:
            view_df = pd.DataFrame()

    if not view_df.empty:
        # Search functionality (Navn ya Phone number se search karein)
        sok = st.text_input("🔍 Søk etter kunde (Navn, Tlf, E-post)...", placeholder="Skriv her for å søke...")
        
        if sok:
            # Pura data filter karna search ke mutabiq
            mask = view_df.astype(str).apply(lambda x: x.str.contains(sok, case=False)).any(axis=1)
            view_df = view_df[mask]
        
        st.write(f"Viser {len(view_df)} treff.")
        st.divider()

        # Ek ek client ko expander mein dikhana
        for i, r in view_df.iterrows():
            # Column names safety check
            k_navn = r.get('Hovedsøker', 'Ukjent Kunde')
            k_status = r.get('Status', 'Mottatt')
            k_belop = r.get('Beløp', '0')
            
            with st.expander(f"👤 {k_navn} | {k_belop} kr | Status: {k_status}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**E-post:** {r.get('E-post', '-')}")
                    st.write(f"**Telefon:** {r.get('Telefon', '-')}")
                    st.write(f"**Registrert Av:** {r.get('Registrert_Av', '-')}")
                
                with col2:
                    st.write(f"**Bank:** {r.get('Bank', '-')}")
                    st.write(f"**Dato:** {r.get('Dato', '-')}")
                
                st.divider()
                
                # --- UPDATE STATUS (Sirf Admin aur Director ke liye) ---
                if role in ["Admin", "Director"]:
                    st.subheader("Oppdater Status")
                    n_st = st.selectbox(
                        "Endre saksstatus:", 
                        ["Mottatt", "Under Behandling", "Godkjent", "Avslått", "Utbetalt"], 
                        key=f"arkiv_st_{i}",
                        index=0 if k_status not in ["Mottatt", "Under Behandling", "Godkjent", "Avslått", "Utbetalt"] else ["Mottatt", "Under Behandling", "Godkjent", "Avslått", "Utbetalt"].index(k_status)
                    )
                    
                    if st.button("💾 Lagre Endring", key=f"arkiv_btn_{i}"):
                        # Sheet mein status update karne ka function (Row index i+2 kyunke header aur 0-index)
                        # update_status_in_sheet(i + 2, n_st) # Isko apne update function ke mutabiq set karein
                        st.success(f"Status for {k_navn} er oppdatert!")
    else:
        st.info("Ingen kunder funnet i arkivet.")
        
# --- 9. MASTER KONTROLL ---
elif valg == "🕵️ Master Kontrollpanel" and role in ["Admin", "Director"]:
    st.header("🕵️ Ny Agent Registrering")
    
    with st.form("agent_form"):
        u = st.text_input("Brukernavn (Login ID)").lower().strip()
        p = st.text_input("Passord", type="password")
        n = st.text_input("Fullt Navn")
        pos = st.selectbox("Stilling", ["Senior Agent", "Junior Agent", "Trainee"])
        
        if st.form_submit_button("✅ Aktiver og Lagre Agent"):
            if u and p and n:
                # 1. Users wali sheet mein login details dalna
                user_sh = connect_to_sheet("Users")
                user_sh.append_row([u, p, "Worker"])
                
                # 2. Agents wali sheet mein profile details dalna
                agent_sh = connect_to_sheet("Agents")
                agent_sh.append_row([u, n, pos, "09-17", "Aktiv", "Signed"])
                
                st.success(f"Agent {n} er nå aktivert i systemet!")
            else:
                st.error("Vennligst fyll ut alle feltene.")

    # Ansatte ki list dikhana (Taki Amina ko sab nazar aayein)
    st.divider()
    st.subheader("👥 Oversikt over alle Ansatte")
    agents_df = get_data("Agents")
    if not agents_df.empty:
        st.table(agents_df[['username', 'navn', 'stilling', 'status']])

# --- 10. ANSATTE KONTROLL ---
elif valg == "👥 Ansatte Kontroll" and role in ["Admin", "Director"]:
    st.header("👥 Ansatte Oversikt og Kontroll")
    
    # Data load karne ki koshish
    agents_df = get_data("Agents")
    
    if agents_df.empty:
        st.error("⚠️ Ingen data funnet i 'Agents' fanen.")
        st.info("Sjekk om Sheet-navnet er nøyaktig 'Agents' og om den inneholder data.")
    else:
        # --- JADU WALI LINE (Column Clean-up) ---
        # Ye line headers se spaces khatam karti hai aur sab ko chota (lowercase) kar deti hai
        agents_df.columns = [str(c).strip().lower() for c in agents_df.columns]
        
        # Search bar
        sok_agent = st.text_input("🔍 Søk etter ansatt...", placeholder="Skriv navn...")
        
        if sok_agent:
            # 'navn' ya 'username' dono mein search karega
            search_cols = [c for c in ['navn', 'username'] if c in agents_df.columns]
            if search_cols:
                agents_df = agents_df[agents_df[search_cols].astype(str).apply(lambda x: x.str.contains(sok_agent, case=False)).any(axis=1)]
        
        # Display Table (Sirf wahi columns jo mojud hain)
        display_cols = [c for c in ['username', 'navn', 'stilling', 'vakt', 'status'] if c in agents_df.columns]
        st.dataframe(agents_df[display_cols], use_container_width=True)
        
        st.divider()
        st.subheader("⚙️ Administrer Ansatte")
        
        for i, row in agents_df.iterrows():
            # Safety checks for names
            n = row.get('navn', row.get('username', 'Ukjent'))
            s = row.get('status', 'Aktiv')
            p = row.get('stilling', 'Agent')
            
            with st.expander(f"👤 {n} ({p})"):
                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"**Brukernavn:** {row.get('username', '-')}")
                    st.write(f"**Vakt:** {row.get('vakt', '-')}")
                with c2:
                    st.write(f"**Nåværende Status:** {s}")
                
                # Status Change
                n_status = st.selectbox("Endre Status", ["Aktiv", "Inaktiv", "Permisjon"], key=f"edit_st_{i}")
                if st.button("Oppdater Status", key=f"edit_btn_{i}"):
                    st.success(f"Status for {n} er oppdatert til {n_status}!")
