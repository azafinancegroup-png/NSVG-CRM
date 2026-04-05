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

# --- 2. DATABASE LOGIKK ---
DB_FILE = "nsvg_database_pro.csv"
LOG_FILE = "nsvg_security_logs.csv"
DOCS_DIR = "nsvg_vedlegg"
USER_FILE = "nsvg_users.csv"
AGENT_RECORDS_FILE = "nsvg_agent_management.csv"

if not os.path.exists(DOCS_DIR): os.makedirs(DOCS_DIR)

def initialize_files():
    if os.path.exists(USER_FILE):
        u_temp = pd.read_csv(USER_FILE)
        if 'role' not in u_temp.columns:
            os.remove(USER_FILE) 
    
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

    if not os.path.exists(DB_FILE):
        # Naye columns: 'Bank_Navn' aur 'Behandlings_Status'
        pd.DataFrame(columns=["ID", "Dato", "Produkt", "Hovedsøker", "Fnr", "Beløp", "Status", "Notater", "Vedlegg_Sti", "Registrert_Av", "Bank_Navn", "Behandlings_Status"]).to_csv(DB_FILE, index=False)

initialize_files()

def get_users_df():
    return pd.read_csv(USER_FILE)

def record_log(user, loc_data, action):
    try:
        lat = loc_data['coords']['latitude'] if loc_data else "N/A"
        lon = loc_data['coords']['longitude'] if loc_data else "N/A"
    except: lat, lon = "N/A", "N/A"
    maps_url = f"https://www.google.com/maps?q={lat},{lon}" if lat != "N/A" else "Ingen lokasjon"
    new_log = {"Tidspunkt": datetime.now().strftime("%d-%m-%Y %H:%M:%S"), "Bruker": user, "Handling": action, "Kart_Lenke": maps_url}
    pd.DataFrame([new_log]).to_csv(LOG_FILE, mode='a', header=not os.path.exists(LOG_FILE), index=False)

# --- 3. INNLOGGINGSSYSTEM ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user_role': None, 'user_id': None})

if not st.session_state['logged_in']:
    st.title("🛡️ NSVG - Sikker Digital Portal")
    st.info("⚠️ Sikkerhet: Vennligst tillat posisjonstilgang.")
    loc = get_geolocation()
    u_input = st.text_input("Brukernavn").lower().strip()
    p_input = st.text_input("Passord", type="password")
    
    if st.button("Logg inn"):
        users_df = get_users_df()
        user_match = users_df[(users_df['username'] == u_input) & (users_df['password'] == p_input)]
        
        if not user_match.empty:
            role_found = user_match.iloc[0]['role']
            st.session_state.update({'logged_in': True, 'user_role': role_found, 'user_id': u_input})
            record_log(u_input, loc, "Innlogging vellykket")
            st.rerun()
        else:
            st.error("Feil brukernavn eller passord!")
    st.stop()

# --- 4. HOVEDDATA ---
df = pd.read_csv(DB_FILE)
role = st.session_state['user_role']
current_user = st.session_state['user_id']

# Admin ser alt, Worker ser bare sine egne saker
display_df = df if role == "Admin" else df[df['Registrert_Av'] == current_user]

st.sidebar.title(f"👤 {current_user.capitalize()}")
menu_options = ["📊 Dashbord", "➕ Registrer ny søknad", "📂 Kunde Arkiv"]
if role == "Admin": menu_options.append("🕵️ Master Kontrollpanel")
valg = st.sidebar.selectbox("Hovedmeny", menu_options)

if st.sidebar.button("🔴 Logg ut"):
    st.session_state.clear()
    st.rerun()

# --- SEKSJON 1: DASHBORD ---
if valg == "📊 Dashbord":
    st.header(f"📊 Oversikt - {current_user.capitalize()}")
    col1, col2 = st.columns(2)
    with col1:
        total_volum = pd.to_numeric(display_df['Beløp'], errors='coerce').sum()
        st.metric("Totalt Volum (kr)", f"{total_volum:,} kr")
    with col2:
        st.metric("Aktive saker", len(display_df))
    st.divider()
    st.subheader("Siste oppdateringer")
    st.dataframe(display_df.tail(15), use_container_width=True)

# --- SEKSJON 2: REGISTRER NY SØKNAD ---
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
            navn = st.text_input("Fullt Navn")
            fnr = st.text_input("Fødselsnummer (11 siffer)")
            epost = st.text_input("E-postadresse")
            tlf = st.text_input("Telefonnummer")
        with c2:
            sivil = st.selectbox("Sivilstatus", ["Gift", "Samboer", "Enslig", "Skilt/Separert"])
            jobb = st.selectbox("Arbeidsstatus", ["Fast ansatt", "Midlertidig", "AAP", "Uføretrygd", "Arbeidsledig", "Selvstendig næringsdrivende"])
            lonn = st.number_input("Årslønn Brutto", min_value=0)

        st.divider()
        notater_input = st.text_area("Beskrivelse av saken")
        opplastede_filer = st.file_uploader("Last opp dokumenter (Vedlegg)", accept_multiple_files=True)
        total_belop = st.number_input("Søknadsbeløp (kr)", min_value=0)

        if st.form_submit_button("SEND INN SAK TIL ADMIN"):
            fil_liste = []
            if opplastede_filer:
                for fil in opplastede_filer:
                    ren_filnavn = f"{fnr}_{fil.name}".replace(" ", "_")
                    with open(os.path.join(DOCS_DIR, ren_filnavn), "wb") as f:
                        f.write(fil.getbuffer())
                    fil_liste.append(ren_filnavn)
            
            new_entry = {
                "ID": len(df) + 1, "Dato": datetime.now().strftime("%d-%m-%Y"),
                "Produkt": prod, "Hovedsøker": navn, "Fnr": fnr, "Beløp": total_belop,
                "Status": "Mottatt", "Notater": notater_input, 
                "Vedlegg_Sti": ",".join(fil_liste), "Registrert_Av": current_user,
                "Bank_Navn": "Ikke sendt ennå", "Behandlings_Status": "Venter på Admin"
            }
            df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
            df.to_csv(DB_FILE, index=False)
            st.success(f"✅ Sak er sendt til Admin!")

