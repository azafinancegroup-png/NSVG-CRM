import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import pytz
import json
import extra_streamlit_components as stx
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ==========================================
# 1. PAGE CONFIGURATION & INITIAL STATE
# ==========================================
st.set_page_config(
    page_title="NSVG CRM Pro",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Timezone Setup (Norway/Oslo)
NORWAY_TZ = pytz.timezone('Europe/Oslo')

def get_norway_now():
    return datetime.datetime.now(NORWAY_TZ)

# ==========================================
# 2. ULTRA-MODERN GLASSMORPHISM CSS ENGINE
# ==========================================
def inject_modern_css():
    st.markdown("""
        <style>
        /* Import Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            color: #1e293b;
        }

        /* Main Container Background */
        .stApp {
            background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        }

        /* Glassmorphism Card Style */
        .glass-card {
            background: rgba(255, 255, 255, 0.75);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.5);
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.07);
            padding: 24px;
            margin-bottom: 20px;
            transition: all 0.3s ease;
        }

        .glass-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 40px 0 rgba(31, 38, 135, 0.12);
        }

        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background: rgba(15, 23, 42, 0.95) !important;
            backdrop-filter: blur(16px);
            border-right: 1px solid rgba(255, 255, 255, 0.1);
        }

        [data-testid="stSidebar"] * {
            color: #f1f5f9 !important;
        }

        [data-testid="stSidebar"] .stRadio label {
            font-size: 1.05rem !important;
            font-weight: 500 !important;
            padding: 10px 14px !important;
            border-radius: 10px !important;
            transition: background 0.2s;
        }

        [data-testid="stSidebar"] .stRadio label:hover {
            background: rgba(255, 255, 255, 0.1) !important;
        }

        /* Modern Metric Cards */
        .metric-card {
            background: linear-gradient(135deg, #ffffff 0%, #f1f5f9 100%);
            border-radius: 14px;
            padding: 18px 22px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.03);
            text-align: left;
        }
        .metric-title {
            font-size: 0.85rem;
            color: #64748b;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .metric-value {
            font-size: 1.8rem;
            color: #0f172a;
            font-weight: 700;
            margin-top: 4px;
        }

        /* Status Badges */
        .badge {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            display: inline-block;
        }
        .badge-active { background-color: #dcfce7; color: #166534; }
        .badge-pending { background-color: #fef3c7; color: #92400e; }
        .badge-rejected { background-color: #fee2e2; color: #991b1b; }
        .badge-info { background-color: #e0f2fe; color: #075985; }

        /* Buttons Upgrade */
        .stButton>button {
            border-radius: 10px !important;
            font-weight: 600 !important;
            transition: all 0.25s ease !important;
            border: none !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05) !important;
        }

        .stButton>button:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1) !important;
        }

        /* Inputs & Form Styling */
        .stTextInput>div>div>input, .stSelectbox>div>div>div, .stNumberInput>div>div>input {
            border-radius: 10px !important;
            border: 1px solid #cbd5e1 !important;
            background-color: #ffffff !important;
        }

        /* Floating Auto-Draft Alert */
        .draft-notice {
            background-color: #eff6ff;
            border-left: 4px solid #3b82f6;
            padding: 10px 16px;
            border-radius: 6px;
            font-size: 0.9rem;
            color: #1e40af;
            margin-bottom: 15px;
        }
        </style>
    """, unsafe_allow_html=True)

inject_modern_css()

# ==========================================
# 3. OPTIMIZED GOOGLE SHEETS CONNECTION (BATCHED & CACHED)
# ==========================================
@st.cache_resource(ttl=3600)
def init_gspread_client():
    """Establishes persistent connection to Google Sheets API"""
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    # Fetch credentials from st.secrets
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

@st.cache_data(ttl=60, show_spinner=False)
def fetch_sheet_data(sheet_name):
    """Cached data fetcher to avoid repeated API calls"""
    try:
        client = init_gspread_client()
        sheet_id = st.secrets["spreadsheet_id"]
        spreadsheet = client.open_by_key(sheet_id)
        worksheet = spreadsheet.worksheet(sheet_name)
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error loading worksheet {sheet_name}: {e}")
        return pd.DataFrame()

def clear_data_cache():
    """Clears cache after data writes/updates"""
    st.cache_data.clear()

def batch_append_row(sheet_name, row_data):
    """Batch appends a row to keep GSheet updates fast"""
    try:
        client = init_gspread_client()
        sheet_id = st.secrets["spreadsheet_id"]
        spreadsheet = client.open_by_key(sheet_id)
        worksheet = spreadsheet.worksheet(sheet_name)
        worksheet.append_row(row_data)
        clear_data_cache()
        return True
    except Exception as e:
        st.error(f"Failed to append data to {sheet_name}: {e}")
        return False

def batch_update_cell(sheet_name, row_idx, col_idx, value):
    """Updates a specific cell safely"""
    try:
        client = init_gspread_client()
        sheet_id = st.secrets["spreadsheet_id"]
        spreadsheet = client.open_by_key(sheet_id)
        worksheet = spreadsheet.worksheet(sheet_name)
        worksheet.update_cell(row_idx, col_idx, value)
        clear_data_cache()
        return True
    except Exception as e:
        st.error(f"Failed cell update in {sheet_name}: {e}")
        return False

# ==========================================
# 4. FORM AUTO-DRAFT & SESSION RECOVERY ENGINE
# ==========================================
def init_draft_system():
    if "form_draft" not in st.session_state:
        st.session_state["form_draft"] = {}

def save_draft_key(key, val):
    st.session_state["form_draft"][key] = val

def get_draft_key(key, default=""):
    return st.session_state["form_draft"].get(key, default)

def clear_drafts():
    st.session_state["form_draft"] = {}

init_draft_system()

# ==========================================
# 5. AUTHENTICATION & COOKIE MANAGEMENT
# ==========================================
def authenticate_user(username, password):
    users_df = fetch_sheet_data("Users")
    if users_df.empty:
        return None
    
    # Filter matching credentials
    matched_user = users_df[
        (users_df['Username'].astype(str) == str(username)) & 
        (users_df['Password'].astype(str) == str(password))
    ]
    
    if not matched_user.empty:
        user_info = matched_user.iloc[0].to_dict()
        return user_info
    return None

# Initialize Session Auth
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "user_info" not in st.session_state:
    st.session_state["user_info"] = {}

# ==========================================
# 6. LOGIN / LOGOUT UI MODULE
# ==========================================
def render_login_screen():
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
            <div class="glass-card" style="text-align: center;">
                <h2 style="color: #0f172a; font-weight: 700; margin-bottom: 5px;">🛡️ NSVG CRM Pro</h2>
                <p style="color: #64748b; font-size: 0.95rem;">Nordic Secure Vault Group - Secure Portal</p>
            </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form", clear_on_submit=False):
            username_input = st.text_input("Brukernavn / Username", placeholder="Enter username...")
            password_input = st.text_input("Passord / Password", type="password", placeholder="Enter password...")
            submit_login = st.form_submit_button("🚀 Logg Inn", use_container_width=True)
            
            if submit_login:
                if username_input and password_input:
                    user_data = authenticate_user(username_input, password_input)
                    if user_data:
                        st.session_state["authenticated"] = True
                        st.session_state["user_info"] = user_data
                        st.success("Vellykket innlogging! / Login successful!")
                        st.rerun()
                    else:
                        st.error("Ugyldig brukernavn eller passord. / Invalid credentials.")
                else:
                    st.warning("Vennligst fyll ut alle felt. / Please fill all fields.")

if not st.session_state["authenticated"]:
    render_login_screen()
    st.stop()


# ==========================================
# PART 2: NY REGISTRERING (DYNAMIC DTI & DRAFTING) & KUNDE ARKIV
# ==========================================

# Current User Shortcuts
CURRENT_USER = st.session_state["user_info"]
USER_ROLE = CURRENT_USER.get("Role", "Worker")
USER_NAME = CURRENT_USER.get("Full Name", CURRENT_USER.get("Username", "User"))

# Top Glassmorphism Navigation Bar
def render_header():
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"""
            <div class="glass-card" style="padding: 12px 20px; margin-bottom: 15px;">
                <span style="font-size: 1.2rem; font-weight: 700; color: #0f172a;">🛡️ NSVG CRM Pro</span>
                <span style="margin-left: 15px; font-size: 0.9rem; color: #64748b;">Aktiv bruker: <b>{USER_NAME}</b> ({USER_ROLE})</span>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        if st.button("🚪 Logg Ut", use_container_width=True):
            st.session_state["authenticated"] = False
            st.session_state["user_info"] = {}
            clear_drafts()
            st.rerun()

render_header()

# Sidebar Modern Navigation
st.sidebar.markdown("<h2 style='text-align: center; color: #f8fafc;'>📌 CRM Meny</h2>", unsafe_allow_html=True)

# Build dynamic menu options based on Roles
menu_options = ["📊 Dashbord", "➕ Ny Registrering", "📂 Kunde Arkiv", "💬 Banking Messaging"]

if USER_ROLE in ["Admin", "Director", "Saksbehandler"]:
    menu_options.append("📋 Oversiktstavle")

if USER_ROLE in ["Admin", "Director"]:
    menu_options.extend(["👥 Ansatte", "🛠️ Master Kontroll"])

menu_options.extend(["📇 Kontakter", "📞 Support"])

selected_tab = st.sidebar.radio("Velg Modul:", menu_options)

st.sidebar.markdown("---")
st.sidebar.caption(f"🇳🇴 Oslo Tid: {get_norway_now().strftime('%d.%m.%Y %H:%M')}")

# ==========================================
# TAB 1: NY REGISTRERING (WITH DRAFT PERSISTENCE & DTI)
# ==========================================
if selected_tab == "➕ Ny Registrering":
    st.markdown("<h2 style='color:#0f172a;'>➕ Ny Kunde Registrering</h2>", unsafe_allow_html=True)
    
    # Auto Draft Recovery Bar
    if st.session_state["form_draft"]:
        st.markdown("""
            <div class="draft-notice">
                💾 <b>Auto-Draft Aktiv:</b> Skjemaet husker tidligere inntastede data automatisk om siden oppdateres!
            </div>
        """, unsafe_allow_html=True)

    with st.form("new_registration_form"):
        st.markdown("### 👤 Personopplysninger")
        col1, col2 = st.columns(2)
        
        with col1:
            k_navn = st.text_input("Kundenavn *", value=get_draft_key("k_navn"), key="reg_k_navn")
            save_draft_key("k_navn", k_navn)
            
            k_fnr = st.text_input("Fødselsnummer (11 siffer) *", value=get_draft_key("k_fnr"), key="reg_k_fnr")
            save_draft_key("k_fnr", k_fnr)
            
            k_epost = st.text_input("E-postadresse *", value=get_draft_key("k_epost"), key="reg_k_epost")
            save_draft_key("k_epost", k_epost)

        with col2:
            k_tlf = st.text_input("Telefonnummer *", value=get_draft_key("k_tlf"), key="reg_k_tlf")
            save_draft_key("k_tlf", k_tlf)
            
            k_adresse = st.text_input("Adresse", value=get_draft_key("k_adresse"), key="reg_k_adresse")
            save_draft_key("k_adresse", k_adresse)
            
            k_sivil = st.selectbox("Sivilstatus", ["Gift", "Samboer", "En enslig", "Skilt"], index=0, key="reg_k_sivil")

        st.markdown("---")
        st.markdown("### 💰 Økonomi & Lånedetaljer")
        col3, col4 = st.columns(2)

        with col3:
            lånetype = st.selectbox("Lånetype *", ["Boliglån", "Omstartslån / Refinansiering", "Billån", "Næringslån"], key="reg_lånetype")
            ønsket_beløp = st.number_input("Ønsket Lånebeløp (NOK) *", min_value=0, step=50000, value=int(get_draft_key("ønsket_beløp", 0)), key="reg_ønsket_beløp")
            save_draft_key("ønsket_beløp", ønsket_beløp)

            årsinntekt = st.number_input("Brutto Årsinntekt (NOK) *", min_value=0, step=25000, value=int(get_draft_key("årsinntekt", 0)), key="reg_årsinntekt")
            save_draft_key("årsinntekt", årsinntekt)

        with col4:
            eksisterende_gjeld = st.number_input("Eksisterende Samlet Gjeld (NOK)", min_value=0, step=25000, value=int(get_draft_key("eksisterende_gjeld", 0)), key="reg_eksisterende_gjeld")
            save_draft_key("eksisterende_gjeld", eksisterende_gjeld)

            medsøker_inntekt = st.number_input("Medsøker Årsinntekt (NOK)", min_value=0, step=25000, value=int(get_draft_key("medsøker_inntekt", 0)), key="reg_medsøker_inntekt")
            save_draft_key("medsøker_inntekt", medsøker_inntekt)

            eiendom_verdi = st.number_input("Estimert Eiendomsverdi (NOK)", min_value=0, step=100000, value=int(get_draft_key("eiendom_verdi", 0)), key="reg_eiendom_verdi")
            save_draft_key("eiendom_verdi", eiendom_verdi)

        # Real-time Dynamic DTI Calculation
        total_inntekt = årsinntekt + medsøker_inntekt
        total_framtidig_gjeld = eksisterende_gjeld + ønsket_beløp
        
        dti_ratio = 0.0
        if total_inntekt > 0:
            dti_ratio = round((total_framtidig_gjeld / total_inntekt), 2)

        st.markdown("#### 📊 Automatisk DTI (Gjeldsgrad) Beregning")
        dti_color = "#166534" if dti_ratio <= 5.0 else "#991b1b"
        st.markdown(f"""
            <div style="background-color:#f1f5f9; padding:12px; border-radius:10px; border-left: 5px solid {dti_color};">
                <b>Beregnet Gjeldsgrad (DTI):</b> <span style="font-size:1.2rem; font-weight:700; color:{dti_color};">{dti_ratio}x</span> 
                <small>(Norsk norm: Maks 5.0x brutto inntekt)</small>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 📝 Saksbehandling & Kommentarer")
        notater = st.text_area("Saksnotater / Spesielle omstendigheter", value=get_draft_key("notater"), key="reg_notater")
        save_draft_key("notater", notater)

        submit_reg = st.form_submit_button("💾 Send Inn & Registrer Sak", use_container_width=True)

        if submit_reg:
            if not k_navn or not k_fnr or not k_epost or ønsket_beløp <= 0:
                st.error("⚠️ Vennligst fyll ut alle obligatoriske felt markerte med (*).")
            else:
                # Prepare row for MainDB sheet matching original columns
                sak_id = f"NSVG-{get_norway_now().strftime('%Y%m%d%H%M%S')}"
                opprettet_dato = get_norway_now().strftime("%Y-%m-%d %H:%M")
                
                row_data = [
                    sak_id,
                    opprettet_dato,
                    k_navn,
                    k_fnr,
                    k_epost,
                    k_tlf,
                    k_adresse,
                    k_sivil,
                    lånetype,
                    ønsket_beløp,
                    årsinntekt,
                    medsøker_inntekt,
                    eksisterende_gjeld,
                    eiendom_verdi,
                    dti_ratio,
                    "Mottatt / Ny Sak", # Default Status
                    USER_NAME,           # Registered By
                    "Ikke Tildelt",      # Assigned Saksbehandler
                    notater,
                    "{}"                  # Empty JSON Chat Log
                ]
                
                success = batch_append_row("MainDB", row_data)
                if success:
                    st.balloons()
                    st.success(f"✅ Sak registrert med ID: **{sak_id}**!")
                    clear_drafts()
                    st.rerun()

# ==========================================
# TAB 2: KUNDE ARKIV (SEARCH, INTERACTIVE EDIT, CASEWORK)
# ==========================================
elif selected_tab == "📂 Kunde Arkiv":
    st.markdown("<h2 style='color:#0f172a;'>📂 Kunde Arkiv & Saksbehandling</h2>", unsafe_allow_html=True)
    
    df_main = fetch_sheet_data("MainDB")
    
    if df_main.empty:
        st.info("Ingen registrerte saker funnet i databasen.")
    else:
        # Search and Filter Toolbar
        col_s1, col_s2, col_s3 = st.columns([2, 1, 1])
        with col_s1:
            search_query = st.text_input("🔍 Søk (Navn, Fnr, Sak ID, Telefon)", placeholder="Skriv inn søkeord...").lower()
        with col_s2:
            status_filter = st.selectbox("Filter Status", ["Alle"] + list(df_main['Status'].unique()) if 'Status' in df_main.columns else ["Alle"])
        with col_s3:
            lanetype_filter = st.selectbox("Filter Lånetype", ["Alle"] + list(df_main['Lånetype'].unique()) if 'Lånetype' in df_main.columns else ["Alle"])

        # Apply Filters
        filtered_df = df_main.copy()
        
        if search_query:
            filtered_df = filtered_df[
                filtered_df['Kundenavn'].astype(str).str.lower().str.contains(search_query) |
                filtered_df['Sak ID'].astype(str).str.lower().str.contains(search_query) |
                filtered_df['Fødselsnummer'].astype(str).str.contains(search_query) |
                filtered_df['Telefon'].astype(str).str.contains(search_query)
            ]
        
        if status_filter != "Alle" and 'Status' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Status'] == status_filter]

        if lanetype_filter != "Alle" and 'Lånetype' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Lånetype'] == lanetype_filter]

        st.markdown(f"<b>Viser {len(filtered_df)} av {len(df_main)} saker</b>", unsafe_allow_html=True)
        
        # Display Interactive Data Grid using AgGrid
        gb = GridOptionsBuilder.from_dataframe(filtered_df[['Sak ID', 'Dato', 'Kundenavn', 'Telefon', 'Lånetype', 'Ønsket Beløp', 'Status', 'Saksbehandler']])
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)
        gb.configure_selection('single', use_checkbox=True)
        gb.configure_column("Ønsket Beløp", type=["numericColumn", "numberColumnFilter"], valueFormatter="x.toLocaleString() + ' kr'")
        grid_options = gb.build()

        grid_response = AgGrid(
            filtered_df,
            gridOptions=grid_options,
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            fit_columns_on_grid_load=True,
            height=350,
            theme='alpine'
        )

        selected_rows = grid_response['selected_rows']
        
        # Detail & Action Inspector Panel
        if selected_rows is not None and len(selected_rows) > 0:
            selected_case = selected_rows.iloc[0].to_dict() if isinstance(selected_rows, pd.DataFrame) else selected_rows[0]
            
            st.markdown("---")
            st.markdown(f"### 📋 Detaljer for Sak: <span style='color:#2563eb;'>{selected_case.get('Sak ID')}</span>", unsafe_allow_html=True)
            
            with st.expander("🛠️ Endre Status / Tildel Saksbehandler / Rediger Sak", expanded=True):
                col_e1, col_e2, col_e3 = st.columns(3)
                
                # Fetch Real Row Index in Original Sheet for safe cell updating
                all_records = df_main.to_dict('records')
                sheet_row_idx = None
                for idx, r in enumerate(all_records):
                    if str(r.get('Sak ID')) == str(selected_case.get('Sak ID')):
                        sheet_row_idx = idx + 2 # Header offset = 2
                        break

                with col_e1:
                    status_options = ["Mottatt / Ny Sak", "Under Behandling", "Dokumentasjon Mangler", "Sendt til Bank", "Innvilget", "Avslått", "Utbetalt"]
                    current_stat = selected_case.get('Status', status_options[0])
                    stat_index = status_options.index(current_stat) if current_stat in status_options else 0
                    new_status = st.selectbox("Oppdater Status", status_options, index=stat_index)

                with col_e2:
                    # Load users list for caseworker assignment
                    users_df = fetch_sheet_data("Users")
                    workers_list = ["Ikke Tildelt"]
                    if not users_df.empty and 'Full Name' in users_df.columns:
                        workers_list.extend(users_df['Full Name'].dropna().tolist())
                    
                    current_assignee = selected_case.get('Saksbehandler', "Ikke Tildelt")
                    assignee_index = workers_list.index(current_assignee) if current_assignee in workers_list else 0
                    new_assignee = st.selectbox("Tildel Saksbehandler", workers_list, index=assignee_index)

                with col_e3:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("💾 Lagre Endringer", use_container_width=True):
                        if sheet_row_idx:
                            # Update Status Col (Col 16) and Saksbehandler Col (Col 18)
                            batch_update_cell("MainDB", sheet_row_idx, 16, new_status)
                            batch_update_cell("MainDB", sheet_row_idx, 18, new_assignee)
                            st.success("✅ Saksopplysninger oppdatert!")
                            st.rerun()

                # Detailed Info Cards
                c_a, c_b, c_c = st.columns(3)
                with c_a:
                    st.markdown(f"""
                        <b>Personalia:</b><br>
                        • Fnr: {selected_case.get('Fødselsnummer')}<br>
                        • E-post: {selected_case.get('Epost')}<br>
                        • Telefon: {selected_case.get('Telefon')}<br>
                        • Adresse: {selected_case.get('Adresse')}
                    """, unsafe_allow_html=True)
                with c_b:
                    st.markdown(f"""
                        <b>Lån & Økonomi:</b><br>
                        • Ønsket Lån: {selected_case.get('Ønsket Beløp')} NOK<br>
                        • Årsinntekt: {selected_case.get('Årsinntekt')} NOK<br>
                        • Eksisterende Gjeld: {selected_case.get('Eksisterende Gjeld')} NOK<br>
                        • DTI Ratio: <b>{selected_case.get('DTI Ratio')}x</b>
                    """, unsafe_allow_html=True)
                with c_c:
                    st.markdown(f"""
                        <b>Saksnotat:</b><br>
                        <i>{selected_case.get('Notater', 'Ingen notater ført.')}</i>
                    """, unsafe_allow_html=True)


