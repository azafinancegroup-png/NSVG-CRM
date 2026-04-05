import streamlit as st
import pandas as pd
import os
from datetime import datetime
from streamlit_js_eval import get_geolocation

# --- 1. CONFIG & STYLE ---
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

# --- 2. DATABASE FILES ---
DB_FILE = "nsvg_database_pro.csv"
LOG_FILE = "nsvg_security_logs.csv"
DOCS_DIR = "nsvg_vedlegg"
USER_FILE = "nsvg_users.csv"
AGENT_RECORDS_FILE = "nsvg_agent_management.csv"

if not os.path.exists(DOCS_DIR): os.makedirs(DOCS_DIR)

# --- 3. AUTO-INITIALIZE (Zero Error Logic) ---
def init_system():
    # Login Users Initialization
    if not os.path.exists(USER_FILE):
        df_users = pd.DataFrame([
            {"username": "admin", "password": "NSVG2026", "role": "Admin"},
            {"username": "amina", "password": "aminaaz0207", "role": "Worker"},
            {"username": "umer", "password": "Umer2026", "role": "Worker"}
        ])
        df_users.to_csv(USER_FILE, index=False)
    
    # Main Database
    if not os.path.exists(DB_FILE):
        cols = ["ID", "Dato", "Produkt", "Hovedsøker", "Fnr", "Beløp", "Status", "Notater", "Vedlegg_Sti", "Registrert_Av", "Bank_Navn", "Behandlings_Status"]
        pd.DataFrame(columns=cols).to_csv(DB_FILE, index=False)

    # Agent Records
    if not os.path.exists(AGENT_RECORDS_FILE):
        cols = ["username", "full_name", "rank", "duty_time", "status", "contract"]
        pd.DataFrame(columns=cols).to_csv(AGENT_RECORDS_FILE, index=False)

    # Logs
    if not os.path.exists(LOG_FILE):
        pd.DataFrame(columns=["Tidspunkt", "Bruker", "Handling", "Kart_Lenke"]).to_csv(LOG_FILE, index=False)

init_system()

def record_log(user, loc_data, action):
    try:
        lat = loc_data['coords']['latitude'] if loc_data else "N/A"
        lon = loc_data['coords']['longitude'] if loc_data else "N/A"
    except: lat, lon = "N/A", "N/A"
    maps_url = f"https://www.google.com/maps?q={lat},{lon}" if lat != "N/A" else "Ingen Posisjon"
    new_log = {"Tidspunkt": datetime.now().strftime("%d-%m-%Y %H:%M:%S"), "Bruker": user, "Handling": action, "Kart_Lenke": maps_url}
    pd.DataFrame([new_log]).to_csv(LOG_FILE, mode='a', header=False, index=False)

# --- 4. AUTHENTICATION ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user_role': None, 'user_id': None})

if not st.session_state['logged_in']:
    st.title("🛡️ NSVG Digital Security Login")
    loc = get_geolocation()
    u_input = st.text_input("Brukernavn").lower().strip()
    p_input = st.text_input("Passord", type="password")
    
    if st.button("Logg inn"):
        users_df = pd.read_csv(USER_FILE)
        # matching logic
        match = users_df[(users_df['username'] == u_input) & (users_df['password'] == p_input)]
        if not match.empty:
            st.session_state.update({'logged_in': True, 'user_role': match.iloc[0]['role'], 'user_id': u_input})
            record_log(u_input, loc, "Logget inn")
            st.rerun()
        else:
            st.error("Ugyldig brukernavn eller passord.")
    st.stop()

# --- 5. APP INTERFACE ---
df_main = pd.read_csv(DB_FILE)
role = st.session_state['user_role']
current_user = st.session_state['user_id']
display_df = df_main if role == "Admin" else df_main[df_main['Registrert_Av'] == current_user]

st.sidebar.title(f"👤 {current_user.upper()}")
menu = ["📊 Dashbord", "➕ Ny Registrering", "📂 Kunde Arkiv"]
if role == "Admin": menu.append("🕵️ Master Kontroll")
valg = st.sidebar.selectbox("Navigasjon", menu)

if st.sidebar.button("🔴 Logg ut"):
    st.session_state.clear()
    st.rerun()

# --- DASHBORD ---
if valg == "📊 Dashbord":
    st.header(f"Velkommen, {current_user.capitalize()}")
    c1, c2 = st.columns(2)
    with c1: st.metric("Mine Saker", len(display_df))
    with c2: 
        v = pd.to_numeric(display_df['Beløp'], errors='coerce').sum()
        st.metric("Total Volum", f"{v:,} kr")
    st.divider()
    st.dataframe(display_df.tail(10), use_container_width=True)

