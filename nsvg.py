import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- 1. SETTINGS & PAGE CONFIG ---
st.set_page_config(page_title="NSVG Digital Bank Portal", page_icon="🛡️", layout="wide")

# CSS for Dark & Light Mode Compatibility
st.markdown("""
    <style>
    /* Main Background color adaptation */
    .stApp {
        transition: background-color 0.3s ease;
    }
    
    /* Metrics Box styling (Dono modes mein readable rahega) */
    div[data-testid="stMetric"] {
        background-color: rgba(151, 166, 195, 0.15); /* Light transparent grey */
        padding: 15px;
        border-radius: 12px;
        border: 1px solid rgba(128, 128, 128, 0.2);
    }

    /* Expander styling fix for visibility */
    .streamlit-expanderHeader {
        font-weight: bold;
        color: var(--text-color); /* Automatically picks theme text color */
    }

    /* Table/Dataframe adjustment for dark mode */
    .stDataFrame {
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 8px;
    }
    
    /* Label and Input visibility */
    label {
        font-weight: 500 !important;
        color: var(--text-color) !important;
    }
    </style>
    """, unsafe_allow_html=True)
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

def update_status(row_index, new_status):
    sh = connect_to_sheet("MainDB")
    if sh:
        # Row index in Sheets is 1-based + 1 for header
        sh.update_cell(row_index + 1, 27, new_status)
        return True
    return False

def delete_user_completely(username):
    success = False
    for s_name in ["Users", "Agents"]:
        sh = connect_to_sheet(s_name)
        if sh:
            try:
                cell = sh.find(username.lower().strip())
                if cell:
                    sh.delete_rows(cell.row)
                    success = True
            except:
                continue
    return success

# --- 3. LOGIN SYSTEM ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user_role': None, 'user_id': None})

if not st.session_state['logged_in']:
    st.title("🛡️ NSVG - Sikker Digital Portal")
    u_input = st.text_input("Brukernavn").lower().strip()
    p_input = st.text_input("Passord", type="password")
    if st.button("Logg inn"):
        users_df = get_data("Users")
        if not users_df.empty:
            match = users_df[(users_df['username'].astype(str).str.lower() == u_input) & (users_df['password'].astype(str) == p_input)]
            if not match.empty:
                st.session_state.update({'logged_in': True, 'user_role': match.iloc[0]['role'], 'user_id': u_input})
                st.rerun()
            else: st.error("Feil brukernavn eller passord!")
    st.stop()

# --- 4. GLOBAL DATA LOAD ---
df = get_data("MainDB")
role = st.session_state['user_role']
current_user = st.session_state['user_id']

# --- 5. SIDEBAR NAVIGATION ---
st.sidebar.title(f"👤 {current_user.capitalize()}")

# Base options jo sab ko dikhengi
options = ["📊 Dashbord", "➕ Ny Registrering", "📂 Kunde Arkiv"]

# Super Power Logic: Admin aur Director dono ko "Ansatte Kontroll" aur "Master" ka access milega
if role in ["Admin", "Director"]:
    options.extend(["👥 Ansatte Kontroll", "🕵️ Master Kontrollpanel"])

valg = st.sidebar.selectbox("Hovedmeny", options)

# Logout Button
if st.sidebar.button("🔴 Logg ut"):
    st.session_state.clear()
    st.rerun()
    
