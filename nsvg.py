import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json
import smtplib
from email.mime.text import MIMEText
import pytz 

# --- GLOBAL SETTINGS ---
def get_norway_time():
    tz = pytz.timezone('Europe/Oslo')
    return datetime.now(tz).strftime("%d.%m.%Y %H:%M")

# --- 1 & 2. DATABASE UPDATE ENGINE (Stable & Fast) ---
def update_sak_in_sheet(sak_id, updated_values_dict):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        sheet = client.open("NSVG_CRM_Data").worksheet("MainDB") 
        data = sheet.get_all_records()
        temp_df = pd.DataFrame(data)
        
        if 'ID' in temp_df.columns:
            matched_rows = temp_df.index[temp_df['ID'].astype(str) == str(sak_id)].tolist()
            if matched_rows:
                actual_row = matched_rows[0] + 2 
                for col_name, new_val in updated_values_dict.items():
                    if col_name in temp_df.columns:
                        col_idx = temp_df.columns.get_loc(col_name) + 1
                        sheet.update_cell(actual_row, col_idx, str(new_val))
                return True
        return False
    except Exception as e:
        st.error(f"Database Error: {e}")
        return False

# --- MAYA'S HUB: THE PROFESSIONAL MESSAGING INTERFACE ---
def display_bank_messaging_hub(sak_id, chat_data, role, username, agent_name="Agent"):
    st.markdown("---")
    # Identity: Ansatt ko sirf BANK nazar aaye
    target_label = "BANK" if role not in ["Admin", "Director"] else agent_name.upper()
    st.subheader(f"💬 Meldinger med {target_label}")
    
    # Professional Styling
    st.markdown("""
        <style>
        .bank-bubble { background-color: #E1F5FE; border-left: 5px solid #0288D1; padding: 10px; border-radius: 10px; margin: 5px; color: black; }
        .agent-bubble { background-color: #F5F5F5; border-right: 5px solid #757575; padding: 10px; border-radius: 10px; margin: 5px; text-align: right; color: black; }
        </style>
    """, unsafe_allow_html=True)

    try:
        messages = json.loads(chat_data) if chat_data and str(chat_data) != 'nan' else []
    except:
        messages = []

    # --- SMART LOGIC: Auto-Mark as Read when opened ---
    has_unread = False
    for m in messages:
        if role not in ["Admin", "Director"] and m.get('role') == "Bank" and m.get('read') == False:
            m['read'] = True
            has_unread = True
        elif role in ["Admin", "Director"] and m.get('role') == "Agent" and m.get('read') == False:
            m['read'] = True
            has_unread = True

    if has_unread:
        update_sak_in_sheet(sak_id, {"Chat_History": json.dumps(messages)})

    # Show History
    for msg in messages:
        is_bank = msg['role'] == "Bank"
        div_class = "bank-bubble" if is_bank else "agent-bubble"
        # Display Name logic
        sender_display = "BANK" if is_bank and role not in ["Admin", "Director"] else msg["sender"]
        st.markdown(f'<div class="{div_class}"><b>{sender_display}</b><br>{msg["text"]}<br><small style="color: grey;">{msg["time"]}</small></div>', unsafe_allow_html=True)

    # Message Input
    msg_text = st.text_input(f"Skriv til {target_label}...", key=f"chat_in_{sak_id}")
    if st.button("🚀 Send Melding", key=f"btn_{sak_id}"):
        if msg_text:
            new_msg = {
                "role": "Bank" if role in ["Admin", "Director"] else "Agent",
                "sender": "BANK" if role in ["Admin", "Director"] else username.upper(),
                "text": msg_text,
                "time": get_norway_time(), # <--- Correct Norway Time
                "read": False # <--- For Notifications
            }
            messages.append(new_msg)
            if update_sak_in_sheet(sak_id, {"Chat_History": json.dumps(messages)}):
                st.rerun()
                
# --- 2. GOOGLE SHEETS CONNECTION ENGINE (Maya Optimized) ---
def connect_to_sheet(sheet_name):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        # Yeh aapki main spreadsheet file ko open karega
        return client.open("NSVG_CRM_Data").worksheet(sheet_name)
    except Exception as e:
        # Agar connection fail ho toh error show karega
        st.error(f"Tilkoblingsfeil (Connection Error): {e}")
        return None

