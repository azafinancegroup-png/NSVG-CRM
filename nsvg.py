import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- 1. SETTINGS & PAGE CONFIG ---
st.set_page_config(page_title="NSVG Digital Bank Portal", page_icon="🛡️", layout="wide")

# --- 2. GOOGLE SHEETS ENGINE ---
def connect_to_sheet(sheet_name):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open("NSVG_CRM_Data").worksheet(sheet_name)
    except:
        return None

def get_data(sheet_name):
    sh = connect_to_sheet(sheet_name)
    if sh:
        data = sh.get_all_records()
        df = pd.DataFrame(data)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    return pd.DataFrame()

def add_data(sheet_name, row_list):
    sh = connect_to_sheet(sheet_name)
    if sh: sh.append_row(row_list)

# --- 7. NY REGISTRERING (CACHED & FAST VERSION) ---
@st.cache_data
def get_country_list():
    base_countries = ["Norge", "Sverige", "Danmark", "UK", "USA", "Pakistan", "India"]
    others = sorted(["Afghanistan", "Albania", "Algerie", "Andorra", "Angola", "Argentina", "Australia", "Bangladesh", "Belgia", "Brasil", "Canada", "Chile", "China", "Egypt", "Finland", "Frankrike", "Hellas", "Island", "Iran", "Irak", "Irland", "Italia", "Japan", "Jordan", "Kuwait", "Latvia", "Libanon", "Malaysia", "Mexico", "Marokko", "Nederland", "New Zealand", "Nigeria", "Oman", "Filippinene", "Polen", "Portugal", "Qatar", "Romania", "Russland", "Saudi Arabia", "Singapore", "Spania", "Sri Lanka", "Sudan", "Sveits", "Syria", "Thailand", "Tunisia", "Tyrkia", "UAE", "Ukraina", "Vietnam"])
    return base_countries + others

# --- LOGIN CHECK (Session State) ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user_role': None, 'user_id': None})

# Assuming Login Logic is here... 
# Role aur current_user yahan se set honge
df = get_data("MainDB")
role = st.session_state['user_role']
current_user = st.session_state['user_id']

# --- SIDEBAR MENU ---
options = ["📊 Dashbord", "➕ Ny Registrering", "📂 Kunde Arkiv"]
if role in ["Admin", "Director"]:
    options.extend(["👥 Ansatte Kontroll", "🕵️ Master Kontrollpanel"])
valg = st.sidebar.selectbox("Hovedmeny", options)

