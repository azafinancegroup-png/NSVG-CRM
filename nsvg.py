import streamlit as st
import pandas as pd
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from streamlit_js_eval import get_geolocation

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="NSVG Digital Bank Portal", page_icon="🛡️", layout="wide")

# Custom CSS
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
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open("NSVG_CRM_Data").worksheet(sheet_name)
    except Exception as e:
        return None

def get_data(sheet_name):
    sheet = connect_to_gsheet(sheet_name)
    if sheet:
        return pd.DataFrame(sheet.get_all_records())
    return pd.DataFrame()

def add_data(sheet_name, row_dict):
    sheet = connect_to_gsheet(sheet_name)
    if sheet:
        sheet.append_row(list(row_dict.values()))

# --- 3. LOGIN & AUTHENTICATION ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user_role': None, 'user_id': None})

if not st.session_state['logged_in']:
    st.title("🛡️ NSVG - Sikker Digital Portal")
    
    # Location Safety (Error Fix)
    loc = get_geolocation()
    
    u_input = st.text_input("Brukernavn").lower().strip()
    p_input = st.text_input("Passord", type="password")
    
    if st.button("Logg inn"):
        users_df = get_data("Users")
        if not users_df.empty:
            # Fixing data types for password comparison
            users_df['password'] = users_df['password'].astype(str)
            match = users_df[(users_df['username'] == u_input) & (users_df['password'] == str(p_input))]
            
            if not match.empty:
                st.session_state.update({'logged_in': True, 'user_role': match.iloc[0]['role'], 'user_id': u_input})
                
                # Safe Location Logging
                try:
                    lat = loc['coords']['latitude'] if (loc and 'coords' in loc) else "N/A"
                    lon = loc['coords']['longitude'] if (loc and 'coords' in loc) else "N/A"
                except:
                    lat, lon = "N/A", "N/A"
                
                maps_url = f"https://www.google.com/maps?q={lat},{lon}" if lat != "N/A" else "Ingen"
                
                add_data("Logs", {
                    "Tidspunkt": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                    "Bruker": u_input, "Handling": "Innlogging suksess", "Kart_Lenke": maps_url
                })
                st.rerun()
            else:
                st.error("Feil brukernavn eller passord!")
        else:
            st.error("Kunne ikke koble til databasen (Users tab mangler or er tom).")
    st.stop()

# --- 4. NAVIGATION & DASHBOARD (Aapka original system) ---
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

# --- DASHBORD SECTION ---
if valg == "📊 Dashbord":
    st.header(f"Oversikt - {current_user.capitalize()}")
    if not display_df.empty:
        c1, c2 = st.columns(2)
        with c1: st.metric("Aktive Saker", len(display_df))
        with c2:
            volum = pd.to_numeric(display_df['Beløp'], errors='coerce').sum()
            st.metric("Totalt Volum (kr)", f"{volum:,} kr")
        st.divider()
        st.subheader("Siste aktiviteter")
        st.dataframe(display_df.tail(10), use_container_width=True)
    else:
        st.info("Ingen data funnet i databasen.")

# --- NY REGISTRERING (Aapka Form) ---
elif valg == "➕ Ny Registrering":
    st.header("➕ Opprett Ny Bankforespørsel")
    prod = st.selectbox("Bankprodukt", ["Boliglån", "Refinansiering", "Mellomfinansiering", "Investlån / Bedrift", "Byggelån", "Forbrukslån", "Billån"])
    
    with st.form("nsvg_bank_form"):
        st.subheader("👤 Kunde Informasjon")
        navn = st.text_input("Fullt Navn (ihht ID)")
        fnr = st.text_input("Fødselsnummer (11 siffer)")
        belop_sokt = st.number_input("Søknadsbeløp (kr)", min_value=0)
        notater_input = st.text_area("Interne notater")

        if st.form_submit_button("SEND SØKNAD"):
            new_entry = {
                "ID": len(df) + 1, "Dato": datetime.now().strftime("%d-%m-%Y"),
                "Produkt": prod, "Hovedsøker": navn, "Fnr": fnr, "Beløp": belop_sokt,
                "Status": "Mottatt", "Notater": notater_input, "Vedlegg_Sti": "",
                "Registrert_Av": current_user, "Bank_Navn": "Vurderes", "Behandlings_Status": "Mottatt"
            }
            add_data("MainDB", new_entry)
            st.success("✅ Søknad er registrert!")

# --- ARKIV SECTION ---
elif valg == "📂 Kunde Arkiv":
    st.header("📂 Kunde Arkiv (Cloud)")
    sok = st.text_input("Søk na Navn eller Fødselsnummer")
    if not display_df.empty:
        res_df = display_df[display_df.astype(str).apply(lambda x: x.str.contains(sok, case=False)).any(axis=1)] if sok else display_df
        st.dataframe(res_df, use_container_width=True)

# --- MASTER KONTROLLPANEL ---
elif valg == "🕵️ Master Kontrollpanel" and role == "Admin":
    st.header("🕵️ System Kontroll")
    tab1, tab2 = st.tabs(["👥 Agentstyring", "🛡️ Cloud Logger"])
    with tab1:
        with st.form("new_agent"):
            new_u = st.text_input("Brukernavn").lower().strip()
            new_p = st.text_input("Passord")
            if st.form_submit_button("AKTIVER AGENT"):
                add_data("Users", {"username": new_u, "password": new_p, "role": "Worker"})
                st.success(f"Agent {new_u} lagret!")
    with tab2:
        st.dataframe(get_data("Logs"), use_container_width=True)