def get_data(sheet_name):
    sh = connect_to_sheet(sheet_name)
    if sh:
        try:
            data = sh.get_all_records()
            df = pd.DataFrame(data)
            # Column names se extra spaces khatam karne ke liye
            df.columns = [str(c).strip() for c in df.columns]
            return df
        except Exception as e:
            st.warning(f"Kunne ikke hente data fra {sheet_name}: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

def add_data(sheet_name, row_list):
    sh = connect_to_sheet(sheet_name)
    if sh: 
        try:
            # Nayi row append karne ke liye
            sh.append_row(row_list)
            return True
        except Exception as e:
            st.error(f"Feil ved lagring av data: {e}")
            return False
    return False
    
# --- 3. CACHING COUNTRIES (SPEED BOOSTER) ---
@st.cache_data
def get_country_list():
    base = ["Norge", "Sverige", "Danmark", "UK", "USA", "Pakistan", "India"]
    others = sorted(["Afghanistan", "Albania", "Algerie", "Andorra", "Angola", "Argentina", "Australia", "Bangladesh", "Belgia", "Brasil", "Canada", "Chile", "China", "Egypt", "Finland", "Frankrike", "Hellas", "Island", "Iran", "Irak", "Irland", "Italia", "Japan", "Jordan", "Kuwait", "Latvia", "Libanon", "Malaysia", "Mexico", "Marokko", "Nederland", "New Zealand", "Nigeria", "Oman", "Filippinene", "Polen", "Portugal", "Qatar", "Romania", "Russland", "Saudi Arabia", "Singapore", "Spania", "Sri Lanka", "Sudan", "Sveits", "Syria", "Thailand", "Tunisia", "Tyrkia", "UAE", "Ukraina", "Vietnam"])
    return base + others

# --- 4. LOGIN SYSTEM ---
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
            else: 
                st.error("Feil brukernavn ya passord!")
    st.stop()

# --- 5. GLOBAL DATA & SIDEBAR (STABLE CONNECTED VERSION) ---

if st.session_state.get('logged_in'):
    role = st.session_state.get('user_role', 'Guest')
    username = st.session_state.get('user_id', 'Guest')
    current_user = username
else:
    role = "Guest"
    username = "Guest"
    current_user = "Guest"

import pandas as pd
try:
    df = get_data("MainDB") 
    if df is None or df.empty:
        df = get_data("Kunder")
except Exception as e:
    st.error(f"Data loading error: {e}")
    df = pd.DataFrame()

options = ["📊 Dashbord", "➕ Ny Registrering", "📂 Kunde Arkiv"]

if role in ["Admin", "Director"]:
    extra = ["👥 Ansatte Kontroll", "📇 Kontakter", "🕵️ Master Kontrollpanel"]
    for item in extra:
        if item not in options:
            options.append(item)

valg = st.sidebar.selectbox("Hovedmeny", options)

def update_sheet_data_internal(worksheet_name, df_to_save):
    try:
        creds_dict = st.secrets["gcp_service_account"]
        from google.oauth2.service_account import Credentials
        import gspread
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        sh = client.open_by_url(st.secrets["spreadsheet"])
        worksheet = sh.worksheet(worksheet_name)
        worksheet.clear()
        worksheet.update([df_to_save.columns.values.tolist()] + df_to_save.values.tolist())
        return True
    except Exception as e:
        st.error(f"Feil ved lagring: {e}")
        return False

if st.sidebar.button("🔴 Logg ut"):
    st.session_state.clear()
    st.rerun()

# =================================================================
# 🏦 FINAL PROFESSIONAL BANKING MESSAGING HUB (UPGRADED)
# =================================================================

def display_bank_messaging_hub(sak_id, chat_data, role, username, agent_name):
    st.markdown("---")
    # Professional Labeling: Ansatt ko sirf "BANK" dikhega
    target_label = "BANK" if role not in ["Admin", "Director"] else agent_name.upper()
    st.subheader(f"💬 Meldinger med {target_label}")

    # Professional Chat Styling (Updated for Delete button alignment)
    st.markdown("""
        <style>
        .bank-bubble { background-color: #E1F5FE; border-left: 5px solid #0288D1; padding: 12px; border-radius: 10px; margin: 8px 0; color: black; }
        .agent-bubble { background-color: #F5F5F5; border-right: 5px solid #757575; padding: 12px; border-radius: 10px; margin: 8px 0; text-align: right; color: black; }
        </style>
    """, unsafe_allow_html=True)

    try:
        messages = json.loads(chat_data) if chat_data and str(chat_data) != 'nan' else []
    except:
        messages = []

    # --- SMART LOGIC: Auto-Mark as Read ---
    has_unread = False
    for m in messages:
        if role not in ["Admin", "Director"] and m.get('role') == "Bank" and m.get('read') == False:
            m['read'] = True
            has_unread = True
        elif role in ["Admin", "Director"] and m.get('role') == "Agent" and m.get('read') == False:
            m['read'] = True
            has_unread = True

    if has_unread:
        update_sak_in_sheet(sak_id, {"Chat_History": json.dumps(messages)})

    # --- DISPLAY MESSAGES WITH DELETE CONTROL ---
    for idx, msg in enumerate(messages):
        is_bank = msg['role'] == "Bank"
        div_class = "bank-bubble" if is_bank else "agent-bubble"
        display_name = "BANK" if is_bank and role not in ["Admin", "Director"] else msg["sender"]
        
        # Grid for Message + Delete Button
        m_col, d_col = st.columns([0.9, 0.1])
        
        with m_col:
            st.markdown(f'<div class="{div_class}"><b>{display_name}</b><br>{msg["text"]}<br><small style="color: grey;">{msg["time"]}</small></div>', unsafe_allow_html=True)
        
        with d_col:
            # SIRF ADMIN SAB KUCH DELETE KAR SAKTA HAI
            if role in ["Admin", "Director"]:
                if st.button("🗑️", key=f"del_{sak_id}_{idx}", help="Slett denne meldingen permanent"):
                    messages.pop(idx)
                    if update_sak_in_sheet(sak_id, {"Chat_History": json.dumps(messages)}):
                        st.rerun()

    st.divider()

    # Input Section (100% Same)
    col_msg, col_file = st.columns([3, 1])
    msg_input = col_msg.text_input(f"Skriv melding til {target_label}...", key=f"input_{sak_id}")
    u_file = col_file.file_uploader("📎", key=f"file_{sak_id}")

    if st.button("🚀 Send Melding", key=f"send_{sak_id}"):
        if msg_input or u_file:
            full_txt = msg_input
            if u_file: full_txt += f"\n\n📎 **Vedlegg:** {u_file.name}"
            
            new_msg = {
                "role": "Bank" if role in ["Admin", "Director"] else "Agent",
                "sender": "BANK" if role in ["Admin", "Director"] else username.upper(),
                "text": full_txt,
                "time": get_norway_time(), 
                "read": False 
            }
            messages.append(new_msg)
            if update_sak_in_sheet(sak_id, {"Chat_History": json.dumps(messages)}):
                st.rerun()
                
# --- 6. DASHBORD (100% PURANA CODE + SMART NOTIFICATIONS & BANKING HUB) ---
if valg == "📊 Dashbord":
    st.header(f"Oversikt - {current_user.capitalize()}")
    
    if not df.empty:
        # Role wise filter: Admin sab dekh sakta hai, Ansatt sirf apni sak (100% SAME)
        if role in ["Admin", "Director"]:
            view_data = df
        else:
            view_data = df[df['Saksbehandler'].astype(str).str.lower() == current_user.lower()]
        
        # --- NEW: ADVANCED NOTIFICATION SYSTEM (Professional Jump Logic) ---
        unread_saker = []
        for i, r in view_data.iterrows():
            chat_h = str(r.get('Chat_History', ''))
            # Check unread messages based on role
            if role in ["Admin", "Director"]:
                if '"role": "Agent"' in chat_h and '"read": false' in chat_h.lower():
                    unread_saker.append({"navn": r.get('Navn', 'Ukjent'), "id": r.get('ID', i)})
            else:
                if '"role": "Bank"' in chat_h and '"read": false' in chat_h.lower():
                    unread_saker.append({"navn": r.get('Navn', 'Ukjent'), "id": r.get('ID', i)})

        if unread_saker:
            st.markdown("### 🔔 Varsler")
            for sak in unread_saker:
                # Jab is button par click hoga, system "Kunde Arkiv" par jump karega aur sak filter kar dega
                if st.button(f"📩 Ny melding i sak: {sak['navn']} (ID: {sak['id']})", key=f"notif_{sak['id']}"):
                    st.session_state.search_query = str(sak['id']) 
                    st.session_state.active_tab = "📂 Kunde Arkiv" 
                    st.rerun()

        # --- METRICS SECTION (Oversikt bars - 100% SAME AS YOURS) ---
        c1, c2, c3 = st.columns(3)
        
        loan_col = 'Lånebeløp' if 'Lånebeløp' in view_data.columns else view_data.columns[0] 
        total_v = pd.to_numeric(view_data[loan_col], errors='coerce').sum()
        
        c1.metric("Antall Saker", len(view_data))
        c2.metric("Total Volum (kr)", f"{total_v:,.0f} kr")
        c3.metric("Provisjon (1%)", f"{total_v * 0.01:,.0f} kr")
        
        st.divider()
        st.subheader("Siste Registrerte Saker")

        # --- SAKER LIST SECTION (Displaying last 15 cases - 100% SAME LOGIC) ---
        for i, r in view_data.tail(15).iterrows():
            # Data extraction with safety
            hoved = r.get('Hovedsøker', 'N/A')
            belop = r.get('Lånebeløp', '0')
            b_status = r.get('Bank_Status', 'Mottatt')
            mangler_msg = r.get('Mangler', '') 
            sak_id = r.get('ID', i)
            chat_h = r.get('Chat_History', '')
            agent_navn = r.get('Saksbehandler', 'Agent')

            # Status Icons (100% SAME)
            if b_status == "Mottatt":
                st_icon = "🔵"
            elif b_status == "Under Behandling":
                st_icon = "🟡"
            elif b_status == "Godkjent":
                st_icon = "🟢"
            else:
                st_icon = "🔴"
            
            # Har case ke liye ek Expander
            with st.expander(f"{st_icon} {hoved} | {belop} kr | Status: {b_status}"):
                
                # --- BANKING CHAT HUB (Integrated) ---
                display_bank_messaging_hub(sak_id, chat_h, role, current_user, agent_navn)
                
                st.divider()

                # --- OLD MESSAGING SYSTEM REMOVED (As requested) ---
                # Purana error aur info block yahan se delete kar diya gaya hai.

                # --- FULL INFO DISPLAY (Aapka loop jo saara data dikhata hai - 100% SAME) ---
                st.markdown("### 📄 Saksinformasjon")
                
                inf_c1, inf_c2 = st.columns(2)
                for count, (col_name, value) in enumerate(r.items()):
                    if col_name in ['Mangler', 'Chat_History']: 
                        continue
                    
                    target_col = inf_c1 if count % 2 == 0 else inf_c2
                    target_col.write(f"**{col_name}:** {value}")
                
                # --- MODIFICATION SYSTEM (Aapka purana system - 100% SAME) ---
                st.markdown("---")
                st.write("🔧 **Rediger Sak / Svar til Admin**")
                
                old_notater = str(r.get('Notater', ''))
                new_notater = st.text_area("Oppdater Notater / Legg til info", value=old_notater, key=f"edit_not_{i}")
                
                ansatt_reply = ""
                if role == "Ansatt":
                    ansatt_reply = st.text_input("Skriv svar til Admin (Status update)", key=f"ans_rep_{i}")
                    
                if st.button("💾 Lagre Endringer", key=f"save_mod_{i}"):
                    final_msg = ansatt_reply if role == "Ansatt" and ansatt_reply.strip() != "" else mangler_msg
                    
                    updates = {
                        "Notater": new_notater,
                        "Mangler": final_msg
                    }
                    
                    with st.spinner("Oppdaterer databasen..."):
                        success = update_sak_in_sheet(sak_id, updates)
                        if success:
                            st.success(f"✅ Sak {sak_id} er oppdatert!")
                            st.rerun()
                        else:
                            st.error("Kunne ikke koble til Google Sheets.")
                            
    else:
        st.warning("Ingen data tilgjengelig i databasen ennå.")
        

# --- 7. NY REGISTRERING (100% ORIGINAL LOGIC + BANKING HUB INTEGRATION) ---
elif valg == "➕ Ny Registrering":
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
            f_eier = bc2.text_area("Navn & Personnummer pe alle eiere")
            f_aksjer = bc2.text_input("Aksjefordeling (%)")
            st.divider()

        # --- 👤 HOVEDSØKER SECTION ---
        st.subheader("👤 Hovedsøker Detaljer")
        c1, c2 = st.columns(2)
        navn = c1.text_input("Fullt Navn (Hovedsøker) *") 
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

        # NEW: Finansiell Status for Hovedsøker
        st.markdown("#### 🏠 Finansiell Status & Gjeld (Hovedsøker)")
        hf1, hf2, hf3 = st.columns(3)
        h_ek = hf1.number_input("Egenkapital (kr) - Hoved", 0, step=10000, format="%d")
        h_sfo = hf2.selectbox("SFO / Barnehage utgifter? - Hoved", ["Nei", "Ja"])
        h_gjeld = hf3.number_input("Eksisterende Gjeld (kr) - Hoved", 0, step=10000, format="%d")

        # --- 👥 MEDSØKER SECTION ---
        m_navn, m_fnr, m_epost, m_tlf, m_sivil, m_pass, m_botid = "", "", "", "", "Gift", "Norge", ""
        m_lonn, m_arb, m_ansatt_tid, m_stilling, m_ekstra, m_pst = 0, "", "", "Fast ansatt", 0, 100
        m_ek, m_sfo, m_gjeld = 0, "Nei", 0
        
        if has_med:
            st.divider()
            st.subheader("👥 Medsøker Detaljer (100% Symmetric Profile)")
            mc1, mc2 = st.columns(2)
            m_navn = mc1.text_input("Fullt Navn (Medsøker)")
            m_fnr = mc1.text_input("Fødselsnummer (11 siffer - Medsøker)")
            m_epost = mc1.text_input("E-post (Medsøker)")
            m_tlf = mc2.text_input("Telefon (Medsøker)")
            m_sivil = mc2.selectbox("Sivilstatus (Medsøker)", ["Enslig", "Gift", "Samboer", "Skilt"], key="ms_sivil")
            m_pass = mc1.selectbox("Statsborgerskap (Medsøker)", countries, key="ms_pass")
            m_botid = mc2.text_input("Botid i Norge (Medsøker)", key="ms_botid")

            st.markdown("#### 💼 Arbeid & Inntekt (Medsøker)")
            ml1, ml2, ml3 = st.columns(3)
            m_lonn = ml1.number_input("Årslønn Brutto (Medsøker)", min_value=0, step=1000, format="%d", key="ms_lonn")
            m_arb = ml2.text_input("Arbeidsgiver (Medsøker)", key="ms_arb")
            m_ansatt_tid = ml3.text_input("Ansettelsestid (Medsøker)", key="ms_time")
            m_stilling = ml1.selectbox("Ansettelsesform (Medsøker)", ["Fast ansatt", "Midlertidig", "Selvstendig"], key="ms_form")
            m_ekstra = ml2.number_input("Bi-inntekt (Medsøker)", 0, key="ms_extra")
            m_pst = ml3.slider("Stillingsprosent (Medsøker)", 0, 100, 100, key="ms_pst")

            st.markdown("#### 🏠 Finansiell Status & Gjeld (Medsøker)")
            mf1, mf2, mf3 = st.columns(3)
            m_ek = mf1.number_input("Egenkapital (kr) - Medsøker", 0, step=10000, format="%d", key="ms_ek")
            m_sfo = mf2.selectbox("SFO / Barnehage? - Medsøker", ["Nei", "Ja"], key="ms_sfo")
            m_gjeld = mf3.number_input("Eksisterende Gjeld (kr) - Medsøker", 0, step=10000, format="%d", key="ms_gjeld")

        st.divider()
        st.subheader("📊 Felles Lånesøknad")
        f1, f2, f3 = st.columns(3)
        belop = f1.number_input("Ønsket Lånebeløp (kr)", 0, step=10000, format="%d")
        barn = f2.number_input("Antall Barn totalt (under 18 år)", 0)
        biler = f3.number_input("Antall Biler totalt", 0)

        notater = st.text_area("Interne Notater (Viktig info for banken)")
        st.file_uploader("Last opp Vedlegg (PDF/Bilder)")

        if st.form_submit_button("🚀 SEND SØKNAD TIL BANKEN"):
            if not navn:
                st.error("Vennligst skriv inn navnet på Hovedsøker!")
            else:
                # Calculations for Sheet columns
                tot_ek = h_ek + m_ek
                tot_gjeld = h_gjeld + m_gjeld
                
                # --- NEW: Initial Banking Chat Message ---
                initial_chat = json.dumps([{
                    "role": "Bank",
                    "sender": "BANK CENTRAL",
                    "text": "Velkommen! Vi har mottatt din søknad og vil behandle den fortløpende. Sjekk denne chatten for oppdateringer.",
                    "time": datetime.now().strftime("%d-%m-%Y %H:%M")
                }])
                
                new_row = [
                    len(df)+1, 
                    datetime.now().strftime("%d-%m-%Y"), 
                    prod, 
                    navn, 
                    fnr, 
                    epost, 
                    tlf, 
                    sivil,
                    "Bedrift" if is_bedrift else "Privat", 
                    "Active", 
                    f_navn if is_bedrift else "", 
                    lonn,
                    barn, 
                    h_sfo, 
                    tot_ek, 
                    tot_gjeld, 
                    biler, 
                    belop, 
                    f_org if is_bedrift else "",
                    f_eier if is_bedrift else "", 
                    f_aksjer if is_bedrift else "",
                    m_navn, 
                    m_fnr, 
                    m_epost, 
                    m_tlf, 
                    m_lonn, 
                    m_arb, 
                    notater,
                    f"P1: {pass_land} | P2: {m_pass} | Botid: {botid}", 
                    current_user, 
                    "Mottatt",
                    "", # Mangler column
                    initial_chat # Maya: New Chat_History column data
                ]
                
                add_data("MainDB", new_row)
                st.success(f"✅ Søknad på {belop:,.0f} kr registrert!")
                st.balloons()
                
# --- 8. KUNDE ARKIV (PRO UPGRADE: SMART JUMP & AUTO-OPEN) ---
elif valg == "📂 Kunde Arkiv":
    st.header("📂 Kunde Arkiv - Full Oversikt")
    
    # --- SMART JUMP LOGIC: Dashboard se click karke aane walon ke liye ---
    jump_id = st.session_state.get('search_query', "")
    
    # 1. Filtering logic (100% Same as your original)
    view_df = df if role in ["Admin", "Director"] else df[df['Saksbehandler'].astype(str).str.lower() == current_user.lower()]
    
    # 2. Search Box (Pre-filled if coming from notification)
    sok = st.text_input("🔍 Søk kunde (Navn, ID, Tlf)...", value=jump_id, placeholder="Skriv her...")
    
    # Agar search box empty ho jaye to session_state clear karein taake jump lock na ho
    if not sok and 'search_query' in st.session_state:
        st.session_state.search_query = ""

    if sok:
        view_df = view_df[view_df.astype(str).apply(lambda x: x.str.contains(sok, case=False)).any(axis=1)]

    st.info(f"Antall saker funnet: {len(view_df)}")

    for i, r in view_df.iterrows():
        sak_id = r.get('ID', i)
        mangler_msg = r.get('Mangler', '') 
        chat_h = str(r.get('Chat_History', '')) 
        agent_navn = r.get('Saksbehandler', 'Agent') 
        
        # --- SMART NOTIFICATION LOGIC (NEW: SENDER CHECK) ---
        is_unread = False
        # Admin ko tab dikhega jab aakhri message Agent ne bheja ho
        if role in ["Admin", "Director"]:
            if '"role": "Agent"' in chat_h and '"read": false' in chat_h.lower():
                is_unread = True
        # Agent ko tab dikhega jab aakhri message Bank/Admin ne bheja ho
        else:
            if '"role": "Bank"' in chat_h and '"read": false' in chat_h.lower():
                is_unread = True
            
        alert_tag = "🔴 NY MELDING | " if is_unread else ""
        
        # --- AUTO-EXPAND LOGIC: Matches search or jump ID ---
        expand_me = True if (sok and str(sak_id) == str(sok)) else False

        with st.expander(f"{alert_tag}📁 {r.get('Navn', 'Ukjent')} | ID: {sak_id} | Status: {r.get('Bank_Status', 'Mottatt')}", expanded=expand_me):
            
            # Checkbox for switching between View and Edit mode
            show_edit = st.checkbox(f"🛠️ Aktiver Redigering / Modify (ID: {sak_id})", key=f"mod_check_{sak_id}")

            if not show_edit:
                # --- A: VIEW MODE (100% Purana Look - Not a single dot changed) ---
                st.markdown(f"### 📄 Sak Detaljer (Fil-visning)")
                v1, v2, v3 = st.columns(3)
                with v1:
                    st.write(f"**Navn:** {r.get('Navn', '-')}")
                    st.write(f"**Fnr:** {r.get('Fnr', '-')}")
                    st.write(f"**Epost:** {r.get('Epost', '-')}")
                    st.write(f"**Tlf:** {r.get('Tlf', '-')}")
                with v2:
                    st.write(f"**Produkt:** {r.get('Produkt', '-')}")
                    st.write(f"**Lånebeløp:** {r.get('Lånebeløp', '0')} kr")
                    st.write(f"**Lønn:** {r.get('Lønn', '0')} kr")
                    st.write(f"**EK:** {r.get('EK', '0')} kr")
                with v3:
                    st.write(f"**Gjeld:** {r.get('Gjeld', '0')} kr")
                    st.write(f"**Sivilstatus:** {r.get('Sivilstatus', '-')}")
                    st.write(f"**Dato:** {r.get('Dato', '-')}")

                st.divider()
                if r.get('Medsøker_Navn'):
                    st.markdown("**👥 Medsøker Info:**")
                    mv1, mv2 = st.columns(2)
                    mv1.write(f"**Navn:** {r.get('Medsøker_Navn')}")
                    mv2.write(f"**Fnr:** {r.get('Medsøker_Fnr')}")
                
                st.write(f"**Notater:** {r.get('Notater', 'Ingen notater')}")

                # --- INTEGRATED MESSAGING HUB ---
                display_bank_messaging_hub(sak_id, chat_h, role, current_user, agent_navn)

            else:
                # --- B: MODIFICATION MODE (100% Purana Look - Safe & Intact) ---
                st.subheader("🛠️ Full Redigeringsmodus")
                
                with st.form(key=f"edit_form_final_{sak_id}"):
                    st.markdown("#### 👤 Hovedsøker Detaljer")
                    h1, h2 = st.columns(2)
                    up_navn = h1.text_input("Fullt Navn", value=str(r.get('Navn', '')))
                    up_fnr = h1.text_input("Fødselsnummer", value=str(r.get('Fnr', '')))
                    up_epost = h2.text_input("E-post", value=str(r.get('Epost', '')))
                    up_tlf = h2.text_input("Telefon", value=str(r.get('Tlf', '')))
                    
                    st.markdown("#### 💼 Økonomi")
                    a1, a2 = st.columns(2)
                    up_lonn = a1.text_input("Lønn (kr)", value=str(r.get('Lønn', '0')))
                    up_gjeld = a1.text_input("Gjeld (kr)", value=str(r.get('Gjeld', '0')))
                    up_belop = a2.text_input("Lånebeløp (kr)", value=str(r.get('Lånebeløp', '0')))
                    up_ek = a2.text_input("EK (kr)", value=str(r.get('EK', '0')))

                    st.markdown("#### 👥 Medsøker")
                    m1, m2 = st.columns(2)
                    up_m_navn = m1.text_input("Medsøker Navn", value=str(r.get('Medsøker_Navn', '')))
                    up_m_fnr = m1.text_input("Medsøker Fnr", value=str(r.get('Medsøker_Fnr', '')))
                    up_m_lonn = m2.text_input("Medsøker Lønn", value=str(r.get('Medsøker_Lønn', '0')))
                    up_m_tlf = m2.text_input("Medsøker Tlf", value=str(r.get('Medsøker_Tlf', '')))

                    st.markdown("#### ⚙️ Status & Notater")
                    up_mangler = st.text_area("Admin Melding (Mangler)", value=str(mangler_msg))
                    
                    current_status = r.get('Bank_Status', 'Mottatt')
                    status_options = ["Mottatt", "Under Behandling", "Godkjent", "Avslått", "Utbetalt"]
                    try:
                        status_idx = status_options.index(current_status)
                    except:
                        status_idx = 0

                    up_st = st.selectbox("Bank Status", status_options, index=status_idx)
                    up_notat = st.text_area("Notater", value=str(r.get('Notater', '')))

                    if st.form_submit_button("💾 Lagre Alle Endringer"):
                        final_data = {
                            "Navn": up_navn, "Fnr": up_fnr, "Epost": up_epost, "Tlf": up_tlf,
                            "Lønn": up_lonn, "Gjeld": up_gjeld, "Lånebeløp": up_belop, "EK": up_ek,
                            "Medsøker_Navn": up_m_navn, "Medsøker_Fnr": up_m_fnr, 
                            "Medsøker_Lønn": up_m_lonn, "Medsøker_Tlf": up_m_tlf,
                            "Bank_Status": up_st, "Notater": up_notat, "Mangler": up_mangler
                        }
                        if update_sak_in_sheet(sak_id, final_data):
                            st.success("✅ Sak oppdatert!")
                            st.rerun()
                            
# --- 9. MASTER KONTROLLPANEL ---
elif valg == "🕵️ Master Kontrollpanel" and role in ["Admin", "Director"]:
    st.header("🕵️ Ny Agent Registrering")
    with st.form("agent_form"):
        u = st.text_input("Brukernavn").lower().strip()
        p = st.text_input("Passord", type="password")
        n = st.text_input("Fullt Navn")
        pos = st.selectbox("Stilling", ["Senior Agent", "Junior Agent", "Trainee"])
        if st.form_submit_button("✅ Aktiver og Lagre Agent"):
            add_data("Users", [u, p, "Worker"])
            add_data("Agents", [u, n, pos, "09-17", "Aktiv", "Signed"])
            st.success(f"Agent {n} aktivert!")
    st.divider()
    st.subheader("👥 Ansatte Liste")
    agents_df = get_data("Agents")
    st.table(agents_df[['username', 'navn', 'stilling', 'status']])

# --- 10. ANSATTE KONTROLL (FULL RE-INTEGRATION + MODIFICATION ENGINE) ---
elif valg == "👥 Ansatte Kontroll" and role in ["Admin", "Director"]:
    st.header("👥 Ansatte Oversikt og Kontroll")
    
    # --- SMART DATA LOADING (To fix Quota 429 Error) ---
    # Hum function ko yahan define kar rahe hain taake cache apply ho sake
    @st.cache_data(ttl=60)
    def get_agents_cached():
        return get_data("Agents")

    try:
        agents_df = get_agents_cached()
        main_df = df # Global load
    except Exception as e:
        st.error(f"Kunne ikke hente agents: {e}")
        agents_df = pd.DataFrame()

    if not agents_df.empty:
        # 1. Search Box (Aapka original search logic)
        sok_agent = st.text_input("🔍 Søk etter ansatt (Navn/ID)...", placeholder="Skriv brukernavn eller navn...")
        
        if sok_agent:
            agents_df = agents_df[agents_df.astype(str).apply(lambda x: x.str.contains(sok_agent, case=False)).any(axis=1)]

        st.write(f"Totalt **{len(agents_df)}** ansatte funnet.")
        st.divider()

        for i, row in agents_df.iterrows():
            a_user = str(row.get('username', '')).strip().lower()
            a_navn = row.get('navn', 'Ukjent')
            
            with st.expander(f"👤 {a_navn} (ID: {a_user})"):
                col1, col2 = st.columns(2)
                
                # --- Agent Details (PURANA CODE - 100% Same) ---
                with col1:
                    st.markdown(f"**Stilling:** `{row.get('stilling', '-')}`")
                    st.markdown(f"**Vakt:** `{row.get('vakt', '-')}`")
                    st.markdown(f"**Nåværende Status:** `{row.get('status', '-')}`")
                
                # --- Performance Metrics (PURANA CODE - 100% Same) ---
                agent_saker = main_df[main_df['Saksbehandler'].astype(str).str.lower() == a_user] if not main_df.empty else pd.DataFrame()
                
                with col2:
                    if not agent_saker.empty:
                        antall = len(agent_saker)
                        l_col = 'Lånebeløp' if 'Lånebeløp' in agent_saker.columns else agent_saker.columns[0]
                        volum = pd.to_numeric(agent_saker[l_col], errors='coerce').sum()
                        st.metric("📦 Saker Registrert", antall)
                        st.write(f"💰 **Total Volum:** {volum:,.0f} kr")
                    else:
                        st.info("Ingen saker registrert ennå.")

                st.divider()
                
                # --- Actions (Slette, Se Saker, Endre Status - PURANA CODE) ---
                act1, act2, act3 = st.columns(3)
                
                with act1:
                    if st.button(f"📂 Se Saker", key=f"v_saker_{i}"):
                        if not agent_saker.empty:
                            st.subheader(f"Saker for {a_navn}")
                            for idx, s_row in agent_saker.iterrows():
                                sak_id = s_row.get('ID', idx)
                                with st.expander(f"📄 Sak: {s_row.get('Hovedsøker', 'Kunde')} (ID: {sak_id})"):
                                    cols = st.columns(2)
                                    for count, (col_name, col_val) in enumerate(s_row.items()):
                                        if col_name != 'Mangler': 
                                            target_col = cols[0] if count % 2 == 0 else cols[1]
                                            target_col.write(f"**{col_name}:** {col_val}")

                                    st.markdown("---")
                                    st.write("🔧 **Admin Action: Status & Messaging**")
                                    
                                    status_options = ["Mottatt", "Under Behandling", "Godkjent", "Avslått", "Utbetalt"]
                                    current_bank_st = s_row.get('Bank_Status', 'Mottatt')
                                    st_idx = status_options.index(current_bank_st) if current_bank_st in status_options else 0
                                    
                                    new_bank_st = st.selectbox("Oppdater Sak Status", status_options, index=st_idx, key=f"st_edit_{idx}_{i}")
                                    
                                    mangler_msg_val = s_row.get('Mangler', '')
                                    mangler_msg = st.text_area("Mangler dokumenter / Melding til ansatt", 
                                                               value=str(mangler_msg_val) if str(mangler_msg_val).lower() != 'nan' else "", 
                                                               placeholder="Skriv her...",
                                                               key=f"msg_edit_{idx}_{i}")
                                    
                                    if st.button(f"🚀 Lagre & Send Live (ID:{sak_id})", key=f"sv_edit_{idx}_{i}"):
                                        updates = {"Bank_Status": new_bank_st, "Mangler": mangler_msg}
                                        with st.spinner("Oppdaterer Google Sheets..."):
                                            success = update_sak_in_sheet(sak_id, updates)
                                            if success:
                                                st.success(f"✅ Sak {sak_id} er oppdatert!")
                                                st.rerun()
                        else:
                            st.warning("Ingen data funnet.")

                with act2:
                    status_options = ["Aktiv", "Inaktiv", "Permisjon"]
                    current_s = row.get('status', 'Aktiv')
                    try: idx_s = status_options.index(current_s)
                    except: idx_s = 0
                    
                    n_st = st.selectbox("Endre Agent Status", status_options, index=idx_s, key=f"st_sel_{i}")
                    if st.button("💾 Oppdater Agent", key=f"upd_btn_{i}"):
                        st.success(f"Agent status oppdatert til {n_st}")

                with act3:
                    if st.button(f"🗑️ Slette Profil", key=f"del_btn_{i}"):
                        if role == "Admin":
                            with st.spinner(f"Sletter {a_user}..."):
                                try:
                                    success = delete_user_completely(a_user)
                                    if success:
                                        st.success(f"✅ Agent {a_user} er slettet!")
                                        st.rerun()
                                except:
                                    st.error("Kunne ikke slette. Sjekk om funksjonen 'delete_user_completely' finnes.")
                        else:
                            st.warning("Kun Admin kan slette ansatte.")
    else:
        st.warning("Ingen ansatte funnet i databasen.")
        
# --- 11. KONTAKTER (ADVANCED OVERSIKT + AUTO-TIME) ---
elif valg == "📇 Kontakter":
    st.header("📇 Kontaktadministrasjon")
    
    import pandas as pd
    import smtplib
    from datetime import datetime
    from email.mime.text import MIMEText

    # INTERNAL SAVE/UPDATE FUNCTION
    def update_sheet_data_internal(worksheet_name, df):
        try:
            creds_dict = st.secrets["gcp_service_account"]
            from google.oauth2.service_account import Credentials
            import gspread
            scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
            client = gspread.authorize(creds)
            sh = client.open_by_url(st.secrets["spreadsheet"])
            worksheet = sh.worksheet(worksheet_name)
            worksheet.clear()
            # DataFrame ko wapis sheet mein dalna
            worksheet.update([df.columns.values.tolist()] + df.values.tolist())
            return True
        except Exception as e:
            st.error(f"Feil ved lagring: {e}")
            return False

    # DATA HENTING
    try:
        contacts_df = get_data("Contacts")
        # Check if timestamp column exists
        if "Sist Endret" not in contacts_df.columns:
            contacts_df["Sist Endret"] = "N/A"
    except:
        contacts_df = pd.DataFrame(columns=["Navn", "E-post", "Telefon", "Sist Endret"])

    # Tabs with clean names as requested
    tab1, tab2, tab3 = st.tabs(["📇 Kontaktliste", "📩 Send E-post", "➕ Ny Kontakt"])

    # --- TAB 1: KONTAKTLISTE (With built-in Editing) ---
    with tab1:
        st.subheader("Oversikt over kontakter")
        
        if not contacts_df.empty:
            # Displaying the list
            st.dataframe(contacts_df, use_container_width=True, hide_index=True)
            
            st.divider()
            
            # Selection for Editing - Built inside the list tab
            selected_name = st.selectbox("Velg en kontakt for å endre detaljer:", ["-- Velg --"] + contacts_df["Navn"].tolist())
            
            if selected_name != "-- Velg --":
                idx = contacts_df[contacts_df["Navn"] == selected_name].index[0]
                last_time = contacts_df.at[idx, "Sist Endret"]
                
                # Showing the last modified time clearly
                st.info(f"⏱️ **Sist endret:** {last_time}")
                
                with st.expander(f"✏️ Redigerer: {selected_name}", expanded=True):
                    with st.form(f"edit_form_{selected_name}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            new_n = st.text_input("Navn", value=str(contacts_df.at[idx, "Navn"]))
                            new_e = st.text_input("E-post", value=str(contacts_df.at[idx, "E-post"]))
                        with col2:
                            new_t = st.text_input("Telefon", value=str(contacts_df.at[idx, "Telefon"]))
                        
                        if st.form_submit_button("💾 Lagre endringer"):
                            # Update timestamp automatically
                            now_time = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                            
                            contacts_df.at[idx, "Navn"] = new_n
                            contacts_df.at[idx, "E-post"] = new_e
                            contacts_df.at[idx, "Telefon"] = new_t
                            contacts_df.at[idx, "Sist Endret"] = now_time
                            
                            if update_sheet_data_internal("Contacts", contacts_df):
                                st.success(f"✅ Oppdatert! Tidspunkt: {now_time}")
                                st.cache_data.clear()
                                st.rerun()
        else:
            st.info("Listen er tom. Legg til en kontakt i 'Ny Kontakt' fanen.")

    # --- TAB 2: SEND E-POST ---
    with tab2:
        st.subheader("Send e-post til kontakt")
        with st.form("quick_mail"):
            rec = st.selectbox("Mottaker", [""] + contacts_df["E-post"].tolist())
            sub = st.text_input("Emne", "Melding fra Iqbal Entrepreneur")
            bod = st.text_area("Melding", height=200)
            if st.form_submit_button("🚀 Send E-post"):
                if rec and bod:
                    try:
                        s_mail = st.secrets["email_auth"]["sender_email"]
                        s_pass = st.secrets["email_auth"]["app_password"]
                        msg = MIMEText(bod)
                        msg['Subject'], msg['From'], msg['To'] = sub, s_mail, rec
                        with smtplib.SMTP('smtp.gmail.com', 587) as server:
                            server.starttls()
                            server.login(s_mail, s_pass)
                            server.sendmail(s_mail, rec, msg.as_string())
                        st.success(f"✅ E-post sendt til {rec}")
                    except Exception as e: 
                        st.error(f"Kunne ikke sende e-post: {e}")
                else:
                    st.warning("Vennligst fyll ut mottaker og melding.")

    # --- TAB 3: NY KONTAKT ---
    with tab3:
        st.subheader("Registrer ny kontakt")
        with st.form("new_con"):
            nn = st.text_input("Navn")
            ne = st.text_input("E-post")
            nt = st.text_input("Telefon")
            if st.form_submit_button("➕ Legg til i systemet"):
                if nn and ne:
                    now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                    new_row = pd.DataFrame([{"Navn":nn, "E-post":ne, "Telefon":nt, "Sist Endret":now}])
                    contacts_df = pd.concat([contacts_df, new_row], ignore_index=True)
                    if update_sheet_data_internal("Contacts", contacts_df):
                        st.success("✅ Kontakt er lagret!")
                        st.cache_data.clear()
                        st.rerun()
                else:
                    st.warning("Navn og e-post er påkrevd.")

# --- FOOTER (FIXED Error Line) ---
st.sidebar.markdown("---")
st.sidebar.caption("NSVG CRM v2.0 | © NORDIC SECURE VAULT GROUP")
