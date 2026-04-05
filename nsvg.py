import streamlit as st
import pandas as pd
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from streamlit_js_eval import get_geolocation

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="NSVG Digital Bank Portal", page_icon="🛡️", layout="wide")

# Custom CSS (Aapka original design)
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

# --- 2. GOOGLE SHEETS CONNECTION ---
def connect_to_gsheet(sheet_name):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        # Secrets se credentials uthana
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        # Sheet kholna
        return client.open("NSVG_CRM_Data").worksheet(sheet_name)
    except Exception as e:
        st.error(f"Database Connection Error: {e}")
        return None

# Helpers for Data
def get_data(sheet_name):
    sheet = connect_to_gsheet(sheet_name)
    if sheet:
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    return pd.DataFrame()

def add_data(sheet_name, row_dict):
    sheet = connect_to_gsheet(sheet_name)
    if sheet:
        sheet.append_row(list(row_dict.values()))

# --- 3. INITIALIZE (Files & Folder) ---
DOCS_DIR = "nsvg_vedlegg"
if not os.path.exists(DOCS_DIR): os.makedirs(DOCS_DIR)

# Note: Humne assume kiya hai ke aapne Google Sheet mein 4 tabs banaye hain:
# "Users", "MainDB", "Agents", "Logs"

# --- 4. LOGIN & AUTHENTICATION ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user_role': None, 'user_id': None})

if not st.session_state['logged_in']:
    st.title("🛡️ NSVG - Sikker Digital Portal")
    loc = get_geolocation()
    u_input = st.text_input("Brukernavn").lower().strip()
    p_input = st.text_input("Passord", type="password")
    
    if st.button("Logg inn"):
        users_df = get_data("Users") # Google Sheet se users uthana
        if not users_df.empty:
            match = users_df[(users_df['username'] == u_input) & (users_df['password'] == str(p_input))]
            if not match.empty:
                st.session_state.update({'logged_in': True, 'user_role': match.iloc[0]['role'], 'user_id': u_input})
                
                # Record Log to Google Sheet
                lat = loc['coords']['latitude'] if loc else "N/A"
                lon = loc['coords']['longitude'] if loc else "N/A"
                maps_url = f"https://www.google.com/maps?q={lat},{lon}" if lat != "N/A" else "Ingen"
                add_data("Logs", {
                    "Tidspunkt": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                    "Bruker": u_input, "Handling": "Innlogging suksess", "Kart_Lenke": maps_url
                })
                st.rerun()
            else:
                st.error("Feil brukernavn eller passord!")
    st.stop()

# --- 5. NAVIGATION ---
df = get_data("MainDB")
role = st.session_state['user_role']
current_user = st.session_state['user_id']
display_df = df if role == "Admin" else df[df['Registrert_Av'] == current_user]

st.sidebar.title(f"👤 {current_user.capitalize()}")
menu = ["📊 Dashbord", "➕ Ny Registrering", "📂 Kunde Arkiv"]
if role == "Admin": 
    menu.extend(["🕵️ Master Kontrollpanel", "👥 Ansatte Kontroll"])
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