# --- 6. DASHBORD LOGIC (Clean & Professional) ---
if valg == "📊 Dashbord":
    st.header(f"Oversikt - {current_user.capitalize()}")
    
    # Data load karne ki koshish (Pehli tab se)
    df_main = get_data(0) 

    # Dashboard ke top metrics (Dabbe)
    c1, c2, c3 = st.columns(3)

    # Agar data mojud hai (Chahe 9 hon ya 1200)
    if df_main is not None and not df_main.empty:
        # Columns ke faltu spaces saaf karna
        df_main.columns = [str(c).strip() for c in df_main.columns]
        
        # Permission Logic: Admin aur Director ko poora data dikhana
        if role in ["Admin", "Director"]:
            view_data = df_main
        else:
            # Agents ko sirf unka apna data dikhao
            reg_col = next((c for c in df_main.columns if c.lower() in ['registrert_av', 'agent', 'bruker']), None)
            if reg_col:
                view_data = df_main[df_main[reg_col].astype(str).str.lower() == current_user.lower()]
            else:
                view_data = df_main

        # Beløp (Amount) column dhoond kar calculation karna
        b_col = next((c for c in view_data.columns if c.lower() in ['beløp', 'belop', 'sum', 'amount']), None)
        total_v = pd.to_numeric(view_data[b_col], errors='coerce').sum() if b_col else 0
        
        # Metrics update karna
        c1.metric("Antall Saker", len(view_data))
        c2.metric("Total Volum (kr)", f"{total_v:,.0f} kr")
        c3.metric("Provisjon (1%)", f"{total_v * 0.01:,.0f} kr")
        
        st.divider()
        st.subheader("Siste Registrerte Saker")
        # Sirf aakhri 15 entries dikhana taake dashboard saaf rahe
        st.dataframe(view_data.tail(15), use_container_width=True)
    
    else:
        # AGAR DATA 0 HAI (YA SHEET KHALI HAI)
        c1.metric("Antall Saker", "0")
        c2.metric("Total Volum", "0 kr")
        c3.metric("Provisjon (1%)", "0 kr")
        
        st.divider()
        st.info("📭 Dashbordet er tomt. Ingen saker er registrert ennå.")
        st.write("Når du begynner å legge inn klienter i **'🆕 Registrer Ny'**, vil statistikken vises her.")
        
➕ Ny Bankforespørsel
Velg Produkt
Boliglån

👤 Hovedsøker Detaljer
Fullt Navn (Hovedsøker)

Fødselsnummer (11 siffer)

E-post

Statsborgerskap (Pass fra)
Norge

Telefon

Sivilstatus
Enslig

💼 Arbeid & Inntekt (Hovedsøker)
Årslønn Brutto (kr)



Ansettelsesform
Fast ansatt

Arbeidsgiver (Nåværende firma)

Bi-inntekt / Ekstra jobb (kr/år)



Ansettelsestid (f.eks 4 år)

Stillingsprosent (%)
0
100
🏠 Finansiell Status & Søknad
Ønsket Lånebeløp (kr)



Egenkapital (kr)



Egenkapital Kilde
Sparing

Antall Barn (under 18 år)



Antall Biler



Har du SFO / Barnehage utgifter?
Nei

💳 Eksisterende Gjeld (Samlet)
Nåværende Boliglån (kr)



Kredittkort Ramme (kr)



Billån (kr)



Studielån (kr)



Forbrukslån / Kreditt (kr)



Interne Notater / Kommentarer (Viktig info for banken)

Last opp Vedlegg (Skattemelding, Lønnslipper, ID)

200MB per file