# ==========================================
# PART 3: MESSAGING HUB, OVERSIKTSTAVLE & ADMIN MASTER CONTROL
# ==========================================

# ==========================================
# TAB 3: BANKING MESSAGING HUB
# ==========================================
elif selected_tab == "💬 Banking Messaging":
    st.markdown("<h2 style='color:#0f172a;'>💬 Banking Messaging Hub</h2>", unsafe_allow_html=True)
    
    df_main = fetch_sheet_data("MainDB")
    
    if df_main.empty:
        st.info("Ingen saker tilgjengelig for meldinger.")
    else:
        # Select Case for Chat
        case_options = df_main['Sak ID'].astype(str) + " - " + df_main['Kundenavn'].astype(str)
        selected_case_str = st.selectbox("Velg Sak for Kommunikasjon:", case_options)
        
        selected_sak_id = selected_case_str.split(" - ")[0]
        case_row = df_main[df_main['Sak ID'].astype(str) == selected_sak_id].iloc[0]
        
        # Locate exact row in Google Sheet
        all_records = df_main.to_dict('records')
        sheet_row_idx = None
        for idx, r in enumerate(all_records):
            if str(r.get('Sak ID')) == str(selected_sak_id):
                sheet_row_idx = idx + 2
                break

        st.markdown(f"### 💬 Meldingslogg for Sak: **{selected_sak_id}** ({case_row.get('Kundenavn')})")
        
        # Decode JSON Chat Log stored in Column 20
        raw_chat_json = case_row.get('ChatLog', '{}')
        try:
            chat_history = json.loads(raw_chat_json) if raw_chat_json and str(raw_chat_json).strip() != "" else []
            if isinstance(chat_history, dict):  # Fallback if initialized as dict
                chat_history = []
        except Exception:
            chat_history = []

        # Display Chat Messages
        chat_container = st.container()
        with chat_container:
            if not chat_history:
                st.info("Ingen meldinger i denne saken ennå. Start samtalen nedenfor.")
            else:
                for msg in chat_history:
                    sender = msg.get("sender", "Ukjent")
                    timestamp = msg.get("timestamp", "")
                    text = msg.get("text", "")
                    
                    is_me = (sender == USER_NAME)
                    align_style = "margin-left: auto; background-color: #dbeafe; text-align: right;" if is_me else "margin-right: auto; background-color: #ffffff;"
                    
                    st.markdown(f"""
                        <div style="max-width: 70%; padding: 12px 16px; border-radius: 12px; margin-bottom: 10px; border: 1px solid #e2e8f0; box-shadow: 0 2px 5px rgba(0,0,0,0.02); {align_style}">
                            <div style="font-size: 0.75rem; color: #64748b; font-weight: 600;">{sender} • {timestamp}</div>
                            <div style="font-size: 0.95rem; color: #0f172a; margin-top: 4px;">{text}</div>
                        </div>
                    """, unsafe_allow_html=True)

        # Send New Message Input Form
        st.markdown("---")
        with st.form("send_chat_message_form", clear_on_submit=True):
            new_msg_text = st.text_area("Skriv melding her...", height=80, placeholder="Type message to bank or agent...")
            submit_msg = st.form_submit_button("📤 Send Melding", use_container_width=True)
            
            if submit_msg and new_msg_text.strip():
                new_entry = {
                    "sender": USER_NAME,
                    "timestamp": get_norway_now().strftime("%d.%m.%Y %H:%M"),
                    "text": new_msg_text.strip()
                }
                chat_history.append(new_entry)
                updated_chat_json = json.dumps(chat_history, ensure_ascii=False)
                
                if sheet_row_idx:
                    batch_update_cell("MainDB", sheet_row_idx, 20, updated_chat_json)
                    st.success("Melding sendt!")
                    st.rerun()

