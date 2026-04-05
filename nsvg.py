import streamlit as st
import pandas as pd
import os
from datetime import datetime
from streamlit_js_eval import get_geolocation

# --- 1. CONFIG & STYLE ---
st.set_page_config(
    page_title="NSVG Digital Bank Portal", 
    page_icon="🛡️", 
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "# NSVG CRM v3.0\nYeh portal professional management ke liye banaya gaya hai."
    }
)

# Advanced CSS: Hide Streamlit branding and style sidebar
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display:none;}
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
USER_FILE = "nsvg_users.csv"
AGENT_RECORDS_FILE = "nsvg_agent_management.csv" # New file for Avtaler, Invoices, etc.
DOCS_DIR = "nsvg_vedlegg"

if not os.path.exists(DOCS_DIR): os.makedirs(DOCS_DIR)

# Initialize Files
def init_files():
    if not os.path.exists(USER_FILE):
        pd.DataFrame([
            {"username": "admin", "password": "NSVG2026", "role": "Admin"},
            {"username": "amina", "password": "aminaaz0207", "role": "Worker"},
            {"username": "umer", "password": "Umer2026", "role": "Worker"},
            {"username": "awari3600", "password": "Awari@9204", "role": "Worker"}
        ]).to_csv(USER_FILE, index=False)
    
    if not os.path.exists(DB_FILE):
        pd.DataFrame(columns=["ID", "Dato", "Produkt", "Hovedsøker", "Fnr", "Beløp", "Status", "Notater", "Vedlegg_Sti", "Registrert_Av"]).to_csv(DB_FILE, index=False)
        
    if not os.path.exists(AGENT_RECORDS_FILE):
        pd.DataFrame(columns=["username", "full_navn", "avtale_info", "time_table", "invoice_status", "rang"]).to_csv(AGENT_RECORDS_FILE, index=False)

init_files()

def get_users_df():
    return pd.read_csv(USER_FILE)

def record_log(user, loc_data, action):
    try:
        lat = loc_data['coords']['latitude'] if loc_data else "N/A"
        lon = loc_data['coords']['longitude'] if loc_data else "N/A"
    except: lat, lon = "N/A", "N/A"
    maps_url = f"https://www.google.com/maps?q={lat},{lon}"
    new_log = {"Timestamp": datetime.now().strftime("%d-%m-%Y %H:%M:%S"), "Bruker": user, "Handling": action, "Maps Link": maps_url}
    pd.DataFrame([new_log]).to_csv(LOG_FILE, mode='a', header=not os.path.exists(LOG_FILE), index=False)

# --- 3. LOGIN SYSTEM ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user_role': None, 'user_id': None})

if not st.session_state['logged_in']:
    st.title("🛡️ NSVG - Sikker Digital Portal")
    loc = get_geolocation()
    u_input = st.text_input("Brukernavn").lower().strip()
    p_input = st.text_input("Passord", type="password")
    
    if st.button("Logg inn"):
        df_u = get_users_df()
        user_match = df_u[(df_u['username'] == u_input) & (df_u['password'] == p_input)]
        
        if not user_match.empty:
            st.session_state.update({
                'logged_in': True, 
                'user_role': user_match.iloc[0]['role'], 
                'user_id': u_input
            })
            record_log(u_input, loc, "Innlogging suksess")
            st.rerun()
        else:
            st.error("Feil brukernavn eller passord!")
    st.stop()

# --- 4. DATA LOADING ---
df = pd.read_csv(DB_FILE)
role = st.session_state['user_role']
current_user = st.session_state['user_id']

# Sidebar Navigation
st.sidebar.title(f"👤 {current_user.capitalize()}")
menu_options = ["📊 Dashbord", "➕ Registrer ny søknad", "📂 Kunde Arkiv"]
if role == "Admin": menu_options.append("🕵️ Master Kontrollpanel")
valg = st.sidebar.selectbox("Hovedmeny", menu_options)

if st.sidebar.button("🔴 Logg ut"):
    st.session_state.clear()
    st.rerun()

# --- SECTION 1: DASHBORD ---
if valg == "📊 Dashbord":
    st.header(f"📊 Dashboard")
    display_df = df[df['Registrert_Av'] == current_user] if role == "Worker" else df
    col1, col2 = st.columns(2)
    with col1:
        total_volum = pd.to_numeric(display_df['Beløp'], errors='coerce').sum()
        st.metric("Total Volum (kr)", f"{total_volum:,} kr")
    with col2:
        st.metric("Aktive saker", len(display_df))
    st.divider()
    st.subheader("Siste registreringer")
    st.dataframe(display_df.tail(10), use_container_width=True)