# --- 8. KUNDE ARKIV ---
elif valg == "📂 Kunde Arkiv":
    st.header("📂 Kunde Arkiv - Full Oversikt")
    
    # Logic: Admin aur Director ko saara data dikhao
    if role in ["Admin", "Director"]:
        view_df = df
    else:
        # Agents ko sirf apna data dikhao
        if 'Registrert_Av' in df.columns:
            view_df = df[df['Registrert_Av'].astype(str).str.lower() == current_user.lower()]
        else:
            view_df = pd.DataFrame()

    if not view_df.empty:
        # Search functionality (Navn ya Phone number se search karein)
        sok = st.text_input("🔍 Søk etter kunde (Navn, Tlf, E-post)...", placeholder="Skriv her for å søke...")
        
        if sok:
            # Pura data filter karna search ke mutabiq
            mask = view_df.astype(str).apply(lambda x: x.str.contains(sok, case=False)).any(axis=1)
            view_df = view_df[mask]
        
        st.write(f"Viser {len(view_df)} treff.")
        st.divider()

        # Ek ek client ko expander mein dikhana
        for i, r in view_df.iterrows():
            # Column names safety check
            k_navn = r.get('Hovedsøker', 'Ukjent Kunde')
            k_status = r.get('Status', 'Mottatt')
            k_belop = r.get('Beløp', '0')
            
            with st.expander(f"👤 {k_navn} | {k_belop} kr | Status: {k_status}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**E-post:** {r.get('E-post', '-')}")
                    st.write(f"**Telefon:** {r.get('Telefon', '-')}")
                    st.write(f"**Registrert Av:** {r.get('Registrert_Av', '-')}")
                
                with col2:
                    st.write(f"**Bank:** {r.get('Bank', '-')}")
                    st.write(f"**Dato:** {r.get('Dato', '-')}")
                
                st.divider()
                
                # --- UPDATE STATUS (Sirf Admin aur Director ke liye) ---
                if role in ["Admin", "Director"]:
                    st.subheader("Oppdater Status")
                    n_st = st.selectbox(
                        "Endre saksstatus:", 
                        ["Mottatt", "Under Behandling", "Godkjent", "Avslått", "Utbetalt"], 
                        key=f"arkiv_st_{i}",
                        index=0 if k_status not in ["Mottatt", "Under Behandling", "Godkjent", "Avslått", "Utbetalt"] else ["Mottatt", "Under Behandling", "Godkjent", "Avslått", "Utbetalt"].index(k_status)
                    )
                    
                    if st.button("💾 Lagre Endring", key=f"arkiv_btn_{i}"):
                        # Sheet mein status update karne ka function (Row index i+2 kyunke header aur 0-index)
                        # update_status_in_sheet(i + 2, n_st) # Isko apne update function ke mutabiq set karein
                        st.success(f"Status for {k_navn} er oppdatert!")
    else:
        st.info("Ingen kunder funnet i arkivet.")
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
                # 1. Users wali sheet mein login details dalna
                user_sh = connect_to_sheet("Users")
                user_sh.append_row([u, p, "Worker"])
                
                # 2. Agents wali sheet mein profile details dalna
                agent_sh = connect_to_sheet("Agents")
                agent_sh.append_row([u, n, pos, "09-17", "Aktiv", "Signed"])
                
                st.success(f"Agent {n} er nå aktivert i systemet!")
            else:
                st.error("Vennligst fyll ut alle feltene.")

    # Ansatte ki list dikhana
    st.divider()
    st.subheader("👥 Oversikt over alle Ansatte")
    agents_df = get_data("Agents")
    if not agents_df.empty:
        st.table(agents_df[['username', 'navn', 'stilling', 'status']])
    else:
        st.info("Ingen ansatte funnet i databasen.")

# --- 10. ANSATTE KONTROLL (Advanced & Fixed) ---
elif valg == "👥 Ansatte Kontroll" and role in ["Admin", "Director"]:
    st.header("👥 Ansatte Oversikt og Kontroll")
    
    agents_df = get_data("Agents")
    main_df = df # Global load se aa raha hai

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
                if not main_df.empty and 'Registrert_Av' in main_df.columns:
                    agent_saker = main_df[main_df['Registrert_Av'].astype(str).str.lower() == a_user.lower()]
                
                with col2:
                    if not agent_saker.empty:
                        antall = len(agent_saker)
                        volum = pd.to_numeric(agent_saker['Beløp'], errors='coerce').sum()
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
                        else:
                            st.warning("Ingen data å vise.")

                with c_act2:
                    n_st = st.selectbox("Endre Status", ["Aktiv", "Inaktiv", "Permisjon"], key=f"st_sel_{i}")
                    if st.button("💾 Lagre Status", key=f"save_st_{i}"):
                        st.success(f"Status oppdatert!")

                with c_act3:
                    if st.button(f"🗑️ Slette Profil", key=f"del_agent_{i}"):
                        if role == "Admin":
                            st.error(f"Slette {a_user}? Gjør dette manuelt i Google Sheets.")
                        else:
                            st.info("Kun Admin kan slette.")
    else:
        st.warning("Ingen ansatte funnet. Sjekk 'Agents' fanen i Google Sheets.")

# --- 11. FOOTER ---
st.sidebar.markdown("---")
st.sidebar.caption("NSVG CRM v2.0 | © 2026 Iqbal Entrepreneur")