# ==========================================
# TAB 4: OVERSIKTSTAVLE (FINANCIAL WORKSPACE)
# ==========================================
elif selected_tab == "📋 Oversiktstavle":
    st.markdown("<h2 style='color:#0f172a;'>📋 Oversiktstavle & Økonomisk Oversikt</h2>", unsafe_allow_html=True)
    
    df_main = fetch_sheet_data("MainDB")
    
    if df_main.empty:
        st.warning("Ingen data tilgjengelig i databasen.")
    else:
        # High Level Financial KPIs
        total_cases = len(df_main)
        total_volume = pd.to_numeric(df_main['Ønsket Beløp'], errors='coerce').sum()
        
        approved_cases = df_main[df_main['Status'].isin(["Innvilget", "Utbetalt"])] if 'Status' in df_main.columns else pd.DataFrame()
        approved_volume = pd.to_numeric(approved_cases['Ønsket Beløp'], errors='coerce').sum() if not approved_cases.empty else 0

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Totalt Antall Saker</div>
                    <div class="metric-value">{total_cases}</div>
                </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Totalt Lånevolum</div>
                    <div class="metric-value">{total_volume:,.0f} NOK</div>
                </div>
            """, unsafe_allow_html=True)
        with c3:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Innvilget Volum</div>
                    <div class="metric-value" style="color:#166534;">{approved_volume:,.0f} NOK</div>
                </div>
            """, unsafe_allow_html=True)
        with c4:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Konverteringsrate</div>
                    <div class="metric-value" style="color:#2563eb;">{(len(approved_cases)/total_cases*100 if total_cases > 0 else 0):.1f}%</div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 📊 Statusfordeling av Saker")
        
        if 'Status' in df_main.columns:
            status_counts = df_main['Status'].value_counts().reset_index()
            status_counts.columns = ['Status', 'Antall Saker']
            st.dataframe(status_counts, use_container_width=True)

