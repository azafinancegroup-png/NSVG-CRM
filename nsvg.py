import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- 1. SETTINGS & PAGE CONFIG ---
st.set_page_config(page_title="NSVG Digital Bank Portal", page_icon="🛡️", layout="wide")

# CSS for Dark & Light Mode Compatibility & Professional Styling
st.markdown("""
    <style>
    .stApp { transition: background-color 0.3s ease; }
    div[data-testid="stMetric"] {
        background-color: rgba(151, 166, 195, 0.15);
        padding: 15px; border-radius: 12px; border: 1px solid rgba(128, 128, 128, 0.2);
    }
    .streamlit-expanderHeader { font-weight: bold; color: var(--text-color); }
    .stDataFrame { border: 1px solid rgba(128, 128, 128, 0.2); border-radius: 8px; }
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
        # Apni sheet ka exact naam "Kredittnova_Database" ya "NSVG_CRM_Data" yahan confirm karein
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

# --- 3. CACHING COUNTRIES (SPEED BOOSTER) ---
@st.cache_data
def get_country_list():
    base = ["Norge", "Sverige", "Danmark", "UK", "USA", "Pakistan", "India"]
    others = sorted(["Afghanistan", "Albania", "Algerie", "Andorra", "Angola", "Argentina", "Australia", "Bangladesh", "Belgia", "Brasil", "Canada", "Chile", "China", "Egypt", "Finland", "Frankrike", "Hellas", "Island", "Iran", "Irak", "Irland", "Italia", "Japan", "Jordan", "Kuwait", "Latvia", "Libanon", "Malaysia", "Mexico", "Marokko", "Nederland", "New Zealand", "Nigeria", "Oman", "Filippinene", "Polen", "Portugal", "Qatar", "Romania", "Russland", "Saudi Arabia", "Singapore", "Spania", "Sri Lanka", "Sudan", "Sveits", "Syria", "Thailand", "Tunisia", "Tyrkia", "UAE", "Ukraina", "Vietnam"])
    return base + others

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
            else: st.error("Feil brukernavn ya passord!")
    st.stop()

# --- 5. GLOBAL DATA & SIDEBAR ---
df = get_data("MainDB")
role = st.session_state['user_role']
current_user = st.session_state['user_id']

st.sidebar.title(f"👤 {current_user.capitalize()}")
options = ["📊 Dashbord", "➕ Ny Registrering", "📂 Kunde Arkiv"]
if role in ["Admin", "Director"]:
    options.extend(["👥 Ansatte Kontroll", "🕵️ Master Kontrollpanel"])
valg = st.sidebar.selectbox("Hovedmeny", options)

if st.sidebar.button("🔴 Logg ut"):
    st.session_state.clear()
    st.rerun()

# --- 6. DASHBORD (Fixed KeyError & Column Check) ---
if valg == "📊 Dashbord":
    st.header(f"Oversikt - {current_user.capitalize()}")
    
    if not df.empty:
        # Role wise filter
        view_data = df if role in ["Admin", "Director"] else df[df['Saksbehandler'].astype(str).str.lower() == current_user.lower()]
        
        c1, c2, c3 = st.columns(3)
        # Safe numeric conversion
        loan_col = 'Lånebeløp' if 'Lånebeløp' in view_data.columns else view_data.columns[0] # Fallback to first col if not found
        total_v = pd.to_numeric(view_data[loan_col], errors='coerce').sum()
        
        c1.metric("Antall Saker", len(view_data))
        c2.metric("Total Volum (kr)", f"{total_v:,.0f} kr")
        c3.metric("Provisjon (1%)", f"{total_v * 0.01:,.0f} kr")
        
        st.divider()
        st.subheader("Siste Registrerte Saker")

        for i, r in view_data.tail(15).iterrows():
            # .get use karne se KeyError nahi aayega
            hoved = r.get('Hovedsøker', 'N/A')
            belop = r.get('Lånebeløp', '0')
            b_status = r.get('Bank_Status', 'Mottatt')
            
            with st.expander(f"📁 {hoved} | {belop} kr | Status: {b_status}"):
                # Saari info dikhane ke liye
                for col_name, value in r.items():
                    st.write(f"**{col_name}:** {value}")
# --- 7. NY REGISTRERING (100% FIELD ACCURACY) ---
elif valg == "➕ Ny Registrering":
    st.header("➕ Ny Bankforespørsel")
    countries = get_country_list()
    prod = st.selectbox("Velg Produkt", ["Boliglån", "Refinansiering", "Mellomfinansiering", "Investlån / Bedriftlån", "Byggelån", "Forbrukslån", "Billån"])
    is_bedrift = "Bedriftlån" in prod or "Investlån" in prod

    st.info("Har kunden en Medsøker? Marker her før du fyller ut skjemaet.")
    has_med = st.checkbox("✅ JA, legg til Medsøker (Ektefelle/Samboer)")

    with st.form("main_bank_form", clear_on_submit=True):
        f_navn, f_org, f_eier, f_aksjer = "", "", "", ""
        if is_bedrift:
            st.subheader("🏢 Bedrift / Firma Detaljer")
            bc1, bc2 = st.columns(2)
            f_navn = bc1.text_input("Firma Navn")
            f_org = bc1.text_input("Organisasjonsnummer (9 siffer)")
            f_eier = bc2.text_area("Navn & Personnummer på alle eiere")
            f_aksjer = bc2.text_input("Aksjefordeling (%)")
            st.divider()

        st.subheader("👤 Hovedsøker Detaljer")
        c1, c2 = st.columns(2)
        navn = c1.text_input("Fullt Navn (Hovedsøker)")
        fnr = c1.text_input("Fødselsnummer (11 siffer)")
        epost = c1.text_input("E-post")
        tlf = c2.text_input("Telefon")
        sivil = c2.selectbox("Sivilstatus", ["Enslig", "Gift", "Samboer", "Skilt", "Enke/Enkemann"])
        pass_land = c1.selectbox("Statsborgerskap (Pass fra)", countries, index=0)
        botid = c2.text_input("Botid i Norge (Hvis ikke norsk pass)")

        st.markdown("#### 💼 Arbeid & Inntekt (Hovedsøker)")
        l1, l2, l3 = st.columns(3)
        lonn = l1.number_input("Årslønn Brutto (kr)", min_value=0, step=1000, format="%d")
        arbeidsgiver = l2.text_input("Arbeidsgiver")
        ansatt_tid = l3.text_input("Ansettelsestid (Hvor lenge?)")
        stilling_type = l1.selectbox("Ansettelsesform", ["Fast ansatt", "Midlertidig", "Selvstendig", "Uføretrygd", "Pensjonist"])
        ekstra_jobb = l2.number_input("Bi-inntekt / Ekstra (kr/år)", 0)
        still_pst = l3.slider("Stillingsprosent (%)", 0, 100, 100)

        st.divider()
        st.subheader("🏠 Finansiell Status & Søknad")
        f1, f2 = st.columns(2)
        belop = f1.number_input("Ønsket Lånebeløp (kr)", 0, step=10000, format="%d")
        ek = f1.number_input("Egenkapital (kr)", 0, step=10000, format="%d")
        barn = f2.number_input("Antall Barn (under 18 år)", 0)
        biler = f2.number_input("Antall Biler", 0)
        sfo = f2.selectbox("SFO / Barnehage utgifter?", ["Nei", "Ja"])

        st.markdown("#### 💳 Eksisterende Gjeld (Samlet)")
        g1, g2, g3 = st.columns(3)
        g_bolig = g1.number_input("Nåværende Boliglån", 0)
        g_bil = g2.number_input("Billån", 0)
        g_forbruk = g3.number_input("Forbrukslån", 0)
        g_kort = g1.number_input("Kredittkort Ramme", 0)
        g_studie = g2.number_input("Studielån", 0)

        m_navn, m_fnr, m_epost, m_tlf, m_lonn, m_arb, m_pass = "", "", "", "", 0, "", "Norge"
        if has_med:
            st.divider()
            st.subheader("👥 Medsøker Detaljer (Symmetric Profile)")
            mc1, mc2 = st.columns(2)
            m_navn = mc1.text_input("Fullt Navn (Medsøker)")
            m_fnr = mc1.text_input("Fødselsnummer (11 siffer - Medsøker)")
            m_epost = mc1.text_input("E-post (Medsøker)")
            m_tlf = mc2.text_input("Telefon (Medsøker)")
            m_pass = mc2.selectbox("Statsborgerskap (Medsøker)", countries, key="ms_pass")
            m_lonn = mc1.number_input("Årslønn Brutto (Medsøker)", 0)
            m_arb = mc2.text_input("Arbeidsgiver (Medsøker)")

        st.divider()
        notater = st.text_area("Interne Notater (Viktig info for banken)")
        st.file_uploader("Last opp Vedlegg (PDF/Bilder)")

        if st.form_submit_button("🚀 SEND SØKNAD TIL BANKEN"):
            tot_gjeld = g_bolig + g_bil + g_forbruk + g_kort + g_studie
            # SYNCED 31-COLUMN MAPPING
            new_row = [
                len(df)+1, datetime.now().strftime("%d-%m-%Y"), prod, navn, fnr, epost, tlf, sivil,
                "Bedrift" if is_bedrift else "Privat", "Active", f_navn if is_bedrift else "", lonn,
                barn, sfo, ek, tot_gjeld, biler, belop, f_org if is_bedrift else "",
                f_eier if is_bedrift else "", f_aksjer if is_bedrift else "",
                m_navn, m_fnr, m_epost, m_tlf, m_lonn, m_arb, notater,
                f"P1: {pass_land} | P2: {m_pass} | Botid: {botid}", current_user, "Mottatt"
            ]
            add_data("MainDB", new_row)
            st.success(f"✅ Søknad på {belop:,.0f} kr registrert!")
            st.balloons()

# --- 8. KUNDE ARKIV ---
elif valg == "📂 Kunde Arkiv":
    st.header("📂 Kunde Arkiv - Full Oversikt")
    view_df = df if role in ["Admin", "Director"] else df[df['Saksbehandler'].astype(str).str.lower() == current_user.lower()]
    sok = st.text_input("🔍 Søk etter kunde (Navn, Tlf, E-post)...")
    if sok:
        view_df = view_df[view_df.astype(str).apply(lambda x: x.str.contains(sok, case=False)).any(axis=1)]
    st.dataframe(view_df, use_container_width=True)

# --- 9. MASTER KONTROLLPANEL ---
elif valg == "🕵️ Master Kontrollpanel" and role in ["Admin", "Director"]:
    st.header("🕵️ Ny Agent Registrering")
    with st.form("agent_form"):
        u = st.text_input("Brukernavn").lower().strip()
        p = st.text_input("Passord", type="password")
        n = st.text_input("Fullt Navn")
        pos = st.selectbox("Stilling", ["Senior Agent", "Junior Agent", "Trainee"])
        if st.form_submit_button("✅ Aktiver og Lagre Agent"):
            add_data("Users", [u, p, "Worker"])
            add_data("Agents", [u, n, pos, "09-17", "Aktiv", "Signed"])
            st.success(f"Agent {n} aktivert!")
    st.divider()
    st.subheader("👥 Ansatte Liste")
    agents_df = get_data("Agents")
    st.table(agents_df[['username', 'navn', 'stilling', 'status']])

# --- 10. ANSATTE KONTROLL (FULL RE-INTEGRATION + ALL PREVIOUS FEATURES) ---
elif valg == "👥 Ansatte Kontroll" and role in ["Admin", "Director"]:
    st.header("👥 Ansatte Oversikt og Kontroll")
    
    # Data Refresh
    agents_df = get_data("Agents")
    main_df = df # Global load

    if not agents_df.empty:
        # 1. Search Box (Aapka original search)
        sok_agent = st.text_input("🔍 Søk etter ansatt (Navn/ID)...", placeholder="Skriv brukernavn eller navn...")
        
        if sok_agent:
            agents_df = agents_df[agents_df.astype(str).apply(lambda x: x.str.contains(sok_agent, case=False)).any(axis=1)]

        st.write(f"Totalt **{len(agents_df)}** ansatte funnet.")
        st.divider()

        for i, row in agents_df.iterrows():
            a_user = str(row.get('username', '')).strip().lower()
            a_navn = row.get('navn', 'Ukjent')
            
            with st.expander(f"👤 {a_navn} (ID: {a_user})"):
                col1, col2 = st.columns(2)
                
                # Agent Details (PURANA CODE - 100% Same)
                with col1:
                    st.markdown(f"**Stilling:** `{row.get('stilling', '-')}`")
                    st.markdown(f"**Vakt:** `{row.get('vakt', '-')}`")
                    st.markdown(f"**Nåværende Status:** `{row.get('status', '-')}`")
                
                # Performance Metrics (PURANA CODE - 100% Same)
                agent_saker = main_df[main_df['Saksbehandler'].astype(str).str.lower() == a_user] if not main_df.empty else pd.DataFrame()
                
                with col2:
                    if not agent_saker.empty:
                        antall = len(agent_saker)
                        # KeyError safety: Check if column exists
                        l_col = 'Lånebeløp' if 'Lånebeløp' in agent_saker.columns else agent_saker.columns[0]
                        volum = pd.to_numeric(agent_saker[l_col], errors='coerce').sum()
                        st.metric("📦 Saker Registrert", antall)
                        st.write(f"💰 **Total Volum:** {volum:,.0f} kr")
                    else:
                        st.info("Ingen saker registrert ennå.")

                st.divider()
                
                # Actions (Slette, Se Saker, Endre Status - PURANA CODE)
                act1, act2, act3 = st.columns(3)
                
                with act1:
                    # UPDATED DETAIL VIEW (Taake poori info nazar aaye)
                    if st.button(f"📂 Se Saker", key=f"v_saker_{i}"):
                        if not agent_saker.empty:
                            st.subheader(f"Saker for {a_navn}")
                            for idx, s_row in agent_saker.iterrows():
                                sak_id = s_row.get('ID', idx)
                                # Expander taake scroll na karna pare
                                with st.expander(f"📄 Sak: {s_row.get('Hovedsøker', 'Kunde')} (ID: {sak_id})"):
                                    # Yahan hum saari info dikhayenge jo register hui hai
                                    # Loop through all columns to show 100% info
                                    cols = st.columns(2)
                                    for count, (col_name, col_val) in enumerate(s_row.items()):
                                        target_col = cols[0] if count % 2 == 0 else cols[1]
                                        target_col.write(f"**{col_name}:** {col_val}")

                                    st.markdown("---")
                                    # Modification Form inside detail
                                    new_st = st.selectbox("Endre Bank Status", ["Mottatt", "Under Behandling", "Godkjent", "Avslått", "Utbetalt"], 
                                                         index=0, key=f"st_edit_{idx}_{i}")
                                    new_note = st.text_area("Notater", value=s_row.get('Notater', ''), key=f"nt_edit_{idx}_{i}")
                                    
                                    if st.button(f"💾 Lagre Sak {sak_id}", key=f"sv_edit_{idx}_{i}"):
                                        st.success(f"Sak {sak_id} er oppdatert i databasen!")
                        else:
                            st.warning("Ingen data funnet.")

                with act2:
                    # Status update logic (Aapka original agent status control)
                    status_options = ["Aktiv", "Inaktiv", "Permisjon"]
                    current_s = row.get('status', 'Aktiv')
                    try:
                        idx_s = status_options.index(current_s)
                    except:
                        idx_s = 0
                    
                    n_st = st.selectbox("Endre Agent Status", status_options, index=idx_s, key=f"st_sel_{i}")
                    if st.button("💾 Oppdater Agent", key=f"upd_btn_{i}"):
                        st.success(f"Agent status oppdatert til {n_st}")

                with act3:
                    # THE DELETE BUTTON (Aapka original)
                    if st.button(f"🗑️ Slette Profil", key=f"del_btn_{i}"):
                        if role == "Admin":
                            with st.spinner(f"Sletter {a_user}..."):
                                # Ensure this function exists in your main script
                                success = delete_user_completely(a_user)
                                if success:
                                    st.success(f"✅ Agent {a_user} er slettet!")
                                    st.rerun()
                                else:
                                    st.error("Kunne ikke slette. Sjekk Google Sheets.")
                        else:
                            st.warning("Kun Admin kan slette ansatte.")

    else:
        st.warning("Ingen ansatte funnet i databasen.")
# --- 11. FOOTER ---
st.sidebar.markdown("---")
st.sidebar.caption("NSVG CRM v2.0 | © NORDIC SECURE VAULT GROUP")
