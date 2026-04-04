import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- 1. CONFIG & STYLE (Aapki pasand ke rang) ---
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
DOCS_DIR = "nsvg_vedlegg"

if not os.path.exists(DOCS_DIR):
    os.makedirs(DOCS_DIR)

# IDs aur Passwords ka database
USERS_DB = {
    "amina": "aminaaz0207",
    "umer": "Umer2026",
    "ali": "AliPass123"
}

def last_data():
    cols = ["ID", "Dato", "Produkt", "Hovedsøker", "Fnr", "Beløp", "Status", "Notater", "Vedlegg_Sti", "Registrert_Av"]
    if not os.path.exists(DB_FILE):
        df = pd.DataFrame(columns=cols)
        df.to_csv(DB_FILE, index=False)
        return df
    df = pd.read_csv(DB_FILE)
    if "Registrert_Av" not in df.columns:
        df["Registrert_Av"] = "System"
        df.to_csv(DB_FILE, index=False)
    return df

def lagre_data(df): 
    df.to_csv(DB_FILE, index=False)

# --- 3. INNLOGGING SYSTEM ---
if 'logged_in' not in st.session_state: 
    st.session_state['logged_in'] = False
    st.session_state['user_role'] = None
    st.session_state['user_id'] = None

if not st.session_state['logged_in']:
    st.title("🛡️ NSVG - Sikker Digital Portal")
    input_user = st.text_input("Brukernavn (User ID)").lower().strip()
    input_pw = st.text_input("Passord", type="password")
    
    if st.button("Logg inn"):
        if input_user == "admin" and input_pw == "NSVG2026":
            st.session_state['logged_in'] = True
            st.session_state['user_role'] = "Admin"
            st.session_state['user_id'] = "Admin"
            st.rerun()
        elif input_user in USERS_DB and input_pw == USERS_DB[input_user]:
            st.session_state['logged_in'] = True
            st.session_state['user_role'] = "Worker"
            st.session_state['user_id'] = input_user.capitalize()
            st.rerun()
        else:
            st.error("Feil brukernavn eller passord!")
    st.stop()

# --- 4. MAIN APP ---
df = last_data()
role = st.session_state['user_role']
current_user = st.session_state['user_id']

# WORKER FILTER: Agar worker hai toh sirf apna data dekhega
if role == "Worker":
    display_df = df[df['Registrert_Av'] == current_user]
else:
    display_df = df

st.sidebar.title(f"👤 {current_user}")
valg = st.sidebar.selectbox("Hovedmeny", ["📊 Dashbord", "➕ Registrer ny søknad", "📂 Kunde Arkiv"])

if st.sidebar.button("🔴 Logg ut"):
    st.session_state.clear()
    st.rerun()

# --- SECTION 1: DASHBORD ---
if valg == "📊 Dashbord":
    st.header(f"📊 Dashboard - {current_user}")
    col1, col2 = st.columns(2)
    with col1:
        # Worker ko sirf apne paise nazar aayenge
        total_volum = pd.to_numeric(display_df['Beløp'], errors='coerce').sum()
        st.metric("Ditt Volum (kr)", f"{total_volum:,} kr")
    with col2:
        st.metric("Dine aktive saker", len(display_df))
    st.divider()
    st.subheader("Siste aktiviteter")
    st.dataframe(display_df.tail(15), use_container_width=True)

