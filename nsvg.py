import streamlit as st
import pandas as pd
import os
from datetime import datetime
from streamlit_js_eval import get_geolocation

# --- 1. KONFIGURASJON OG STIL ---
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
    # 1. Sjekk Brukerfil
    if not os.path.exists(USER_FILE):
        pd.DataFrame([
            {"username": "admin", "password": "NSVG2026", "role": "Admin"},
            {"username": "amina", "password": "aminaaz0207", "role": "Worker"},
            {"username": "umer", "password": "Umer2026", "role": "Worker"},
            {"username": "ali", "password": "AliPass123", "role": "Worker"},
            {"username": "awari3600", "password": "Awari@9204", "role": "Worker"}
        ]).to_csv(USER_FILE, index=False)

    # 2. Sjekk Sikkerhetslogger (Fix KeyError: Tidspunkt)
    if os.path.exists(LOG_FILE):
        temp_log = pd.read_csv(LOG_FILE)
        if "Tidspunkt" not in temp_log.columns:
            os.remove(LOG_FILE) # Slett gammel fil med feil format
    
    if not os.path.exists(LOG_FILE):
        pd.DataFrame(columns=["Tidspunkt", "Bruker", "Handling", "Kart_Lenke"]).to_csv(LOG_FILE, index=False)

    # 3. Sjekk Hoveddatabase (Legg til Bank og Prosess felt)
    required_db_cols = ["ID", "Dato", "Produkt", "Hovedsøker", "Fnr", "Beløp", "Status", "Notater", "Vedlegg_Sti", "Registrert_Av", "Bank_Navn", "Behandlings_Status"]
    if os.path.exists(DB_FILE):
        temp_db = pd.read_csv(DB_FILE)
        if "Bank_Navn" not in temp_db.columns:
            os.remove(DB_FILE) # Slett hvis gamle kolonner mangler
            
    if not os.path.exists(DB_FILE):
        pd.DataFrame(columns=required_db_cols).to_csv(DB_FILE, index=False)

    if not os.path.exists(AGENT_RECORDS_FILE):
        pd.DataFrame(columns=["username", "full_name", "rank", "duty_time", "invoice_status", "contract"]).to_csv(AGENT_RECORDS_FILE, index=False)

initialize_files()

def record_log(user, loc_data, action):
    try:
        lat = loc_data['coords']['latitude'] if loc_data else "N/A"
        lon = loc_data['coords']['longitude'] if loc_data else "N/A"
    except: lat, lon = "N/A", "N/A"
    maps_url = f"https://www.google.com/maps?q={lat},{lon}" if lat != "N/A" else "Ingen lokasjon"
    new_log = {"Tidspunkt": datetime.now().strftime("%d-%m-%Y %H:%M:%S"), "Bruker": user, "Handling": action, "Kart_Lenke": maps_url}
    pd.DataFrame([new_log]).to_csv(LOG_FILE, mode='a', header=False, index=False)

# --- 3. INNLOGGING SYSTEM ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user_role': None, 'user_id': None})

if not st.session_state['logged_in']:
    st.title("🛡️ NSVG - Sikker Digital Portal")
    st.info("⚠️ Sikkerhet: Vennligst tillat posisjonstilgang.")
    loc = get_geolocation()
    u_input = st.text_input("Brukernavn").lower().strip()
    p_input = st.text_input("Passord", type="password")
    
    if st.button("Logg inn"):
        users_df = pd.read_csv(USER_FILE)
        user_match = users_df[(users_df['username'] == u_input) & (users_df['password'] == p_input)]
        
        if not user_match.empty:
            st.session_state.update({'logged_in': True, 'user_role': user_match.iloc[0]['role'], 'user_id': u_input})
            record_log(u_input, loc, "Innlogging suksess")
            st.rerun()
        else:
            st.error("Feil brukernavn eller passord!")
    st.stop()

# --- 4. DATA LASTING ---
df = pd.read_csv(DB_FILE)
role = st.session_state['user_role']
current_user = st.session_state['user_id']
# Admin ser alt, Worker ser kun sitt eget
display_df = df if role == "Admin" else df[df['Registrert_Av'] == current_user]

st.sidebar.title(f"👤 {current_user.capitalize()}")
menu = ["📊 Dashbord", "➕ Registrer ny søknad", "📂 Kunde Arkiv"]
if role == "Admin": menu.append("🕵️ Master Kontrollpanel")
valg = st.sidebar.selectbox("Hovedmeny", menu)

if st.sidebar.button("🔴 Logg ut"):
    st.session_state.clear()
    st.rerun()

# --- SECTION 1: DASHBORD ---
if valg == "📊 Dashbord":
    st.header(f"📊 Oversikt for {current_user.capitalize()}")
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Antall saker", len(display_df))
    with c2:
        volum = pd.to_numeric(display_df['Beløp'], errors='coerce').sum()
        st.metric("Totalt volum (kr)", f"{volum:,} kr")
    
    st.divider()
    st.subheader("Siste aktiviteter")
    st.dataframe(display_df.tail(10), use_container_width=True)

