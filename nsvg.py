
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
        'About': "# NSVG CRM v2.0\nYeh portal khas taur par **NSVG Agents** ke liye banaya gaya hai."
    }
)

# Yeh CSS footer aur Streamlit ka default branding hide kar degi
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
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

if not os.path.exists(DOCS_DIR): os.makedirs(DOCS_DIR)

# Initialize Users with the new agent Awari3600
if not os.path.exists(USER_FILE):
    pd.DataFrame([
        {"username": "amina", "password": "aminaaz0207"},
        {"username": "umer", "password": "Umer2026"},
        {"username": "ali", "password": "AliPass123"},
        {"username": "awari3600", "password": "Awari@9204"}
    ]).to_csv(USER_FILE, index=False)

def get_users():
    return pd.read_csv(USER_FILE).set_index("username")["password"].to_dict()

def save_user_password(username, new_password):
    u_df = pd.read_csv(USER_FILE)
    u_df.loc[u_df['username'] == username, 'password'] = new_password
    u_df.to_csv(USER_FILE, index=False)

def record_log(user, loc_data, action):
    try:
        lat = loc_data['coords']['latitude'] if loc_data else "N/A"
        lon = loc_data['coords']['longitude'] if loc_data else "N/A"
    except: lat, lon = "N/A", "N/A"
    maps_url = f"https://www.google.com/maps?q={lat},{lon}" if lat != "N/A" else "No Location"
    new_log = {"Timestamp": datetime.now().strftime("%d-%m-%Y %H:%M:%S"), "Bruker": user, "Handling": action, "Maps Link": maps_url}
    log_df = pd.DataFrame([new_log])
    if not os.path.exists(LOG_FILE): log_df.to_csv(LOG_FILE, index=False)
    else: log_df.to_csv(LOG_FILE, mode='a', header=False, index=False)

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
        USERS_DB = get_users()
        
        # New User auto-registration check if file exists
        if u_input == "awari3600" and p_input == "Awari@9204" and u_input not in USERS_DB:
             u_df = pd.read_csv(USER_FILE)
             if u_input not in u_df['username'].values:
                 new_u = pd.DataFrame([{"username": "awari3600", "password": "Awari@9204"}])
                 u_df = pd.concat([u_df, new_u], ignore_index=True)
                 u_df.to_csv(USER_FILE, index=False)
                 USERS_DB = get_users()

        if u_input == "admin" and p_input == "NSVG2026":
            st.session_state.update({'logged_in': True, 'user_role': "Admin", 'user_id': "Admin"})
            record_log("Admin", loc, "Innlogging suksess")
            st.rerun()
        elif u_input in USERS_DB and p_input == USERS_DB[u_input]:
            st.session_state.update({'logged_in': True, 'user_role': "Worker", 'user_id': u_input.capitalize()})
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

st.sidebar.title(f"👤 {current_user}")
menu_options = ["📊 Dashbord", "➕ Registrer ny søknad", "📂 Kunde Arkiv"]
if role == "Admin": menu_options.append("🕵️ Master Kontrollpanel")
valg = st.sidebar.selectbox("Hovedmeny", menu_options)

if st.sidebar.button("🔴 Logg ut"):
    st.session_state.clear()
    st.rerun()

# --- SECTION 1: DASHBORD ---
if valg == "📊 Dashbord":
    st.header(f"📊 Dashboard - {current_user}")
    col1, col2 = st.columns(2)
    with col1:
        total_volum = pd.to_numeric(display_df['Beløp'], errors='coerce').sum()
        st.metric("Ditt Volum (kr)", f"{total_volum:,} kr")
    with col2:
        st.metric("Dine aktive saker", len(display_df))
    st.divider()
    st.dataframe(display_df.tail(15), use_container_width=True)