# --- NY REGISTRERING (Full Norsk Detailed Form) ---
elif valg == "➕ Ny Registrering":
    st.header("➕ Registrer Ny Kunde")
    prod = st.selectbox("Velg Produkt", ["Boliglån", "Refinansiering", "Mellomfinansiering", "Investlån / Bedrift", "Forbrukslån", "Billån"])
    
    with st.form("reg_form"):
        col1, col2 = st.columns(2)
        with col1:
            navn = st.text_input("Fullt Navn")
            fnr = st.text_input("Fødselsnummer (11 siffer)")
            epost = st.text_input("E-post")
            tlf = st.text_input("Telefon")
        with col2:
            sivil = st.selectbox("Sivilstatus", ["Gift", "Samboer", "Enslig", "Skilt"])
            jobb = st.selectbox("Arbeid", ["Fast", "Midlertidig", "AAP", "Uføretrygd", "Selvstendig"])
            lonn = st.number_input("Årslønn Brutto", min_value=0)
            firma = st.text_input("Arbeidsgiver")

        st.divider()
        c3, c4 = st.columns(2)
        with c3:
            ek = st.number_input("Egenkapital", min_value=0)
            gjeld = st.number_input("Eksisterende Gjeld", min_value=0)
        with c4:
            belop = st.number_input("Søknadsbeløp", min_value=0)
            barn = st.number_input("Antall barn under 18", min_value=0)

        notat = st.text_area("Notater til saksbehandler")
        filer = st.file_uploader("Last opp vedlegg", accept_multiple_files=True)
        
        if st.form_submit_button("Send Søknad"):
            fil_str = []
            if filer:
                for f in filer:
                    fname = f"{fnr}_{f.name}".replace(" ", "_")
                    with open(os.path.join(DOCS_DIR, fname), "wb") as storage: storage.write(f.getbuffer())
                    fil_str.append(fname)
            
            new_data = {
                "ID": len(df_main)+1, "Dato": datetime.now().strftime("%d-%m-%Y"),
                "Produkt": prod, "Hovedsøker": navn, "Fnr": fnr, "Beløp": belop,
                "Status": "Mottatt", "Notater": notat, "Vedlegg_Sti": ",".join(fil_str),
                "Registrert_Av": current_user, "Bank_Navn": "Vurderes", "Behandlings_Status": "Venter"
            }
            pd.concat([df_main, pd.DataFrame([new_data])], ignore_index=True).to_csv(DB_FILE, index=False)
            st.success("Søknad registrert!")

# --- KUNDE ARKIV ---
elif valg == "📂 Kunde Arkiv":
    st.header("📂 Arkiv & Oppfølging")
    sok = st.text_input("Søk navn/fnr")
    filtered = display_df[display_df.astype(str).apply(lambda x: x.str.contains(sok, case=False)).any(axis=1)] if sok else display_df
    
    for i, rad in filtered.iterrows():
        with st.expander(f"📄 {rad['Hovedsøker']} ({rad['Produkt']})"):
            st.write(f"**Bank:** {rad['Bank_Navn']} | **Status:** {rad['Behandlings_Status']}")
            if role == "Admin":
                with st.form(f"upd_{i}"):
                    nb = st.text_input("Sett Bank", value=rad['Bank_Navn'])
                    ns = st.selectbox("Ny Status", ["Behandles", "Mangler Dok", "Godkjent", "Avslag"])
                    if st.form_submit_button("Oppdater"):
                        df_main.at[i, 'Bank_Navn'] = nb
                        df_main.at[i, 'Behandlings_Status'] = ns
                        df_main.to_csv(DB_FILE, index=False)
                        st.rerun()

# --- MASTER KONTROLL (The Core Management) ---
elif valg == "🕵️ Master Kontroll" and role == "Admin":
    st.header("🕵️ System Management")
    tab1, tab2 = st.tabs(["👥 Agentstyring", "🛡️ Logger"])
    
    with tab1:
        st.subheader("Opprett Ny Agent (Worker)")
        with st.form("agent_creation"):
            new_u = st.text_input("Agent Brukernavn (Login ID)").lower().strip()
            new_p = st.text_input("Passord")
            new_fn = st.text_input("Agent Fullt Navn")
            new_rank = st.selectbox("Rank", ["Junior", "Senior", "Partner"])
            
            if st.form_submit_button("🔥 AKTIVER AGENT"):
                u_df = pd.read_csv(USER_FILE)
                if new_u in u_df['username'].values:
                    st.error("Brukernavn er allerede tatt!")
                else:
                    # 1. Update Login File
                    new_login = pd.DataFrame([{"username": new_u, "password": new_p, "role": "Worker"}])
                    new_login.to_csv(USER_FILE, mode='a', header=False, index=False)
                    
                    # 2. Update Agent Records
                    new_rec = pd.DataFrame([{"username": new_u, "full_name": new_fn, "rank": new_rank, "duty_time": "0", "status": "Active", "contract": "Signed"}])
                    new_rec.to_csv(AGENT_RECORDS_FILE, mode='a', header=False, index=False)
                    
                    st.success(f"Agent {new_fn} er nå live!")
                    st.rerun()

        st.divider()
        st.subheader("Aktive Agenter")
        st.dataframe(pd.read_csv(AGENT_RECORDS_FILE), use_container_width=True)

    with tab2:
        st.subheader("Sikkerhetslogg (Geolocation Tracking)")
        st.dataframe(pd.read_csv(LOG_FILE).sort_values("Tidspunkt", ascending=False), use_container_width=True)