# --- 7. NY REGISTRERING (YOUR EXACT CODE) ---
if valg == "➕ Ny Registrering":
    st.header("➕ Ny Bankforespørsel")
    countries = get_country_list()
    prod = st.selectbox("Velg Produkt", ["Boliglån", "Refinansiering", "Mellomfinansiering", "Investlån / Bedriftlån", "Byggelån", "Forbrukslån", "Billån"])
    is_bedrift = "Bedriftlån" in prod or "Investlån" in prod

    st.info("Har kunden en Medsøker? Marker her før du fyller ut skjemaet.")
    has_med = st.checkbox("✅ JA, legg til Medsøker (Ektefelle/Samboer)")

    with st.form("main_bank_form", clear_on_submit=True):
        f_navn, f_org, f_eier, f_aksjer = "", "", "", ""
        if is_bedrift:
            st.subheader("🏢 Bedrift / Firma Detaljer")
            bc1, bc2 = st.columns(2)
            f_navn = bc1.text_input("Firma Navn")
            f_org = bc1.text_input("Organisasjonsnummer (9 siffer)")
            f_eier = bc2.text_area("Navn & Personnummer på alle eiere")
            f_aksjer = bc2.text_input("Aksjefordeling (%)")
            st.divider()

        # --- HOVEDSØKER SECTION ---
        st.subheader("👤 Hovedsøker Detaljer")
        c1, c2 = st.columns(2)
        navn = c1.text_input("Fullt Navn (Hovedsøker)")
        fnr = c1.text_input("Fødselsnummer (11 siffer)")
        epost = c1.text_input("E-post")
        tlf = c2.text_input("Telefon")
        sivil = c2.selectbox("Sivilstatus", ["Enslig", "Gift", "Samboer", "Skilt", "Enke/Enkemann"])
        pass_land = c1.selectbox("Statsborgerskap (Pass fra)", countries, index=0)
        botid = c2.text_input("Botid i Norge (Hvis ikke norsk pass)")

        st.markdown("#### 💼 Arbeid & Inntekt (Hovedsøker)")
        l1, l2, l3 = st.columns(3)
        lonn = l1.number_input("Årslønn Brutto (kr)", min_value=0, step=1000, format="%d")
        arbeidsgiver = l2.text_input("Arbeidsgiver")
        ansatt_tid = l3.text_input("Ansettelsestid (Hvor lenge?)")
        stilling_type = l1.selectbox("Ansettelsesform", ["Fast ansatt", "Midlertidig", "Selvstendig", "Uføretrygd", "Pensjonist"])
        ekstra_jobb = l2.number_input("Bi-inntekt / Ekstra (kr/år)", 0)
        still_pst = l3.slider("Stillingsprosent (%)", 0, 100, 100)

        st.divider()

        # --- FINANCIAL & DEBT SECTION ---
        st.subheader("🏠 Finansiell Status & Søknad")
        f1, f2 = st.columns(2)
        belop = f1.number_input("Ønsket Lånebeløp (kr)", 0, step=10000, format="%d")
        ek = f1.number_input("Egenkapital (kr)", 0, step=10000, format="%d")
        ek_kilde = f1.selectbox("Egenkapital Kilde", ["Sparing", "Salg av bolig", "Arv/Gave", "Lån fra familie", "Annet"])
        barn = f2.number_input("Antall Barn (under 18 år)", 0)
        biler = f2.number_input("Antall Biler", 0)
        sfo = f2.selectbox("SFO / Barnehage utgifter?", ["Nei", "Ja"])

        st.markdown("#### 💳 Eksisterende Gjeld (Samlet)")
        g1, g2, g3 = st.columns(3)
        g_bolig = g1.number_input("Nåværende Boliglån (kr)", 0, step=10000, format="%d")
        g_bil = g2.number_input("Billån (kr)", 0, step=5000, format="%d")
        g_forbruk = g3.number_input("Forbrukslån (kr)", 0, step=5000, format="%d")
        g_kort = g1.number_input("Kredittkort Ramme (kr)", 0, step=5000, format="%d")
        g_studie = g2.number_input("Studielån (kr)", 0, step=5000, format="%d")

        # --- MEDSØKER SECTION ---
        m_navn, m_fnr, m_epost, m_tlf, m_sivil, m_pass, m_botid = "", "", "", "", "Gift", "Norge", ""
        m_lonn, m_arb, m_tid, m_still_type, m_ekstra, m_pst = 0, "", "", "Fast ansatt", 0, 100

        if has_med:
            st.divider()
            st.subheader("👥 Medsøker Detaljer (Symmetric Profile)")
            mc1, mc2 = st.columns(2)
            m_navn = mc1.text_input("Fullt Navn (Medsøker)")
            m_fnr = mc1.text_input("Fødselsnummer (11 siffer - Medsøker)")
            m_epost = mc1.text_input("E-post (Medsøker)")
            m_tlf = mc2.text_input("Telefon (Medsøker)")
            m_sivil = mc2.selectbox("Sivilstatus (Medsøker)", ["Gift", "Samboer", "Skilt", "Enke/Enkemann", "Enslig"], key="ms_sivil")
            m_pass = mc2.selectbox("Statsborgerskap (Medsøker)", countries, key="ms_pass")
            m_botid = mc1.text_input("Botid i Norge (Medsøker)", key="ms_botid")

            st.markdown("#### 💼 Arbeid & Inntekt (Medsøker)")
            ml1, ml2, ml3 = st.columns(3)
            m_lonn = ml1.number_input("Årslønn Brutto (Medsøker - kr)", 0, step=1000, format="%d")
            m_arb = ml2.text_input("Arbeidsgiver (Medsøker)")
            m_tid = ml3.text_input("Ansettelsestid (Medsøker)")
            m_still_type = ml1.selectbox("Ansettelsesform (Medsøker)", ["Fast ansatt", "Midlertidig", "Selvstendig", "Uføretrygd", "Pensjonist"], key="ms_job")
            m_ekstra = ml2.number_input("Bi-inntekt / Ekstra (Medsøker)", 0, key="ms_ekstra")
            m_pst = ml3.slider("Stillingsprosent (Medsøker %)", 0, 100, 100, key="ms_pst")

        st.divider()
        notater = st.text_area("Interne Notater (Viktig info for banken)")
        st.file_uploader("Last opp Vedlegg (PDF/Bilder)")

        submit = st.form_submit_button("🚀 SEND SØKNAD TIL BANKEN")
        if submit:
            tot_gjeld = g_bolig + g_bil + g_forbruk + g_kort + g_studie
            # YOUR SHEET SEQUENCE: ID, Dato, Produkt, Navn, Fnr, Epost, Tlf, Sivilstatus, Type, Status, Firma, Lønn, Barn, SFO, EK, Gjeld, Biler, Lånebeløp, OrgNr, Eiere, Aksjer, Medsøker_Navn, Medsøker_Fnr, Medsøker_Epost, Medsøker_Tlf, Medsøker_Lønn, Medsøker_Arbeid, Notater, Pass_Info, Saksbehandler, Bank_Status
            new_row = [
                len(df)+1, datetime.now().strftime("%d-%m-%Y"), prod, navn, fnr, epost, tlf, sivil,
                "Bedrift" if is_bedrift else "Privat", "Active", f_navn if is_bedrift else "", lonn,
                barn, sfo, ek, tot_gjeld, biler, belop, f_org if is_bedrift else "",
                f_eier if is_bedrift else "", f_aksjer if is_bedrift else "",
                m_navn, m_fnr, m_epost, m_tlf, m_lonn, m_arb, notater,
                f"P1: {pass_land} | P2: {m_pass}", current_user, "Mottatt"
            ]
            add_data("MainDB", new_row)
            st.success(f"✅ Søknad registrert!")
            st.balloons()

