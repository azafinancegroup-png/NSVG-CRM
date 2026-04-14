import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json
import smtplib
from email.mime.text import MIMEText
import pytz 

# =================================================================
# --- 1. CONFIGURATION & 2026 THEME (PISTACHIO-GRAY) ---
# =================================================================
st.set_page_config(page_title="NSVG CRM Pro", layout="wide")

# Custom CSS for Modern Aesthetic
st.markdown("""
    <style>
    .stApp { background-color: #F4F7F6; } /* Light Grayish-Pistachio */
    
    /* Metrics Styling */
    div[data-testid="stMetricValue"] {
        background-color: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border-bottom: 5px solid #B2D2A4;
    }

    /* Pistachio Buttons */
    .stButton>button {
        background-color: #B2D2A4 !important;
        color: #2E4031 !important;
        border-radius: 10px !important;
        border: none !important;
        font-weight: bold !important;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #98B88A !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }

    /* Glassmorphism Sidebar */
    [data-testid="stSidebar"] {
        background-color: rgba(255, 255, 255, 0.8);
        backdrop-filter: blur(10px);
    }
    
    /* Chat Bubble Styles (Updated for 2026 Look) */
    .bank-bubble { background-color: #E1F5FE; border-left: 5px solid #0288D1; padding: 12px; border-radius: 12px; margin: 8px; color: black; }
    .agent-bubble { background-color: #FFFFFF; border-right: 5px solid #B2D2A4; padding: 12px; border-radius: 12px; margin: 8px; text-align: right; color: black; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# =================================================================
# --- 2. GLOBAL SETTINGS & PERSISTENCE ---
# =================================================================
def get_norway_time():
    tz = pytz.timezone('Europe/Oslo')
    return datetime.now(tz).strftime("%d.%m.%Y %H:%M")

# REFRESH FIX: Page refresh se logout nahi hoga
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "📊 Dashbord"

# =================================================================
# --- 3. DATABASE UPDATE ENGINE (Stable & Fast) ---
# =================================================================
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

# =================================================================
# --- 4. MAYA'S HUB: THE PROFESSIONAL MESSAGING INTERFACE ---
# =================================================================
def display_bank_messaging_hub(sak_id, chat_data, role, username, agent_name="Agent"):
    st.markdown("---")
    # Identity: Ansatt ko sirf BANK nazar aaye
    target_label = "BANK" if role not in ["Admin", "Director"] else agent_name.upper()
    st.subheader(f"💬 Meldinger med {target_label}")
    
    try:
        messages = json.loads(chat_data) if chat_data and str(chat_data) != 'nan' else []
    except:
        messages = []

    # --- SMART LOGIC: Auto-Mark as Read when opened ---
    has_unread = False
    me_clean = str(username).lower().strip()
    
    for m in messages:
        # Check if last message is unread AND not sent by current user
        if not m.get('read', True) and str(m.get('sender', '')).lower().strip() != me_clean:
            m['read'] = True
            has_unread = True

    if has_unread:
        update_sak_in_sheet(sak_id, {"Chat_History": json.dumps(messages)})

    # Show History
    for msg in messages:
        is_bank = msg.get('role') == "Bank"
        div_class = "bank-bubble" if is_bank else "agent-bubble"
        
        # Display Name logic
        sender_display = "BANK" if is_bank and role not in ["Admin", "Director"] else msg.get("sender", "System")
        
        st.markdown(f'''
            <div class="{div_class}">
                <b>{sender_display}</b><br>
                {msg.get("text", "")}<br>
                <small style="color: grey;">{msg.get("time", "")}</small>
            </div>
            ''', unsafe_allow_html=True)

# =================================================================
# --- 5. BANK CHECKLIST FUNCTION (MODERN & MOTTY INCLUDED) ---
# =================================================================
def display_bank_checklist(selected_bank):
    st.markdown(f"#### 📋 {selected_bank} Checklist")
    requirements = {
        "Lendo": ["Siste 3 mnd lønnsslipp", "Siste skattemelding", "ID-kopi"],
        "Axo Finans": ["Gjeldsbrev signering", "Bekreftelse på arbeidsforhold", "E-skatt tilgang"],
        "Motty": ["BankID verifisering", "Oversikt over refinansiering", "Bilde av gyldig pass"]
    }
    selected_reqs = requirements.get(selected_bank, ["Standard dokumentasjon"])
    for req in selected_reqs:
        st.checkbox(req, key=f"check_{selected_bank}_{req}")


# =================================================================
# --- 2. GOOGLE SHEETS CONNECTION ENGINE (Maya Optimized) ---
# =================================================================

def connect_to_sheet(sheet_name):
    """
    Establish connection to the specific worksheet in NSVG_CRM_Data.
    """
    try:
        from oauth2client.service_account import ServiceAccountCredentials
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # Yeh aapki main spreadsheet file "NSVG_CRM_Data" ko open karega
        # Aur jo 'sheet_name' (e.g. "MainDB") aap bhejenge us tab ko select karega
        return client.open("NSVG_CRM_Data").worksheet(sheet_name)
    except Exception as e:
        st.error(f"Tilkoblingsfeil (Connection Error): {e}")
        return None

@st.cache_data(ttl=60)
def get_data(sheet_name):
    """
    Read all data from the sheet and return as a DataFrame.
    """
    sh = connect_to_sheet(sheet_name)
    if sh:
        try:
            data = sh.get_all_records()
            df = pd.DataFrame(data)
            # Column names se extra spaces khatam karne ke liye
            df.columns = [str(c).strip() for c in df.columns]
            return df
        except Exception as e:
            if "429" in str(e):
                st.error("Google API Limit nådd. Vent 60 sekunder...")
            return pd.DataFrame()
    return pd.DataFrame()

def add_data(sheet_name, row_list):
    """
    Append a new row to the Google Sheet.
    """
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
            
            # Pure data ko A1 cell se start karke update karna
            sh.update('A1', data_to_update)
            st.cache_data.clear() # Cache mitaein taake updates foran dikhein
            return True
        except Exception as e:
            st.error(f"⚠️ Google Sheets Update Error: {e}")
            return False
    return False

def delete_sak_from_sheet(sak_id): 
    """ 
    Google Sheet se specific ID wali row ko dhoond kar delete karne ka function.
    Is mein kisi naye 'delete column' ki zaroorat nahi hai.
    """
    try:
        # Sheet open karein (Aapki worksheet ka naam "MainDB" hai)
        sh = connect_to_sheet("MainDB")
        if sh:
            rows = sh.get_all_records()
            # Loop laga kar har row mein 'ID' check karein
            for index, row in enumerate(rows):
                if str(row.get('ID')) == str(sak_id):
                    # row_to_delete = index + 2 
                    # (+1 for header, +1 because gspread rows start at 1)
                    row_num = index + 2
                    sh.delete_rows(row_num)
                    st.cache_data.clear() # Cache saaf karein taake list update ho jaye
                    return True
            return False # Agar ID na mile
        else:
            st.error("Kunne ikke koble til databasen (MainDB).")
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


# =================================================================
# --- 5. GLOBAL DATA & SIDEBAR (STABLE CONNECTED VERSION) ---
# =================================================================

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

# --- DYNAMIC NAVIGATION LOGIC (BEDI FULL FEATURES RESTORED) ---
if role in ["Admin", "Director"]:
    options = [
        "📊 Dashbord", 
        "➕ Ny Registrering", 
        "📂 Kunde Arkiv", 
        "👥 Ansatte Kontroll", 
        "📇 Kontakter", 
        "💼 Saksbehandler Panel", 
        "🛠️ Master Kontroll"  # <--- Linked to Section 9
    ]

elif role == "Saksbehandler":
    # BEDI/SAKSBEHANDLER: Saare Ansatt features + Saksbehandler menu merge kar diye
    options = [
        "📊 Dashbord", 
        "➕ Ny Registrering", 
        "📥 Nye Oppgaver",      # Saksbehandler Feature
        "📂 Kunde Arkiv", 
        "🏦 Bankens Renters",    # Ansatt Feature
        "📜 Dokumentmaler",      # Ansatt Feature
        "📞 Support Center"      # Ansatt Feature
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
    # Handle agent_name if it's None
    agent_display = str(agent_name).upper() if agent_name else "AGENT"
    target_label = "BANK" if role not in ["Admin", "Director"] else agent_display
    
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
                

# =================================================================
# --- 6. DASHBORD (ARCTIC LIGHT THEME - 100% ORIGINAL + MASTER ADMIN) ---
# =================================================================

# --- APPLYING MODERN LIGHT THEME ---
st.markdown("""
    <style>
    /* Arctic Light Background */
    .stApp {
        background-color: #F1F4F8;
        color: #2D3436;
    }
    
    /* Metrics & Cards */
    div[data-testid="stMetricValue"], .stExpander {
        background-color: #FFFFFF !important;
        color: #2D3436 !important;
        border-radius: 15px;
        border: 1px solid #D1D8E0 !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }

    /* Professional Blue Buttons */
    .stButton>button {
        background-color: #4A69BD !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: 500 !important;
    }
    .stButton>button:hover {
        background-color: #1E3799 !important;
        color: white !important;
    }

    /* Sidebar: Professional Off-White */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E1E8ED !important;
    }
    
    /* Input & Select Boxes */
    input, textarea, .stSelectbox {
        background-color: #FFFFFF !important;
        color: #2D3436 !important;
        border: 1px solid #CED6E0 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- DASHBOARD DISPLAY LOGIC ---
if valg == "📊 Dashbord":
    if role in ["Admin", "Director"]:
        st.title(f"🏛️ Velkommen, {username}")
        st.subheader("Systemoversikt og Admin Kontroll")
    elif role == "Saksbehandler":
        st.title(f"💼 Velkommen, {username}")
        st.subheader("Din arbeidsflyt og tildelte saker")
    else:
        st.title(f"👋 Hei, {username}")
        st.subheader("Oversikt over dine registreringer")

    st.divider()
    
    if not df.empty:
        df_clean = df.copy()
        
        # Data Cleaning
        for col in ['Saksbehandler', 'Assigned_To']:
            if col in df_clean.columns:
                df_clean[col] = df_clean[col].fillna('Ingen').astype(str)
            else:
                df_clean[col] = "Ingen"

        current_u_lower = str(current_user).lower().strip()
        
        # Filtering Logic
        if role in ["Admin", "Director"]:
            view_data = df_clean.copy()
        elif role == "Saksbehandler":
            mask_mine = df_clean['Saksbehandler'].str.lower().str.strip() == current_u_lower
            mask_assigned = df_clean['Assigned_To'].str.lower().str.strip() == current_u_lower
            view_data = df_clean[mask_mine | mask_assigned].copy()
        else:
            view_data = df_clean[df_clean['Saksbehandler'].str.lower().str.strip() == current_u_lower].copy()
        
        # --- NOTIFICATIONS ---
        unread_saker = []
        for i, r in view_data.iterrows():
            chat_h = str(r.get('Chat_History', ''))
            if not chat_h or chat_h in ['[]', 'nan']: continue
            try:
                msgs = json.loads(chat_h)
                if msgs:
                    last_msg = msgs[-1]
                    if not last_msg.get('read', True) and str(last_msg.get('sender', '')).lower().strip() != current_u_lower:
                        unread_saker.append({"navn": r.get('Hovedsøker', 'Ukjent'), "id": r.get('ID', i)})
            except: continue

        if unread_saker:
            st.markdown("### 🔔 Varsler")
            for sak in unread_saker:
                if st.button(f"📩 Ny melding: {sak['navn']} (ID: {sak['id']})", key=f"notif_{sak['id']}"):
                    st.session_state.search_query = str(sak['id']) 
                    st.session_state.active_tab = "🔍 Søk i Kunder" 
                    st.rerun()

        # --- METRICS ---
        c1, c2, c3 = st.columns(3)
        loan_vals = pd.to_numeric(view_data['Lånebeløp'], errors='coerce').fillna(0)
        percent_vals = pd.to_numeric(view_data['Provisjon_Prosent'], errors='coerce').fillna(0) if 'Provisjon_Prosent' in view_data.columns else 0
        total_v = loan_vals.sum()
        total_p = (loan_vals * percent_vals / 100).sum()
        
        c1.metric("Antall Saker", len(view_data))
        c2.metric("Total Volum", f"{total_v:,.0f} kr")
        c3.metric("Beregnet Provisjon", f"{total_p:,.0f} kr")
        
        st.divider()
        st.subheader("Siste Registrerte Saker")

        # --- SAKER LIST (CLEAN HEADER LOGIC) ---
        for i, r in view_data.tail(15).iterrows():
            hoved = str(r.get('Hovedsøker', 'Ukjent Kunde')).strip()
            if hoved in ["nan", "None", "", "N/A"]: hoved = "Ukjent Kunde"

            try:
                belop_raw = r.get('Lånebeløp', 0)
                belop = float(belop_raw) if not pd.isna(belop_raw) else 0
            except: belop = 0

            b_status = r.get('Bank_Status', 'Mottatt')
            st_icon = "🔵" if b_status == "Mottatt" else "🟡" if b_status == "Under Behandling" else "🟢" if b_status == "Godkjent" else "🔴"
            
            assigned_to_header = str(r.get('Assigned_To', 'Ingen')).strip()
            if "[" in assigned_to_header or "{" in assigned_to_header or assigned_to_header.lower() in ["nan", "none", ""]:
                assigned_to_header = "Ingen"

            sak_id = str(r.get('ID', i))
            chat_h = r.get('Chat_History', '')
            agent_navn = r.get('Saksbehandler', 'Agent')

            # --- DISPLAY EXPANDER ---
            with st.expander(f"{st_icon} {hoved} | {belop:,.0f} kr | Ansvar: {assigned_to_header}"):
                
                # --- BEDI'S COPY TOOL ---
                if role in ["Saksbehandler", "Admin", "Director"]:
                    st.info("📋 **Portal Copy Tool**")
                    fnr_val = r.get('Fødselsnummer', 'N/A')
                    tlf_val = r.get('Telefon', 'N/A')
                    copy_text = f"NAVN: {hoved}\nBELØP: {belop}\nFNR: {fnr_val}\nTLF: {tlf_val}"
                    st.text_area("Klar til kopiering:", value=copy_text, height=100, key=f"cp_{sak_id}")
                    if st.button("🚀 Marker som 'Sendt til Bank'", key=f"bsent_{sak_id}"):
                        if update_sak_in_sheet(sak_id, {"Bank_Status": "Under Behandling"}):
                            st.rerun()

                # --- CHAT HUB ---
                display_bank_messaging_hub(sak_id, chat_h, role, current_user, agent_navn)
                
                # --- ADMIN ASSIGNMENT (DYNAMIC AGENT LIST) ---
                if role in ["Admin", "Director"]:
                    st.divider()
                    st.markdown("### 👤 Tildel Saksbehandler")
                    
                    # Fetching agents from DB for the dropdown
                    agents_data = get_data("Agents")
                    agent_list = ["Ingen"] + agents_data['navn'].tolist() if not agents_data.empty else ["Ingen", "Bedi", "Iqbal"]
                    
                    try:
                        current_idx = agent_list.index(assigned_to_header) if assigned_to_header in agent_list else 0
                    except: current_idx = 0
                    
                    new_asgn = st.selectbox("Velg Saksbehandler:", agent_list, index=current_idx, key=f"as_{sak_id}")
                    if st.button("Oppdater Ansvar", key=f"asb_{sak_id}"):
                        if update_sak_in_sheet(sak_id, {"Assigned_To": new_asgn}):
                            st.success(f"Ansvar tildelt {new_asgn}!")
                            st.rerun()

                # --- INFO & NOTES ---
                st.markdown("### 📄 Saksinformasjon")
                for k, v in r.items():
                    if k not in ['Chat_History', 'Assigned_To', 'Mangler']:
                        st.write(f"**{k}:** {v}")
                
                old_notater = str(r.get('Notater', ''))
                new_notater = st.text_area("Oppdater Notater", value=old_notater if old_notater != "nan" else "", key=f"edit_not_{sak_id}")
                if st.button("💾 Lagre Endringer", key=f"save_mod_{sak_id}"):
                    if update_sak_in_sheet(sak_id, {"Notater": new_notater}):
                        st.success("Lagret!")
                        st.rerun()
    else:
        st.warning("Ingen data tilgjengelig.")



# =================================================================
# --- 7. NY REGISTRERING (FINAL VERIFIED - NOTHING SKIPPED) ---
# =================================================================
elif valg == "➕ Ny Registrering":
    # --- 📈 DYNAMIC PROGRESS TRACKER ---
    steps = 0
    if st.session_state.get('navn_input'): steps += 25
    if st.session_state.get('fnr_input'): steps += 25
    if st.session_state.get('belop_input'): steps += 25
    if st.session_state.get('epost_input'): steps += 25

    # --- NEW MASTER STYLE HEADER ---
    st.markdown(f"""
        <div style='background: #2C3E50; padding: 20px; border-radius: 15px; color: white; margin-bottom: 20px; border-left: 10px solid #F1C40F;'>
            <h2 style='margin:0; color: #F1C40F;'>🚀 Ny Bankforespørsel</h2>
            <p style='opacity: 0.8; margin-bottom: 10px;'>Opprett en ny lånesøknad i systemet</p>
            <div style='background: rgba(255,255,255,0.1); border-radius: 10px; padding: 5px;'>
                <small>Søknad Completion: {steps}%</small>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    st.progress(steps / 100)

    countries = get_country_list()
    
    # --- SMART SELECTION ---
    c_top1, c_top2 = st.columns([2, 1])
    prod = c_top1.selectbox("🎯 Velg Produkt Type", ["Boliglån", "Refinansiering", "Mellomfinansiering", "Investlån / Bedriftlån", "Byggelån", "Forbrukslån", "Billån"])
    is_bedrift = "Bedriftlån" in prod or "Investlån" in prod
    is_billan = prod == "Billån"
    is_refin_mellom = prod in ["Refinansiering", "Mellomfinansiering"]

    st.markdown("---")
    st.info("💡 **Tips:** Har kunden en Medsøker? Marker her før du fyller ut skjemaet.")
    has_med = st.checkbox("✅ JA, legg til Medsøker (Ektefelle/Samboer)", key="med_toggle")

    with st.form("main_bank_form", clear_on_submit=True):
        f_navn, f_org, f_eier, f_aksjer = "", "", "", ""
        
        # --- 🏢 BEDRIFT SECTION (STAYS UNCHANGED) ---
        if is_bedrift:
            st.subheader("🏢 Bedrift / Firma Detaljer")
            bc1, bc2 = st.columns(2)
            f_navn = bc1.text_input("Firma Navn", placeholder="Eks: Nord Secure AS")
            f_org = bc1.text_input("Organisasjonsnummer (9 siffer)", placeholder="987 654 321")
            f_eier = bc2.text_area("Navn & Personnummer på alle eiere", placeholder="Ola Nordmann (010180 12345) - 50%")
            f_aksjer = bc2.text_input("Aksjefordeling (%)", placeholder="Eks: 50/50")
            st.divider()

        # --- 🏠 REFINANSIERING / MELLOMFINANSIERING SECTION (MODIFIED) ---
        eks_bank, eks_lan, bolig_takst, takst_alder = "", 0, 0, ""
        andre_lan_info, andre_bolig_info = "", ""

        if is_refin_mellom:
            st.markdown(f"<h3 style='color: #E67E22;'>🏠 Eiendomsdetaljer ({prod})</h3>", unsafe_allow_html=True)
            r1, r2 = st.columns(2)
            eks_bank = r1.text_input("Hvilken bank har de i dag?", placeholder="Eks: DNB, SpareBank 1")
            eks_lan = r2.number_input("Eksisterende boliglån totalt (kr)", min_value=0, step=50000, format="%d")
            
            # New Column for multiple loans
            andre_lan_info = st.text_input("Andre boliglån? (Bank & Beløp)", placeholder="Eks: Nordea 1.2M, Danske Bank 500k")
            
            st.markdown("---")
            r3, r4 = st.columns(2)
            bolig_takst = r3.number_input("Hovedbolig Takst (kr)", min_value=0, step=100000, format="%d")
            takst_alder = r4.text_input("Takst alder (Hovedbolig)", placeholder="Eks: e-takst fra Mars 2026")
            
            # New field for multiple properties
            andre_bolig_info = st.text_area("Andre Eiendommer? (Takst & Alder)", placeholder="Eks: Utleiebolig Oslo: 4M (Jan 2026), Hytte: 2M (2025)")
            st.divider()

        # --- 🚗 EXCLUSIVE BILLÅN SECTION ---
        if is_billan:
            st.markdown("<h3 style='color: #F39C12;'>🚗 Kjøretøy Detaljer (Billån)</h3>", unsafe_allow_html=True)
            v1, v2, v3 = st.columns(3)
            bil_merke = v1.text_input("Bilmerke & Modell", placeholder="Eks: Tesla Model 3")
            bil_reg = v2.text_input("Registreringsnummer", placeholder="Eks: EL 12345")
            bil_km = v3.text_input("Kilometerstand", placeholder="Eks: 45 000 km")
            
            v4, v5 = st.columns([2, 1])
            finn_link = v4.text_input("Finn.no Link (Valgfritt)", placeholder="https://www.finn.no/car/used/ad.html?finnkode=...")
            bil_egenkapital = v5.number_input("Egenkapital til bil (kr)", min_value=0, step=5000)
            st.divider()

        # --- 👤 HOVEDSØKER SECTION ---
        st.markdown("<h3 style='color: #4A69BD;'>👤 Hovedsøker Detaljer</h3>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        navn = c1.text_input("Fullt Navn (Hovedsøker) *", key="navn_input", placeholder="Eks: Ola Nordmann") 
        fnr = c1.text_input("Fødselsnummer (11 siffer)", key="fnr_input", placeholder="11 siffer (ddmmååxxxxx)")
        epost = c1.text_input("E-post", key="epost_input", placeholder="ola.nordmann@gmail.com")
        tlf = c2.text_input("Telefon", placeholder="Eks: 400 00 000")
        sivil = c2.selectbox("Sivilstatus", ["Enslig", "Gift", "Samboer", "Skilt", "Enke/Enkemann"])
        pass_land = c1.selectbox("Statsborgerskap (Pass fra)", countries, index=0)
        botid = c2.text_input("Botid i Norge", placeholder="Eks: Siden fødsel / 10 år")

        st.markdown("#### 💼 Arbeid & Inntekt (Hovedsøker)")
        l1, l2, l3 = st.columns(3)
        lonn = l1.number_input("Årslønn Brutto (kr)", min_value=0, step=10000, format="%d")
        arbeidsgiver = l2.text_input("Arbeidsgiver", placeholder="Eks: Equinor AS")
        ansatt_tid = l3.text_input("Ansettelsestid", placeholder="Eks: 3 år / Fast")
        stilling_type = l1.selectbox("Ansettelsesform", ["Fast ansatt", "Midlertidig", "Selvstendig", "Uføretrygd", "Pensjonist"])
        ekstra_jobb = l2.number_input("Bi-inntekt / Ekstra (kr/år)", 0)
        still_pst = l3.slider("Stillingsprosent (%)", 0, 100, 100)

        st.markdown("#### 🏠 Finansiell Status & Gjeld (Hovedsøker)")
        hf1, hf2, hf3, hf4 = st.columns(4)
        h_ek = hf1.number_input("Egenkapital (kr) - Hoved", 0, step=10000, format="%d")
        h_sfo = hf2.selectbox("SFO / Barnehage utgifter? - Hoved", ["Nei", "Ja"])
        h_gjeld = hf3.number_input("Forbruksgjeld (kr) - Hoved", 0, step=10000, format="%d")
        h_boliglan = hf4.number_input("Boliglån (kr) - Hoved", 0, step=50000, format="%d")

        # --- 👥 MEDSØKER SECTION ---
        m_navn, m_fnr, m_epost, m_tlf, m_sivil, m_pass, m_botid = "", "", "", "", "Gift", "Norge", ""
        m_lonn, m_arb, m_ansatt_tid, m_stilling, m_ekstra, m_pst = 0, "", "", "Fast ansatt", 0, 100
        m_ek, m_sfo, m_gjeld = 0, "Nei", 0
        
        if has_med:
            st.divider()
            st.markdown("<h3 style='color: #10AC84;'>👥 Medsøker Detaljer</h3>", unsafe_allow_html=True)
            mc1, mc2 = st.columns(2)
            m_navn = mc1.text_input("Fullt Navn (Medsøker)", placeholder="Eks: Kari Nordmann")
            m_fnr = mc1.text_input("Fødselsnummer (11 siffer - Medsøker)", placeholder="11 siffer")
            m_epost = mc1.text_input("E-post (Medsøker)", placeholder="kari@gmail.com")
            m_tlf = mc2.text_input("Telefon (Medsøker)", placeholder="Eks: 900 00 000")
            m_pass = mc1.selectbox("Statsborgerskap (Medsøker)", countries, key="ms_pass")
            m_botid = mc2.text_input("Botid i Norge (Medsøker)", key="ms_botid", placeholder="Eks: 5 år")

            st.markdown("#### 💼 Arbeid & Inntekt (Medsøker)")
            ml1, ml2, ml3 = st.columns(3)
            m_lonn = ml1.number_input("Årslønn Brutto (Medsøker)", min_value=0, step=10000, format="%d", key="ms_lonn")
            m_arb = ml2.text_input("Arbeidsgiver (Medsøker)", key="ms_arb", placeholder="Eks: Oslo Kommune")
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
        st.markdown("<h3 style='color: #2C3E50;'>📊 Lånesøknad & Vedlegg</h3>", unsafe_allow_html=True)
        f1, f2, f3 = st.columns(3)
        belop = f1.number_input("Ønsket Lånebeløp (kr)", 0, step=50000, format="%d", key="belop_input")
        barn = f2.number_input("Antall Barn totalt", 0, step=1)
        biler = f3.number_input("Antall Biler totalt", 0, step=1)

        # --- 📉 AUTO-CALCULATION SUMMARY BOX ---
        total_inc = lonn + m_lonn + ekstra_jobb + m_ekstra
        total_debt = h_gjeld + m_gjeld + h_boliglan + belop
        dti = round(total_debt / total_inc, 2) if total_inc > 0 else 0
        
        st.markdown(f"""
            <div style='background: #F0F4F8; padding: 15px; border-radius: 10px; border: 1px dashed #4A69BD; margin-bottom: 20px;'>
                <h4 style='margin:0; color: #4A69BD;'>📊 Økonomisk Oversikt (Live Analysis)</h4>
                <div style='display: flex; justify-content: space-between; margin-top: 10px;'>
                    <span>Total Inntekt: <b>{total_inc:,.0f} kr</b></span>
                    <span>Total Gjeld (inkl. bolig): <b>{total_debt:,.0f} kr</b></span>
                    <span>Gjeldsgrad: <span style='color:{"#E74C3C" if dti > 5 else "#27AE60"};'><b>{dti}x</b></span></span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Build dynamic notes based on product
        if is_billan:
            final_notes = f"--- BILLÅN INFO ---\nBil: {bil_merke}\nReg nr: {bil_reg}\nKM: {bil_km}\nEgenkapital: {bil_egenkapital} kr\nLink: {finn_link}"
        elif is_refin_mellom:
            final_notes = f"--- {prod.upper()} INFO ---\nBank i dag: {eks_bank}\nEksisterende lån: {eks_lan:,.0f} kr\nAndre lån: {andre_lan_info}\nTakst Hovedbolig: {bolig_takst:,.0f} kr ({takst_alder})\nAndre Eiendommer: {andre_bolig_info}"
        else:
            final_notes = ""

        notater = st.text_area("Interne Notater (Viktig info for banken)", value=final_notes, placeholder="Skriv relevante kommentarer her...")

        # --- 📂 DOKUMENT OPPLASTING ---
        st.markdown("#### 📁 Dokumentasjon")
        uploaded_files = st.file_uploader("Last opp Vedlegg (PDF, JPG, PNG)", accept_multiple_files=True, key="doc_uploader")
        
        # --- 🛡️ STATUS LOCK ---
        user_role = str(st.session_state.get('role', 'Ansatt')).strip().capitalize()
        if user_role in ["Admin", "Director"]:
            final_status = st.selectbox("Sak Status (KUN ADMIN)", ["Mottatt", "Under Behandling", "Godkjent", "Avslått", "Utbetalt"])
        else:
            final_status = "Mottatt"

        # --- 🚀 SUBMIT ---
        submit = st.form_submit_button("🚀 SEND SØKNAD TIL BANKEN", use_container_width=True)
        
        if submit:
            if not navn:
                st.error("Vennligst skriv inn navnet på Hovedsøker!")
            else:
                import json
                from datetime import datetime
                initial_chat = json.dumps([{"role": "Bank", "sender": "SYSTEM", "text": f"Søknad om {prod} mottatt.", "time": datetime.now().strftime("%d-%m-%Y %H:%M")}])
                
                # Precise 33-column mapping (PRESERVED 100%)
                new_row = [
                    len(df)+1, datetime.now().strftime("%d-%m-%Y"), prod, navn, fnr, epost, tlf, sivil,
                    "Bedrift" if is_bedrift else "Privat", "Active", f_navn if is_bedrift else "",
                    lonn, barn, h_sfo, (h_ek + m_ek), (h_gjeld + m_gjeld + h_boliglan), biler, belop,
                    f_org if is_bedrift else "", f_eier if is_bedrift else "", f_aksjer if is_bedrift else "",
                    m_navn, m_fnr, m_epost, m_tlf, m_lonn, m_arb, notater, f"P1: {pass_land} | P2: {m_pass}",
                    current_user, final_status, "Ingen", initial_chat
                ]
                
                if add_data("MainDB", new_row):
                    st.success(f"✅ {prod} registrert! ID: {len(df)+1}")
                    if uploaded_files: st.info(f"📂 {len(uploaded_files)} filer lagret.")
                    st.balloons()
                    st.rerun()                    
                    

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
            


# =================================================================
# --- 9. MASTER KONTROLLPANEL (COMPLETE ADMIN HUB) ---
# =================================================================
elif valg == "🛠️ Master Kontroll" and role in ["Admin", "Director"]:
    st.markdown(f"""
        <div style='background: #2C3E50; padding: 20px; border-radius: 15px; color: white; margin-bottom: 20px;'>
            <h2 style='margin:0; color: #F1C40F;'>🕵️ Master Kontrollpanel</h2>
            <p style='opacity: 0.8;'>Global styring av Agenter og Saker</p>
        </div>
    """, unsafe_allow_html=True)

    # --- TEEN TABS: Agents, Cases, aur System ---
    tab_agents, tab_cases, tab_system = st.tabs([
        "👥 Agentstyring", 
        "🛠️ Global Sakshåndtering", 
        "⚙️ System Verktøy"
    ])

    # --- TAB 1: AGENTSTYRING (Registration & Overview) ---
    with tab_agents:
        sub_tab1, sub_tab2 = st.tabs(["➕ Registrer Ny Agent", "📋 Oversikt Ansatte"])
        
        with sub_tab1:
            st.subheader("Opprett ny tilgang")
            with st.form("agent_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                u = col1.text_input("Brukernavn (Login)", placeholder="f.eks: ola123").lower().strip()
                p = col1.text_input("Passord", type="password", placeholder="Minimum 6 tegn")
                n = col2.text_input("Fullt Navn", placeholder="Ola Nordmann")
                pos = col2.selectbox("Stilling", ["Senior Agent", "Junior Agent", "Trainee", "Analytiker"])
                
                if st.form_submit_button("🚀 AKTIVER OG LAGRE AGENT", use_container_width=True):
                    if u and p and n:
                        add_data("Users", [u, p, "Worker"])
                        add_data("Agents", [u, n, pos, "09-17", "Aktiv", "Signert"])
                        st.success(f"✅ {n} er nå aktivert!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Fyll ut alle felt!")

        with sub_tab2:
            st.subheader("Aktive Agenter")
            agents_df = get_data("Agents")
            if not agents_df.empty:
                st.dataframe(agents_df[['username', 'navn', 'stilling', 'status']], use_container_width=True, hide_index=True)
            else:
                st.warning("Ingen agenter funnet.")

    # --- TAB 2: GLOBAL SAKSHÅNDTERING (Cases Management) ---
    with tab_cases:
        st.subheader("Global Oversikt over alle Saker")
        if not df.empty:
            search_m = st.text_input("🔍 Søk i databasen (Navn, ID, FNR)...", key="master_search")
            m_data = df.copy()
            if search_m:
                m_data = m_data[m_data.astype(str).apply(lambda x: x.str.contains(search_m, case=False)).any(axis=1)]

            st.write(f"Viser **{len(m_data)}** saker.")

            # Dynamic Agent List for assignment
            agents_list_df = get_data("Agents")
            agent_names = ["Ingen"] + agents_list_df['navn'].tolist() if not agents_list_df.empty else ["Ingen", "Bedi", "Iqbal"]

            for i, r in m_data.iterrows():
                sak_id = str(r.get('ID', i))
                hoved = str(r.get('Hovedsøker', r.get('Navn', 'Ukjent Kunde'))).strip()
                if hoved in ["nan", "", "N/A", "None"]: hoved = "Ukjent Kunde"
                belop = r.get('Lånebeløp', '0')
                ansvar_header = str(r.get('Assigned_To', 'Ingen')).strip()
                if "[" in ansvar_header or "{" in ansvar_header or ansvar_header.lower() in ["nan", "none", ""]: 
                    ansvar_header = "Ingen"

                with st.expander(f"🆔 {sak_id} | 👤 {hoved} | 💰 {belop} kr | 🛡️ Ansvar: {ansvar_header}"):
                    mc1, mc2 = st.columns(2)
                    
                    with mc1:
                        st.markdown("#### 👤 Endre Ansvar")
                        try:
                            idx = agent_names.index(ansvar_header) if ansvar_header in agent_names else 0
                        except: idx = 0
                        
                        new_asgn = st.selectbox("Velg Saksbehandler:", agent_names, index=idx, key=f"m_as_{sak_id}")
                        if st.button("Oppdater Ansvar", key=f"m_asb_{sak_id}"):
                            if update_sak_in_sheet(sak_id, {"Assigned_To": new_asgn}):
                                st.success("Oppdatert!")
                                st.rerun()

                    with mc2:
                        st.markdown("#### 🗑️ Slette Sak")
                        confirm_delete = st.checkbox("Bekreft permanent sletting", key=f"del_conf_{sak_id}")
                        if st.button(f"❌ SLETT SAK {sak_id}", key=f"del_btn_{sak_id}"):
                            if confirm_delete:
                                if delete_sak_from_sheet(sak_id):
                                    st.success(f"Sak {sak_id} slettet!")
                                    st.rerun()
                            else:
                                st.error("Bekreft sletting først!")

                    st.json(r.to_dict())
        else:
            st.warning("Databasen er tom.")

    # --- TAB 3: SYSTEM TOOLS ---
    with tab_system:
        st.write(f"Logget inn som: **{current_user}**")
        if st.button("Rens System Cache"):
            st.cache_data.clear()
            st.rerun()
            

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
# --- 💼 SAKSBEHANDLER PANEL (Error Fixed Version) ---
# =================================================================
elif valg == "💼 Saksbehandler Panel":
    st.header(f"💼 Saksbehandler: {current_user}")

    # Safety Check: Check if dataframe is not empty
    if df is not None and not df.empty:
        # Create a copy to work with
        sb_df = df.copy()

        # Check if 'Saksbehandler' column exists in your Sheet/DF
        if 'Saksbehandler' in sb_df.columns:
            # Safe Filtering
            # Hum .astype(str) se pehle check kar rahe hain ke data hai
            ny_mask = (sb_df['Saksbehandler'].fillna('').astype(str).str.lower() == str(current_user).lower()) & \
                      (sb_df.get('Status', '') == "Ny")
            
            ny_saker = sb_df[ny_mask]

            # --- DISPLAY LOGIC ---
            st.subheader("📥 Ny Oppgaver")
            if not ny_saker.empty:
                for idx, row in ny_saker.iterrows():
                    sak_id = str(row.get('ID', idx))
                    with st.expander(f"🆕 NY SAK: {row.get('Navn', 'Ukjent')}"):
                        st.write(f"**Beløp:** {row.get('Lånebeløp', '0')} kr")
                        if st.button(f"✅ Start Behandling", key=f"start_{sak_id}"):
                            if update_sak_in_sheet(sak_id, {"Status": "Under Behandling"}):
                                st.success("Saken er flyttet!")
                                st.rerun()
            else:
                st.info("Ingen nye oppgaver.")
        else:
            # Agar column name sheet mein kuch aur hai toh yahan error dikhayega
            st.error("⚠️ Kolonnen 'Saksbehandler' ble ikke funnet i databasen. Sjekk overskriften i Google Sheets.")
    else:
        st.warning("Databasen er tom eller ikke lastet inn.")
        
# --- FOOTER (FIXED Error Line) ---
st.sidebar.markdown("---")
st.sidebar.caption("NSVG CRM v2.0 | © NORDIC SECURE VAULT GROUP")