# --- SECTION 2: REGISTRER NY SØKNAD (DETAILED) ---
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

            if "Refinansiering" in prod or "Mellomfinansiering" in prod:
                st.info("Eksisterende Eiendom")
                takst = st.number_input("Siste verdivurdering / E-takst", min_value=0)
                takst_alder = st.selectbox("Er taksten eldre enn 6 måneder?", ["Nei", "Ja"])

        elif is_bedrift:
            st.warning("Firmadetaljer (Bedrift)")
            orgnr = st.text_input("Organisasjonsnummer")
            firmanavn = st.text_input("Firmaets navn")
            regn_2 = st.checkbox("Regnskap for siste 2 år tilgjengelig")
            plan = st.text_area("Formål med lånet")

        if has_medsoker:
            st.divider()
            st.subheader("👥 Informasjon om Med-søker")
            m1, m2 = st.columns(2)
            with m1:
                m_navn = st.text_input("Medsøker Navn")
                m_fnr = st.text_input("Medsøker Fnr")
            with m2:
                m_lonn = st.number_input("Medsøker Årslønn", min_value=0)
                m_gjeld = st.number_input("Medsøker gjeld/kreditt", min_value=0)

        st.divider()
        st.subheader("📎 Dokumentasjon og Notater")
        notater_input = st.text_area("Interne notater")
        opplastede_filer = st.file_uploader("Last opp dokumenter", accept_multiple_files=True)
        total_belop = st.number_input("Endelig søknadsbeløp (kr)", min_value=0)

        if st.form_submit_button("SEND INN SØKNAD TIL VAULT"):
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
                "Status": "Til vurdering", "Notater": notater_input, 
                "Vedlegg_Sti": ",".join(fil_liste), "Registrert_Av": current_user
            }
            df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
            df.to_csv(DB_FILE, index=False)
            st.success(f"✅ Søknad arkivert!")

# --- SECTION 3: KUNDE ARKIV ---
elif valg == "📂 Kunde Arkiv":
    st.header(f"📂 Arkiv - {current_user}")
    sok = st.text_input("Søk i arkivet (Navn eller Fnr)")
    res_df = display_df[display_df.astype(str).apply(lambda x: x.str.contains(sok, case=False)).any(axis=1)] if sok else display_df

    for i, rad in res_df.iterrows():
        with st.expander(f"📁 {rad['Hovedsøker']} - {rad['Produkt']}"):
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"**Beløp:** {rad['Beløp']:,} kr")
                st.write(f"**Fnr:** {rad['Fnr']}")
            with c2:
                st.write(f"**Dato:** {rad['Dato']}")
                st.write(f"**Status:** {rad['Status']}")
            st.info(f"**Notater:** {rad['Notater']}")
            
            vedlegg = str(rad['Vedlegg_Sti'])
            if vedlegg and vedlegg != "nan" and vedlegg != "":
                for f_name in vedlegg.split(","):
                    f_path = os.path.join(DOCS_DIR, f_name)
                    if os.path.exists(f_path):
                        with open(f_path, "rb") as d_file:
                            st.download_button(f"📥 {f_name.split('_', 1)[-1]}", d_file, file_name=f_name, key=f"{f_name}_{i}")

# --- SECTION 4: MASTER KONTROLLPANEL (ADMIN ONLY) ---
elif valg == "🕵️ Master Kontrollpanel" and role == "Admin":
    st.header("🕵️ Master Kontrollpanel")
    t1, t2 = st.tabs(["Sikkerhetslogger", "Brukerinnstillinger"])
    with t1:
        if os.path.exists(LOG_FILE): st.dataframe(pd.read_csv(LOG_FILE).sort_values("Timestamp", ascending=False), use_container_width=True)
    with t2:
        st.subheader("Endre Passord")
        target = st.selectbox("Velg Bruker", list(get_users().keys()))
        new_p = st.text_input("Nytt Passord", type="password")
        if st.button("Lagre Nytt Passord"):
            save_user_password(target, new_p)
            st.success("Passord oppdatert!")