# --- SECTION 2: NY SØKNAD ---
elif valg == "➕ Registrer ny søknad":
    st.header("➕ Opprett Ny Sak")
    with st.form("nsvg_skjema"):
        navn = st.text_input("Fullt Navn (ihht ID)")
        fnr = st.text_input("Fødselsnummer (11 siffer)")
        prod = st.selectbox("Produkt", ["Boliglån", "Refinansiering", "Investlån", "Forbrukslån", "Billån"])
        belop = st.number_input("Søknadsbeløp (kr)", min_value=0)
        notater = st.text_area("Beskrivelse av saken")
        filer = st.file_uploader("Last opp vedlegg", accept_multiple_files=True)
        
        if st.form_submit_button("SEND SAK TIL VAULT"):
            fil_navn = []
            if filer:
                for f in filer:
                    f_clean = f"{fnr}_{f.name}".replace(" ", "_")
                    with open(os.path.join(DOCS_DIR, f_clean), "wb") as save_f:
                        save_f.write(f.getbuffer())
                    fil_navn.append(f_clean)
            
            new_sak = {
                "ID": len(df) + 1, "Dato": datetime.now().strftime("%d-%m-%Y"),
                "Produkt": prod, "Hovedsøker": navn, "Fnr": fnr, "Beløp": belop,
                "Status": "Mottatt", "Notater": notater, "Vedlegg_Sti": ",".join(fil_navn),
                "Registrert_Av": current_user, "Bank_Navn": "Vurderes", "Behandlings_Status": "Venter på Admin"
            }
            df = pd.concat([df, pd.DataFrame([new_sak])], ignore_index=True)
            df.to_csv(DB_FILE, index=False)
            st.success("✅ Saken er sendt! Admin vil behandle den nå.")

# --- SECTION 3: KUNDE ARKIV (CONTROL SYSTEM) ---
elif valg == "📂 Kunde Arkiv":
    st.header("📂 Sakshåndtering og Arkiv")
    sok = st.text_input("Søk (Navn/Fnr)")
    if sok:
        display_df = display_df[display_df.astype(str).apply(lambda x: x.str.contains(sok, case=False)).any(axis=1)]

    for i, rad in display_df.iterrows():
        # Fargekode basert på status
        status_txt = rad['Behandlings_Status']
        header_label = f"📁 {rad['Hovedsøker']} | Agent: {rad['Registrert_Av']}"
        
        with st.expander(header_label):
            c1, c2, c3 = st.columns(3)
            with c1:
                st.write(f"**Produkt:** {rad['Produkt']}")
                st.write(f"**Beløp:** {rad['Beløp']:,} kr")
            with c2:
                st.write(f"**Bank:** {rad['Bank_Navn']}")
                st.write(f"**Prosess:** {rad['Behandlings_Status']}")
            with c3:
                st.write(f"**Registrert av:** {rad['Registrert_Av']}")
                st.write(f"**Dato:** {rad['Dato']}")
            
            st.info(f"**Agent Notat:** {rad['Notater']}")
            
            # Vedlegg Nedlasting
            vedlegg = str(rad['Vedlegg_Sti'])
            if vedlegg and vedlegg != "nan":
                for fn in vedlegg.split(","):
                    fpath = os.path.join(DOCS_DIR, fn)
                    if os.path.exists(fpath):
                        with open(fpath, "rb") as dl:
                            st.download_button(f"📥 Last ned {fn.split('_', 1)[-1]}", dl, file_name=fn, key=f"dl_{i}_{fn}")

            # ADMIN UPDATE SYSTEM
            if role == "Admin":
                st.divider()
                st.subheader("⚙️ Oppdater prosess for Agent")
                with st.form(f"admin_upd_{i}"):
                    u_bank = st.text_input("Hvilken bank er saken sendt til?", value=rad['Bank_Navn'])
                    u_status = st.selectbox("Statusoppdatering", [
                        "Venter på Admin", "Sak opprettet i Bank", "Dokumenter sendt", 
                        "Bank behandler", "Mangler info fra kunde", "Godkjent", "Avslått"
                    ], index=0)
                    if st.form_submit_button("Oppdater Agent"):
                        df.at[i, 'Bank_Navn'] = u_bank
                        df.at[i, 'Behandlings_Status'] = u_status
                        df.to_csv(DB_FILE, index=False)
                        st.success("Agent er oppdatert!")
                        st.rerun()

# --- SECTION 4: MASTER KONTROLLPANEL ---
elif valg == "🕵️ Master Kontrollpanel" and role == "Admin":
    st.header("🕵️ Master Kontrollpanel")
    t1, t2, t3 = st.tabs(["👥 Agentstyring", "📑 Agentinfo", "🛡️ Sikkerhetslogger"])
    
    with t1:
        st.subheader("Opprett ny Agent/Worker")
        new_u = st.text_input("Nytt Brukernavn").lower().strip()
        new_p = st.text_input("Nytt Passord")
        if st.button("Opprett"):
            u_df = pd.read_csv(USER_FILE)
            if new_u in u_df['username'].values: st.error("Eksisterer!")
            else:
                pd.DataFrame([{"username": new_u, "password": new_p, "role": "Worker"}]).to_csv(USER_FILE, mode='a', header=False, index=False)
                st.success(f"{new_u} er lagt til!")
        st.dataframe(pd.read_csv(USER_FILE))

    with t2:
        st.subheader("Agent detaljer")
        a_df = pd.read_csv(AGENT_RECORDS_FILE)
        st.dataframe(a_df)

    with t3:
        st.subheader("Sikkerhetslogger")
        log_df = pd.read_csv(LOG_FILE)
        # Sorter på Tidspunkt (Tidspunkt column is fixed now)
        st.dataframe(log_df.sort_values("Tidspunkt", ascending=False), use_container_width=True)