# --- SECTION: NY REGISTRERING (Wahi aapka form) ---
elif valg == "➕ Ny Registrering":
    st.header("➕ Opprett Ny Bankforespørsel")
    prod = st.selectbox("Bankprodukt", ["Boliglån", "Refinansiering", "Mellomfinansiering", "Investlån / Bedrift", "Byggelån", "Forbrukslån", "Billån"])
    
    is_bedrift = "Investlån" in prod
    has_medsoker = False if is_bedrift else (st.radio("Søknadstype", ["Alene søker", "Med-søker / Kausjonist"]) == "Med-søker / Kausjonist")

    with st.form("nsvg_bank_form"):
        st.subheader("👤 Kunde Informasjon")
        c1, c2 = st.columns(2)
        with c1:
            navn = st.text_input("Fullt Navn (ihht ID)")
            fnr = st.text_input("Fødselsnummer (11 siffer)")
            epost = st.text_input("E-post")
            tlf = st.text_input("Telefonnummer")
        with c2:
            sivil = st.selectbox("Sivilstatus", ["Enslig", "Gift", "Samboer", "Skilt"])
            sektor = st.selectbox("Sektor", ["Privat", "Offentlig", "Statlig", "Kommunal"])
            jobb = st.selectbox("Arbeidsstatus", ["Fast ansatt", "Midlertidig", "AAP", "Uføre", "Selvstendig"])
            firma = st.text_input("Firma / Arbeidsgiver")
            lonn = st.number_input("Årslønn Brutto (kr)", min_value=0)

        st.divider()
        st.subheader("🏠 Finansiell Detaljer")
        k1, k2 = st.columns(2)
        with k1:
            barn = st.number_input("Barn under 18 år", min_value=0)
            sfo = st.selectbox("SFO/Barnehage?", ["Nei", "Ja"])
            ek = st.number_input("Egenkapital (kr)", min_value=0)
        with k2:
            gjeld = st.number_input("Annen gjeld (kr)", min_value=0)
            biler = st.number_input("Antall biler", min_value=0)
            belop_sokt = st.number_input("Søknadsbeløp (kr)", min_value=0)

        notater_input = st.text_area("Interne notater / Kommentarer")
        opplastede_filer = st.file_uploader("Last opp dokumenter", accept_multiple_files=True)

        if st.form_submit_button("SEND SØKNAD"):
            fil_liste = []
            if opplastede_filer:
                for fil in opplastede_filer:
                    fn = f"{fnr}_{fil.name}".replace(" ", "_")
                    with open(os.path.join(DOCS_DIR, fn), "wb") as f: f.write(fil.getbuffer())
                    fil_liste.append(fn)
            
            new_entry = {
                "ID": len(df) + 1, "Dato": datetime.now().strftime("%d-%m-%Y"),
                "Produkt": prod, "Hovedsøker": navn, "Fnr": fnr, "Beløp": belop_sokt,
                "Status": "Mottatt", "Notater": notater_input, "Vedlegg_Sti": ",".join(fil_liste),
                "Registrert_Av": current_user, "Bank_Navn": "Vurderes", "Behandlings_Status": "Mottatt"
            }
            # SAVE TO GOOGLE SHEET
            add_data("MainDB", new_entry)
            st.success("✅ Søknad er registrert i Cloud Database!")

# --- SECTION: KUNDE ARKIV ---
elif valg == "📂 Kunde Arkiv":
    st.header("📂 Kunde Arkiv (Cloud)")
    sok = st.text_input("Søk na Navn eller Fødselsnummer")
    res_df = display_df[display_df.astype(str).apply(lambda x: x.str.contains(sok, case=False)).any(axis=1)] if sok else display_df
    st.dataframe(res_df, use_container_width=True)

# --- SECTION: ANSATTE KONTROLL ---
elif valg == "👥 Ansatte Kontroll" and role == "Admin":
    st.header("👥 Worker Management")
    users_list = get_data("Users")
    logs_data = get_data("Logs")
    workers = users_list[users_list['role'] == 'Worker']
    
    if workers.empty:
        st.info("Ingen arbeidere registrert.")
    else:
        for idx, worker in workers.iterrows():
            uname = worker['username']
            with st.expander(f"👤 {uname.capitalize()}"):
                w_cases = df[df['Registrert_Av'] == uname]
                st.metric("Saker i Cloud", len(w_cases))
                st.dataframe(w_cases.tail(5), use_container_width=True)

# --- SECTION: MASTER KONTROLLPANEL ---
elif valg == "🕵️ Master Kontrollpanel" and role == "Admin":
    st.header("🕵️ System Kontroll")
    tab1, tab2 = st.tabs(["👥 Agentstyring", "🛡️ Cloud Logger"])

    with tab1:
        st.subheader("Opprett Ny Agent")
        with st.form("new_agent_form"):
            new_u = st.text_input("Brukernavn").lower().strip()
            new_p = st.text_input("Passord")
            if st.form_submit_button("AKTIVER AGENT"):
                add_data("Users", {"username": new_u, "password": new_p, "role": "Worker"})
                st.success(f"Agent {new_u} lagret i Google Sheets!")
                st.rerun()

    with tab2:
        st.dataframe(get_data("Logs").sort_values("Tidspunkt", ascending=False), use_container_width=True)