# --- SECTION 2: REGISTRER NY SØKNAD ---
elif valg == "➕ Registrer ny søknad":
    st.header("➕ Opprett Ny Bankforespørsel")
    prod = st.selectbox("Velg bankprodukt", ["Boliglån", "Refinansiering", "Mellomfinansiering", "Bedriftslån", "Forbrukslån", "Billån"])
    
    with st.form("nsvg_bank_skjema"):
        c1, c2 = st.columns(2)
        with c1:
            navn = st.text_input("Fullt Navn")
            fnr = st.text_input("Fødselsnummer (11 siffer)")
            epost = st.text_input("E-post")
        with c2:
            lonn = st.number_input("Årslønn (Brutto)", min_value=0)
            total_belop = st.number_input("Søknadsbeløp (kr)", min_value=0)
        
        notater_input = st.text_area("Notater / Kommentarer")
        opplastede_filer = st.file_uploader("Last opp dokumenter", accept_multiple_files=True)
        
        if st.form_submit_button("SEND INN SØKNAD"):
            fil_liste = []
            for fil in opplastede_filer:
                ren_filnavn = f"{fnr}_{fil.name}".replace(" ", "_")
                with open(os.path.join(DOCS_DIR, ren_filnavn), "wb") as f:
                    f.write(fil.getbuffer())
                fil_liste.append(ren_filnavn)
            
            new_entry = {
                "ID": len(df) + 1, "Dato": datetime.now().strftime("%d-%m-%Y"),
                "Produkt": prod, "Hovedsøker": navn, "Fnr": fnr, "Beløp": total_belop,
                "Status": "Til vurdering", "Notater": notater_input, 
                "Vedlegg_Sti": ",".join(fil_liste), "Registrert_Av": current_user
            }
            pd.DataFrame([new_entry]).to_csv(DB_FILE, mode='a', header=False, index=False)
            st.success("✅ Søknad er sendt!")

# --- SECTION 3: KUNDE ARKIV ---
elif valg == "📂 Kunde Arkiv":
    st.header("📂 Arkiv")
    display_df = df[df['Registrert_Av'] == current_user] if role == "Worker" else df
    sok = st.text_input("Søk Navn eller Fnr")
    if sok:
        display_df = display_df[display_df.astype(str).apply(lambda x: x.str.contains(sok, case=False)).any(axis=1)]

    for i, rad in display_df.iterrows():
        with st.expander(f"📁 {rad['Hovedsøker']} - {rad['Produkt']}"):
            st.write(f"**Beløp:** {rad['Beløp']:,} kr | **Status:** {rad['Status']}")
            st.write(f"**Notater:** {rad['Notater']}")
            vedlegg = str(rad['Vedlegg_Sti'])
            if vedlegg != "nan" and vedlegg != "":
                for f_name in vedlegg.split(","):
                    st.download_button(f"📥 {f_name}", open(os.path.join(DOCS_DIR, f_name), "rb"), file_name=f_name)

# --- SECTION 4: MASTER KONTROLLPANEL (The Pro Section) ---
elif valg == "🕵️ Master Kontrollpanel" and role == "Admin":
    st.header("🕵️ Admin Master Control")
    t1, t2, t3 = st.tabs(["👥 Agent Management", "📑 Agent Records", "🛡️ Security Logs"])
    
    with t1:
        st.subheader("Add/Edit Agents")
        with st.expander("➕ Create New Agent"):
            new_user = st.text_input("New Username").lower().strip()
            new_pass = st.text_input("New Password")
            if st.button("Save New Agent"):
                u_df = pd.read_csv(USER_FILE)
                if new_user in u_df['username'].values:
                    st.error("User already exists!")
                else:
                    new_line = pd.DataFrame([{"username": new_user, "password": new_pass, "role": "Worker"}])
                    new_line.to_csv(USER_FILE, mode='a', header=False, index=False)
                    st.success("Agent created!")

        st.divider()
        st.write("All Active Users")
        st.dataframe(pd.read_csv(USER_FILE), use_container_width=True)

    with t2:
        st.subheader("Worker Tilgang & Management (Invoices, Avtaler, Ranks)")
        agent_df = pd.read_csv(AGENT_RECORDS_FILE)
        
        with st.form("agent_record_form"):
            target_agent = st.selectbox("Select Agent", pd.read_csv(USER_FILE)['username'].unique())
            a_navn = st.text_input("Fullt Navn")
            a_avtale = st.text_area("Avtale Detail (Contract)")
            a_time = st.text_input("Time Table (e.g. 08:00 - 16:00)")
            a_rank = st.selectbox("Rang (Level)", ["Junior", "Senior", "Master", "Partner"])
            a_invoice = st.selectbox("Invoice Status", ["Paid", "Pending", "Overdue"])
            
            if st.form_submit_button("Update Agent Records"):
                # Remove old record if exists and add new
                agent_df = agent_df[agent_df['username'] != target_agent]
                new_rec = {
                    "username": target_agent, "full_navn": a_navn, 
                    "avtale_info": a_avtale, "time_table": a_time, 
                    "invoice_status": a_invoice, "rang": a_rank
                }
                agent_df = pd.concat([agent_df, pd.DataFrame([new_rec])], ignore_index=True)
                agent_df.to_csv(AGENT_RECORDS_FILE, index=False)
                st.success(f"Records updated for {target_agent}!")

        st.divider()
        st.write("Agent Directory")
        st.dataframe(agent_df, use_container_width=True)

    with t3:
        if os.path.exists(LOG_FILE):
            st.dataframe(pd.read_csv(LOG_FILE).sort_values("Timestamp", ascending=False), use_container_width=True)