# --- SEKSJON 3: KUNDE ARKIV (Admin Updates Process Here) ---
elif valg == "📂 Kunde Arkiv":
    st.header(f"📂 Sakshåndtering og Arkiv")
    sok = st.text_input("Søk i arkivet (Navn eller Fnr)")
    res_df = display_df[display_df.astype(str).apply(lambda x: x.str.contains(sok, case=False)).any(axis=1)] if sok else display_df

    for i, rad in res_df.iterrows():
        # Rangering farge basert på status
        status_color = "🔵" if rad['Behandlings_Status'] == "Venter på Admin" else "🟢"
        
        with st.expander(f"{status_color} {rad['Hovedsøker']} - {rad['Produkt']} (Fra: {rad['Registrert_Av']})"):
            c1, c2, c3 = st.columns(3)
            with c1:
                st.write(f"**Beløp:** {rad['Beløp']:,} kr")
                st.write(f"**Fnr:** {rad['Fnr']}")
                st.write(f"**Agent:** {rad['Registrert_Av']}")
            with c2:
                st.write(f"**Dato:** {rad['Dato']}")
                st.info(f"**Bank:** {rad['Bank_Navn']}")
            with c3:
                st.warning(f"**Status:** {rad['Behandlings_Status']}")
            
            st.write(f"**Notater:** {rad['Notater']}")
            
            # Vedlegg seksjon
            vedlegg = str(rad['Vedlegg_Sti'])
            if vedlegg and vedlegg != "nan" and vedlegg != "":
                for f_name in vedlegg.split(","):
                    f_path = os.path.join(DOCS_DIR, f_name)
                    if os.path.exists(f_path):
                        with open(f_path, "rb") as d_file:
                            st.download_button(f"📥 Last ned {f_name.split('_', 1)[-1]}", d_file, file_name=f_name, key=f"{f_name}_{i}")

            # --- ADMIN KONTROLL PANEL FOR HVER SAK ---
            if role == "Admin":
                st.divider()
                st.subheader("⚙️ Administrer Sak (Kun Admin)")
                with st.form(f"admin_update_{i}"):
                    u_bank = st.text_input("Hvilken Bank?", value=rad['Bank_Navn'])
                    u_status = st.selectbox("Oppdater Status", [
                        "Venter på vurdering", 
                        "Sendt til Bank", 
                        "Bank behandler saken", 
                        "Mangler dokumentasjon", 
                        "Godkjent / Innvilget", 
                        "Avslått"
                    ])
                    if st.form_submit_button("Lagre oppdatering"):
                        df.at[i, 'Bank_Navn'] = u_bank
                        df.at[i, 'Behandlings_Status'] = u_status
                        df.to_csv(DB_FILE, index=False)
                        st.success("✅ Status er oppdatert og agenten kan se dette nå.")
                        st.rerun()

# --- SEKSJON 4: MASTER KONTROLLPANEL ---
elif valg == "🕵️ Master Kontrollpanel" and role == "Admin":
    st.header("🕵️ Master Kontrollpanel")
    t1, t2, t3 = st.tabs(["👥 Agentstyring", "📑 Agentinfo", "🛡️ Sikkerhetslogger"])
    
    with t1:
        st.subheader("Legg til ny agent/worker")
        new_u = st.text_input("Nytt Brukernavn").lower().strip()
        new_p = st.text_input("Nytt Passord")
        if st.button("Opprett Bruker"):
            u_df = get_users_df()
            if new_u in u_df['username'].values: st.error("Brukernavn eksisterer allerede!")
            else:
                new_row = pd.DataFrame([{"username": new_u, "password": new_p, "role": "Worker"}])
                new_row.to_csv(USER_FILE, mode='a', header=False, index=False)
                st.success(f"Bruker {new_u} er opprettet!")
        st.dataframe(get_users_df())

    with t2:
        st.subheader("Administrer Agent Profiler")
        a_df = pd.read_csv(AGENT_RECORDS_FILE)
        with st.form("agent_data"):
            u_select = st.selectbox("Velg Agent", get_users_df()['username'].unique())
            f_name = st.text_input("Fullt Navn")
            u_rank = st.selectbox("Nivå", ["Junior", "Senior", "Partner"])
            u_time = st.text_input("Arbeidstid")
            u_inv = st.selectbox("Faktura Status", ["Betalt", "Ubetalt"])
            u_contract = st.text_area("Kontrakt Detaljer")
            if st.form_submit_button("Oppdater Profil"):
                a_df = a_df[a_df['username'] != u_select]
                new_data = {"username": u_select, "full_name": f_name, "rank": u_rank, "duty_time": u_time, "invoice_status": u_inv, "contract": u_contract}
                a_df = pd.concat([a_df, pd.DataFrame([new_data])])
                a_df.to_csv(AGENT_RECORDS_FILE, index=False)
                st.success("Profil er oppdatert!")
        st.dataframe(a_df)

    with t3:
        if os.path.exists(LOG_FILE):
            st.dataframe(pd.read_csv(LOG_FILE).sort_values("Tidspunkt", ascending=False), use_container_width=True)
