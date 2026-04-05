import streamlit as st
import pandas as pd
import os
from datetime import datetime
from streamlit_js_eval import get_geolocation

# --- 1. KONFIGURASJON ---
st.set_page_config(page_title="NSVG Digital Bank Portal", page_icon="🛡️", layout="wide")

# Custom CSS for Professional Look
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

# --- 2. DATABASE & FILE MANAGEMENT ---
DB_FILE = "nsvg_database_pro.csv"
LOG_FILE = "nsvg_security_logs.csv"
DOCS_DIR = "nsvg_vedlegg"
USER_FILE = "nsvg_users.csv"
AGENT_RECORDS_FILE = "nsvg_agent_management.csv"

if not os.path.exists(DOCS_DIR): os.makedirs(DOCS_DIR)

def initialize_files():
    if not os.path.exists(USER_FILE):
        pd.DataFrame([
            {"username": "admin", "password": "NSVG2026", "role": "Admin"},
            {"username": "amina", "password": "aminaaz0207", "role": "Worker"},
            {"username": "umer", "password": "Umer2026", "role": "Worker"}
        ]).to_csv(USER_FILE, index=False)

    required_cols = ["ID", "Dato", "Produkt", "Hovedsøker", "Fnr", "Beløp", "Status", "Notater", "Vedlegg_Sti", "Registrert_Av", "Bank_Navn", "Behandlings_Status"]
    if not os.path.exists(DB_FILE):
        pd.DataFrame(columns=required_cols).to_csv(DB_FILE, index=False)

    if not os.path.exists(AGENT_RECORDS_FILE):
        pd.DataFrame(columns=["username", "full_name", "rank", "duty_time", "invoice_status", "contract"]).to_csv(AGENT_RECORDS_FILE, index=False)

    if not os.path.exists(LOG_FILE):
        pd.DataFrame(columns=["Tidspunkt", "Bruker", "Handling", "Kart_Lenke"]).to_csv(LOG_FILE, index=False)

initialize_files()

def record_log(user, loc_data, action):
    try:
        lat = loc_data['coords']['latitude'] if loc_data else "N/A"
        lon = loc_data['coords']['longitude'] if loc_data else "N/A"
    except: lat, lon = "N/A", "N/A"
    maps_url = f"https://www.google.com/maps?q={lat},{lon}" if lat != "N/A" else "Ingen"
    new_log = {"Tidspunkt": datetime.now().strftime("%d-%m-%Y %H:%M:%S"), "Bruker": user, "Handling": action, "Kart_Lenke": maps_url}
    pd.DataFrame([new_log]).to_csv(LOG_FILE, mode='a', header=False, index=False)

# --- 3. LOGIN & AUTHENTICATION ---
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
        else:
            st.error("Feil brukernavn eller passord!")
    st.stop()

# --- 4. NAVIGATION ---
df = pd.read_csv(DB_FILE)
role = st.session_state['user_role']
current_user = st.session_state['user_id']
display_df = df if role == "Admin" else df[df['Registrert_Av'] == current_user]

st.sidebar.title(f"👤 {current_user.capitalize()}")
menu = ["📊 Dashbord", "➕ Ny Registrering", "📂 Kunde Arkiv"]
if role == "Admin": 
    menu.append("🕵️ Master Kontrollpanel")
    menu.append("👥 Ansatte Kontroll") # Naya Section
valg = st.sidebar.selectbox("Hovedmeny", menu)

if st.sidebar.button("🔴 Logg ut"):
    st.session_state.clear()
    st.rerun()

# --- SECTION: DASHBORD ---
if valg == "📊 Dashbord":
    st.header(f"Oversikt - {current_user.capitalize()}")
    c1, c2 = st.columns(2)
    with c1: st.metric("Aktive Saker", len(display_df))
    with c2:
        volum = pd.to_numeric(display_df['Beløp'], errors='coerce').sum()
        st.metric("Totalt Volum (kr)", f"{volum:,} kr")
    st.divider()
    st.subheader("Siste aktiviteter")
    st.dataframe(display_df.tail(10), use_container_width=True)

# --- SECTION: NY REGISTRERING ---
elif valg == "➕ Ny Registrering":
    st.header("➕ Opprett Ny Bankforespørsel")
    prod = st.selectbox("Bankprodukt", ["Boliglån", "Refinansiering", "Mellomfinansiering", "Investlån / Bedrift", "Byggelån", "Forbrukslån", "Billån"])
    is_bedrift = "Investlån" in prod
    has_medsoker = False if is_bedrift else (st.radio("Søknadstype", ["Alene søker", "Med-søker / Kausjonist"]) == "Med-søker / Kausjonist")

    with st.form("nsvg_bank_form"):
        st.subheader("👤 Kunde Informasjon")
        c1, c2 = st.columns(2)
        with c1:
            navn = st.text_input("Fullt Navn")
            fnr = st.text_input("Fødselsnummer")
            epost = st.text_input("E-post")
        with c2:
            lonn = st.number_input("Årslønn Brutto (kr)", min_value=0)
            belop_sokt = st.number_input("Søknadsbeløp (kr)", min_value=0)
        
        notater_input = st.text_area("Interne notater")
        if st.form_submit_button("SEND SØKNAD"):
            new_entry = {
                "ID": len(df) + 1, "Dato": datetime.now().strftime("%d-%m-%Y"),
                "Produkt": prod, "Hovedsøker": navn, "Fnr": fnr, "Beløp": belop_sokt,
                "Status": "Mottatt", "Notater": notater_input, "Vedlegg_Sti": "",
                "Registrert_Av": current_user, "Bank_Navn": "Vurderes", "Behandlings_Status": "Mottatt"
            }
            pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True).to_csv(DB_FILE, index=False)
            st.success("✅ Søknad registrert!")