# ==========================================
# TAB 5: ANSATTE (ADMIN STAFF MANAGEMENT)
# ==========================================
elif selected_tab == "👥 Ansatte":
    st.markdown("<h2 style='color:#0f172a;'>👥 Ansatte & Tilgangsstyring</h2>", unsafe_allow_html=True)
    
    users_df = fetch_sheet_data("Users")
    
    st.markdown("### 📋 Registrerte Brukere i Systemet")
    if not users_df.empty:
        st.dataframe(users_df[['Username', 'Full Name', 'Role', 'Email', 'Commission Split']], use_container_width=True)
    
    st.markdown("---")
    st.markdown("### ➕ Legg til Ny Ansatt")
    with st.form("add_new_user_form"):
        col_u1, col_u2 = st.columns(2)
        with col_u1:
            u_name = st.text_input("Brukernavn *")
            u_pass = st.text_input("Passord *", type="password")
            u_fullname = st.text_input("Fullstendig Navn *")
        with col_u2:
            u_role = st.selectbox("Rolle", ["Admin", "Director", "Saksbehandler", "Worker"])
            u_email = st.text_input("E-postadresse")
            u_split = st.number_input("Provisjonsdeling / Commission Split (%)", min_value=0, max_value=100, value=50)

        submit_user = st.form_submit_button("➕ Opprett Bruker", use_container_width=True)
        if submit_user:
            if not u_name or not u_pass or not u_fullname:
                st.error("Fyll ut alle påkrevde felt.")
            else:
                new_user_row = [u_name, u_pass, u_role, u_fullname, u_email, u_split]
                success = batch_append_row("Users", new_user_row)
                if success:
                    st.success(f"✅ Bruker '{u_name}' ble opprettet!")
                    st.rerun()

