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

# --- 2. GOOGLE SHEETS CONNECTION ENGINE (Maya Optimized) ---

def connect_to_sheet(sheet_name):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        from oauth2client.service_account import ServiceAccountCredentials
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        # Yeh aapki main spreadsheet file ko open karega
        return client.open("NSVG_CRM_Data").worksheet(sheet_name)
    except Exception as e:
        st.error(f"Tilkoblingsfeil (Connection Error): {e}")
        return None

@st.cache_data(ttl=60)
def get_data(sheet_name):
    sh = connect_to_sheet(sheet_name)
    if sh:
        try:
            data = sh.get_all_records()
            df = pd.DataFrame(data)
            df.columns = [str(c).strip() for c in df.columns]
            return df
        except Exception as e:
            if "429" in str(e):
                st.error("Google API Limit nådd. Vent 60 sekunder...")
            return pd.DataFrame()
    return pd.DataFrame()

def add_data(sheet_name, row_list):
    sh = connect_to_sheet(sheet_name)
    if sh: 
        try:
            sh.append_row(row_list)
            st.cache_data.clear() # Cache clear taake naya data foran dikhe
            return True
        except Exception as e:
            st.error(f"Feil ved lagring av data: {e}")
            return False
    return False

# YE RHA NAYA UPDATED FUNCTION (Jo aapne manga tha)
def update_sheet_data_internal(worksheet_name, df):
    """
    Puri sheet ko naye data se update karne ke liye (Svar/Reply save karne ke liye).
    """
    sh = connect_to_sheet(worksheet_name)
    if sh:
        try:
            sh.clear()
            # NaN values ko handle karna taake Google Sheet error na de
            df_filled = df.fillna("")
            data_to_update = [df_filled.columns.values.tolist()] + df_filled.values.tolist()
            
            # Pure data ko A1 cell se start karke update karna (Zyada stable method)
            sh.update('A1', data_to_update)
            st.cache_data.clear() # Cache mitaein taake naya jawab foran dikhe
            return True
        except Exception as e:
            st.error(f"⚠️ Google Sheets Update Error: {e}")
            return False
    return False

# AAPKA DELETE FUNCTION (Yeh skip nahi hua!)
def delete_sak_from_sheet(sak_id): 
    """ 
    Google Sheet se specific ID wali row ko delete karne ka function.
    """
    try:
        sh = connect_to_sheet("MainDB")
        if sh:
            rows = sh.get_all_records()
            for index, row in enumerate(rows):
                if str(row.get('ID')) == str(sak_id):
                    # +2 adjustment (1 for header, 1 for 0-index)
                    row_to_delete = index + 2
                    sh.delete_rows(row_to_delete)
                    st.cache_data.clear()
                    return True
        else:
            st.error("Kunne ikke koble til databasen (MainDB).")
            return False
        return False
    except Exception as e:
        st.error(f"⚠️ Database Error ved sletting: {e}")
        return False
        
# --- 3. CACHING COUNTRIES (SPEED BOOSTER) ---
@st.cache_data
def get_country_list():
    base = ["Norge", "Sverige", "Danmark", "UK", "USA", "Pakistan", "India"]
    others = sorted(["Afghanistan", "Albania", "Algerie", "Andorra", "Angola", "Argentina", "Australia", "Bangladesh", "Belgia", "Brasil", "Canada", "Chile", "China", "Egypt", "Finland", "Frankrike", "Hellas", "Island", "Iran", "Irak", "Irland", "Italia", "Japan", "Jordan", "Kuwait", "Latvia", "Libanon", "Malaysia", "Mexico", "Marokko", "Nederland", "New Zealand", "Nigeria", "Oman", "Filippinene", "Polen", "Portugal", "Qatar", "Romania", "Russland", "Saudi Arabia", "Singapore", "Spania", "Sri Lanka", "Sudan", "Sveits", "Syria", "Thailand", "Tunisia", "Tyrkia", "UAE", "Ukraina", "Vietnam"])
    return base + others
    
# --- 4. LOGIN SYSTEM ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user_role': None, 'user_id': None, 'navn': None})

if not st.session_state['logged_in']:
    st.title("🛡️ NSVG - Sikker Digital Portal")
    u_input = st.text_input("Brukernavn").lower().strip()
    p_input = st.text_input("Passord", type="password")
    
    if st.button("Logg inn"):
        users_df = get_data("Users")
        if not users_df.empty:
            match = users_df[(users_df['username'].astype(str).str.lower() == u_input) & 
                             (users_df['password'].astype(str) == p_input)]
            
            if not match.empty:
                # Role aur ID save karna
                role = match.iloc[0]['role']
                st.session_state.update({'logged_in': True, 'user_role': role, 'user_id': u_input})
                
                # --- NEW: Agents ki sheet se Full Name nikalna ---
                try:
                    agents_df = get_data("Agents")
                    # Username match karke naam uthana
                    agent_match = agents_df[agents_df['username'].astype(str).str.lower() == u_input]
                    if not agent_match.empty:
                        st.session_state['navn'] = agent_match.iloc[0]['navn']
                    else:
                        st.session_state['navn'] = u_input # Agar naam na mile to ID hi sahi
                except:
                    st.session_state['navn'] = u_input
                # -----------------------------------------------
                
                st.success(f"Velkommen, {st.session_state['navn']}!")
                st.rerun()
            else: 
                st.error("Feil brukernavn ya passord!")
    st.stop()


# --- 5. GLOBAL DATA & SIDEBAR (STABLE CONNECTED VERSION - SAKSBEHANDLER UPDATE) ---

if st.session_state.get('logged_in'):
    raw_user = str(st.session_state.get('user_id', 'Guest')).lower().strip()
    
    # BEDI PEHCHAN: Role define ho raha hai lekin features Ansatt wale bhi rahen ge
    if raw_user == "bedi":
        role = "Saksbehandler"
    else:
        role = st.session_state.get('user_role', 'Guest')
        
    # FIX: Pehle check karein ke 'navn' (Name) hai, warna user_id dikhaye
    username = st.session_state.get('navn') or st.session_state.get('user_id') or "Bruker"
    current_user = st.session_state.get('user_id', 'Guest')