# --- SECTION: KUNDE ARKIV ---
elif valg == "📂 Kunde Arkiv":
    st.header("📂 Kunde Arkiv")
    sok = st.text_input("Søk på Navn")
    res_df = display_df[display_df['Hovedsøker'].str.contains(sok, case=False)] if sok else display_df
    st.dataframe(res_df, use_container_width=True)

# --- NEW SECTION: ANSATTE KONTROLL (THE CRM MASTER) ---
elif valg == "👥 Ansatte Kontroll" and role == "Admin":
    st.header("👥 Ansatte & Worker Management")
    
    # Files Refresh
    users_list = pd.read_csv(USER_FILE)
    agents_list = pd.read_csv(AGENT_RECORDS_FILE)
    logs_data = pd.read_csv(LOG_FILE)
    
    workers = users_list[users_list['role'] == 'Worker']
    
    if workers.empty:
        st.info("Ingen arbeidere funnet i systemet.")
    else:
        for idx, worker in workers.iterrows():
            username = worker['username']
            
            # Get Agent Details
            agent_detail = agents_list[agents_list['username'] == username]
            full_name = agent_detail['full_name'].values[0] if not agent_detail.empty else username.capitalize()
            rank = agent_detail['rank'].values[0] if not agent_detail.empty else "Worker"
            
            with st.expander(f"👤 {full_name} (@{username}) - {rank}"):
                col1, col2, col3 = st.columns(3)
                
                # Column 1: Performance
                with col1:
                    worker_cases = df[df['Registrert_Av'] == username]
                    st.metric("Saker Registrert", len(worker_cases))
                    total_vol = pd.to_numeric(worker_cases['Beløp'], errors='coerce').sum()
                    st.write(f"**Total Volum:** {total_vol:,} kr")
                
                # Column 2: Last Activities
                with col2:
                    st.write("**Siste Login Aktivitet:**")
                    worker_logs = logs_data[logs_data['Bruker'] == username].tail(3)
                    if not worker_logs.empty:
                        for _, l in worker_logs.iterrows():
                            st.caption(f"🕒 {l['Tidspunkt']} - {l['Handling']}")
                    else:
                        st.write("Ingen logg funnet.")
                
                # Column 3: Control Actions
                with col3:
                    st.write("**System Kontroll:**")
                    if st.button(f"Slett {username} helt", key=f"del_{username}"):
                        # Delete from Users
                        new_u = users_list[users_list['username'] != username]
                        new_u.to_csv(USER_FILE, index=False)
                        # Delete from Agent Management
                        new_a = agents_list[agents_list['username'] != username]
                        new_a.to_csv(AGENT_RECORDS_FILE, index=False)
                        st.error(f"{username} slettet fra databasen!")
                        st.rerun()

                st.divider()
                st.write("**Arbeidshistorikk (Siste 5 saker):**")
                st.table(worker_cases[['Dato', 'Hovedsøker', 'Produkt', 'Beløp', 'Behandlings_Status']].tail(5))

# --- SECTION: MASTER KONTROLLPANEL ---
elif valg == "🕵️ Master Kontrollpanel" and role == "Admin":
    st.header("🕵️ System Kontroll")
    tab1, tab2, tab3 = st.tabs(["➕ Opprett Agent", "🛡️ Logger", "📊 Statistikk"])

    with tab1:
        st.subheader("Lag ny tilgang")
        with st.form("new_agent_form"):
            new_u = st.text_input("Brukernavn").lower().strip()
            new_p = st.text_input("Passord")
            full_n = st.text_input("Fullt Navn")
            rank = st.selectbox("Stilling", ["Junior Agent", "Senior Agent", "Partner"])
            if st.form_submit_button("AKTIVER AGENT"):
                pd.DataFrame([{"username": new_u, "password": new_p, "role": "Worker"}]).to_csv(USER_FILE, mode='a', header=False, index=False)
                pd.DataFrame([{"username": new_u, "full_name": full_n, "rank": rank, "duty_time": "N/A", "invoice_status": "Active", "contract": "Signed"}]).to_csv(AGENT_RECORDS_FILE, mode='a', header=False, index=False)
                st.success(f"Agent {full_n} er aktivert!")
                st.rerun()

    with tab2:
        st.dataframe(pd.read_csv(LOG_FILE).sort_values("Tidspunkt", ascending=False), use_container_width=True)

    with tab3:
        st.bar_chart(df['Registrert_Av'].value_counts())