# ==========================================
# TAB 6: MASTER KONTROLL (SYSTEM & CACHE CONTROL)
# ==========================================
elif selected_tab == "🛠️ Master Kontroll":
    st.markdown("<h2 style='color:#0f172a;'>🛠️ Master Kontroll Panel</h2>", unsafe_allow_html=True)
    
    col_m1, col_m2 = st.columns(2)
    
    with col_m1:
        st.markdown("""
            <div class="glass-card">
                <h3>🔄 Tøm System-Cache</h3>
                <p>Bruk denne knappen hvis du har gjort direkte endringer i Google Sheets og ønsker at CRM-en skal hente alt på nytt umiddelbart.</p>
            </div>
        """, unsafe_allow_html=True)
        if st.button("🧹 Tøm Cache Nå", use_container_width=True):
            clear_data_cache()
            st.success("✅ System cache er tømt!")
            st.rerun()

    with col_m2:
        st.markdown("""
            <div class="glass-card">
                <h3>⚙️ System Status</h3>
                <p><b>Database:</b> Tilkoblet Google Sheets API v4<br>
                <b>Tidssone:</b> Europe/Oslo<br>
                <b>Versjon:</b> 2026 Enterprise Edition</p>
            </div>
        """, unsafe_allow_html=True)

# ==========================================
# PART 4: DASHBOARD, KONTAKTER, SUPPORT & MAIN LOOP
# ==========================================