# --- 9. MASTER KONTROLL ---
elif valg == "🕵️ Master Kontrollpanel" and role in ["Admin", "Director"]:
    st.header("🕵️ Ny Agent Registrering")
    with st.form("agent_form"):
        u = st.text_input("Brukernavn (Login ID)").lower().strip()
        p = st.text_input("Passord", type="password")
        n = st.text_input("Fullt Navn")
        pos = st.selectbox("Stilling", ["Senior Agent", "Junior Agent", "Trainee"])
        
        if st.form_submit_button("✅ Aktiver og Lagre Agent"):
            if u and p and n:
                user_sh = connect_to_sheet("Users")
                user_sh.append_row([u, p, "Worker"])
                agent_sh = connect_to_sheet("Agents")
                agent_sh.append_row([u, n, pos, "09-17", "Aktiv", "Signed"])
                st.success(f"Agent {n} er nå aktivert!")

    st.divider()
    st.subheader("👥 Oversikt over alle Ansatte")
    agents_df = get_data("Agents")
    if not agents_df.empty:
        st.table(agents_df[['username', 'navn', 'stilling', 'status']])

# --- 10. ANSATTE KONTROLL (EXACT CODE) ---
elif valg == "👥 Ansatte Kontroll" and role in ["Admin", "Director"]:
    st.header("👥 Ansatte Oversikt og Kontroll")
    agents_df = get_data("Agents")
    main_df = df

    if not agents_df.empty:
        sok_agent = st.text_input("🔍 Søk etter ansatt (Navn/ID)...")
        if sok_agent:
            agents_df = agents_df[agents_df.astype(str).apply(lambda x: x.str.contains(sok_agent, case=False)).any(axis=1)]

        st.write(f"Totalt {len(agents_df)} ansatte funnet.")

        for i, row in agents_df.iterrows():
            a_user = str(row.get('username', '')).strip()
            a_navn = row.get('navn', 'Ukjent')
            
            with st.expander(f"👤 {a_navn} (ID: {a_user})"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Stilling:** {row.get('stilling', '-')}")
                    st.write(f"**Vakt:** {row.get('vakt', '-')}")
                    st.write(f"**Status:** {row.get('status', '-')}")
                
                agent_saker = pd.DataFrame()
                if not main_df.empty and 'Saksbehandler' in main_df.columns:
                    agent_saker = main_df[main_df['Saksbehandler'].astype(str).str.lower() == a_user.lower()]
                
                with col2:
                    if not agent_saker.empty:
                        antall = len(agent_saker)
                        volum = pd.to_numeric(agent_saker['Lånebeløp'], errors='coerce').sum()
                        st.metric("Antall Saker", antall)
                        st.write(f"**Total Volum:** {volum:,.0f} kr")
                    else:
                        st.info("Ingen saker registrert.")

                st.divider()
                c_act1, c_act2, c_act3 = st.columns(3)
                with c_act1:
                    if st.button(f"📂 Se Saker", key=f"view_saker_{i}"):
                        if not agent_saker.empty:
                            st.subheader(f"Siste 10 saker for {a_navn}")
                            st.dataframe(agent_saker.tail(10), use_container_width=True)
                with c_act2:
                    n_st = st.selectbox("Endre Status", ["Aktiv", "Inaktiv", "Permisjon"], key=f"st_sel_{i}")
                    if st.button("💾 Lagre Status", key=f"save_st_{i}"):
                        st.success(f"Status oppdatert!")
                with c_act3:
                    if st.button(f"🗑️ Slette Profil", key=f"del_agent_{i}"):
                        if role == "Admin":
                            st.error(f"Slette {a_user}? Gjør dette manuelt i Google Sheets.")

# --- 11. FOOTER ---
st.sidebar.markdown("---")
st.sidebar.caption("NSVG CRM v2.0 | © NORDIC SECURE VAULT GROUP")
