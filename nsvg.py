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

# --- 2. DATABASE LOGIC ---
DB_FILE = "nsvg_database_pro.csv"
LOG_FILE = "nsvg_security_logs.csv"
DOCS_DIR = "nsvg_vedlegg"
USER_FILE = "nsvg_users.csv"
AGENT_RECORDS_FILE = "nsvg_agent_management.csv" # New Feature File

if not os.path.exists(DOCS_DIR): os.makedirs(DOCS_DIR)

# --- AUTOMATIC LOGIN REPAIR & INITIALIZATION ---
def initialize_files():
    # Force fix for the 'role' column error
    if os.path.exists(USER_FILE):
        u_temp = pd.read_csv(USER_FILE)
        if 'role' not in u_temp.columns:
            os.remove(USER_FILE) # Purani kharab file delete karo
    
    if not os.path.exists(USER_FILE):
        pd.DataFrame([
            {"username": "admin", "password": "NSVG2026", "role": "Admin"},
            {"username": "amina", "password": "aminaaz0207", "role": "Worker"},
            {"username": "umer", "password": "Umer2026", "role": "Worker"},
            {"username": "ali", "password": "AliPass123", "role": "Worker"},
            {"username": "awari3600", "password": "Awari@9204", "role": "Worker"}
        ]).to_csv(USER_FILE, index=False)
    
    if not os.path.exists(AGENT_RECORDS_FILE):
        pd.DataFrame(columns=["username", "full_name", "rank", "duty_time", "invoice_status", "contract"]).to_csv(AGENT_RECORDS_FILE, index=False)

initialize_files()

def get_users_df():
    return pd.read_csv(USER_FILE)

def record_log(user, loc_data, action):
    try:
        lat = loc_data['coords']['latitude'] if loc_data else "N/A"
        lon = loc_data['coords']['longitude'] if loc_data else "N/A"
    except: lat, lon = "N/A", "N/A"
    maps_url = f"https://www.google.com/maps?q={lat},{lon}" if lat != "N/A" else "No Location"
    new_log = {"Timestamp": datetime.now().strftime("%d-%m-%Y %H:%M:%S"), "Bruker": user, "Handling": action, "Maps Link": maps_url}
    pd.DataFrame([new_log]).to_csv(LOG_FILE, mode='a', header=not os.path.exists(LOG_FILE), index=False)

# --- 3. INNLOGGING SYSTEM ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user_role': None, 'user_id': None})

if not st.session_state['logged_in']:
    st.title("🛡️ NSVG - Sikker Digital Portal")
    st.info("⚠️ Security: Klikk 'Allow' på posisjon øverst.")
    loc = get_geolocation()
    u_input = st.text_input("Brukernavn (User ID)").lower().strip()
    p_input = st.text_input("Passord", type="password")
    
    if st.button("Logg inn"):
        users_df = get_users_df()
        user_match = users_df[(users_df['username'] == u_input) & (users_df['password'] == p_input)]
        
        if not user_match.empty:
            role_found = user_match.iloc[0]['role']
            st.session_state.update({'logged_in': True, 'user_role': role_found, 'user_id': u_input})
            record_log(u_input, loc, "Innlogging suksess")
            st.rerun()
        else:
            st.error("Feil brukernavn eller passord!")
    st.stop()

# --- 4. MAIN APP ---
if not os.path.exists(DB_FILE):
    pd.DataFrame(columns=["ID", "Dato", "Produkt", "Hovedsøker", "Fnr", "Beløp", "Status", "Notater", "Vedlegg_Sti", "Registrert_Av"]).to_csv(DB_FILE, index=False)

df = pd.read_csv(DB_FILE)
role = st.session_state['user_role']
current_user = st.session_state['user_id']
display_df = df[df['Registrert_Av'] == current_user] if role == "Worker" else df

st.sidebar.title(f"👤 {current_user.capitalize()}")
menu_options = ["📊 Dashbord", "➕ Registrer ny søknad", "📂 Kunde Arkiv"]
if role == "Admin": menu_options.append("🕵️ Master Kontrollpanel")
valg = st.sidebar.selectbox("Hovedmeny", menu_options)

if st.sidebar.button("🔴 Logg ut"):
    st.session_state.clear()
    st.rerun()

# --- SECTION 1: DASHBORD ---
if valg == "📊 Dashbord":
    st.header(f"📊 Dashboard - {current_user.capitalize()}")
    col1, col2 = st.columns(2)
    with col1:
        total_volum = pd.to_numeric(display_df['Beløp'], errors='coerce').sum()
        st.metric("Ditt Volum (kr)", f"{total_volum:,} kr")
    with col2:
        st.metric("Dine aktive saker", len(display_df))
    st.divider()
    st.dataframe(display_df.tail(15), use_container_width=True)