# ==========================================
# TAB 0: DASHBOARD (MAIN OVERVIEW)
# ==========================================
if selected_tab == "📊 Dashbord":
    st.markdown("<h2 style='color:#0f172a;'>📊 CRM Dashbord & Oversikt</h2>", unsafe_allow_html=True)
    
    df_main = fetch_sheet_data("MainDB")
    
    if df_main.empty:
        st.info("Ingen data registrert i systemet ennå. Start med å opprette en ny sak under 'Ny Registrering'.")
    else:
        # Dashboard Financial KPI Calculations
        tot_saker = len(df_main)
        mottatt_saker = len(df_main[df_main['Status'] == "Mottatt / Ny Sak"]) if 'Status' in df_main.columns else 0
        under_behandling = len(df_main[df_main['Status'] == "Under Behandling"]) if 'Status' in df_main.columns else 0
        innvilget = len(df_main[df_main['Status'].isin(["Innvilget", "Utbetalt"])]) if 'Status' in df_main.columns else 0

        # KPI Display Row
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        with kpi1:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Totalt Antall Saker</div>
                    <div class="metric-value">{tot_saker}</div>
                </div>
            """, unsafe_allow_html=True)
        with kpi2:
            st.markdown(f"""
                <div class="metric-card" style="border-left: 4px solid #f59e0b;">
                    <div class="metric-title">Nye Saker / Mottatt</div>
                    <div class="metric-value" style="color:#d97706;">{mottatt_saker}</div>
                </div>
            """, unsafe_allow_html=True)
        with kpi3:
            st.markdown(f"""
                <div class="metric-card" style="border-left: 4px solid #3b82f6;">
                    <div class="metric-title">Under Behandling</div>
                    <div class="metric-value" style="color:#2563eb;">{under_behandling}</div>
                </div>
            """, unsafe_allow_html=True)
        with kpi4:
            st.markdown(f"""
                <div class="metric-card" style="border-left: 4px solid #22c55e;">
                    <div class="metric-title">Innvilget / Utbetalt</div>
                    <div class="metric-value" style="color:#166534;">{innvilget}</div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        
        # Recent Activity Table
        st.markdown("### ⏱️ Siste Registrerte Saker")
        recent_df = df_main.tail(8).iloc[::-1] # Last 8 cases reversed
        st.dataframe(recent_df[['Sak ID', 'Dato', 'Kundenavn', 'Lånetype', 'Ønsket Beløp', 'Status', 'Saksbehandler']], use_container_width=True)