else:
    role = "Guest"
    username = "Guest"
    current_user = "Guest"

import pandas as pd
try:
    # Data fetching logic
    df = get_data("MainDB") 
    if df is None or df.empty:
        df = get_data("Kunder")
except Exception as e:
    st.error(f"Data loading error: {e}")
    df = pd.DataFrame()

# --- DYNAMIC NAVIGATION LOGIC (THE FIX - BEDI FULL FEATURES RESTORED) ---
if role in ["Admin", "Director"]:
    options = [
        "📊 Dashbord", 
        "➕ Ny Registrering", 
        "📂 Kunde Arkiv", 
        "👥 Ansatte Kontroll", 
        "📇 Kontakter", 
        "💼 Saksbehandler Panel", 
        "🕵️ Master Kontrollpanel"
    ]
elif role == "Saksbehandler":
    # BEDI/SAKSBEHANDLER KE LIYE: Saare Ansatt features + Saksbehandler menu merge kar diye
    options = [
        "📊 Dashbord", 
        "➕ Ny Registrering", 
        "📥 Nye Oppgaver",      # Saksbehandler Feature
        "📂 Kunde Arkiv", 
        "🏦 Bank Portaler",      # Saksbehandler Feature
        "🏦 Bankens Renters",    # Ansatt Feature (Restored)
        "📜 Dokumentmaler",      # Ansatt Feature (Restored)
        "📞 Support Center"      # Ansatt Feature (Restored)
    ]
else:
    # Regular Ansatt (Employees)
    options = [
        "📊 Dashbord", 
        "➕ Ny Registrering", 
        "📂 Kunde Arkiv", 
        "🏦 Bankens Renters", 
        "📜 Dokumentmaler", 
        "📞 Support Center"
    ]

valg = st.sidebar.selectbox("Hovedmeny", options)

# --- INTERNAL FUNCTIONS ---
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
# 🏦 FINAL PROFESSIONAL BANKING MESSAGING HUB (STABLE VERSION)
# =================================================================

def display_bank_messaging_hub(sak_id, chat_data, role, username, agent_name):
    st.markdown("---")
    me_clean = str(username).lower().strip()
    target_label = "BANK" if role not in ["Admin", "Director"] else agent_name.upper()
    
    st.subheader(f"💬 Meldinger med {target_label}")

    st.markdown("""
        <style>
        .bank-bubble { background-color: #E1F5FE; border-left: 5px solid #0288D1; padding: 12px; border-radius: 10px; margin: 8px 0; color: black; }
        .agent-bubble { background-color: #F5F5F5; border-right: 5px solid #757575; padding: 12px; border-radius: 10px; margin: 8px 0; text-align: right; color: black; }
        </style>
    """, unsafe_allow_html=True)

    try:
        import json
        messages = json.loads(chat_data) if chat_data and str(chat_data) != 'nan' else []
    except:
        messages = []

    has_unread = False
    for m in messages:
        m_sender = str(m.get('sender', '')).lower().strip()
        if m.get('read') == False and m_sender != me_clean:
            m['read'] = True
            has_unread = True

    if has_unread:
        update_sak_in_sheet(sak_id, {"Chat_History": json.dumps(messages)})

    for idx, msg in enumerate(messages):
        is_bank = msg['role'] == "Bank"
        div_class = "bank-bubble" if is_bank else "agent-bubble"
        sender_raw = msg.get("sender", "SYSTEM")
        display_name_msg = "BANK" if is_bank and role not in ["Admin", "Director"] else sender_raw.upper()
        
        m_col, d_col = st.columns([0.9, 0.1])
        with m_col:
            st.markdown(f'<div class="{div_class}"><b>{display_name_msg}</b><br>{msg["text"]}<br><small style="color: grey;">{msg["time"]}</small></div>', unsafe_allow_html=True)
        with d_col:
            if role in ["Admin", "Director"]:
                if st.button("🗑️", key=f"del_{sak_id}_{idx}"):
                    messages.pop(idx)
                    update_sak_in_sheet(sak_id, {"Chat_History": json.dumps(messages)})
                    st.rerun()

    st.divider()
    col_msg, col_file = st.columns([3, 1])
    msg_input = col_msg.text_input(f"Skriv melding...", key=f"input_{sak_id}")
    u_file = col_file.file_uploader("📎", key=f"file_{sak_id}")

    if st.button("🚀 Send Melding", key=f"send_{sak_id}"):
        if msg_input or u_file:
            full_txt = msg_input
            if u_file: full_txt += f"\n\n📎 **Vedlegg:** {u_file.name}"
            
            new_msg = {
                "role": "Bank" if role in ["Admin", "Director"] else "Agent",
                "sender": me_clean, 
                "text": full_txt,
                "time": get_norway_time(), 
                "read": False 
            }
            messages.append(new_msg)
            if update_sak_in_sheet(sak_id, {"Chat_History": json.dumps(messages)}):
                st.rerun()
                
