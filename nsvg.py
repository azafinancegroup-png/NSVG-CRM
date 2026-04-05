import streamlit as st
import pandas as pd
import os
from datetime import datetime
from streamlit_js_eval import get_geolocation

# --- 1. KONFIGURASJON OG STIL (Back to Detailed Style) ---
st.set_page_config(page_title="NSVG Digital Bank Portal", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e0e0e0; }
    [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] label, [data-testid="stSidebar"] .stSelectbox div {
        color: #002366 !important; font-weight: bold !important;
    }
    .stButton > button {
        background-color: transparent !important; color: #0000FF !important; border: 2px solid #0000FF !important; border-radius: 8px; transition: 0.3s;
    }
    .stButton > button:hover { background-color: #0000FF !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABASE LOGIKK & AUTO-REPAIR ---
DB_FILE = "nsvg_database_pro.csv"
LOG_FILE = "nsvg_security_logs.csv"
DOCS_DIR = "nsvg_vedlegg"
USER_FILE = "nsvg_users.csv"
AGENT_RECORDS_FILE = "nsvg_agent_management.csv"

if not os.path.exists(DOCS_DIR): os.makedirs(DOCS_DIR)

def initialize_files():
    # Sjekk og reparer Brukerfil
    if not os.path.exists(USER_FILE):
        pd.DataFrame([
            {"username": "admin", "password": "NSVG2026", "role": "Admin"},
            {"username": "amina", "password": "aminaaz0207", "role": "Worker"},
            {"username": "umer", "password": "Umer2026", "role": "Worker"},
            {"username": "ali", "password": "AliPass123", "role": "Worker"},
            {"username": "awari3600", "password": "Awari@9204", "role": "Worker"}
        ]).to_csv(USER_FILE, index=False)

    # Auto-Repair Logger (Fixer KeyError: Tidspunkt)
    if os.path.exists(LOG_FILE):
        try:
            temp_log = pd.read_csv(LOG_FILE)
            if "Tidspunkt" not in temp_log.columns:
                os.remove(LOG_FILE)
        except: os.remove(LOG_FILE)
    
    if not os.path.exists(LOG_FILE):
        pd.DataFrame(columns=["Tidspunkt", "Bruker", "Handling", "Kart_Lenke"]).to_csv(LOG_FILE, index=False)

    # Auto-Repair Hoveddatabase (Må inneholde Bank og Prosess felt)
    required_cols = ["ID", "Dato", "Produkt", "Hovedsøker", "Fnr", "Beløp", "Status", "Notater", "Vedlegg_Sti", "Registrert_Av", "Bank_Navn", "Behandlings_Status"]
    if os.path.exists(DB_FILE):
        try:
            temp_db = pd.read_csv(DB_FILE)
            if "Bank_Navn" not in temp_db.columns or "Registrert_Av" not in temp_db.columns:
                os.remove(DB_FILE)
        except: os.remove(DB_FILE)
            
    if not os.path.exists(DB_FILE):
        pd.DataFrame(columns=required_cols).to_csv(DB_FILE, index=False)

    if not os.path.exists(AGENT_RECORDS_FILE):
        pd.DataFrame(columns=["username", "full_name", "rank", "duty_time", "invoice_status", "contract"]).to_csv(AGENT_RECORDS_FILE, index=False)

initialize_files()

def record_log(user, loc_data, action):
    try:
        lat = loc_data['coords']['latitude'] if loc_data else "N/A"
        lon = loc_data['coords']['longitude'] if loc_data else "N/A"
    except: lat, lon = "N/A", "N/A"
    maps_url = f"https://www.google.com/maps?q={lat},{lon}" if lat != "N/A" else "Ingen"
    new_log = {"Tidspunkt": datetime.now().strftime("%d-%m-%Y %H:%M:%S"), "Bruker": user, "Handling": action, "Kart_Lenke": maps_url}
    pd.DataFrame([new_log]).to_csv(LOG_FILE, mode='a', header=False, index=False)

# --- 3. INNLOGGING ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user_role': None, 'user_id': None})

if not st.session_state['logged_in']:
    st.title("🛡️ NSVG - Sikker Digital Portal")
    loc = get_geolocation()
    u_input = st.text_input("Brukernavn").lower().strip()
    p_input = st.text_input("Passord", type="password")
    if st.button("Logg inn"):
        users_df = pd.read_csv(USER_FILE)
        match = users_df[(users_df['username'] == u_input) & (users_df['password'] == p_input)]
        if not match.empty:
            st.session_state.update({'logged_in': True, 'user_role': match.iloc[0]['role'], 'user_id': u_input})
            record_log(u_input, loc, "Innlogging suksess")
            st.rerun()
        else: st.error("Feil brukernavn eller passord!")
    st.stop()

# --- 4. DATA LASTING ---
df = pd.read_csv(DB_FILE)
role = st.session_state['user_role']
current_user = st.session_state['user_id']
display_df = df if role == "Admin" else df[df['Registrert_Av'] == current_user]

st.sidebar.title(f"👤 {current_user.capitalize()}")
menu = ["📊 Dashbord", "➕ Registrer ny søknad", "📂 Kunde Arkiv"]
if role == "Admin": menu.append("🕵️ Master Kontrollpanel")
valg = st.sidebar.selectbox("Hovedmeny", menu)

if st.sidebar.button("🔴 Logg ut"):
    st.session_state.clear()
    st.rerun()

# --- 📊 DASHBORD ---
if valg == "📊 Dashbord":
    st.header(f"Oversikt - {current_user.capitalize()}")
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Antall saker", len(display_df))
    with c2:
        volum = pd.to_numeric(display_df['Beløp'], errors='coerce').sum()
        st.metric("Totalt Volum (kr)", f"{volum:,} kr")
    st.divider()
    st.subheader("Siste registrerte saker")
    st.dataframe(display_df.tail(10), use_container_width=True)

# --- ➕ REGISTRER NY SØKNAD (DETAILED) ---
elif valg == "➕ Registrer ny søknad":
    st.header("Opprett Ny Bankforespørsel")
    prod = st.selectbox("Velg bankprodukt", ["Boliglån", "Boliglån Refinansiering", "Mellomfinansiering", "Investlån", "Forbrukslån", "Billån"])
    
    has_medsoker = False
    if "Investlån" not in prod:
        has_medsoker = st.radio("Søknadstype", ["Alene søker", "Med-søker / Kausjonist"]) == "Med-søker / Kausjonist"

    with st.form("nsvg_bank_form"):
        st.subheader("👤 Informasjon om Hovedsøker")
        c1, c2 = st.columns(2)
        with c1:
            navn = st.text_input("Fullt Navn (ihht ID)")
            fnr = st.text_input("Fødselsnummer (11 siffer)")
            epost = st.text_input("E-postadresse")
            tlf = st.text_input("Telefonnummer")
        with c2:
            sivil = st.selectbox("Sivilstatus", ["Enslig", "Gift", "Samboer", "Skilt/Separert"])
            jobb = st.selectbox("Arbeidsstatus", ["Fast ansatt", "Midlertidig", "AAP", "Uføretrygd", "Selvstendig næringsdrivende"])
            firma = st.text_input("Arbeidsgiver / Firma")
            lonn = st.number_input("Brutto årslønn (kr)", min_value=0)

        st.divider()
        st.subheader("📑 Finansielle detaljer")
        f1, f2 = st.columns(2)
        with f1:
            ek = st.number_input("Egenkapital (kr)", min_value=0)
            gjeld = st.number_input("Annen gjeld/Kreditt (kr)", min_value=0)
            biler = st.number_input("Antall biler", min_value=0)
        with f2:
            soknad_belop = st.number_input("Søknadsbeløp (kr)", min_value=0)
            bolig_verdi = st.number_input("Verdivurdering (hvis refinans)", min_value=0)
            barn = st.number_input("Antall barn under 18", min_value=0)

        if has_medsoker:
            st.divider()
            st.subheader("👥 Informasjon om Med-søker")
            m1, m2 = st.columns(2)
            with m1:
                m_navn = st.text_input("Medsøker Navn")
                m_fnr = st.text_input("Medsøker Fnr")
            with m2:
                m_lonn = st.number_input("Medsøker Brutto Lønn", min_value=0)
                m_gjeld = st.number_input("Medsøker Gjeld", min_value=0)

        st.divider()
        notat = st.text_area("Beskrivelse / Notater til Admin")
        opplastede_filer = st.file_uploader("Last opp dokumenter", accept_multiple_files=True)

        if st.form_submit_button("SEND SØKNAD TIL ADMIN"):
            fil_str = []
            if opplastede_filer:
                for f in opplastede_filer:
                    fn = f"{fnr}_{f.name}".replace(" ", "_")
                    with open(os.path.join(DOCS_DIR, fn), "wb") as storage:
                        storage.write(f.getbuffer())
                    fil_str.append(fn)

            info_notat = f"{notat} | Sivil: {sivil}, Jobb: {jobb}, EK: {ek}, Gjeld: {gjeld}"
            new_entry = {
                "ID": len(df) + 1, "Dato": datetime.now().strftime("%d-%m-%Y"),
                "Produkt": prod, "Hovedsøker": navn, "Fnr": fnr, "Beløp": soknad_belop,
                "Status": "Mottatt", "Notater": info_notat, "Vedlegg_Sti": ",".join(fil_str),
                "Registrert_Av": current_user, "Bank_Navn": "Vurderes", "Behandlings_Status": "Venter på Admin"
            }
            df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
            df.to_csv(DB_FILE, index=False)
            st.success("✅ Sak er registrert og sendt til Admin!")

# --- 📂 KUNDE ARKIV (CONTROL SYSTEM) ---
elif valg == "📂 Kunde Arkiv":
    st.header("Saksbehandling og Arkiv")
    sok = st.text_input("Søk i arkivet (Navn eller Fnr)")
    if sok:
        display_df = display_df[display_df.astype(str).apply(lambda x: x.str.contains(sok, case=False)).any(axis=1)]

    for i, rad in display_df.iterrows():
        with st.expander(f"📁 {rad['Hovedsøker']} (Agent: {rad['Registrert_Av']})"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Bank:** {rad['Bank_Navn']}")
                st.write(f"**Prosess:** {rad['Behandlings_Status']}")
                st.write(f"**Beløp:** {rad['Beløp']:,} kr")
            with col2:
                st.write(f"**Fnr:** {rad['Fnr']}")
                st.write(f"**Dato:** {rad['Dato']}")
                st.write(f"**Produkt:** {rad['Produkt']}")
            
            st.info(f"**Saksdetaljer:** {rad['Notater']}")
            
            # Vedlegg system
            vedlegg = str(rad['Vedlegg_Sti'])
            if vedlegg and vedlegg != "nan":
                st.write("📎 **Vedlegg:**")
                for fn in vedlegg.split(","):
                    fpath = os.path.join(DOCS_DIR, fn)
                    if os.path.exists(fpath):
                        with open(fpath, "rb") as d:
                            st.download_button(f"Last ned {fn.split('_', 1)[-1]}", d, file_name=fn, key=f"dl_{i}_{fn}")

            # ADMIN UPDATE (ONLY FOR ADMIN)
            if role == "Admin":
                st.divider()
                st.subheader("Oppdater sak og gi beskjed til Agent")
                with st.form(f"upd_form_{i}"):
                    u_bank = st.text_input("Hvilken bank er saken hos?", value=rad['Bank_Navn'])
                    u_proc = st.selectbox("Statusoppdatering", [
                        "Venter på Admin", "Sendt til Bank", "Behandles av Bank", 
                        "Mangler dokumentasjon", "Godkjent", "Avslag", "Utbetalt"
                    ], index=0)
                    if st.form_submit_button("Lagre og Send Update"):
                        df.at[i, 'Bank_Navn'] = u_bank
                        df.at[i, 'Behandlings_Status'] = u_proc
                        df.to_csv(DB_FILE, index=False)
                        st.success("Agent har fått oppdateringen!")
                        st.rerun()

# --- 🕵️ MASTER KONTROLLPANEL ---
elif valg == "🕵️ Master Kontrollpanel" and role == "Admin":
    st.header("🕵️ Systemstyring")
    t1, t2, t3 = st.tabs(["🛡️ Sikkerhetslogger", "👥 Brukerstyring", "📑 Agentinfo"])
    
    with t1:
        st.subheader("Systemlogger")
        log_df = pd.read_csv(LOG_FILE)
        st.dataframe(log_df.sort_values("Tidspunkt", ascending=False), use_container_width=True)
    
    with t2:
        st.subheader("Opprett ny Agent")
        nu = st.text_input("Nytt Brukernavn").lower().strip()
        np = st.text_input("Passord")
        if st.button("Legg til Worker"):
            u_df = pd.read_csv(USER_FILE)
            if nu in u_df['username'].values: st.error("Finnes fra før!")
            else:
                pd.DataFrame([{"username": nu, "password": np, "role": "Worker"}]).to_csv(USER_FILE, mode='a', header=False, index=False)
                st.success(f"{nu} er nå lagt til.")
        st.dataframe(pd.read_csv(USER_FILE))

    with t3:
        st.subheader("Registrerte agenter")
        st.dataframe(pd.read_csv(AGENT_RECORDS_FILE))