# ==========================================
# TAB 7: KONTAKTER
# ==========================================
elif selected_tab == "📇 Kontakter":
    st.markdown("<h2 style='color:#0f172a;'>📇 Eksterne Kontakter & Banker</h2>", unsafe_allow_html=True)
    
    contacts_df = fetch_sheet_data("Contacts")
    
    if not contacts_df.empty:
        st.dataframe(contacts_df, use_container_width=True)
    else:
        st.info("Ingen eksterne kontakter registrert i databasen.")
        
    st.markdown("---")
    st.markdown("### ➕ Legg til Ny Kontakt")
    with st.form("add_contact_form"):
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            c_navn = st.text_input("Kontaktnavn / Bank *")
            c_person = st.text_input("Kontaktperson")
        with col_c2:
            c_epost = st.text_input("E-postadresse *")
            c_tlf = st.text_input("Telefonnummer")
            
        submit_contact = st.form_submit_button("💾 Lagre Kontakt", use_container_width=True)
        if submit_contact:
            if c_navn and c_epost:
                new_c_row = [c_navn, c_person, c_epost, c_tlf]
                success = batch_append_row("Contacts", new_c_row)
                if success:
                    st.success("✅ Kontakt registrert!")
                    st.rerun()
            else:
                st.error("Fyll ut obligatoriske felt markerte med (*).")