# --- 6. DASHBORD (FINAL VERSION WITH BEDI & ADMIN ASSIGNMENT TOOL) ---
if valg == "📊 Dashbord":
    st.header(f"Oversikt - {current_user.capitalize()}")
    
    if not df.empty:
        # --- ROLE BASED DATA FILTERING (STABLE) ---
        if role in ["Admin", "Director"]:
            view_data = df.copy()
        elif role == "Saksbehandler":
            # Logic: Bedi apni saker (as agent) + jo usay assign hui hain (as processor) dono dekhega
            mask_mine = df['Saksbehandler'].astype(str).str.lower() == current_user.lower()
            mask_assigned = pd.Series(False, index=df.index)
            if 'Assigned_To' in df.columns:
                mask_assigned = df['Assigned_To'].astype(str).str.lower() == current_user.lower()
            view_data = df[mask_mine | mask_assigned].copy()
        else:
            view_data = df[df['Saksbehandler'].astype(str).str.lower() == current_user.lower()].copy()
        
        # --- NOTIFICATION LOGIC (UNCHANGED) ---
        unread_saker = []
        me_clean = str(current_user).lower().strip() 
        for i, r in view_data.iterrows():
            chat_h = str(r.get('Chat_History', ''))
            if not chat_h or chat_h in ['[]', 'nan']: continue
            try:
                import json
                msgs = json.loads(chat_h)
                if msgs:
                    last_msg = msgs[-1]
                    if not last_msg.get('read', True) and str(last_msg.get('sender', '')).lower().strip() != me_clean:
                        unread_saker.append({"navn": r.get('Hovedsøker', 'Ukjent'), "id": r.get('ID', i)})
            except: continue

        if unread_saker:
            st.markdown("### 🔔 Varsler (Nye meldinger)")
            for sak in unread_saker:
                if st.button(f"📩 Ny melding i sak: {sak['navn']} (ID: {sak['id']})", key=f"notif_{sak['id']}"):
                    st.session_state.search_query = str(sak['id']) 
                    st.session_state.active_tab = "📂 Kunde Arkiv" 
                    st.rerun()

        # --- METRICS SECTION (UNCHANGED) ---
        c1, c2, c3 = st.columns(3)
        loan_vals = pd.to_numeric(view_data['Lånebeløp'], errors='coerce').fillna(0)
        percent_vals = pd.to_numeric(view_data['Provisjon_Prosent'], errors='coerce').fillna(0) if 'Provisjon_Prosent' in view_data.columns else 0
        total_v = loan_vals.sum()
        total_p = (loan_vals * percent_vals / 100).sum()
        
        c1.metric("Antall Saker", len(view_data))
        c2.metric("Total Volum (kr)", f"{total_v:,.0f} kr")
        c3.metric("Din Provisjon", f"{total_p:,.0f} kr")
        
        st.divider()
        st.subheader("Siste Registrerte Saker")

        # --- SAKER LIST SECTION ---
        for i, r in view_data.tail(15).iterrows():
            hoved = r.get('Hovedsøker', 'N/A')
            belop = r.get('Lånebeløp', '0')
            b_status = r.get('Bank_Status', 'Mottatt')
            sak_id = r.get('ID', i)
            chat_h = r.get('Chat_History', '')
            agent_navn = r.get('Saksbehandler', 'Agent')
            assigned_to = r.get('Assigned_To', 'Ingen')

            st_icon = "🔴"
            if b_status == "Mottatt": st_icon = "🔵"
            elif b_status == "Under Behandling": st_icon = "🟡"
            elif b_status == "Godkjent": st_icon = "🟢"
            
            with st.expander(f"{st_icon} {hoved} | {belop} kr | Ansvar: {assigned_to}"):
                
                # --- NEW: BEDI'S BANK COPY TOOL (Visible only to Bedi or Admin) ---
                if role == "Saksbehandler" or role in ["Admin", "Director"]:
                    st.info("📋 **Bank Portal Copy Tool**")
                    copy_text = f"NAVN: {hoved}\nBELØP: {belop}\nFNR: {r.get('Fødselsnummer', 'N/A')}\nTLF: {r.get('Telefon', 'N/A')}"
                    st.text_area("Klar til kopiering:", value=copy_text, height=100, key=f"cp_{sak_id}")
                    if st.button("🚀 Marker som 'Sendt til Bank'", key=f"bsent_{sak_id}"):
                        update_sak_in_sheet(sak_id, {"Bank_Status": "Under Behandling"})
                        st.rerun()

                # --- BANKING CHAT HUB (STABLE) ---
                display_bank_messaging_hub(sak_id, chat_h, role, current_user, agent_navn)
                
                st.divider()

                # --- INFO & ADMIN ASSIGNMENT ---
                inf_c1, inf_c2 = st.columns(2)
                with inf_c1:
                    st.markdown("### 📄 Saksinformasjon")
                    # Aapka purana dynamic display loop
                    for count, (col_name, value) in enumerate(r.items()):
                        if col_name in ['Mangler', 'Chat_History', 'Assigned_To']: continue
                        if count % 2 == 0: st.write(f"**{col_name}:** {value}")
                
                with inf_c2:
                    for count, (col_name, value) in enumerate(r.items()):
                        if col_name in ['Mangler', 'Chat_History', 'Assigned_To']: continue
                        if count % 2 != 0: st.write(f"**{col_name}:** {value}")
                    
                    # Naya Assignment Dropdown for Admin
                    if role in ["Admin", "Director"]:
                        st.markdown("---")
                        st.write("👤 **Tildel Saksbehandler**")
                        new_asgn = st.selectbox("Velg:", ["Ingen", "Bedi"], index=1 if str(assigned_to)=="Bedi" else 0, key=f"as_{sak_id}")
                        if st.button("Oppdater Ansvar", key=f"asb_{sak_id}"):
                            update_sak_in_sheet(sak_id, {"Assigned_To": new_asgn})
                            st.rerun()

                # --- MODIFICATION SYSTEM (UNCHANGED) ---
                st.markdown("---")
                old_notater = str(r.get('Notater', ''))
                new_notater = st.text_area("Oppdater Notater", value=old_notater, key=f"edit_not_{i}")
                
                if st.button("💾 Lagre Endringer", key=f"save_mod_{i}"):
                    if update_sak_in_sheet(sak_id, {"Notater": new_notater}):
                        st.success("Oppdatert!")
                        st.rerun()
                            
    else:
        st.warning("Ingen data tilgjengelig.")
        

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

        # --- 🛡️ HARD-LOCK SECURITY (Status Control) ---
        # Yahan hum role check karte hain aur Ansatt se dropdown chheen lete hain
        user_role = st.session_state.get('role', 'Ansatt').strip().capitalize()
        
        if user_role in ["Admin", "Director"]:
            status_options = ["Mottatt", "Under Behandling", "Godkjent", "Avslått", "Utbetalt"]
            final_status = st.selectbox("Sak Status (KUN ADMIN/DIRECTOR)", status_options, index=0)
        else:
            final_status = "Mottatt"
            st.info("ℹ️ Status settes automatisk til: **Mottatt**")

        if st.form_submit_button("🚀 SEND SØKNAD TIL BANKEN"):
            if not navn:
                st.error("Vennligst skriv inn navnet på Hovedsøker!")
            else:
                tot_ek = h_ek + m_ek
                tot_gjeld = h_gjeld + m_gjeld
                
                initial_chat = json.dumps([{
                    "role": "Bank",
                    "sender": "BANK CENTRAL",
                    "text": "Velkommen! Vi har mottatt din søknad og vil behandle den fortløpende.",
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
                    final_status, # Security Locked Status
                    "", 
                    initial_chat 
                ]
                
                add_data("MainDB", new_row)
                st.success(f"✅ Søknad registrert! Status: {final_status}")
                st.balloons()


elif valg == "📂 Kunde Arkiv":
    st.header("📂 Kunde Arkiv - Modern Oversikt")
    
    # 1. SMART DATAHENTING (CACHE FOR SPEED)
    @st.cache_data(ttl=60)
    def sikker_data_henting():
        return df
    
    gjeldende_df = sikker_data_henting()
    countries = get_country_list()

    # 2. SØKE- LOGIKK & URL PARAMETERS
    query_params = st.query_params
    url_id = query_params.get("search_query", "")
    if url_id:
        st.session_state.search_query = url_id
    hopp_til_id = st.session_state.get('search_query', "")

    # 3. FILTRERING BASERT PÅ ROLLE (ADMIN VS ANSATT)
    visnings_df = gjeldende_df if role in ["Admin", "Director"] else gjeldende_df[gjeldende_df['Saksbehandler'].astype(str).str.lower() == current_user.lower()]
    
    sok = st.text_input("🔍 Søk etter kunde...", value=hopp_til_id, placeholder="Navn, ID, Telefon...", key="arkiv_sok_hoved")
    if sok:
        visnings_df = visnings_df[visnings_df.astype(str).apply(lambda x: x.str.contains(sok, case=False)).any(axis=1)]

    st.info(f"✨ **Viser {len(visnings_df)} aktive saker i systemet**")

    # --- HOVEDLØKKE FOR SAKER ---
    for i, r in visnings_df.iterrows():
        sak_id = str(r.get('ID', i))
        gjeldende_status = r.get('Bank_Status', 'Mottatt')
        chat_historikk = str(r.get('Chat_History', '[]')) 
        agent_navn = r.get('Saksbehandler', 'Agent') 
        
        # STATUS ICON LOGIKK
        status_ikon = "🔵"
        if gjeldende_status == "Godkjent": status_ikon = "🟢"
        elif gjeldende_status == "Avslått": status_ikon = "🔴"
        elif gjeldende_status == "Under Behandling": status_ikon = "🟡"
        elif gjeldende_status == "Utbetalt": status_ikon = "🟣"

        har_ulest = False
        if '"read": false' in chat_historikk.lower():
            try:
                import json
                meldinger = json.loads(chat_historikk)
                if meldinger and meldinger[-1].get('read') == False and str(meldinger[-1].get('sender', '')).lower() != str(current_user).lower():
                    har_ulest = True
            except: pass
            
        varsel = "🔴 NY MELDING | " if har_ulest else ""
        skal_utvides = True if (sok and str(sak_id) == str(sok)) else False

        # --- EKSPANDERBAR BOKS ---
        with st.expander(f"{varsel}{status_ikon} **{r.get('Navn', 'Ukjent')}** | ID: {sak_id} | STATUS: {gjeldende_status}", expanded=skal_utvides):
            
            if gjeldende_status == "Godkjent": st.success(f"✅ **Saken er Godkjent av Banken**")
            elif gjeldende_status == "Avslått": st.error(f"❌ **Saken er Avslått av Banken**")
            elif gjeldende_status == "Under Behandling": st.warning(f"⏳ **Saken er til vurdering hos Banken**")
            else: st.info(f"📩 **Søknaden er Mottatt**")

            st.divider()
            
            # Control Tabs: Redigering vs Sletting
            vis_redigering = st.checkbox(f"🛠️ Modifiser søknadsdata (Full tilgang)", key=f"mod_sjekk_{sak_id}")

            if not vis_redigering:
                # --- VISNINGSMODUS ---
                st.markdown(f"#### 📄 Søknadsdetaljer")
                v1, v2, v3 = st.columns(3)
                with v1:
                    st.write(f"**👤 Navn:** {r.get('Navn')}")
                    st.write(f"**📞 Tlf:** {r.get('Tlf')}")
                with v2:
                    st.write(f"**🏠 Produkt:** {r.get('Produkt')}")
                    st.write(f"**💰 Lånebeløp:** {r.get('Lånebeløp')} kr")
                with v3:
                    st.write(f"**📅 Dato:** {r.get('Dato')}")
                    st.write(f"**👨‍💼 Ansvarlig:** {agent_navn}")

                st.write(f"**📝 Kommentarer:** {r.get('Notater', 'Ingen kommentarer lagret.')}")

                # --- 🚀 NEW FEATURE: SEND TIL BEDI (KUN ADMIN) ---
                if role in ["Admin", "Director"]:
                    st.divider()
                    st.subheader("👨‍💼 Tildel Saksbehandler")
                    # Admin aur Yasin nikal diye hain
                    saksbehandler_liste = ["-- Velg --", "Bedi"] 
                    
                    current_sb = r.get('Saksbehandler', "-- Velg --")
                    if current_sb not in saksbehandler_liste:
                        current_sb = "-- Velg --"
                    
                    selected_sb = st.selectbox(f"Send saken til:", 
                                               saksbehandler_liste, 
                                               index=saksbehandler_liste.index(current_sb),
                                               key=f"sb_assign_{sak_id}")
                    
                    if st.button("🚀 Send sak nå", key=f"btn_sb_{sak_id}"):
                        if selected_sb != "-- Velg --":
                            # "Status": "Ny" ensures it lands in the Saksbehandler's New Tasks
                            if update_sak_in_sheet(sak_id, {"Saksbehandler": selected_sb, "Status": "Ny"}):
                                st.toast(f"✅ Sak sendt til {selected_sb}!", icon="🚀")
                                st.success(f"Saken er tildelt {selected_sb} og vil vises i deres Ny Oppgaver.")
                                st.cache_data.clear()
                                st.rerun()
                        else:
                            st.warning("Vennligst velg Bedi for å sende saken.")

                display_bank_messaging_hub(sak_id, chat_historikk, role, current_user, agent_navn)

            else:
                # --- FULL REDIGERING & SLETTING ---
                with st.form(key=f"full_edit_form_{sak_id}"):
                    st.subheader("📝 Oppdater Søknadsinformasjon")
                    
                    prod = st.selectbox("Velg Produkt", ["Boliglån", "Refinansiering", "Mellomfinansiering", "Investlån / Bedriftlån", "Byggelån", "Forbrukslån", "Billån"], 
                                      index=["Boliglån", "Refinansiering", "Mellomfinansiering", "Investlån / Bedriftlån", "Byggelån", "Forbrukslån", "Billån"].index(r.get('Produkt', 'Boliglån')))
                    
                    is_bedrift = "Bedriftlån" in prod or "Investlån" in prod
                    
                    if is_bedrift:
                        st.markdown("#### 🏢 Bedriftinformasjon")
                        bc1, bc2 = st.columns(2)
                        up_f_navn = bc1.text_input("Firma Navn", value=str(r.get('Firma_Navn', '')))
                        up_f_org = bc1.text_input("Organisasjonsnummer", value=str(r.get('Org_Nr', '')))
                        up_f_eier = bc2.text_area("Eiere & Personnummer", value=str(r.get('Eiere_Info', '')))
                        up_f_aksjer = bc2.text_input("Aksjefordeling (%)", value=str(r.get('Aksjer', '')))
                        st.divider()

                    st.markdown("#### 👤 Hovedsøker")
                    h1, h2 = st.columns(2)
                    up_navn = h1.text_input("Fullt Navn *", value=str(r.get('Navn', '')))
                    up_fnr = h1.text_input("Fødselsnummer", value=str(r.get('Fnr', '')))
                    up_epost = h2.text_input("E-post", value=str(r.get('Epost', '')))
                    up_tlf = h2.text_input("Telefon", value=str(r.get('Tlf', '')))
                    
                    st.markdown("#### 💼 Økonomisk Profil")
                    l1, l2, l3 = st.columns(3)
                    up_lonn = l1.number_input("Årslønn Brutto (kr)", value=int(r.get('Lønn', 0)), step=1000)
                    up_ek = l2.number_input("Egenkapital (kr)", value=int(r.get('EK', 0)), step=1000)
                    up_gjeld = l3.number_input("Total Gjeld (kr)", value=int(r.get('Gjeld', 0)), step=1000)

                    st.divider()
                    st.markdown("#### 👥 Medsøker")
                    m1, m2 = st.columns(2)
                    up_m_navn = m1.text_input("Medsøker Fullt Navn", value=str(r.get('Medsøker_Navn', '')))
                    up_m_fnr = m1.text_input("Medsøker Fødselsnummer", value=str(r.get('Medsøker_Fnr', '')))
                    up_m_lonn = m2.number_input("Medsøker Årslønn", value=int(r.get('Medsøker_Lønn', 0)), step=1000)
                    up_m_tlf = m2.text_input("Medsøker Telefon", value=str(r.get('Medsøker_Tlf', '')))

                    st.divider()
                    st.markdown("#### 🏦 Bankbehandling & Godkjenning")
                    up_belop = st.number_input("Søkt Lånebeløp (kr)", value=int(r.get('Lånebeløp', 0)), step=10000)
                    up_mangler = st.text_area("Mangler fra kunden", value=str(r.get('Mangler', '')))
                    up_notat = st.text_area("Bankens interne notater", value=str(r.get('Notater', '')))

                    if role in ["Admin", "Director"]:
                        status_valg = ["Mottatt", "Under Behandling", "Godkjent", "Avslått", "Utbetalt"]
                        try: s_idx = status_valg.index(gjeldende_status)
                        except: s_idx = 0
                        up_st = st.selectbox("Oppdater Endelig Saksstatus", status_valg, index=s_idx)
                    else:
                        up_st = gjeldende_status
                        st.info(f"📊 **Nåværende Bankstatus:** {gjeldende_status}")

                    if st.form_submit_button("💾 OPPDATER SØKNAD"):
                        data_til_oppdatering = {
                            "Produkt": prod, "Navn": up_navn, "Fnr": up_fnr, "Epost": up_epost, "Tlf": up_tlf,
                            "Lønn": up_lonn, "EK": up_ek, "Gjeld": up_gjeld, "Bank_Status": up_st,
                            "Medsøker_Navn": up_m_navn, "Medsøker_Fnr": up_m_fnr, "Medsøker_Lønn": up_m_lonn,
                            "Medsøker_Tlf": up_m_tlf, "Lånebeløp": up_belop, "Notater": up_notat, "Mangler": up_mangler
                        }
                        if is_bedrift:
                            data_til_oppdatering.update({"Firma_Navn": up_f_navn, "Org_Nr": up_f_org, "Eiere_Info": up_f_eier, "Aksjer": up_f_aksjer})
                        
                        if update_sak_in_sheet(sak_id, data_til_oppdatering):
                            st.cache_data.clear()
                            st.success(f"✅ Søknad {sak_id} er oppdatert!")
                            st.rerun()

                # --- 🗑️ SLETTING ---
                if role in ["Admin", "Director"]:
                    st.divider()
                    with st.expander("⚠️ Faresone: Slett denne søknaden"):
                        st.warning(f"Vil du slette saken til **{r.get('Navn')}** permanent?")
                        bekreft_sletting = st.checkbox(f"Bekreft sletting av sak {sak_id}", key=f"del_confirm_{sak_id}")
                        if st.button(f"🗑️ SLETT SØKNAD PERMANENT", key=f"del_btn_{sak_id}", disabled=not bekreft_sletting):
                            if delete_sak_from_sheet(sak_id):
                                st.cache_data.clear()
                                st.error(f"✅ Sak {sak_id} er fjernet.")
                                st.rerun()

elif valg == "🏦 Bankens Renters":
    st.header("🏦 Aktuelle Bankrenter")
    st.info("Oversikt over gjeldende renter for ulike låneprodukter.")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Boliglån (Flytende)", "4.85%", "+0.25%")
        st.metric("Refinansiering", "5.10%", "-0.10%")
    with col2:
        st.metric("Billån", "6.20%", "Stabil")
        st.metric("Forbrukslån", "11.5%", "Stabil")

elif valg == "📞 Support Center":
    st.header("📞 Bank Support Center")
    tab1, tab2 = st.tabs(["📩 Send Forespørsel", "📜 Min Historikk"])
    with tab1:
        st.success("Vår supportavdeling er tilgjengelig: Man-Fre (09:00 - 16:00)")
        with st.form("support_form"):
            sup_topic = st.selectbox("Tema", ["Teknisk feil", "Spørsmål om sak", "Prioritert utbetaling", "Annet"])
            sup_msg = st.text_area("Beskrivelse")
            if st.form_submit_button("🚀 Send Forespørsel"):
                if sup_msg:
                    now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                    sender = st.session_state.get('navn', st.session_state.get('user_id', 'Ukjent'))
                    support_data = [now, sender, sup_topic, sup_msg, "Åpen", "Venter på svar..."]
                    if add_data("Support", support_data):
                        st.balloons()
                        st.success("✅ Forespørsel sendt!")
                        st.rerun()
    with tab2:
        st.subheader("Mine tidligere henvendelser")
        try:
            s_df = get_data("Support")
            my_name = st.session_state.get('navn', '')
            my_saker = s_df[s_df['Fra_Bruker'] == my_name]
            if not my_saker.empty:
                for idx, row in my_saker.sort_index(ascending=False).iterrows():
                    with st.expander(f"📌 {row['Tidspunkt']} - {row['Tema']} ({row['Status']})"):
                        st.write(f"**Din melding:** {row['Beskrivelse']}")
                        st.info(f"**Bankens svar:** {row['Svar_Fra_Admin']}")
            else:
                st.info("Du har ingen registrerte forespørsler.")
        except:
            st.error("Kunne ikke hente historikk.")
            


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

# --- 10. ANSATTE KONTROLL (ADVANCED & SECURE VERSION) ---
elif valg == "👥 Ansatte Kontroll" and role in ["Admin", "Director"]:
    st.header("👥 Ansatte Oversikt og Kontroll")
    
    # Professional Status Styling Function
    def get_status_badge(status):
        colors = {
            "Mottatt": ("#6c757d", "⚪"),        # Grey
            "Under Behandling": ("#007bff", "🔵"), # Blue
            "Godkjent": ("#28a745", "🟢"),         # Green
            "Avslått": ("#dc3545", "🔴"),          # Red
            "Utbetalt": ("#ffc107", "🟡")          # Gold/Yellow
        }
        color, icon = colors.get(status, ("#000000", "❓"))
        return f'<span style="background-color:{color}; color:white; padding:4px 10px; border-radius:12px; font-weight:bold; font-size:14px;">{icon} {status}</span>'

    @st.cache_data(ttl=60)
    def get_agents_cached():
        return get_data("Agents")

    try:
        agents_df = get_agents_cached()
        main_df = df 
    except Exception as e:
        st.error(f"Kunne ikke hente agents: {e}")
        agents_df = pd.DataFrame()

    if not agents_df.empty:
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
                
                with col1:
                    st.markdown(f"**Stilling:** `{row.get('stilling', '-')}`")
                    st.markdown(f"**Vakt:** `{row.get('vakt', '-')}`")
                    st.markdown(f"**Nåværende Status:** `{row.get('status', '-')}`")
                
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
                
                act1, act2, act3 = st.columns(3)
                
                with act1:
                    if st.button(f"📂 Se Saker", key=f"v_saker_{i}"):
                        if not agent_saker.empty:
                            st.subheader(f"Saker for {a_navn}")
                            for idx, s_row in agent_saker.iterrows():
                                sak_id = s_row.get('ID', idx)
                                current_st = s_row.get('Bank_Status', 'Mottatt')
                                
                                with st.expander(f"📄 Sak: {s_row.get('Hovedsøker', 'Kunde')} (ID: {sak_id})"):
                                    # Modern Header with Badge
                                    st.markdown(f"**Status:** {get_status_badge(current_st)}", unsafe_allow_html=True)
                                    
                                    cols = st.columns(2)
                                    for count, (col_name, col_val) in enumerate(s_row.items()):
                                        if col_name not in ['Mangler', 'Bank_Status']: 
                                            target_col = cols[0] if count % 2 == 0 else cols[1]
                                            target_col.write(f"**{col_name}:** {col_val}")

                                    st.markdown("---")
                                    st.write("🔧 **Admin Action: Status & Provisjon**")
                                    
                                    # 1. Status Update (Admin/Director Only)
                                    status_options = ["Mottatt", "Under Behandling", "Godkjent", "Avslått", "Utbetalt"]
                                    st_idx = status_options.index(current_st) if current_st in status_options else 0
                                    new_bank_st = st.selectbox("Oppdater Sak Status", status_options, index=st_idx, key=f"st_edit_{idx}_{i}")
                                    
                                    # 2. Provisjon Engine (Add Admin Provisjon manually if missing)
                                    admin_prov_val = s_row.get('Admin_Provisjon', 0)
                                    if pd.isna(admin_prov_val): admin_prov_val = 0
                                    
                                    new_admin_p = st.number_input("Total Provisjon fra Bank (kr)", value=float(admin_prov_val), key=f"adm_p_{idx}_{i}")
                                    
                                    # Display 10% Share if Approved
                                    if new_bank_st == "Godkjent":
                                        ansatt_share = new_admin_p * 0.10
                                        st.success(f"💎 **Ansatt Provisjon (10%):** {ansatt_share:,.2f} kr")
                                    
                                    mangler_msg_val = s_row.get('Mangler', '')
                                    mangler_msg = st.text_area("Mangler dokumenter / Melding til ansatt", 
                                                               value=str(mangler_msg_val) if str(mangler_msg_val).lower() != 'nan' else "", 
                                                               key=f"msg_edit_{idx}_{i}")
                                    
                                    if st.button(f"🚀 Lagre Sak & Send Live", key=f"sv_edit_{idx}_{i}"):
                                        updates = {
                                            "Bank_Status": new_bank_st, 
                                            "Mangler": mangler_msg,
                                            "Admin_Provisjon": new_admin_p
                                        }
                                        with st.spinner("Oppdaterer..."):
                                            success = update_sak_in_sheet(sak_id, updates)
                                            if success:
                                                st.success(f"✅ Sak {sak_id} oppdatert!")
                                                st.rerun()
                        else:
                            st.warning("Ingen data funnet.")

                with act2:
                    status_options_ag = ["Aktiv", "Inaktiv", "Permisjon"]
                    current_s = row.get('status', 'Aktiv')
                    idx_s = status_options_ag.index(current_s) if current_s in status_options_ag else 0
                    n_st = st.selectbox("Endre Agent Status", status_options_ag, index=idx_s, key=f"st_sel_{i}")
                    if st.button("💾 Oppdater Agent", key=f"upd_btn_{i}"):
                        st.success(f"Agent status oppdatert til {n_st}")

                with act3:
                    if st.button(f"🗑️ Slette Profil", key=f"del_btn_{i}"):
                        if role == "Admin":
                            with st.spinner(f"Sletter..."):
                                success = delete_user_completely(a_user)
                                if success:
                                    st.success(f"✅ Agent {a_user} slettet!")
                                    st.rerun()
                        else:
                            st.warning("Kun Admin kan slette.")
    else:
        st.warning("Ingen ansatte funnet.")


# --- SUPPORT MANAGEMENT FOR ADMIN (Yeh Dashboard ya Main area mein rahega) ---

if role in ["Admin", "Director"] and valg == "📊 Dashbord": # Maine isse Dashboard se link kar diya hai
    st.divider()
    st.header("📥 Support Management (Admin)")
    
    try:
        # Henter data fra Google Sheets
        support_df = get_data("Support")
        
        if support_df is not None and not support_df.empty:
            # Viser de nyeste meldingene først
            for i, row in support_df.sort_index(ascending=False).iterrows():
                
                # Check priority
                priority_tag = "⚠️ HASTE" if row['Tema'] == "Prioritert utbetaling" else ""
                
                # Status indicator
                color = "🔴" if row['Status'] == "Åpen" else "🟢"
                
                with st.expander(f"{color} {priority_tag} Fra: {row['Fra_Bruker']} | Tema: {row['Tema']} | Tid: {row['Tidspunkt']}"):
                    st.write(f"**Melding:** {row['Beskrivelse']}")
                    st.info(f"**Nåværende Svar:** {row['Svar_Fra_Admin']}")
                    
                    # Admin handlinger
                    new_reply = st.text_area("Skriv svar til ansatt", value=row['Svar_Fra_Admin'], key=f"ans_{i}")
                    
                    status_options = ["Åpen", "Behandles", "Løst / Ferdig"]
                    current_status = row['Status'] if row['Status'] in status_options else "Åpen"
                    
                    new_status = st.selectbox("Oppdater Status", status_options, 
                                             index=status_options.index(current_status), 
                                             key=f"stat_{i}")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button("💾 Lagre Svar & Oppdater", key=f"save_{i}"):
                            support_df.at[i, 'Svar_Fra_Admin'] = new_reply
                            support_df.at[i, 'Status'] = new_status
                            
                            with st.spinner("Lagrer svar..."):
                                if update_sheet_data_internal("Support", support_df):
                                    st.cache_data.clear()
                                    st.success("✅ Svar er lagret!")
                                    st.rerun() 
                    
                    with col2:
                        if st.button("🗑️ Slett Melding", key=f"del_msg_{i}"):
                            new_df = support_df.drop(i)
                            with st.spinner("Sletter..."):
                                if update_sheet_data_internal("Support", new_df):
                                    st.cache_data.clear()
                                    st.warning("Melding slettet!")
                                    st.rerun()
        else:
            st.info("Ingen aktive support-forespørsler.")
            
    except Exception as e:
        st.error(f"Feil ved henting av support: {e}")



# --- 11. KONTAKTER (RESTORED - NO CHANGES SKIPPED) ---
elif valg == "📇 Kontakter":
    st.header("📇 Kontaktadministrasjon")
    
    import pandas as pd
    import smtplib
    from datetime import datetime
    from email.mime.text import MIMEText

    # DATA HENTING
    try:
        contacts_df = get_data("Contacts")
        if contacts_df is None: 
            contacts_df = pd.DataFrame(columns=["Navn", "E-post", "Telefon", "Sist Endret"])
        if "Sist Endret" not in contacts_df.columns:
            contacts_df["Sist Endret"] = "N/A"
    except:
        contacts_df = pd.DataFrame(columns=["Navn", "E-post", "Telefon", "Sist Endret"])

    # Tabs (Wahi purane 3 tabs)
    tab1, tab2, tab3 = st.tabs(["📇 Kontaktliste", "📩 Send E-post", "➕ Ny Kontakt"])

    # --- TAB 1: KONTAKTLISTE (Restored Editing Logic) ---
    with tab1:
        st.subheader("Oversikt over kontakter")
        if not contacts_df.empty:
            st.dataframe(contacts_df, use_container_width=True, hide_index=True)
            st.divider()
            
            selected_name = st.selectbox("Velg en kontakt for å endre detaljer:", ["-- Velg --"] + contacts_df["Navn"].tolist())
            
            if selected_name != "-- Velg --":
                idx = contacts_df[contacts_df["Navn"] == selected_name].index[0]
                last_time = contacts_df.at[idx, "Sist Endret"]
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
            st.info("Listen er tom.")

    # --- TAB 2: SEND E-POST (Restored Email Logic) ---
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
                        st.success(f"✅ E-post sendt!")
                    except Exception as e: 
                        st.error(f"Feil: {e}")
                else:
                    st.warning("Fyll ut alle felt.")

    # --- TAB 3: NY KONTAKT ---
    with tab3:
        st.subheader("Registrer ny kontakt")
        with st.form("new_con"):
            nn = st.text_input("Navn")
            ne = st.text_input("E-post")
            nt = st.text_input("Telefon")
            if st.form_submit_button("➕ Legg til"):
                if nn and ne:
                    now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                    new_row = pd.DataFrame([{"Navn":nn, "E-post":ne, "Telefon":nt, "Sist Endret":now}])
                    contacts_df = pd.concat([contacts_df, new_row], ignore_index=True)
                    if update_sheet_data_internal("Contacts", contacts_df):
                        st.success("✅ Lagret!")
                        st.cache_data.clear()
                        st.rerun()
                        


# --- SEARCH FOR THIS LINE AND REPLACE EVERYTHING UNTIL THE FOOTER ---
elif valg == "📜 Dokumentmaler":
    st.header("🏦 NSVG – Dokumentasjonsportal")
    st.caption("Nordic Secure Vault Group | Professional Banking Standards")
    st.markdown("---")
    
    # Direct View Message
    st.success("✅ **Portal-modus:** Alle krav vises direkte nedenfor. Ingen nedlasting nødvendig.")

    # --- MAIN CONTENT LAYOUT ---
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🏠 Boliglån & Refinans")
        with st.container():
            st.markdown("""
            **Påkrevd Dokumentasjon:**
            * **Lønn:** Siste 3 mnd lønnslipper.
            * **Skatt:** Siste års skattemelding (fullstendig).
            * **Verdi:** Oppdatert **E-takst** (maks 6 mnd gammel).
            * **Gjeld:** Oversikt over eksisterende gjeld og etakst.
            
            **Sjekkliste:**
            - [x] ID-kontroll utført
            - [x] Skattemelding kontrollert
            - [x] E-takst bekreftet
            """)

    with col2:
        st.markdown("### 🏢 Næringslån (Bedrift)")
        with st.container():
            st.markdown("""
            **Påkrevd Dokumentasjon:**
            * **Regnskap:** Fullstendig årsregnskap for **siste 2 år**.
            * **Drift:** Foreløpig saldobalanse for inneværende år.
            * **Firma:** Ny firmaattest fra Brønnøysund.
            * **UBO:** Oversikt over reelle rettighetshavere.
            
            **Sjekkliste:**
            - [x] 2 års regnskap mottatt
            - [x] Saldobalanse sjekket
            - [x] Firmaattest verifisert
            """)

    st.markdown("---")
    st.warning("🛡️ **NSVG Security:** Alle filer må sjekkes for KYC/AML-compliance før de sendes til banken.")

# =================================================================
# --- 💼 SAKSBEHANDLER PANEL (Linked with Ny Oppgaver) ---
# =================================================================
elif valg == "💼 Saksbehandler Panel":
    st.header("💼 Saksbehandler Arbeidsbenk")
    
    # 1. Filter: Sirf wo cases jo IS user ko assign hain aur status "Ny" ya "Klargjøring" hai
    try:
        # Hum check kar rahe hain ke Saksbehandler column match kare aur Status khatam na hui ho
        mask = (df['Saksbehandler'].astype(str).str.lower() == username.lower())
        ny_oppgaver_df = df[mask]
    except:
        ny_oppgaver_df = pd.DataFrame()

    if not ny_oppgaver_df.empty:
        st.subheader(f"📥 Ny Oppgaver ({len(ny_oppgaver_df)})")
        
        # Selectbox for active tasks
        selected_name = st.selectbox("Velg oppgave for å starte behandling:", ["-- Velg sak --"] + ny_oppgaver_df['Navn'].tolist())
        
        if selected_name != "-- Velg sak --":
            sak_data = ny_oppgaver_df[ny_oppgaver_df['Navn'] == selected_name].iloc[0]
            sak_id = sak_data.get('ID', 'N/A')
            
            # --- BANK TOOLS SECTION ---
            st.markdown("### 🏦 Bank Portal Copy Tool")
            summary_text = f"""NAVN: {sak_data.get('Navn')}
FØDSELSNR: {sak_data.get('Fodselsnr', 'Se vedlegg')}
SUM: {sak_data.get('Lånesum')} NOK
INNTEKT: {sak_data.get('Inntekt')}
GJELD: {sak_data.get('Gjeld')}"""

            st.code(summary_text, language="text") # Code block for easy one-click copy
            st.caption("Klar til kopiering: Bruk knappen øverst til høyre i boksen.")

            # --- STATUS UPDATE ---
            st.divider()
            new_st = st.selectbox("Oppdater status direkte:", ["Ny", "Sendt til Bank", "Venter på Tilbud", "Fullført"])
            if st.button("Lagre framdrift"):
                if update_sak_in_sheet(sak_id, {"Status": new_st}):
                    st.toast("✅ Status oppdatert!")
                    st.rerun()
    else:
        st.info("📭 Ingen nye oppgaver tildelt deg ennå.")
        


# --- FOOTER (FIXED Error Line) ---
st.sidebar.markdown("---")
st.sidebar.caption("NSVG CRM v2.0 | © NORDIC SECURE VAULT GROUP")
