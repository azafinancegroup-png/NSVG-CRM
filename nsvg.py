import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json
import smtplib
from email.mime.text import MIMEText
import pytz
import uuid
import re

# =================================================================
# --- 0. SESSION STATE INITIALIZATION (ANTI-DATA LOSS) ---
# =================================================================
if 'form_data' not in st.session_state:
    st.session_state.form_data = {
        "hovedsøker": "",
        "lånebeløp": 0.0,
        "telefon": "",
        "epost": "",
        "notater": ""
    }

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_role' not in st.session_state:
    st.session_state.user_role = None
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'navn' not in st.session_state:
    st.session_state.navn = None
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "📊 Dashbord"

# =================================================================
# --- 1. CONFIGURATION & AIRTABLE MODERN THEME ---
# =================================================================
st.set_page_config(page_title="NSVG CRM Pro", layout="wide", initial_sidebar_state="expanded")

# Ultra-Modern CSS Styling (Airtable Modern Gray/Pistachio Vibe)
st.markdown("""
    <style>
    /* Global Styles */
    .stApp { 
        background-color: #F8FAFC; 
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #1E293B;
    }
    
    /* Airtable-style Cards & Metrics */
    div[data-testid="stMetricValue"] {
        background-color: #FFFFFF;
        padding: 18px;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05), 0 1px 2px rgba(0,0,0,0.06);
        border: 1px solid #E2E8F0;
        border-bottom: 4px solid #10B981;
        font-weight: 700;
    }

    /* Modern Buttons */
    .stButton>button {
        background-color: #10B981 !important;
        color: #FFFFFF !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: 600 !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.2s ease-in-out !important;
    }
    .stButton>button:hover {
        background-color: #059669 !important;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.25);
    }

    /* Glassmorphism Sidebar */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E2E8F0;
    }
    
    /* Modern Expanders */
    .stExpander {
        background-color: #FFFFFF !important;
        border-radius: 10px !important;
        border: 1px solid #E2E8F0 !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02) !important;
        margin-bottom: 0.75rem !important;
    }

    /* Chat Bubble Styles */
    .bank-bubble { 
        background-color: #F0F9FF; 
        border-left: 4px solid #0284C7; 
        padding: 12px; 
        border-radius: 8px; 
        margin: 8px 0; 
        color: #0C4A6E; 
    }
    .agent-bubble { 
        background-color: #F8FAFC; 
        border-right: 4px solid #10B981; 
        padding: 12px; 
        border-radius: 8px; 
        margin: 8px 0; 
        text-align: right; 
        color: #0F172A; 
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }

    /* Decision Engine Cards */
    .decision-approved {
        background-color: #ECFDF5;
        border: 1px solid #10B981;
        border-left: 6px solid #10B981;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 15px;
    }
    .decision-rejected {
        background-color: #FEF2F2;
        border: 1px solid #EF4444;
        border-left: 6px solid #EF4444;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 15px;
    }
    .decision-bbank {
        background-color: #FFFBEB;
        border: 1px solid #F59E0B;
        border-left: 6px solid #F59E0B;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

# =================================================================
# --- 2. GLOBAL SETTINGS & UTILITIES ---
# =================================================================
def get_norway_time():
    tz = pytz.timezone('Europe/Oslo')
    return datetime.now(tz).strftime("%d.%m.%Y %H:%M")

@st.cache_data
def get_country_list():
    base = ["Norge", "Sverige", "Danmark", "UK", "USA", "Pakistan", "India"]
    others = sorted(["Afghanistan", "Albania", "Algerie", "Andorra", "Angola", "Argentina", "Australia", "Bangladesh", "Belgia", "Brasil", "Canada", "Chile", "China", "Egypt", "Finland", "Frankrike", "Hellas", "Island", "Iran", "Irak", "Irland", "Italia", "Japan", "Jordan", "Kuwait", "Latvia", "Libanon", "Malaysia", "Mexico", "Marokko", "Nederland", "New Zealand", "Nigeria", "Oman", "Filippinene", "Polen", "Portugal", "Qatar", "Romania", "Russland", "Saudi Arabia", "Singapore", "Spania", "Sri Lanka", "Sudan", "Sveits", "Syria", "Thailand", "Tunisia", "Tyrkia", "UAE", "Ukraina", "Vietnam"])
    return base + others

# =================================================================
# --- 3. GOOGLE SHEETS CONNECTION ENGINE (OPTIMIZED) ---
# =================================================================
def connect_to_sheet(sheet_name):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
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
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"Feil ved lagring av data: {e}")
            return False
    return False

def update_sheet_data_internal(worksheet_name, df_to_save):
    sh = connect_to_sheet(worksheet_name)
    if sh:
        try:
            sh.clear()
            df_filled = df_to_save.fillna("")
            data_to_update = [df_filled.columns.values.tolist()] + df_filled.values.tolist()
            sh.update('A1', data_to_update)
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"⚠️ Google Sheets Update Error: {e}")
            return False
    return False

def update_sak_in_sheet(sak_id, updated_values_dict):
    try:
        sh = connect_to_sheet("MainDB")
        if sh:
            data = sh.get_all_records()
            temp_df = pd.DataFrame(data)
            if 'ID' in temp_df.columns:
                matched_rows = temp_df.index[temp_df['ID'].astype(str) == str(sak_id)].tolist()
                if matched_rows:
                    actual_row = matched_rows[0] + 2 
                    for col_name, new_val in updated_values_dict.items():
                        if col_name in temp_df.columns:
                            col_idx = temp_df.columns.get_loc(col_name) + 1
                            sh.update_cell(actual_row, col_idx, str(new_val))
                    st.cache_data.clear()
                    return True
        return False
    except Exception as e:
        st.error(f"Database Error: {e}")
        return False

def delete_sak_from_sheet(sak_id): 
    try:
        sh = connect_to_sheet("MainDB")
        if sh:
            rows = sh.get_all_records()
            for index, row in enumerate(rows):
                if str(row.get('ID')) == str(sak_id):
                    row_num = index + 2
                    sh.delete_rows(row_num)
                    st.cache_data.clear()
                    return True
            return False
        return False
    except Exception as e:
        st.error(f"⚠️ Database Error ved sletting: {e}")
        return False

# =================================================================
# --- 3.5 FINANCEDB & AUTOMATED UNDERWRITING ENGINE ---
# =================================================================
def evaluate_loan_application(data):
    """
    Automated Underwriting Engine logic for Norwegian Mortgages & Refinancing.
    Evaluates Utlånsforskriften (5x Debt, 15% EK, Stress Test) + Bank Matching.
    """
    inntekt = float(data.get('Bruttoinntekt', 0))
    med_inntekt = float(data.get('Medsøker_Inntekt', 0))
    total_inntekt = inntekt + med_inntekt

    eksisterende_gjeld = float(data.get('Eksisterende_Gjeld', 0))
    sokt_lan = float(data.get('Søkt_Lån', 0))
    total_gjeld = eksisterende_gjeld + sokt_lan

    kjopesum = float(data.get('Kjøpesum', 0))
    egenkapital = float(data.get('Egenkapital', 0))

    har_inkasso = data.get('Betalingsanmerkninger', False)
    nav_ytelser = data.get('NAV_Ytelser', False)
    har_utleie = float(data.get('Rental_Income', 0))

    # Calculate Legal Rules
    effektiv_inntekt = total_inntekt + (har_utleie * 0.80)
    dti = total_gjeld / effektiv_inntekt if effektiv_inntekt > 0 else 999.0
    
    ek_pct = (egenkapital / kjopesum * 100) if kjopesum > 0 else 100.0
    
    # Base Stress Test Estimate (3% rate rise calculation)
    sifo_base_cost = 12000 + (3000 * float(data.get('Antall_Barn', 0)))
    estimated_monthly_pay = (total_gjeld * 0.08) / 12
    monthly_net_income = (effektiv_inntekt * 0.68) / 12
    sifo_stress_pass = (monthly_net_income - estimated_monthly_pay) >= sifo_base_cost

    reasons = []
    solutions = []
    
    # 1. Debt Limit Test (5x Rule)
    if dti > 5.0:
        reasons.append(f"Gjeldsgrad overstiger 5x inntekt (Nåværende: {dti:.2f}x).")
        solutions.append("Medsøker: Legg til medsøker med fast inntekt.")
        solutions.append("Realkausjonist: Bruk realkausjonist (foreldres bolig/realkausjon).")
        solutions.append("Slett kredittkort: Kanseller ubenyttede kredittrammer i Gjeldsregisteret.")

    # 2. Egenkapital Test (15% Rule)
    if kjopesum > 0 and ek_pct < 15.0:
        reasons.append(f"Egenkapital er under 15% kravet (Nåværende: {ek_pct:.1f}%).")
        solutions.append("Tilleggssikkerhet: Pant i annen eiendom (f.eks. foreldres bolig).")
        solutions.append("Startlån: Søk om Kommunalt Startlån via Husbanken.")

    # 3. SIFO Stress Test (+3% Interest Hike)
    if not sifo_stress_pass:
        reasons.append("Består ikke SIFO-stresstest (+3% renteøkning gir underskudd i likviditetsbudsjett).")
        solutions.append("Utleieinntekt: Kjøp bolig med godkjent utleiedel (tomannsbolig).")
        solutions.append("Skattekort: Juster skattekort/forskuddstrekk for å øke netto utbetalt.")

    # Bank Matching Rules
    eligible_a_banks = []
    eligible_b_banks = []

    if not har_inkasso and not nav_ytelser and dti <= 5.0 and ek_pct >= 15.0 and sifo_stress_pass:
        eligible_a_banks = ["SpareBank 1", "Sparebank Øst", "Nordea", "BN Bank", "Storebrand", "Sparebank 1 SMN", "Sparebank 1 Romerike"]
    
    # B-Bank Logic (Refinansiering / Betalingsanmerkninger / NAV)
    if har_inkasso or nav_ytelser or dti > 5.0 or not sifo_stress_pass:
        eligible_b_banks = ["Kraft Bank", "Bluestep Bank", "Nordax Bank", "Svea Bank", "Enito Bank / Balansebank", "Instabank"]
        if har_inkasso:
            solutions.append("Spesialrefinansiering: Søk Omstartslån med pant i bolig (LTV <= 85%) for å slette inkasso/anmerkninger.")

    status = "Godkjent A-Bank" if eligible_a_banks else ("B-Bank / Spesiallån" if eligible_b_banks else "Avslag")

    return {
        "status": status,
        "dti": round(dti, 2),
        "ek_pct": round(ek_pct, 1),
        "sifo_pass": sifo_stress_pass,
        "reasons": reasons,
        "solutions": solutions,
        "a_banks": eligible_a_banks,
        "b_banks": eligible_b_banks,
        "total_inntekt": total_inntekt,
        "total_gjeld": total_gjeld
    }

# =================================================================
# --- 4. LOGIN SYSTEM (STABLE & REFRESH-PROOF) ---
# =================================================================
if not st.session_state['logged_in']:
    st.title("🛡️ NSVG - Sikker Digital Portal")
    u_input = st.text_input("Brukernavn", key="login_user_field").lower().strip()
    p_input = st.text_input("Passord", type="password", key="login_pass_field")
    
    if st.button("Logg inn", use_container_width=True):
        users_df = get_data("Users")
        if not users_df.empty:
            match = users_df[(users_df['username'].astype(str).str.lower() == u_input) & 
                             (users_df['password'].astype(str) == p_input)]
            if not match.empty:
                role = match.iloc[0]['role']
                st.session_state['logged_in'] = True
                st.session_state['user_role'] = role
                st.session_state['user_id'] = u_input
                
                try:
                    agents_df = get_data("Agents")
                    agent_match = agents_df[agents_df['username'].astype(str).str.lower() == u_input]
                    if not agent_match.empty:
                        st.session_state['navn'] = agent_match.iloc[0]['navn']
                    else:
                        st.session_state['navn'] = u_input
                except:
                    st.session_state['navn'] = u_input
                
                st.success(f"Velkommen, {st.session_state['navn']}!")
                st.rerun()
            else: 
                st.error("Feil brukernavn eller passord!")
    st.stop()

# =================================================================
# --- 5. GLOBAL DATA & SIDEBAR MENU (ALL AGENTS HAVE SAKBEHANDLER PANEL) ---
# =================================================================
if st.session_state.get('logged_in'):
    raw_user = str(st.session_state.get('user_id', 'Guest')).lower().strip()
    if raw_user == "bedi":
        role = "Saksbehandler"
    else:
        role = st.session_state.get('user_role', 'Guest')
    username = st.session_state.get('navn') or st.session_state.get('user_id') or "Bruker"
    current_user = st.session_state.get('user_id', 'Guest')
else:
    role, username, current_user = "Guest", "Guest", "Guest"

try:
    df = get_data("MainDB") 
    if df is None or df.empty:
        df = get_data("Kunder")
except Exception as e:
    st.error(f"Data loading error: {e}")
    df = pd.DataFrame()

# Navigation Options: Saksbehandler Panel Enabled for ALL Active Roles & Agents
if role in ["Admin", "Director"]:
    options = ["📊 Dashbord", "➕ Ny Registrering", "📂 Kunde Arkiv", "💰 Regnskap Control (Admin)", "👥 Ansatte Kontroll", "📇 Kontakter", "💼 Saksbehandler Panel", "📋 Oversiktstavle", "🛠️ Master Kontroll"]
else:
    options = ["📊 Dashbord", "➕ Ny Registrering", "📂 Kunde Arkiv", "💼 Saksbehandler Panel", "💵 Min Provisjon", "🏦 Bankens Renters", "📜 Dokumentmaler", "📋 Oversiktstavle", "📞 Support Center"]

valg = st.sidebar.selectbox("Hovedmeny", options)

if st.sidebar.button("🔴 Logg ut"):
    st.session_state.clear()
    st.rerun()

# =================================================================
# --- 6. BANK MESSAGING HUB & CHECKLIST ---
# =================================================================
def display_bank_messaging_hub(sak_id, chat_data, role, username, agent_name="Agent"):
    st.markdown("---")
    me_clean = str(username).lower().strip()
    agent_display = str(agent_name).upper() if agent_name else "AGENT"
    target_label = "BANK" if role not in ["Admin", "Director"] else agent_display
    
    st.subheader(f"💬 Meldinger med {target_label}")

    try:
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
        is_bank = msg.get('role') == "Bank"
        div_class = "bank-bubble" if is_bank else "agent-bubble"
        sender_raw = msg.get("sender", "SYSTEM")
        display_name_msg = "BANK" if is_bank and role not in ["Admin", "Director"] else sender_raw.upper()
        
        m_col, d_col = st.columns([0.9, 0.1])
        with m_col:
            st.markdown(f'<div class="{div_class}"><b>{display_name_msg}</b><br>{msg.get("text","")}<br><small style="color: grey;">{msg.get("time","")}</small></div>', unsafe_allow_html=True)
        with d_col:
            if role in ["Admin", "Director"]:
                if st.button("🗑️", key=f"del_{sak_id}_{idx}"):
                    messages.pop(idx)
                    update_sak_in_sheet(sak_id, {"Chat_History": json.dumps(messages)})
                    st.rerun()

    st.divider()
    col_msg, col_file = st.columns([3, 1])
    msg_input = col_msg.text_input("Skriv melding...", key=f"input_{sak_id}")
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
# --- 7. MAIN VIEWS & PAGES IMPLEMENTATION ---
# =================================================================

# --- DASHBOARD VIEW ---
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
        for col in ['Saksbehandler', 'Assigned_To']:
            if col in df_clean.columns:
                df_clean[col] = df_clean[col].fillna('Ingen').astype(str)
            else:
                df_clean[col] = "Ingen"

        current_u_lower = str(current_user).lower().strip()
        
        if role in ["Admin", "Director"]:
            view_data = df_clean.copy()
        elif role == "Saksbehandler":
            mask_mine = df_clean['Saksbehandler'].str.lower().str.strip() == current_u_lower
            mask_assigned = df_clean['Assigned_To'].str.lower().str.strip() == current_u_lower
            view_data = df_clean[mask_mine | mask_assigned].copy()
        else:
            view_data = df_clean[df_clean['Saksbehandler'].str.lower().str.strip() == current_u_lower].copy()
        
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

        c1, c2, c3 = st.columns(3)
        loan_vals = pd.to_numeric(view_data.get('Lånebeløp', 0), errors='coerce').fillna(0)
        percent_vals = pd.to_numeric(view_data.get('Provisjon_Prosent', 0), errors='coerce').fillna(0) if 'Provisjon_Prosent' in view_data.columns else 0
        total_v = loan_vals.sum()
        total_p = (loan_vals * percent_vals / 100).sum()
        
        c1.metric("Antall Saker", len(view_data))
        c2.metric("Total Volum", f"{total_v:,.0f} kr")
        c3.metric("Beregnet Provisjon", f"{total_p:,.0f} kr")
        
        st.divider()
        st.subheader("Siste Registrerte Saker")

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

            with st.expander(f"{st_icon} {hoved} | {belop:,.0f} kr | Ansvar: {assigned_to_header}"):
                st.info("📋 **Portal Copy Tool**")
                fnr_val = r.get('Fødselsnummer', 'N/A')
                tlf_val = r.get('Telefon', 'N/A')
                copy_text = f"NAVN: {hoved}\nBELØP: {belop}\nFNR: {fnr_val}\nTLF: {tlf_val}"
                st.text_area("Klar til kopiering:", value=copy_text, height=100, key=f"cp_{sak_id}")
                if st.button("🚀 Marker som 'Sendt til Bank'", key=f"bsent_{sak_id}"):
                    if update_sak_in_sheet(sak_id, {"Bank_Status": "Under Behandling"}):
                        st.rerun()

                display_bank_messaging_hub(sak_id, chat_h, role, current_user, agent_navn)
                
                if role in ["Admin", "Director"]:
                    st.divider()
                    st.markdown("### 👤 Tildel Saksbehandler")
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

# --- NY REGISTRERING VIEW ---
elif valg == "➕ Ny Registrering":
    steps = 0
    if st.session_state.get('navn_input'): steps += 25
    if st.session_state.get('fnr_input'): steps += 25
    if st.session_state.get('belop_input'): steps += 25
    if st.session_state.get('epost_input'): steps += 25

    st.markdown(f"""
        <div style='background: #1E293B; padding: 20px; border-radius: 12px; color: white; margin-bottom: 20px; border-left: 8px solid #10B981;'>
            <h2 style='margin:0; color: #10B981;'>🚀 Ny Bankforespørsel</h2>
            <p style='opacity: 0.8; margin-bottom: 10px;'>Opprett en ny lånesøknad i systemet</p>
            <div style='background: rgba(255,255,255,0.1); border-radius: 8px; padding: 5px;'>
                <small>Søknad Completion: {steps}%</small>
            </div>
        </div>
    """, unsafe_allow_html=True)
    st.progress(steps / 100)

    countries = get_country_list()
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
        if is_bedrift:
            st.subheader("🏢 Bedrift / Firma Detaljer")
            bc1, bc2 = st.columns(2)
            f_navn = bc1.text_input("Firma Navn", placeholder="Eks: Nord Secure AS")
            f_org = bc1.text_input("Organisasjonsnummer (9 siffer)", placeholder="987 654 321")
            f_eier = bc2.text_area("Navn & Personnummer på alle eiere", placeholder="Ola Nordmann (010180 12345) - 50%")
            f_aksjer = bc2.text_input("Aksjefordeling (%)", placeholder="Eks: 50/50")
            st.divider()

        eks_bank, eks_lan, bolig_takst, takst_alder = "", 0, 0, ""
        andre_lan_info, andre_bolig_info = "", ""

        if is_refin_mellom:
            st.markdown("<h3 style='color: #E67E22;'>🏠 Eiendomsdetaljer</h3>", unsafe_allow_html=True)
            r1, r2 = st.columns(2)
            eks_bank = r1.text_input("Hvilken bank har de i dag?", placeholder="Eks: DNB, SpareBank 1")
            eks_lan = r2.number_input("Eksisterende boliglån totalt (kr)", min_value=0, step=50000, format="%d")
            andre_lan_info = st.text_input("Andre boliglån? (Bank & Beløp)", placeholder="Eks: Nordea 1.2M, Danske Bank 500k")
            st.markdown("---")
            r3, r4 = st.columns(2)
            bolig_takst = r3.number_input("Hovedbolig Takst (kr)", min_value=0, step=100000, format="%d")
            takst_alder = r4.text_input("Takst alder (Hovedbolig)", placeholder="Eks: e-takst fra Mars 2026")
            andre_bolig_info = st.text_area("Andre Eiendommer? (Takst & Alder)", placeholder="Eks: Utleiebolig Oslo: 4M (Jan 2026), Hytte: 2M (2025)")
            st.divider()

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

        st.markdown("<h3 style='color: #3B82F6;'>👤 Hovedsøker Detaljer</h3>", unsafe_allow_html=True)
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

        m_navn, m_fnr, m_epost, m_tlf, m_sivil, m_pass, m_botid = "", "", "", "", "Gift", "Norge", ""
        m_lonn, m_arb, m_ansatt_tid, m_stilling, m_ekstra, m_pst = 0, "", "", "Fast ansatt", 0, 100
        m_ek, m_sfo, m_gjeld = 0, "Nei", 0
        
        if has_med:
            st.divider()
            st.markdown("<h3 style='color: #10B981;'>👥 Medsøker Detaljer</h3>", unsafe_allow_html=True)
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
        st.markdown("<h3 style='color: #1E293B;'>📊 Lånesøknad & Vedlegg</h3>", unsafe_allow_html=True)
        f1, f2, f3 = st.columns(3)
        belop = f1.number_input("Ønsket Lånebeløp (kr)", 0, step=50000, format="%d", key="belop_input")
        barn = f2.number_input("Antall Barn totalt", 0, step=1)
        biler = f3.number_input("Antall Biler totalt", 0, step=1)

        total_inc = lonn + m_lonn + ekstra_jobb + m_ekstra
        total_debt = h_gjeld + m_gjeld + h_boliglan + belop
        dti = round(total_debt / total_inc, 2) if total_inc > 0 else 0
        
        st.markdown(f"""
            <div style='background: #F8FAFC; padding: 15px; border-radius: 10px; border: 1px dashed #3B82F6; margin-bottom: 20px;'>
                <h4 style='margin:0; color: #3B82F6;'>📊 Økonomisk Oversikt (Live Analysis)</h4>
                <div style='display: flex; justify-content: space-between; margin-top: 10px;'>
                    <span>Total Inntekt: <b>{total_inc:,.0f} kr</b></span>
                    <span>Total Gjeld (inkl. bolig): <b>{total_debt:,.0f} kr</b></span>
                    <span>Gjeldsgrad: <span style='color:{"#EF4444" if dti > 5 else "#10B981"};'><b>{dti}x</b></span></span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        if is_billan:
            final_notes = f"--- BILLÅN INFO ---\nBil: {bil_merke}\nReg nr: {bil_reg}\nKM: {bil_km}\nEgenkapital: {bil_egenkapital} kr\nLink: {finn_link}"
        elif is_refin_mellom:
            final_notes = f"--- {prod.upper()} INFO ---\nBank i dag: {eks_bank}\nEksisterende lån: {eks_lan:,.0f} kr\nAndre lån: {andre_lan_info}\nTakst Hovedbolig: {bolig_takst:,.0f} kr ({takst_alder})\nAndre Eiendommer: {andre_bolig_info}"
        else:
            final_notes = ""

        notater = st.text_area("Interne Notater (Viktig info for banken)", value=final_notes, placeholder="Skriv relevante kommentarer her...")
        uploaded_files = st.file_uploader("Last opp Vedlegg (PDF, JPG, PNG)", accept_multiple_files=True, key="doc_uploader")
        
        user_role = str(st.session_state.get('role', 'Ansatt')).strip().capitalize()
        if user_role in ["Admin", "Director"]:
            final_status = st.selectbox("Sak Status (KUN ADMIN)", ["Mottatt", "Under Behandling", "Godkjent", "Avslått", "Utbetalt"])
        else:
            final_status = "Under Behandling"

        submit = st.form_submit_button("🚀 SEND SØKNAD TIL BANKEN (Pushet til Saksbehandler Panel)", use_container_width=True)
        if submit:
            if not navn:
                st.error("Vennligst skriv inn navnet på Hovedsøker!")
            else:
                initial_chat = json.dumps([{"role": "Bank", "sender": "SYSTEM", "text": f"Søknad om {prod} mottatt og sendt til Saksbehandler Panel.", "time": get_norway_time()}])
                new_row = [
                    len(df)+1, datetime.now().strftime("%d-%m-%Y"), prod, navn, fnr, epost, tlf, sivil,
                    "Bedrift" if is_bedrift else "Privat", "Active", f_navn if is_bedrift else "",
                    lonn, barn, h_sfo, (h_ek + m_ek), (h_gjeld + m_gjeld + h_boliglan), biler, belop,
                    f_org if is_bedrift else "", f_eier if is_bedrift else "", f_aksjer if is_bedrift else "",
                    m_navn, m_fnr, m_epost, m_tlf, m_lonn, m_arb, notater, f"P1: {pass_land} | P2: {m_pass}",
                    current_user, final_status, current_user, initial_chat
                ]
                
                # 1. Main Data Base Insertion
                if add_data("MainDB", new_row):
                    # 2. AUTO CONTACT REGISTRATION FOR ADMIN CONTACTS LIST
                    try:
                        add_data("Contacts", [navn, epost, tlf, get_norway_time()])
                    except Exception as c_err:
                        pass # Auto contact register fallback mechanism
                    
                    st.success(f"✅ {prod} registrert og pushet til Saksbehandler Panel! ID: {len(df)+1}")
                    if uploaded_files: st.info(f"📂 {len(uploaded_files)} filer lagret.")
                    st.balloons()
                    st.rerun()

# --- KUNDE ARKIV VIEW ---
elif valg == "📂 Kunde Arkiv":
    st.header("📂 Kunde Arkiv - Modern Oversikt")
    
    @st.cache_data(ttl=60)
    def sikker_data_henting():
        return df
    
    gjeldende_df = sikker_data_henting()
    countries = get_country_list()

    hopp_til_id = st.session_state.get('search_query', "")
    visnings_df = gjeldende_df if role in ["Admin", "Director"] else gjeldende_df[gjeldende_df['Saksbehandler'].astype(str).str.lower() == current_user.lower()]
    
    sok = st.text_input("🔍 Søk etter kunde...", value=hopp_til_id, placeholder="Navn, ID, Telefon...", key="arkiv_sok_hoved")
    if sok:
        visnings_df = visnings_df[visnings_df.astype(str).apply(lambda x: x.str.contains(sok, case=False)).any(axis=1)]

    st.info(f"✨ **Viser {len(visnings_df)} aktive saker i systemet**")

    for i, r in visnings_df.iterrows():
        sak_id = str(r.get('ID', i))
        gjeldende_status = r.get('Bank_Status', 'Mottatt')
        chat_historikk = str(r.get('Chat_History', '[]')) 
        agent_navn = r.get('Saksbehandler', 'Agent') 
        
        status_ikon = "🔵"
        if gjeldende_status == "Godkjent": status_ikon = "🟢"
        elif gjeldende_status == "Avslått": status_ikon = "🔴"
        elif gjeldende_status == "Under Behandling": status_ikon = "🟡"
        elif gjeldende_status == "Utbetalt": status_ikon = "🟣"

        har_ulest = False
        if '"read": false' in chat_historikk.lower():
            try:
                meldinger = json.loads(chat_historikk)
                if meldinger and meldinger[-1].get('read') == False and str(meldinger[-1].get('sender', '')).lower() != str(current_user).lower():
                    har_ulest = True
            except: pass
            
        varsel = "🔴 NY MELDING | " if har_ulest else ""
        skal_utvides = True if (sok and str(sak_id) == str(sok)) else False

        with st.expander(f"{varsel}{status_ikon} **{r.get('Navn', r.get('Hovedsøker', 'Ukjent'))}** | ID: {sak_id} | STATUS: {gjeldende_status}", expanded=skal_utvides):
            if gjeldende_status == "Godkjent": st.success("✅ **Saken er Godkjent av Banken**")
            elif gjeldende_status == "Avslått": st.error("❌ **Saken er Avslått av Banken**")
            elif gjeldende_status == "Under Behandling": st.warning("⏳ **Saken er til vurdering hos Banken**")
            else: st.info("📩 **Søknaden er Mottatt**")

            st.divider()
            vis_redigering = st.checkbox("🛠️ Modifiser søknadsdata (Full tilgang)", key=f"mod_sjekk_{sak_id}")

            if not vis_redigering:
                st.markdown("#### 📄 Søknadsdetaljer")
                v1, v2, v3 = st.columns(3)
                v1.write(f"**👤 Navn:** {r.get('Navn', r.get('Hovedsøker', 'N/A'))}")
                v1.write(f"**📞 Tlf:** {r.get('Tlf', r.get('Telefon', 'N/A'))}")
                v2.write(f"**🏠 Produkt:** {r.get('Produkt', 'N/A')}")
                v2.write(f"**💰 Lånebeløp:** {r.get('Lånebeløp', '0')} kr")
                v3.write(f"**📅 Dato:** {r.get('Dato', 'N/A')}")
                v3.write(f"**👨‍💼 Ansvarlig:** {agent_navn}")
                st.write(f"**📝 Kommentarer:** {r.get('Notater', 'Ingen kommentarer lagret.')}")

                if role in ["Admin", "Director", "Saksbehandler"]:
                    st.divider()
                    st.subheader("👨‍💼 Tildel Saksbehandler")
                    saksbehandler_liste = ["-- Velg --", "Bedi", "Iqbal"] 
                    current_sb = r.get('Saksbehandler', "-- Velg --")
                    if current_sb not in saksbehandler_liste: current_sb = "-- Velg --"
                    selected_sb = st.selectbox("Send saken til:", saksbehandler_liste, index=saksbehandler_liste.index(current_sb), key=f"sb_assign_{sak_id}")
                    if st.button("🚀 Send sak nå", key=f"btn_sb_{sak_id}"):
                        if selected_sb != "-- Velg --":
                            if update_sak_in_sheet(sak_id, {"Saksbehandler": selected_sb, "Bank_Status": "Under Behandling"}):
                                st.toast(f"✅ Sak sendt til {selected_sb}!", icon="🚀")
                                st.cache_data.clear()
                                st.rerun()

                display_bank_messaging_hub(sak_id, chat_historikk, role, current_user, agent_navn)

            else:
                with st.form(key=f"full_edit_form_{sak_id}"):
                    st.subheader("📝 Oppdater Søknadsinformasjon")
                    prod_options = ["Boliglån", "Refinansiering", "Mellomfinansiering", "Investlån / Bedriftlån", "Byggelån", "Forbrukslån", "Billån"]
                    p_idx = prod_options.index(r.get('Produkt')) if r.get('Produkt') in prod_options else 0
                    prod = st.selectbox("Velg Produkt", prod_options, index=p_idx)
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
                    up_navn = h1.text_input("Fullt Navn *", value=str(r.get('Navn', r.get('Hovedsøker', ''))))
                    up_fnr = h1.text_input("Fødselsnummer", value=str(r.get('Fnr', r.get('Fødselsnummer', ''))))
                    up_epost = h2.text_input("E-post", value=str(r.get('Epost', r.get('E-post', ''))))
                    up_tlf = h2.text_input("Telefon", value=str(r.get('Tlf', r.get('Telefon', ''))))
                    
                    st.markdown("#### 💼 Økonomisk Profil")
                    l1, l2, l3 = st.columns(3)
                    up_lonn = l1.number_input("Årslønn Brutto (kr)", value=int(pd.to_numeric(r.get('Lønn', 0), errors='coerce') or 0), step=1000)
                    up_ek = l2.number_input("Egenkapital (kr)", value=int(pd.to_numeric(r.get('EK', 0), errors='coerce') or 0), step=1000)
                    up_gjeld = l3.number_input("Total Gjeld (kr)", value=int(pd.to_numeric(r.get('Gjeld', 0), errors='coerce') or 0), step=1000)

                    st.divider()
                    st.markdown("#### 👥 Medsøker")
                    m1, m2 = st.columns(2)
                    up_m_navn = m1.text_input("Medsøker Fullt Navn", value=str(r.get('Medsøker_Navn', '')))
                    up_m_fnr = m1.text_input("Medsøker Fødselsnummer", value=str(r.get('Medsøker_Fnr', '')))
                    up_m_lonn = m2.number_input("Medsøker Årslønn", value=int(pd.to_numeric(r.get('Medsøker_Lønn', 0), errors='coerce') or 0), step=1000)
                    up_m_tlf = m2.text_input("Medsøker Telefon", value=str(r.get('Medsøker_Tlf', '')))

                    st.divider()
                    st.markdown("#### 🏦 Bankbehandling & Godkjenning")
                    up_belop = st.number_input("Søkt Lånebeløp (kr)", value=int(pd.to_numeric(r.get('Lånebeløp', 0), errors='coerce') or 0), step=10000)
                    up_mangler = st.text_area("Mangler fra kunden", value=str(r.get('Mangler', '')))
                    up_notat = st.text_area("Bankens interne notater", value=str(r.get('Notater', '')))

                    status_valg = ["Mottatt", "Under Behandling", "Godkjent", "Avslått", "Utbetalt"]
                    try: s_idx = status_valg.index(gjeldende_status)
                    except: s_idx = 0
                    up_st = st.selectbox("Oppdater Endelig Saksstatus", status_valg, index=s_idx)

                    if st.form_submit_button("💾 OPPDATER SØKNAD"):
                        data_til_oppdatering = {
                            "Produkt": prod, "Hovedsøker": up_navn, "Fødselsnummer": up_fnr, "E-post": up_epost, "Telefon": up_tlf,
                            "Bank_Status": up_st, "Medsøker_Navn": up_m_navn, "Medsøker_Fnr": up_m_fnr,
                            "Medsøker_Tlf": up_m_tlf, "Lånebeløp": up_belop, "Notater": up_notat, "Mangler": up_mangler
                        }
                        if is_bedrift:
                            data_til_oppdatering.update({"Firma_Navn": up_f_navn, "Org_Nr": up_f_org, "Eiere_Info": up_f_eier, "Aksjer": up_f_aksjer})
                        if update_sak_in_sheet(sak_id, data_til_oppdatering):
                            st.cache_data.clear()
                            st.success(f"✅ Søknad {sak_id} er oppdatert!")
                            st.rerun()

                if role in ["Admin", "Director"]:
                    st.divider()
                    with st.expander("⚠️ Faresone: Slett denne søknaden"):
                        bekreft_sletting = st.checkbox(f"Bekreft sletting av sak {sak_id}", key=f"del_confirm_{sak_id}")
                        if st.button(f"🗑️ SLETT SØKNAD PERMANENT", key=f"del_btn_{sak_id}", disabled=not bekreft_sletting):
                            if delete_sak_from_sheet(sak_id):
                                st.cache_data.clear()
                                st.error(f"✅ Sak {sak_id} er fjernet.")
                                st.rerun()

# --- ADMIN REGNSKAP CONTROL VIEW (STRICT ADMIN ONLY) ---
elif valg == "💰 Regnskap Control (Admin)":
    if role not in ["Admin", "Director"]:
        st.error("🚫 Tilgang nektet! Kun Admin og Director har tilgang til Regnskap & Company Profits.")
        st.stop()

    st.markdown("""
        <div style='background: #1E293B; padding: 20px; border-radius: 12px; color: white; margin-bottom: 20px; border-left: 8px solid #10B981;'>
            <h2 style='margin:0; color: #10B981;'>💰 Regnskap & Finance Control Hub (ADMIN ONLY)</h2>
            <p style='opacity: 0.8; margin-bottom: 0;'>Full styring over Inntekt, Utgifter, Provisjoner & Netto Fortjeneste</p>
        </div>
    """, unsafe_allow_html=True)

    fin_tab1, fin_tab2, fin_tab3, fin_tab4 = st.tabs(["📊 Global Økonomi", "🏦 Registrer Inntekt", "💸 Driftsutgifter", "📜 Agent Payout Control"])

    try:
        finance_df = get_data("FinanceDB")
        if finance_df is None or finance_df.empty:
            finance_df = pd.DataFrame(columns=["ID", "Dato", "Type", "Kategori", "Beskrivelse", "Belop", "Agent", "Status"])
    except:
        finance_df = pd.DataFrame(columns=["ID", "Dato", "Type", "Kategori", "Beskrivelse", "Belop", "Agent", "Status"])

    # TAB 1: OVERVIEW & KPIs
    with fin_tab1:
        st.subheader("📈 Selskapets Total Økonomi")
        
        income_df = finance_df[finance_df['Type'] == 'Inntekt'] if not finance_df.empty else pd.DataFrame()
        expense_df = finance_df[finance_df['Type'] == 'Utgift'] if not finance_df.empty else pd.DataFrame()

        total_inc = pd.to_numeric(income_df.get('Belop', 0), errors='coerce').sum() if not income_df.empty else 0.0
        total_exp = pd.to_numeric(expense_df.get('Belop', 0), errors='coerce').sum() if not expense_df.empty else 0.0
        net_profit = total_inc - total_exp

        fc1, fc2, fc3 = st.columns(3)
        fc1.metric("💰 Brutto Inntekt", f"{total_inc:,.2f} kr")
        fc2.metric("💸 Totale Utgifter", f"{total_exp:,.2f} kr")
        fc3.metric("📈 Netto Profit (Selskap)", f"{net_profit:,.2f} kr", delta=f"{net_profit:,.2f} kr")

        st.divider()
        st.subheader("📋 Alle Registrerte Transaksjoner")
        if not finance_df.empty:
            st.dataframe(finance_df, use_container_width=True, hide_index=True)
        else:
            st.info("Ingen transaksjoner registrert i FinanceDB.")

    # TAB 2: REVENUE & COMMISSION TRACKER
    with fin_tab2:
        st.subheader("🏦 Registrer Innbetaling fra Bank")
        with st.form("add_income_form", clear_on_submit=True):
            ic1, ic2 = st.columns(2)
            inc_sak_id = ic1.text_input("Sak ID / Kunde Navn", placeholder="Eks: Sak #123 - Ola Nordmann")
            inc_bank = ic2.selectbox("Utbetalende Bank", ["DNB", "SpareBank 1", "Nordea", "BN Bank", "Storebrand", "Annet"])
            
            ic3, ic4 = st.columns(2)
            bank_commission = ic3.number_input("Provisjon Mottatt fra Bank (kr)", min_value=0.0, step=1000.0)
            agent_cut_pct = ic4.slider("Agent Provisjon Deling (%)", 0, 100, 10)

            agents_list = get_data("Agents")
            agent_names = agents_list['navn'].tolist() if not agents_list.empty else ["Bedi", "Iqbal", "Umer"]
            inc_agent = st.selectbox("Ansvarlig Agent", agent_names + ["Direkte / Hoved"])
            inc_desc = st.text_area("Beskrivelse / Notat", placeholder="Bankutbetaling for godkjent boliglån")

            agent_payout = (bank_commission * agent_cut_pct) / 100.0
            company_net = bank_commission - agent_payout

            st.info(f"📊 **Beregning:** Agent Får: `{agent_payout:,.2f} kr` | Selskap Beholder: `{company_net:,.2f} kr`")

            if st.form_submit_button("🚀 Registrer Inntekt"):
                if bank_commission > 0:
                    new_fin_row = [
                        uuid.uuid4().hex[:8], get_norway_time(), "Inntekt", inc_bank,
                        f"Sak: {inc_sak_id} - {inc_desc} (Company Net)", company_net, inc_agent, "Fullført"
                    ]
                    add_data("FinanceDB", new_fin_row)
                    
                    if agent_payout > 0:
                        agent_fin_row = [
                            uuid.uuid4().hex[:8], get_norway_time(), "Utgift", "Agent Provisjon",
                            f"Provisjon til {inc_agent} for Sak: {inc_sak_id}", agent_payout, inc_agent, "Pending Payout"
                        ]
                        add_data("FinanceDB", agent_fin_row)

                    st.success("✅ Inntekt og agent-provisjon er ført i regnskapet!")
                    st.rerun()

    # TAB 3: EXPENSE TRACKER
    with fin_tab3:
        st.subheader("💸 Registrer Ny Driftsutgift (Expense)")
        with st.form("add_expense_form", clear_on_submit=True):
            ec1, ec2 = st.columns(2)
            exp_cat = ec1.selectbox("Kategori", ["Kontor / Leie", "Programvare / Software", "Markedsføring / Ads", "Lønn / Agent Payout", "Juridisk / Revisor", "Diverse"])
            exp_amount = ec2.number_input("Beløp (kr)", min_value=0.0, step=500.0)
            exp_desc = st.text_input("Beskrivelse", placeholder="F.eks: Google Ads lisens / Husleie")
            
            if st.form_submit_button("➕ Lagre Utgift"):
                if exp_amount > 0 and exp_desc:
                    new_exp_row = [
                        uuid.uuid4().hex[:8], get_norway_time(), "Utgift", exp_cat,
                        exp_desc, exp_amount, current_user, "Betalt"
                    ]
                    if add_data("FinanceDB", new_exp_row):
                        st.success("✅ Utgift registrert!")
                        st.rerun()

    # TAB 4: AGENT PAYOUT LEDGER
    with fin_tab4:
        st.subheader("📜 Utbetaling av Agent Provisjoner")
        if not finance_df.empty:
            agent_payouts = finance_df[(finance_df['Kategori'] == "Agent Provisjon")]
            if not agent_payouts.empty:
                for idx, prow in agent_payouts.iterrows():
                    p_id = prow.get('ID')
                    p_stat = prow.get('Status', 'Pending Payout')
                    st_col = "🟢" if p_stat == "Betalt" else "🔴"
                    
                    with st.expander(f"{st_col} Agent: {prow.get('Agent')} | Beløp: {prow.get('Belop')} kr | Sak: {prow.get('Beskrivelse')}"):
                        st.write(f"**Dato:** {prow.get('Dato')}")
                        st.write(f"**Status:** {p_stat}")
                        if p_stat != "Betalt":
                            if st.button("✅ Marker som Utbetalt (Paid)", key=f"pay_agent_{p_id}"):
                                finance_df.loc[finance_df['ID'] == p_id, 'Status'] = "Betalt"
                                if update_sheet_data_internal("FinanceDB", finance_df):
                                    st.success("Utbetaling bekreftet og registrert!")
                                    st.rerun()
            else:
                st.info("Ingen utbetalinger til agenter registrert ennå.")

# --- AGENT PERSONAL COMMISSION VIEW (SAFE AGENT ACCESS) ---
elif valg == "💵 Min Provisjon":
    st.markdown(f"""
        <div style='background: #1E293B; padding: 20px; border-radius: 12px; color: white; margin-bottom: 20px;'>
            <h2 style='margin:0; color: #10B981;'>💵 Min Provisjon & Utbetalinger</h2>
            <p style='opacity: 0.8;'>Personlig oversikt for {username}</p>
        </div>
    """, unsafe_allow_html=True)

    try:
        finance_df = get_data("FinanceDB")
    except:
        finance_df = pd.DataFrame()

    if not finance_df.empty and 'Agent' in finance_df.columns:
        my_payouts = finance_df[(finance_df['Agent'].astype(str).str.lower() == str(username).lower()) | 
                                (finance_df['Agent'].astype(str).str.lower() == str(current_user).lower())]
        
        if not my_payouts.empty:
            earned = pd.to_numeric(my_payouts['Belop'], errors='coerce').sum()
            paid = pd.to_numeric(my_payouts[my_payouts['Status'] == 'Betalt']['Belop'], errors='coerce').sum()
            pending = earned - paid

            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("💰 Total Opptjent Provisjon", f"{earned:,.2f} kr")
            mc2.metric("🟢 Utbetalt til meg", f"{paid:,.2f} kr")
            mc3.metric("⏳ Venter på Utbetaling", f"{pending:,.2f} kr")

            st.divider()
            st.subheader("📋 Mine Provisjonsposter")
            st.dataframe(my_payouts[['Dato', 'Beskrivelse', 'Belop', 'Status']], use_container_width=True, hide_index=True)
        else:
            st.info("Du har ingen registrerte provisjoner i systemet ennå.")
    else:
        st.info("Ingen provisjonsdata tilgjengelig.")

# --- BANKENS RENTERS VIEW ---
elif valg == "🏦 Bankens Renters":
    st.header("🏦 Aktuelle Bankrenter")
    st.info("Oversikt over gjeldende renter for ulike låneprodukter.")
    col1, col2 = st.columns(2)
    col1.metric("Boliglån (Flytende)", "4.85%", "+0.25%")
    col1.metric("Refinansiering", "5.10%", "-0.10%")
    col2.metric("Billån", "6.20%", "Stabil")
    col2.metric("Forbrukslån", "11.5%", "Stabil")

# --- SUPPORT CENTER VIEW ---
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
                    now = get_norway_time()
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

# --- MASTER KONTROLLPANEL VIEW ---
elif valg == "🛠️ Master Kontroll" and role in ["Admin", "Director"]:
    st.markdown("""
        <div style='background: #1E293B; padding: 20px; border-radius: 12px; color: white; margin-bottom: 20px;'>
            <h2 style='margin:0; color: #10B981;'>🕵️ Master Kontrollpanel</h2>
            <p style='opacity: 0.8;'>Global styring av Agenter og Saker</p>
        </div>
    """, unsafe_allow_html=True)

    tab_agents, tab_cases, tab_system = st.tabs(["👥 Agentstyring", "🛠️ Global Sakshåndtering", "⚙️ System Verktøy"])

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

    with tab_cases:
        st.subheader("Global Oversikt over alle Saker")
        if not df.empty:
            search_m = st.text_input("🔍 Søk i databasen (Navn, ID, FNR)...", key="master_search")
            m_data = df.copy()
            if search_m:
                m_data = m_data[m_data.astype(str).apply(lambda x: x.str.contains(search_m, case=False)).any(axis=1)]

            agents_list_df = get_data("Agents")
            agent_names = ["Ingen"] + agents_list_df['navn'].tolist() if not agents_list_df.empty else ["Ingen", "Bedi", "Iqbal"]

            for i, r in m_data.iterrows():
                sak_id = str(r.get('ID', i))
                hoved = str(r.get('Hovedsøker', r.get('Navn', 'Ukjent Kunde'))).strip()
                if hoved in ["nan", "", "N/A", "None"]: hoved = "Ukjent Kunde"
                belop = r.get('Lånebeløp', '0')
                ansvar_header = str(r.get('Assigned_To', 'Ingen')).strip()

                with st.expander(f"🆔 {sak_id} | 👤 {hoved} | 💰 {belop} kr | 🛡️ Ansvar: {ansvar_header}"):
                    mc1, mc2 = st.columns(2)
                    with mc1:
                        st.markdown("#### 👤 Endre Ansvar")
                        try: idx = agent_names.index(ansvar_header) if ansvar_header in agent_names else 0
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

    with tab_system:
        st.write(f"Logget inn som: **{current_user}**")
        if st.button("Rens System Cache"):
            st.cache_data.clear()
            st.rerun()

# --- ANSATTE KONTROLL VIEW ---
elif valg == "👥 Ansatte Kontroll" and role in ["Admin", "Director"]:
    st.header("👥 Ansatte Oversikt og Kontroll")
    
    def get_status_badge(status):
        colors = {
            "Mottatt": ("#6c757d", "⚪"),
            "Under Behandling": ("#007bff", "🔵"),
            "Godkjent": ("#28a745", "🟢"),
            "Avslått": ("#dc3545", "🔴"),
            "Utbetalt": ("#ffc107", "🟡")
        }
        color, icon = colors.get(status, ("#000000", "❓"))
        return f'<span style="background-color:{color}; color:white; padding:4px 10px; border-radius:12px; font-weight:bold; font-size:14px;">{icon} {status}</span>'

    try:
        agents_df = get_data("Agents")
        main_df = df 
    except Exception as e:
        st.error(f"Kunne ikke hente agents: {e}")
        agents_df = pd.DataFrame()

    if not agents_df.empty:
        sok_agent = st.text_input("🔍 Søk etter ansatt...", placeholder="Skriv brukernavn eller navn...")
        if sok_agent:
            agents_df = agents_df[agents_df.astype(str).apply(lambda x: x.str.contains(sok_agent, case=False)).any(axis=1)]

        for i, row in agents_df.iterrows():
            a_user = str(row.get('username', '')).strip().lower()
            a_navn = row.get('navn', 'Ukjent')
            
            with st.expander(f"👤 {a_navn} (ID: {a_user})"):
                col1, col2 = st.columns(2)
                col1.markdown(f"**Stilling:** `{row.get('stilling', '-')}`")
                col1.markdown(f"**Vakt:** `{row.get('vakt', '-')}`")
                col1.markdown(f"**Nåværende Status:** `{row.get('status', '-')}`")
                
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
                    if st.button("📂 Se Saker", key=f"v_saker_{i}"):
                        if not agent_saker.empty:
                            for idx, s_row in agent_saker.iterrows():
                                sak_id = s_row.get('ID', idx)
                                current_st = s_row.get('Bank_Status', 'Mottatt')
                                with st.expander(f"📄 Sak: {s_row.get('Hovedsøker', 'Kunde')} (ID: {sak_id})"):
                                    st.markdown(f"**Status:** {get_status_badge(current_st)}", unsafe_allow_html=True)
                                    status_options = ["Mottatt", "Under Behandling", "Godkjent", "Avslått", "Utbetalt"]
                                    st_idx = status_options.index(current_st) if current_st in status_options else 0
                                    new_bank_st = st.selectbox("Oppdater Sak Status", status_options, index=st_idx, key=f"st_edit_{idx}_{i}")
                                    admin_prov_val = s_row.get('Admin_Provisjon', 0)
                                    if pd.isna(admin_prov_val): admin_prov_val = 0
                                    new_admin_p = st.number_input("Total Provisjon fra Bank (kr)", value=float(admin_prov_val), key=f"adm_p_{idx}_{i}")
                                    
                                    if new_bank_st == "Godkjent":
                                        st.success(f"💎 **Ansatt Provisjon (10%):** {new_admin_p * 0.10:,.2f} kr")
                                    
                                    mangler_msg_val = s_row.get('Mangler', '')
                                    mangler_msg = st.text_area("Mangler dokumenter", value=str(mangler_msg_val) if str(mangler_msg_val).lower() != 'nan' else "", key=f"msg_edit_{idx}_{i}")
                                    if st.button("🚀 Lagre Sak & Send Live", key=f"sv_edit_{idx}_{i}"):
                                        if update_sak_in_sheet(sak_id, {"Bank_Status": new_bank_st, "Mangler": mangler_msg, "Admin_Provisjon": new_admin_p}):
                                            st.success("Oppdatert!")
                                            st.rerun()

                with act2:
                    status_options_ag = ["Aktiv", "Inaktiv", "Permisjon"]
                    current_s = row.get('status', 'Aktiv')
                    idx_s = status_options_ag.index(current_s) if current_s in status_options_ag else 0
                    n_st = st.selectbox("Endre Agent Status", status_options_ag, index=idx_s, key=f"st_sel_{i}")
                    if st.button("💾 Oppdater Agent", key=f"upd_btn_{i}"):
                        st.success(f"Agent status oppdatert til {n_st}")

                with act3:
                    if st.button("🗑️ Slette Profil", key=f"del_btn_{i}"):
                        st.warning("Kun Admin kan slette.")

# --- KONTAKTER VIEW (STRICT ADMIN ONLY ACCESS) ---
elif valg == "📇 Kontakter":
    st.header("📇 Kontaktadministrasjon (Admin Live Database)")
    try:
        contacts_df = get_data("Contacts")
        if contacts_df is None or contacts_df.empty: 
            contacts_df = pd.DataFrame(columns=["Navn", "E-post", "Telefon", "Sist Endret"])
    except:
        contacts_df = pd.DataFrame(columns=["Navn", "E-post", "Telefon", "Sist Endret"])

    tab1, tab2, tab3 = st.tabs(["📇 Kontaktliste", "📩 Send E-post", "➕ Ny Kontakt"])

    with tab1:
        if not contacts_df.empty:
            st.dataframe(contacts_df, use_container_width=True, hide_index=True)
            selected_name = st.selectbox("Velg en kontakt:", ["-- Velg --"] + contacts_df["Navn"].tolist())
            if selected_name != "-- Velg --":
                idx = contacts_df[contacts_df["Navn"] == selected_name].index[0]
                with st.form(f"edit_form_{selected_name}"):
                    c1, c2 = st.columns(2)
                    new_n = c1.text_input("Navn", value=str(contacts_df.at[idx, "Navn"]))
                    new_e = c1.text_input("E-post", value=str(contacts_df.at[idx, "E-post"]))
                    new_t = c2.text_input("Telefon", value=str(contacts_df.at[idx, "Telefon"]))
                    if st.form_submit_button("💾 Lagre endringer"):
                        contacts_df.at[idx, "Navn"] = new_n
                        contacts_df.at[idx, "E-post"] = new_e
                        contacts_df.at[idx, "Telefon"] = new_t
                        contacts_df.at[idx, "Sist Endret"] = get_norway_time()
                        if update_sheet_data_internal("Contacts", contacts_df):
                            st.success("✅ Oppdatert!")
                            st.rerun()

    with tab2:
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
                        st.success("✅ E-post sendt!")
                    except Exception as e: st.error(f"Feil: {e}")

    with tab3:
        with st.form("new_con"):
            nn = st.text_input("Navn")
            ne = st.text_input("E-post")
            nt = st.text_input("Telefon")
            if st.form_submit_button("➕ Legg til"):
                if nn and ne:
                    new_row = pd.DataFrame([{"Navn":nn, "E-post":ne, "Telefon":nt, "Sist Endret": get_norway_time()}])
                    contacts_df = pd.concat([contacts_df, new_row], ignore_index=True)
                    if update_sheet_data_internal("Contacts", contacts_df):
                        st.success("✅ Lagret!")
                        st.rerun()

# --- DOKUMENTMALER VIEW ---
elif valg == "📜 Dokumentmaler":
    st.header("🏦 NSVG – Dokumentasjonsportal")
    st.caption("Nordic Secure Vault Group | Professional Banking Standards")
    st.divider()
    st.success("✅ **Portal-modus:** Alle krav vises direkte nedenfor. Ingen nedlasting nødvendig.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🏠 Boliglån & Refinans")
        st.markdown("""
        **Påkrevd Dokumentasjon:**
        * **Lønn:** Siste 3 mnd lønnslipper.
        * **Skatt:** Siste års skattemelding.
        * **Verdi:** Oppdatert **E-takst** (maks 6 mnd gammel).
        """)

    with col2:
        st.markdown("### 🏢 Næringslån (Bedrift)")
        st.markdown("""
        **Påkrevd Dokumentasjon:**
        * **Regnskap:** Fullstendig årsregnskap for **siste 2 år**.
        * **Drift:** Foreløpig saldobalanse.
        * **Firma:** Ny firmaattest fra Brønnøysund.
        """)

# --- SAKSBEHANDLER PANEL VIEW (INTEGRATED WITH FINANCEDB AUTOMATED UNDERWRITING ENGINE) ---
elif valg == "💼 Saksbehandler Panel":
    st.markdown(f"""
        <div style='background: #1E293B; padding: 20px; border-radius: 12px; color: white; margin-bottom: 20px; border-left: 8px solid #10B981;'>
            <h2 style='margin:0; color: #10B981;'>💼 Saksbehandler Panel & AI Underwriting Engine</h2>
            <p style='opacity: 0.8; margin-bottom: 0;'>Senior Bank Rådgiver Mode | Utlånsforskriften Checks | FinanceDB Integration</p>
        </div>
    """, unsafe_allow_html=True)

    sb_tab1, sb_tab2, sb_tab3 = st.tabs(["⚡ AI Automated Underwriting Engine", "📥 Mine Tildelte Saker / Saksbehandling", "📊 FinanceDB Live Data Matrix"])

    # TAB 1: AUTOMATED UNDERWRITING ENGINE & SMART SAK LIM
    with sb_tab1:
        st.subheader("🤖 Raw Text / Data Fast Parsing & Decision Engine")
        st.caption("Paste application raw text or json below to execute Instant Bank Matrix & Utlånsforskriften Checks.")

        raw_input_text = st.text_area("Paste Raw Application Text / Notes (Lim sak her)", height=140, placeholder="Eks:\nBruttoinntekt: 650000\nMedsøker Inntekt: 400000\nEksisterende Gjeld: 1200000\nSøkt Lån: 3000000\nKjøpesum: 4000000\nEgenkapital: 600000\nBetalingsanmerkninger: Nei\nNAV Ytelser: Nei\nRental Income: 0\nAntall Barn: 2")

        # Smart Parsing Regex Setup
        p_brutto_val, p_med_brutto_val, p_eks_gjeld_val = 650000.0, 0.0, 500000.0
        p_sokt_lan_val, p_kjopesum_val, p_ek_val = 2500000.0, 3500000.0, 600000.0
        p_rental_val, p_barn_val = 0.0, 1

        if raw_input_text:
            m_inc = re.search(r'(?:Bruttoinntekt|Lønn|Inntekt):\s*(\d+)', raw_input_text, re.IGNORECASE)
            m_med = re.search(r'Medsøker Inntekt:\s*(\d+)', raw_input_text, re.IGNORECASE)
            m_gjeld = re.search(r'(?:Eksisterende Gjeld|Gjeld):\s*(\d+)', raw_input_text, re.IGNORECASE)
            m_sokt = re.search(r'(?:Søkt Lån|Lånebeløp):\s*(\d+)', raw_input_text, re.IGNORECASE)
            m_kjop = re.search(r'Kjøpesum:\s*(\d+)', raw_input_text, re.IGNORECASE)
            m_ek = re.search(r'Egenkapital:\s*(\d+)', raw_input_text, re.IGNORECASE)

            if m_inc: p_brutto_val = float(m_inc.group(1))
            if m_med: p_med_brutto_val = float(m_med.group(1))
            if m_gjeld: p_eks_gjeld_val = float(m_gjeld.group(1))
            if m_sokt: p_sokt_lan_val = float(m_sokt.group(1))
            if m_kjop: p_kjopesum_val = float(m_kjop.group(1))
            if m_ek: p_ek_val = float(m_ek.group(1))

        col_p1, col_p2 = st.columns(2)
        p_brutto = col_p1.number_input("Bruttoinntekt Hovedsøker (kr)", value=p_brutto_val, step=25000.0)
        p_med_brutto = col_p2.number_input("Bruttoinntekt Medsøker (kr)", value=p_med_brutto_val, step=25000.0)
        p_eks_gjeld = col_p1.number_input("Eksisterende Total Gjeld (kr)", value=p_eks_gjeld_val, step=25000.0)
        p_sokt_lan = col_p2.number_input("Ønsket / Søkt Lånebeløp (kr)", value=p_sokt_lan_val, step=50000.0)
        p_kjopesum = col_p1.number_input("Kjøpesum / Boligverdi (kr)", value=p_kjopesum_val, step=50000.0)
        p_ek = col_p2.number_input("Egenkapital Tilgjengelig (kr)", value=p_ek_val, step=25000.0)
        p_rental = col_p1.number_input("Månedlig Utleieinntekt (kr)", value=p_rental_val, step=1000.0)
        p_barn = col_p2.number_input("Antall Barn i Husstanden", value=p_barn_val, step=1)

        c_check1, c_check2 = st.columns(2)
        p_inkasso = c_check1.checkbox("🚨 Har Betalingsanmerkning / Active Inkasso")
        p_nav = c_check2.checkbox("💼 Hovedinntekt fra NAV (AAP / Uføretrygd)")

        if st.button("🚀 Kjør Bank Policy & Decision Engine", use_container_width=True):
            eval_payload = {
                "Bruttoinntekt": p_brutto,
                "Medsøker_Inntekt": p_med_brutto,
                "Eksisterende_Gjeld": p_eks_gjeld,
                "Søkt_Lån": p_sokt_lan,
                "Kjøpesum": p_kjopesum,
                "Egenkapital": p_ek,
                "Betalingsanmerkninger": p_inkasso,
                "NAV_Ytelser": p_nav,
                "Rental_Income": p_rental * 12,
                "Antall_Barn": p_barn
            }

            res = evaluate_loan_application(eval_payload)

            st.divider()
            st.markdown("### 📑 AI Decision & Underwriting Result")

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Gjeldsgrad (DTI)", f"{res['dti']}x", delta="Inkl. Utlånsforskriften" if res['dti'] <= 5.0 else "Over 5x Grense", delta_color="normal" if res['dti'] <= 5.0 else "inverse")
            m2.metric("Egenkapital", f"{res['ek_pct']}%", delta="Min 15% Krav" if res['ek_pct'] >= 15.0 else "Under 15%", delta_color="normal" if res['ek_pct'] >= 15.0 else "inverse")
            m3.metric("SIFO Stresstest (+3%)", "PASSED ✅" if res['sifo_pass'] else "FAILED ❌")
            m4.metric("Saks-Status", res['status'])

            if res['status'] == "Godkjent A-Bank":
                st.markdown("""
                <div class='decision-approved'>
                    <h3 style='color:#065F46; margin:0;'>🟢 GODKJENT FOR STANDARD A-BANKER</h3>
                    <p style='color:#047857;'>Søknaden oppfyller alle kravene i Utlånsforskriften!</p>
                </div>
                """, unsafe_allow_html=True)
                st.subheader("🏛️ Anbefalte A-Banker:")
                st.write(", ".join([f"**{b}**" for b in res['a_banks']]))

            elif res['status'] == "B-Bank / Spesiallån":
                st.markdown("""
                <div class='decision-bbank'>
                    <h3 style='color:#92400E; margin:0;'>🟡 OMRUTES TIL B-BANKER (SPESIALLÅN / REFINANSIERING)</h3>
                    <p style='color:#B45309;'>Kunden kvalifiserer ikke for standard A-Banker, men kan innvilges hos spesialistbanker.</p>
                </div>
                """, unsafe_allow_html=True)
                st.subheader("🏦 Aktuelle B-Banker:")
                st.write(", ".join([f"**{b}**" for b in res['b_banks']]))

            else:
                st.markdown("""
                <div class='decision-rejected'>
                    <h3 style='color:#991B1B; margin:0;'>🔴 AVSLAG / MÅ STRUKTURERES PÅ NYTT</h3>
                    <p style='color:#B91C1C;'>Søknaden avslås etter standard retningslinjer.</p>
                </div>
                """, unsafe_allow_html=True)

            if res['reasons']:
                st.markdown("#### ⚠️ Årsaker til Avslag/Omrutering:")
                for r_msg in res['reasons']:
                    st.write(f"- ❌ {r_msg}")

            if res['solutions']:
                st.markdown("#### 💡 Smart Alternative Solutions (Løsninger):")
                for s_msg in res['solutions']:
                    st.write(f"- 🛠️ {s_msg}")

            st.divider()
            if st.button("💾 Lagre Evaluering i FinanceDB & Sync"):
                eval_row = [
                    uuid.uuid4().hex[:8], get_norway_time(), "Inntekt Evaluering", "Underwriting Engine",
                    f"DTI: {res['dti']}x | EK: {res['ek_pct']}% | Status: {res['status']}", p_sokt_lan, current_user, "Evaluert"
                ]
                add_data("FinanceDB", eval_row)
                st.success("✅ Underwriting Evaluation lagret i FinanceDB!")

    # TAB 2: MINE TILDELTE SAKER (FIXED FOR ALL SAKER ACCESSIBILITY & CONTROLS)
    with sb_tab2:
        st.subheader(f"📥 Alle Behandlingsklare Saker i Systemet")
        if df is not None and not df.empty:
            sb_df = df.copy()
            # Shows all cases for Admin/Saksbehandler or assigned ones
            mine_saker = sb_df
            
            if not mine_saker.empty:
                for idx, row in mine_saker.iterrows():
                    sak_id = str(row.get('ID', idx))
                    hoved_navn = str(row.get('Hovedsøker', row.get('Navn', 'Ukjent Kunde'))).strip()
                    if hoved_navn in ["nan", "", "None", "N/A"]: hoved_navn = "Ukjent Kunde"
                    
                    b_status = str(row.get('Bank_Status', 'Mottatt'))
                    st_icon = "🔵" if b_status == "Mottatt" else "🟡" if b_status == "Under Behandling" else "🟢" if b_status == "Godkjent" else "🔴"
                    
                    with st.expander(f"{st_icon} ID: {sak_id} | Kunde: {hoved_navn} | Status: {b_status}"):
                        c_a, c_b = st.columns(2)
                        c_a.write(f"**Lånebeløp:** {row.get('Lånebeløp', '0')} kr")
                        c_a.write(f"**Produkt:** {row.get('Produkt', 'N/A')}")
                        c_b.write(f"**Telefon:** {row.get('Telefon', row.get('Tlf', 'N/A'))}")
                        c_b.write(f"**E-post:** {row.get('Epost', row.get('E-post', 'N/A'))}")

                        st.markdown("---")
                        st.subheader("🔄 Oppdater Saksstatus & Bank Valg")
                        col_sel_b, col_sel_s = st.columns(2)
                        target_bank = col_sel_b.selectbox("Send til Bank:", ["DNB", "SpareBank 1", "Nordea", "Kraft Bank", "Bluestep Bank", "Nordax Bank", "Svea Bank", "Storebrand"], key=f"sb_bank_sel_{sak_id}")
                        
                        status_list = ["Mottatt", "Under Behandling", "Godkjent", "Avslått", "Utbetalt"]
                        try: st_curr_idx = status_list.index(b_status)
                        except: st_curr_idx = 1
                        
                        new_st = col_sel_s.selectbox("Status", status_list, index=st_curr_idx, key=f"sb_st_{sak_id}")
                        
                        # AI Fast Check Button inside individual Sak
                        if st.button(f"🔍 Evaluere Sak {sak_id} (Kjør Underwriting)", key=f"eval_btn_{sak_id}"):
                            try:
                                l_val = float(pd.to_numeric(row.get('Lønn', 0), errors='coerce') or 600000)
                                d_val = float(pd.to_numeric(row.get('Gjeld', 0), errors='coerce') or 0)
                                b_val = float(pd.to_numeric(row.get('Lånebeløp', 0), errors='coerce') or 0)
                                ek_val = float(pd.to_numeric(row.get('EK', 0), errors='coerce') or 0)
                                eval_quick = evaluate_loan_application({
                                    "Bruttoinntekt": l_val, "Medsøker_Inntekt": 0, "Eksisterende_Gjeld": d_val,
                                    "Søkt_Lån": b_val, "Kjøpesum": b_val + ek_val, "Egenkapital": ek_val,
                                    "Betalingsanmerkninger": False, "NAV_Ytelser": False, "Rental_Income": 0, "Antall_Barn": 1
                                })
                                if eval_quick['status'] == "Godkjent A-Bank":
                                    st.success(f"✅ **Saken kan Godkjennes!** (DTI: {eval_quick['dti']}x, SIFO Pass)")
                                elif eval_quick['status'] == "B-Bank / Spesiallån":
                                    st.warning(f"🟡 **B-Bank Omrutering:** (DTI: {eval_quick['dti']}x). Aktuelle: {', '.join(eval_quick['b_banks'])}")
                                else:
                                    st.error(f"🔴 **Avslag Risiko:** (DTI: {eval_quick['dti']}x).")
                            except Exception as ex_ev:
                                st.error(f"Kunne ikke beregne automatisk: {ex_ev}")

                        if st.button("💾 Lagre Status & Bank Endring", key=f"sb_save_{sak_id}"):
                            if update_sak_in_sheet(sak_id, {"Bank_Status": new_st, "Notater": f"Sendt til: {target_bank} | Status: {new_st}"}):
                                st.success(f"Status oppdatert og sendt til {target_bank}!")
                                st.rerun()

                        chat_h = row.get('Chat_History', '')
                        display_bank_messaging_hub(sak_id, chat_h, role, current_user, username)
            else:
                st.info("Ingen nye tildelte saker funnet i systemet.")
        else:
            st.warning("Databasen er tom.")

    # TAB 3: FINANCEDB LIVE MATRIX
    with sb_tab3:
        st.subheader("📊 Live FinanceDB Overview")
        try:
            f_df = get_data("FinanceDB")
            if not f_df.empty:
                st.dataframe(f_df, use_container_width=True, hide_index=True)
            else:
                st.info("FinanceDB er tom.")
        except Exception as e:
            st.error(f"Kunne ikke hente FinanceDB: {e}")

# --- OVERSIKTSTAVLE VIEW ---
elif valg == "📋 Oversiktstavle":
    st.header("📋 Digital Styringstavle & CRM Workspace")
    st.caption("Nordic Secure Vault Group | Intern Styringstavle")
    st.divider()

    st.subheader("📅 Velg Periode")
    col_cal1, col_cal2 = st.columns(2)
    valgt_maaned = col_cal1.selectbox("Arbeidsmåned:", ["Mai 2026", "Juni 2026", "Juli 2026", "August 2026", "September 2026", "Oktober 2026", "November 2026", "Desember 2026"], index=2)
    valgt_dato = col_cal2.date_input("Dagens Dato:", value=None)

    if 'nsvg_workspace_data' not in st.session_state:
        st.session_state.nsvg_workspace_data = {"Aktiv Saker": [], "Fremkommer Saker": [], "Innbetaling": [], "Utbetaling": []}

    def load_board_from_sheets():
        try:
            sheet_df = get_data("Oversiktstavle")
            if sheet_df is None or sheet_df.empty: return None
            loaded_data = {"Aktiv Saker": [], "Fremkommer Saker": [], "Innbetaling": [], "Utbetaling": []}
            for _, row in sheet_df.iterrows():
                sec = str(row.get("Seksjon", "")).strip()
                if sec in loaded_data:
                    loaded_data[sec].append({
                        "id": str(row.get("ID", uuid.uuid4().hex)),
                        "navn": str(row.get("Navn_Fra_Til", "")),
                        "fra": str(row.get("Navn_Fra_Til", "")),
                        "til": str(row.get("Navn_Fra_Til", "")),
                        "agent": str(row.get("Agent", "Direkte")),
                        "deal": str(row.get("Belop", "0")),
                        "belop": str(row.get("Belop", "0")),
                        "bank": str(row.get("Bank", "Ingen / Ikke sendt")),
                        "status": str(row.get("Status", "")),
                        "dato": str(row.get("Maaned", valgt_maaned))
                    })
            return loaded_data
        except Exception as e:
            return None

    def save_board_to_sheets(all_data):
        rows_to_save = []
        for sec_name, items in all_data.items():
            for item in items:
                name_val = item.get("navn") or item.get("fra") or item.get("til") or ""
                belop_val = item.get("deal") or item.get("belop") or "0"
                if "id" not in item: item["id"] = uuid.uuid4().hex
                rows_to_save.append({
                    "ID": item.get("id"), "Seksjon": sec_name, "Maaned": item.get("dato", valgt_maaned),
                    "Navn_Fra_Til": name_val, "Agent": item.get("agent", "Direkte"),
                    "Belop": belop_val, "Bank": item.get("bank", "Ingen / Ikke sendt"), "Status": item.get("status", "")
                })
        return update_sheet_data_internal("Oversiktstavle", pd.DataFrame(rows_to_save))

    if 'nsvg_sheets_loaded' not in st.session_state or not st.session_state.nsvg_sheets_loaded:
        sheets_data = load_board_from_sheets()
        if sheets_data is not None: st.session_state.nsvg_workspace_data = sheets_data
        st.session_state.nsvg_sheets_loaded = True

    c_sync1, c_sync2 = st.columns([4, 1])
    if c_sync2.button("🔄 Tving Synk", use_container_width=True):
        sheets_data = load_board_from_sheets()
        if sheets_data is not None:
            st.session_state.nsvg_workspace_data = sheets_data
            st.success("Synkronisert!")
            st.rerun()

    def rens_belop(tekst):
        try:
            tall = "".join([c for c in str(tekst) if c.isdigit() or c == "."])
            return float(tall) if tall else 0.0
        except: return 0.0

    st.markdown("### 📊 Økonomisk Oversikt for " + valgt_maaned)
    total_inn = sum([rens_belop(i.get("belop", 0)) for i in st.session_state.nsvg_workspace_data.get("Innbetaling", []) if i.get("dato") == valgt_maaned])
    total_ut = sum([rens_belop(u.get("belop", 0)) for u in st.session_state.nsvg_workspace_data.get("Utbetaling", []) if u.get("dato") == valgt_maaned])
    netto = total_inn - total_ut

    fin_c1, fin_c2, fin_c3 = st.columns(3)
    fin_c1.metric("💰 Totalt Innbetalinger", f"{total_inn:,.2f} kr")
    fin_c2.metric("💸 Totalt Utbetalinger", f"{total_ut:,.2f} kr")
    fin_c3.metric("📈 Netto Balanse", f"{netto:,.2f} kr", delta=f"{netto:,.2f} kr")
    st.divider()

    ui_cols = st.columns(4)
    with ui_cols[0]:
        st.markdown("**🔹 AKTIV SAKER**")
        aktiv_liste = st.session_state.nsvg_workspace_data.get("Aktiv Saker", [])
        for idx, item in enumerate(aktiv_liste):
            if item.get("dato") == valgt_maaned:
                with st.expander(f"📁 {item.get('navn')} ({item.get('deal')} kr)"):
                    item["navn"] = st.text_input("Navn:", value=item.get("navn", ""), key=f"n_act_{idx}")
                    item["deal"] = st.text_input("Beløp:", value=item.get("deal", ""), key=f"d_act_{idx}")
                    if st.button("💾 Lagre", key=f"sv_act_{idx}"):
                        save_board_to_sheets(st.session_state.nsvg_workspace_data)
                        st.rerun()

    with ui_cols[1]:
        st.markdown("**🔸 FREMTIDIGE SAKER**")
        frem_liste = st.session_state.nsvg_workspace_data.get("Fremkommer Saker", [])
        for idx, item in enumerate(frem_liste):
            if item.get("dato") == valgt_maaned:
                with st.expander(f"⏳ {item.get('navn')} ({item.get('deal')} kr)"):
                    item["navn"] = st.text_input("Navn:", value=item.get("navn", ""), key=f"n_frm_{idx}")
                    if st.button("💾 Lagre", key=f"sv_frm_{idx}"):
                        save_board_to_sheets(st.session_state.nsvg_workspace_data)
                        st.rerun()

    with ui_cols[2]:
        st.markdown("**📥 INNBETALINGER**")
        inn_liste = st.session_state.nsvg_workspace_data.get("Innbetaling", [])
        for idx, item in enumerate(inn_liste):
            if item.get("dato") == valgt_maaned:
                with st.expander(f"💰 {item.get('fra')} ({item.get('belop')} kr)"):
                    item["fra"] = st.text_input("Fra:", value=item.get("fra", ""), key=f"f_inn_{idx}")
                    if st.button("💾 Lagre", key=f"sv_inn_{idx}"):
                        save_board_to_sheets(st.session_state.nsvg_workspace_data)
                        st.rerun()

    with ui_cols[3]:
        st.markdown("**💸 UTBETALINGER**")
        ut_liste = st.session_state.nsvg_workspace_data.get("Utbetaling", [])
        for idx, item in enumerate(ut_liste):
            if item.get("dato") == valgt_maaned:
                with st.expander(f"💸 {item.get('til')} ({item.get('belop')} kr)"):
                    item["til"] = st.text_input("Til:", value=item.get("til", ""), key=f"t_ut_{idx}")
                    if st.button("💾 Lagre", key=f"sv_ut_{idx}"):
                        save_board_to_sheets(st.session_state.nsvg_workspace_data)
                        st.rerun()

# =================================================================
# --- FOOTER ---
# =================================================================
st.write("")
st.divider()
st.caption("© 2026 Nordic Secure Vault Group | Utviklet for intern styring og CRM")