# ==========================================
# TAB 8: SUPPORT & TICKET DISPATCH
# ==========================================
elif selected_tab == "📞 Support":
    st.markdown("<h2 style='color:#0f172a;'>📞 Support Center & Hjelp</h2>", unsafe_allow_html=True)
    
    col_sup1, col_sup2 = st.columns([1.5, 1])
    
    with col_sup1:
        st.markdown("""
            <div class="glass-card">
                <h3>📬 Send Support Henvendelse</h3>
                <p>Opplever du tekniske problemer eller trenger hjelp med CRM-systemet? Send en direkte melding til IT-support.</p>
            </div>
        """, unsafe_allow_html=True)
        
        with st.form("support_ticket_form"):
            sup_emne = st.text_input("Emne / Problem *")
            sup_prioritet = st.selectbox("Prioritet", ["Lav", "Medium", "Høy", "Kritisk"])
            sup_melding = st.text_area("Beskriv problemet i detalj *", height=120)
            
            submit_support = st.form_submit_button("📩 Send Support Henvendelse", use_container_width=True)
            if submit_support:
                if sup_emne and sup_melding:
                    ticket_id = f"TICK-{get_norway_now().strftime('%Y%m%d%H%M')}"
                    ticket_row = [ticket_id, get_norway_now().strftime("%Y-%m-%d %H:%M"), USER_NAME, sup_emne, sup_prioritet, sup_melding, "Åpen"]
                    
                    success = batch_append_row("Support", ticket_row)
                    if success:
                        st.balloons()
                        st.success(f"✅ Henvendelse sendt med ID: **{ticket_id}**! Supportteamet vil gi tilbakemelding snarest.")
                else:
                    st.error("Fyll ut emne og beskrivelse.")

    with col_sup2:
        st.markdown("""
            <div class="glass-card">
                <h3>📞 Direkte Kontakt</h3>
                <p><b>NSVG IT-Support Desk</b><br>
                📧 E-post: support@nsvg.no<br>
                ☎️ Telefon: +47 22 00 00 00<br>
                🕒 Åpningstider: 08:00 - 16:00 (Man-Fre)</p>
            </div>
        """, unsafe_allow_html=True)
        
        # Display Support Tickets Log
        support_df = fetch_sheet_data("Support")
        if not support_df.empty:
            st.markdown("### 📋 Dine Support Henvendelser")
            st.dataframe(support_df, use_container_width=True)