# --- SECTION 2: REGISTRER NY SØKNAD (Aapka Lock Code) ---
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
            firma = st.text_input("Navn på arbeidsgiver / Firma")
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
                ek_kilde = st.text_input("Kilde til egenkapital (Sparing, Gave, Arv?)")
                omrade = st.text_input("Ønsket område for boligkjøp")
            with k2:
                gjeld = st.number_input("Annen gjeld (Forbrukslån/Kreditt)", min_value=0)
                ramme = st.number_input("Samlet ramme pả kredittkort", min_value=0)
                biler = st.number_input("Antall biler i husholdningen", min_value=0)
                billan = st.number_input("Restgjeld billån", min_value=0)
                utleie = st.selectbox("Skal boligen ha utleiedel?", ["Nei", "Ja"])
                banker = st.text_input("Hvilke banker er søkt i tidligere?")

            if "Refinansiering" in prod or "Mellomfinansiering" in prod:
                st.info("Eksisterende Eiendom")
                takst = st.number_input("Siste verdivurdering / E-takst", min_value=0)
                takst_alder = st.selectbox("Er taksten eldre enn 6 måneder?", ["Nei", "Ja (Krever ny e-takst)"])

        elif is_bedrift:
            st.warning("Firmadetaljer (Bedrift)")
            orgnr = st.text_input("Organisasjonsnummer")
            firmanavn = st.text_input("Firmaets navn")
            regn_2 = st.checkbox("Regnskap for siste 2 år er tilgjengelig")
            regn_ia = st.checkbox("Regnskap for inneværende år er tilgjengelig")
            plan = st.text_area("Formål med lånet / Investeringsplan")

        if has_medsoker:
            st.divider()
            st.subheader("👥 Informasjon om Med-søker")
            m1, m2 = st.columns(2)
            with m1:
                m_navn = st.text_input("Medsøker Navn")
                m_fnr = st.text_input("Medsøker Fnr")
                m_jobb = st.selectbox("Medsøker Arbeidsstatus", ["Fast ansatt", "AAP", "Uføre", "Selvstendig"])
            with m2:
                m_lonn = st.number_input("Medsøker Årslønn", min_value=0)
                m_gjeld = st.number_input("Medsøker gjeld/kreditt", min_value=0)

        st.divider()
        st.subheader("📎 Dokumentasjon og Notater")
        notater_input = st.text_area("Interne notater / Kommentarer til saken")
        opplastede_filer = st.file_uploader("Last opp nødvendige dokumenter", accept_multiple_files=True)
        total_belop = st.number_input("Endelig søknadsbeløp til banken (kr)", min_value=0)

        if st.form_submit_button("SEND INN SØKNAD TIL VAULT"):
            fil_liste = []
            if opplastede_filer:
                for fil in opplastede_filer:
                    ren_filnavn = f"{fnr}_{fil.name}".replace(" ", "_")
                    with open(os.path.join(DOCS_DIR, ren_filnavn), "wb") as f:
                        f.write(fil.getbuffer())
                    fil_liste.append(ren_filnavn)
            
            ny_kunde = {
                "ID": len(df) + 1, "Dato": datetime.now().strftime("%d-%m-%Y"),
                "Produkt": prod, "Hovedsøker": navn, "Fnr": fnr,
                "Beløp": total_belop, "Status": "Til vurdering",
                "Notater": notater_input, "Vedlegg_Sti": ",".join(fil_liste),
                "Registrert_Av": current_user
            }
            df = pd.concat([df, pd.DataFrame([ny_kunde])], ignore_index=True)
            lagre_data(df)
            st.success(f"✅ Søknad arkivert av {current_user}!")

# --- SECTION 3: KUNDE ARKIV ---
elif valg == "📂 Kunde Arkiv":
    st.header(f"📂 Arkiv - {current_user}")
    sok = st.text_input("Søk i arkivet (Navn eller Fnr)")
    
    # Filter by Search
    res_df = display_df[display_df.astype(str).apply(lambda x: x.str.contains(sok, case=False)).any(axis=1)] if sok else display_df

    for i, rad in res_df.iterrows():
        with st.expander(f"📁 {rad['Hovedsøker']} - {rad['Produkt']}"):
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"**Søknadsbeløp:** {rad['Beløp']:,} kr")
                st.write(f"**Registrert Av:** {rad['Registrert_Av']}")
            with c2:
                st.write(f"**Dato:** {rad['Dato']}")
                st.write(f"**Status:** {rad['Status']}")
            st.info(f"**Notater:**\n{rad['Notater']}")
            
            vedlegg = str(rad['Vedlegg_Sti'])
            if vedlegg and vedlegg != "nan" and vedlegg != "":
                st.write("**📎 Vedlegg:**")
                for f_name in vedlegg.split(","):
                    f_path = os.path.join(DOCS_DIR, f_name)
                    if os.path.exists(f_path):
                        with open(f_path, "rb") as d_file:
                            st.download_button(f"📥 {f_name.split('_', 1)[-1]}", d_file, file_name=f_name, key=f"{f_name}_{i}")