# --- SECTION 2: REGISTRER NY SØKNAD (Vohi Detailed Form) ---
elif valg == "➕ Registrer ny søknad":
    st.header("➕ Opprett Ny Bankforespørsel")
    prod = st.selectbox("Velg ønsket bankprodukt", [
        "1. Boliglån", "2. Boliglån Refinansiering", "3. Mellomfinansiering", 
        "4. Investlån / Bedriftslån / Leasing", "5. Byggelån", "6. Forbrukslån", "7. Billån"
    ])

    is_bedrift = "Investlån" in prod
    has_medsoker = False
    if not is_bedrift:
        has_medsoker = st.radio("Søknadstype", ["Alene søker", "Med-søker / Kausjonist"]) == "Med-søker / Kausjonist"

    with st.form("nsvg_bank_skjema"):
        st.subheader("👤 Informasjon om Hovedsøker")
        c1, c2 = st.columns(2)
        with c1:
            navn = st.text_input("Fullt Navn (ihht ID)")
            fnr = st.text_input("Fødselsnummer (11 siffer)")
            epost = st.text_input("E-postadresse")
            tlf = st.text_input("Telefonnummer")
        with c2:
            sivil = st.selectbox("Sivilstatus", ["Gift", "Samboer", "Enslig", "Skilt/Separert"])
            jobb = st.selectbox("Arbeidsstatus", ["Fast ansatt", "Midlertidig", "AAP", "Uføretrygd", "Arbeidsledig", "Selvstendig næringsdrivende"])
            sektor = st.selectbox("Arbeidssektor", ["Privat sektor", "Offentlig/Statlig", "Kommunal"])
            firma = st.text_input("Navn na arbeidsgiver / Firma")
            ansatt_tid = st.text_input("Hvor lenge har du jobbet der?")
            lonn = st.number_input("Årslønn før skatt (Brutto)", min_value=0)

        st.divider()
        st.subheader(f"📑 Spesifikke krav for {prod}")
        # ... (Same detailed logic from your previous code)
        if "Boliglån" in prod or "Mellomfinansiering" in prod:
            k1, k2 = st.columns(2)
            with k1:
                barn = st.number_input("Antall barn under 18 år", min_value=0)
                sfo = st.selectbox("Går barn i SFO/Barnehage?", ["Nei", "Ja"])
                ek = st.number_input("Egenkapital (kr)", min_value=0)
                ek_kilde = st.text_input("Kilde til egenkapital")
                omrade = st.text_input("Ønsket område for boligkjøp")
            with k2:
                gjeld = st.number_input("Annen gjeld (Forbrukslån/Kreditt)", min_value=0)
                ramme = st.number_input("Samlet ramme na kredittkort", min_value=0)
                biler = st.number_input("Antall biler i husholdningen", min_value=0)
                billan = st.number_input("Restgjeld billån", min_value=0)
                utleie = st.selectbox("Skal boligen ha utleiedel?", ["Nei", "Ja"])

        if st.form_submit_button("SEND INN SØKNAD TIL VAULT"):
            # Registration Logic
            new_entry = {
                "ID": len(df) + 1, "Dato": datetime.now().strftime("%d-%m-%Y"),
                "Produkt": prod, "Hovedsøker": navn, "Fnr": fnr, "Beløp": total_belop if 'total_belop' in locals() else 0,
                "Status": "Til vurdering", "Notater": "Søknad sendt", 
                "Vedlegg_Sti": "", "Registrert_Av": current_user
            }
            pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True).to_csv(DB_FILE, index=False)
            st.success(f"✅ Søknad arkivert!")

# --- SECTION 3: KUNDE ARKIV ---
elif valg == "📂 Kunde Arkiv":
    st.header(f"📂 Arkiv - {current_user.capitalize()}")
    sok = st.text_input("Søk i arkivet (Navn eller Fnr)")
    res_df = display_df[display_df.astype(str).apply(lambda x: x.str.contains(sok, case=False)).any(axis=1)] if sok else display_df
    st.dataframe(res_df, use_container_width=True)

# --- SECTION 4: MASTER KONTROLLPANEL (The Missing Piece) ---
elif valg == "🕵️ Master Kontrollpanel" and role == "Admin":
    st.header("🕵️ Master Kontrollpanel")
    t1, t2, t3 = st.tabs(["👥 Agent Management", "📑 Agent Records", "🛡️ Sikkerhetslogger"])
    
    with t1:
        st.subheader("Add New Worker")
        new_u = st.text_input("New Username").lower().strip()
        new_p = st.text_input("New Password")
        if st.button("Create Worker"):
            u_df = get_users_df()
            if new_u in u_df['username'].values: st.error("Exists!")
            else:
                pd.DataFrame([{"username": new_u, "password": new_p, "role": "Worker"}]).to_csv(USER_FILE, mode='a', header=False, index=False)
                st.success(f"User {new_u} created!")
        st.dataframe(get_users_df())

    with t2:
        st.subheader("Manage Agent Profiles")
        a_df = pd.read_csv(AGENT_RECORDS_FILE)
        with st.form("agent_data"):
            u_select = st.selectbox("Select Agent", get_users_df()['username'].unique())
            f_name = st.text_input("Asli Naam (Full Name)")
            u_rank = st.selectbox("Level", ["Junior", "Senior", "Partner"])
            u_time = st.text_input("Duty Timing (e.g. 09-17)")
            u_inv = st.selectbox("Invoice Status", ["Paid", "Pending"])
            u_contract = st.text_area("Contract (Avtale) Details")
            if st.form_submit_button("Update Record"):
                a_df = a_df[a_df['username'] != u_select]
                new_data = {"username": u_select, "full_name": f_name, "rank": u_rank, "duty_time": u_time, "invoice_status": u_inv, "contract": u_contract}
                pd.concat([a_df, pd.DataFrame([new_data])]).to_csv(AGENT_RECORDS_FILE, index=False)
                st.success("Record Updated!")
        st.dataframe(a_df)

    with t3:
        if os.path.exists(LOG_FILE):
            st.dataframe(pd.read_csv(LOG_FILE).sort_values("Timestamp", ascending=False))
