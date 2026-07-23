import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import pytz
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Safely import AgGrid with Fallback
try:
    from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
    HAS_AGGRID = True
except ImportError:
    HAS_AGGRID = False

# ==========================================
# 1. PAGE CONFIGURATION & TIMEZONE SETUP
# ==========================================
st.set_page_config(
    page_title="NSVG CRM Pro",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

NORWAY_TZ = pytz.timezone('Europe/Oslo')

def get_norway_now():
    return datetime.datetime.now(NORWAY_TZ)

def get_norway_now_str():
    return get_norway_now().strftime("%Y-%m-%d %H:%M:%S")

# ==========================================
# 2. ADVANCED GLASSMORPHISM & MODERN CSS
# ==========================================
def inject_custom_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            color: #0f172a;
        }

        .stApp {
            background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        }

        .glass-card {
            background: rgba(255, 255, 255, 0.85);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.6);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
            padding: 24px;
            margin-bottom: 20px;
            transition: all 0.3s ease;
        }

        .glass-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 14px 35px rgba(0, 0, 0, 0.08);
        }

        [data-testid="stSidebar"] {
            background: rgba(15, 23, 42, 0.96) !important;
            backdrop-filter: blur(20px);
            border-right: 1px solid rgba(255, 255, 255, 0.1);
        }

        [data-testid="stSidebar"] * {
            color: #f8fafc !important;
        }

        [data-testid="stSidebar"] .stRadio label {
            font-size: 1.05rem !important;
            font-weight: 500 !important;
            padding: 12px 16px !important;
            border-radius: 12px !important;
            margin-bottom: 4px !important;
            transition: all 0.2s ease !important;
        }

        [data-testid="stSidebar"] .stRadio label:hover {
            background: rgba(255, 255, 255, 0.12) !important;
        }

        .metric-card {
            background: #ffffff;
            border-radius: 14px;
            padding: 20px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 4px 12px rgba(0,0,0,0.03);
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
            margin-top: 6px;
        }

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

        .stButton>button {
            border-radius: 10px !important;
            font-weight: 600 !important;
            padding: 10px 20px !important;
            transition: all 0.2s ease !important;
        }

        .stButton>button:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 15px rgba(0,0,0,0.1) !important;
        }

        .draft-notice {
            background-color: #eff6ff;
            border-left: 4px solid #3b82f6;
            padding: 12px 18px;
            border-radius: 8px;
            font-size: 0.9rem;
            color: #1e40af;
            margin-bottom: 20px;
        }
        </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# ==========================================
# 3. OPTIMIZED CACHED GOOGLE SHEETS ENGINE
# ==========================================
@st.cache_resource(ttl=3600)
def init_gspread_client():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

@st.cache_data(ttl=60, show_spinner=False)
def fetch_sheet_data(sheet_name):
    try:
        client = init_gspread_client()
        sheet_id = st.secrets["spreadsheet_id"]
        spreadsheet = client.open_by_key(sheet_id)
        worksheet = spreadsheet.worksheet(sheet_name)
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Feil ved henting av data fra {sheet_name}: {e}")
        return pd.DataFrame()

def clear_data_cache():
    st.cache_data.clear()

def batch_append_row(sheet_name, row_data):
    try:
        client = init_gspread_client()
        sheet_id = st.secrets["spreadsheet_id"]
        spreadsheet = client.open_by_key(sheet_id)
        worksheet = spreadsheet.worksheet(sheet_name)
        worksheet.append_row(row_data)
        clear_data_cache()
        return True
    except Exception as e:
        st.error(f"Feil ved skriving til {sheet_name}: {e}")
        return False

def batch_update_cell(sheet_name, row_idx, col_idx, value):
    try:
        client = init_gspread_client()
        sheet_id = st.secrets["spreadsheet_id"]
        spreadsheet = client.open_by_key(sheet_id)
        worksheet = spreadsheet.worksheet(sheet_name)
        worksheet.update_cell(row_idx, col_idx, value)
        clear_data_cache()
        return True
    except Exception as e:
        st.error(f"Feil ved celoppdatering i {sheet_name}: {e}")
        return False

# ==========================================
# 4. AUTO-DRAFT SESSION PERSISTENCE ENGINE
# ==========================================
if "form_draft" not in st.session_state:
    st.session_state["form_draft"] = {}

def save_draft_key(key, val):
    st.session_state["form_draft"][key] = val

def get_draft_key(key, default=""):
    return st.session_state["form_draft"].get(key, default)

def clear_drafts():
    st.session_state["form_draft"] = {}

# ==========================================
# 5. AUTHENTICATION & LOGIN MANAGEMENT
# ==========================================
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "user_info" not in st.session_state:
    st.session_state["user_info"] = {}

def authenticate_user(username, password):
    users_df = fetch_sheet_data("Users")
    if users_df.empty:
        return None
    
    matched_user = users_df[
        (users_df['Username'].astype(str) == str(username)) & 
        (users_df['Password'].astype(str) == str(password))
    ]
    
    if not matched_user.empty:
        return matched_user.iloc[0].to_dict()
    return None

def render_login_screen():
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
            <div class="glass-card" style="text-align: center;">
                <h1 style="color: #0f172a; font-weight: 700; margin-bottom: 5px;">🛡️ NSVG CRM Pro</h1>
                <p style="color: #64748b; font-size: 0.95rem;">Nordic Secure Vault Group • Enterprise System</p>
            </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form", clear_on_submit=False):
            username_input = st.text_input("Brukernavn", placeholder="Skriv inn brukernavn...")
            password_input = st.text_input("Passord", type="password", placeholder="Skriv inn passord...")
            submit_login = st.form_submit_button("🚀 Logg Inn", use_container_width=True)
            
            if submit_login:
                if username_input and password_input:
                    user_data = authenticate_user(username_input, password_input)
                    if user_data:
                        st.session_state["authenticated"] = True
                        st.session_state["user_info"] = user_data
                        st.success("Vellykket innlogging!")
                        st.rerun()
                    else:
                        st.error("Ugyldig brukernavn eller passord.")
                else:
                    st.warning("Vennligst fyll ut alle felt.")

if not st.session_state["authenticated"]:
    render_login_screen()
    st.stop()

# ==========================================
# PART 2 / 6: HEADER, NAVIGATION, DASHBOARD & NY REGISTRERING (PART 1)
# ==========================================

CURRENT_USER = st.session_state["user_info"]
USER_ROLE = CURRENT_USER.get("Role", "Worker")
USER_NAME = CURRENT_USER.get("Full Name", CURRENT_USER.get("Username", "User"))

# ------------------------------------------
# TOP NAVIGATION HEADER
# ------------------------------------------
def render_header():
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"""
            <div class="glass-card" style="padding: 14px 22px; margin-bottom: 20px;">
                <span style="font-size: 1.3rem; font-weight: 700; color: #0f172a;">🛡️ NSVG CRM Pro</span>
                <span style="margin-left: 18px; font-size: 0.95rem; color: #64748b;">Aktiv Bruker: <b>{USER_NAME}</b> (<span style="color:#2563eb;">{USER_ROLE}</span>)</span>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        if st.button("🚪 Logg Ut", use_container_width=True):
            st.session_state["authenticated"] = False
            st.session_state["user_info"] = {}
            clear_drafts()
            st.rerun()

render_header()

# ------------------------------------------
# SIDEBAR NAVIGATION MENU
# ------------------------------------------
st.sidebar.markdown("<h2 style='text-align: center; color: #f8fafc; font-weight: 700;'>📌 CRM Meny</h2>", unsafe_allow_html=True)

menu_options = ["📊 Dashbord", "➕ Ny Registrering", "📂 Kunde Arkiv", "💬 Banking Messaging"]

if USER_ROLE in ["Admin", "Director", "Saksbehandler"]:
    menu_options.append("📋 Oversiktstavle")

if USER_ROLE in ["Admin", "Director"]:
    menu_options.extend(["👥 Ansatte", "🛠️ Master Kontroll"])

menu_options.extend(["📇 Kontakter", "📞 Support"])

selected_tab = st.sidebar.radio("Velg Modul:", menu_options)

st.sidebar.markdown("---")
st.sidebar.markdown(f"""
    <div style="text-align: center; font-size: 0.85rem; color: #94a3b8;">
        🇳🇴 <b>Oslo Tid:</b><br>{get_norway_now().strftime('%d.%m.%Y %H:%M')}
    </div>
""", unsafe_allow_html=True)

# ==========================================
# TAB 0: DASHBOARD MODULE
# ==========================================
if selected_tab == "📊 Dashbord":
    st.markdown("<h2 style='color:#0f172a;'>📊 CRM Dashbord & Systemoversikt</h2>", unsafe_allow_html=True)
    
    df_main = fetch_sheet_data("MainDB")
    
    if df_main.empty:
        st.info("Ingen data registrert i databasen ennå. Start med å opprette en ny sak under 'Ny Registrering'.")
    else:
        # Calculate Key Performance Indicators
        tot_saker = len(df_main)
        mottatt_saker = len(df_main[df_main['Status'] == "Mottatt / Ny Sak"]) if 'Status' in df_main.columns else 0
        under_behandling = len(df_main[df_main['Status'] == "Under Behandling"]) if 'Status' in df_main.columns else 0
        innvilget = len(df_main[df_main['Status'].isin(["Innvilget", "Utbetalt"])]) if 'Status' in df_main.columns else 0

        # KPI Display Metrics
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
        
        # Recent Cases Quick View Table
        st.markdown("### ⏱️ Siste Registrerte Saker")
        recent_df = df_main.tail(10).iloc[::-1]
        
        display_cols = ['Sak ID', 'Dato', 'Kundenavn', 'Lånetype', 'Ønsket Beløp', 'Status', 'Saksbehandler']
        valid_cols = [c for c in display_cols if c in recent_df.columns]
        
        st.dataframe(recent_df[valid_cols], use_container_width=True)

# ==========================================
# TAB 1: NY REGISTRERING (PART 1 - PERSONALIA & DRAFTING)
# ==========================================
elif selected_tab == "➕ Ny Registrering":
    st.markdown("<h2 style='color:#0f172a;'>➕ Ny Kunde Registrering</h2>", unsafe_allow_html=True)
    
    if st.session_state["form_draft"]:
        st.markdown("""
            <div class="draft-notice">
                💾 <b>Auto-Draft Aktiv:</b> Data du fyller inn blir automatisk tatt vare på om siden gjenoppfriskes!
            </div>
        """, unsafe_allow_html=True)

    with st.form("new_registration_form_main"):
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
            
            sivil_options = ["Gift", "Samboer", "Enslig", "Skilt"]
            saved_sivil = get_draft_key("k_sivil", "Gift")
            sivil_idx = sivil_options.index(saved_sivil) if saved_sivil in sivil_options else 0
            k_sivil = st.selectbox("Sivilstatus", sivil_options, index=sivil_idx, key="reg_k_sivil")
            save_draft_key("k_sivil", k_sivil)

# ==========================================
# PART 3 / 6: NY REGISTRERING (PART 2 - DTI & SUBMIT) & KUNDE ARKIV (PART 1)
# ==========================================

        st.markdown("---")
        st.markdown("### 💰 Økonomi & Lånedetaljer")
        col3, col4 = st.columns(2)

        with col3:
            lanetype_opts = ["Boliglån", "Omstartslån / Refinansiering", "Billån", "Næringslån"]
            saved_lanetype = get_draft_key("lånetype", "Boliglån")
            lanetype_idx = lanetype_opts.index(saved_lanetype) if saved_lanetype in lanetype_opts else 0
            lånetype = st.selectbox("Lånetype *", lanetype_opts, index=lanetype_idx, key="reg_lånetype")
            save_draft_key("lånetype", lånetype)

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

        # Dynamic Debt-To-Income (DTI) Calculations
        total_inntekt = årsinntekt + medsøker_inntekt
        total_framtidig_gjeld = eksisterende_gjeld + ønsket_beløp
        
        dti_ratio = 0.0
        if total_inntekt > 0:
            dti_ratio = round((total_framtidig_gjeld / total_inntekt), 2)

        st.markdown("#### 📊 Automatisk DTI (Gjeldsgrad) Beregning")
        dti_color = "#166534" if dti_ratio <= 5.0 else "#991b1b"
        st.markdown(f"""
            <div style="background-color:#ffffff; padding:16px; border-radius:12px; border: 1px solid #e2e8f0; border-left: 6px solid {dti_color}; box-shadow: 0 2px 8px rgba(0,0,0,0.02);">
                <b>Beregnet Gjeldsgrad (DTI):</b> <span style="font-size:1.3rem; font-weight:700; color:{dti_color};">{dti_ratio}x</span> 
                <span style="margin-left: 10px; color:#64748b; font-size: 0.9rem;">(Maks anbefalt gjeldsgrad i Norge: 5.0x brutto inntekt)</span>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 📝 Saksbehandling & Notater")
        notater = st.text_area("Saksnotater / Spesielle omstendigheter", value=get_draft_key("notater"), key="reg_notater")
        save_draft_key("notater", notater)

        submit_reg = st.form_submit_button("💾 Send Inn & Registrer Sak", use_container_width=True)

        if submit_reg:
            if not k_navn or not k_fnr or not k_epost or ønsket_beløp <= 0:
                st.error("⚠️ Vennligst fyll ut alle obligatoriske felt markerte med (*).")
            else:
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
                    "Mottatt / Ny Sak",
                    USER_NAME,
                    "Ikke Tildelt",
                    notater,
                    "{}"
                ]
                
                success = batch_append_row("MainDB", row_data)
                if success:
                    st.balloons()
                    st.success(f"✅ Sak registrert med ID: **{sak_id}**!")
                    clear_drafts()
                    st.rerun()

# ==========================================
# TAB 2: KUNDE ARKIV (PART 1 - SEARCH & LIST)
# ==========================================
elif selected_tab == "📂 Kunde Arkiv":
    st.markdown("<h2 style='color:#0f172a;'>📂 Kunde Arkiv & Saksbehandling</h2>", unsafe_allow_html=True)
    
    df_main = fetch_sheet_data("MainDB")
    
    if df_main.empty:
        st.info("Ingen registrerte saker funnet i databasen.")
    else:
        # Search & Filter Header Toolbar
        col_s1, col_s2, col_s3 = st.columns([2, 1, 1])
        with col_s1:
            search_query = st.text_input("🔍 Søk (Navn, Fnr, Sak ID, Telefon)", placeholder="Skriv inn søkeord...").lower()
        with col_s2:
            status_opts = ["Alle"] + list(df_main['Status'].unique()) if 'Status' in df_main.columns else ["Alle"]
            status_filter = st.selectbox("Filter Status", status_opts)
        with col_s3:
            ltype_opts = ["Alle"] + list(df_main['Lånetype'].unique()) if 'Lånetype' in df_main.columns else ["Alle"]
            lanetype_filter = st.selectbox("Filter Lånetype", ltype_opts)

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
        
        # Display Table using AgGrid if available, otherwise native dataframe
        if HAS_AGGRID:
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
        else:
            st.dataframe(filtered_df[['Sak ID', 'Dato', 'Kundenavn', 'Telefon', 'Lånetype', 'Ønsket Beløp', 'Status', 'Saksbehandler']], use_container_width=True)
            selected_rows = None

# ==========================================
# PART 4 / 6: KUNDE ARKIV (PART 2 - INSPECTOR) & BANKING MESSAGING HUB
# ==========================================

        # Detail & Action Inspector Panel for Selected Case
        if selected_rows is not None and len(selected_rows) > 0:
            if isinstance(selected_rows, pd.DataFrame):
                selected_case = selected_rows.iloc[0].to_dict()
            else:
                selected_case = selected_rows[0]
            
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
                    new_status = st.selectbox("Oppdater Status", status_options, index=stat_index, key="arkiv_stat_select")

                with col_e2:
                    users_df = fetch_sheet_data("Users")
                    workers_list = ["Ikke Tildelt"]
                    if not users_df.empty and 'Full Name' in users_df.columns:
                        workers_list.extend(users_df['Full Name'].dropna().tolist())
                    
                    current_assignee = selected_case.get('Saksbehandler', "Ikke Tildelt")
                    assignee_index = workers_list.index(current_assignee) if current_assignee in workers_list else 0
                    new_assignee = st.selectbox("Tildel Saksbehandler", workers_list, index=assignee_index, key="arkiv_assign_select")

                with col_e3:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("💾 Lagre Endringer", use_container_width=True, key="btn_save_case_edits"):
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
                        <div class="glass-card" style="padding:15px;">
                            <b>Personalia:</b><br>
                            • Fnr: {selected_case.get('Fødselsnummer')}<br>
                            • E-post: {selected_case.get('Epost')}<br>
                            • Telefon: {selected_case.get('Telefon')}<br>
                            • Adresse: {selected_case.get('Adresse')}
                        </div>
                    """, unsafe_allow_html=True)
                with c_b:
                    st.markdown(f"""
                        <div class="glass-card" style="padding:15px;">
                            <b>Lån & Økonomi:</b><br>
                            • Ønsket Lån: {selected_case.get('Ønsket Beløp')} NOK<br>
                            • Årsinntekt: {selected_case.get('Årsinntekt')} NOK<br>
                            • Eksisterende Gjeld: {selected_case.get('Eksisterende Gjeld')} NOK<br>
                            • DTI Ratio: <b>{selected_case.get('DTI Ratio')}x</b>
                        </div>
                    """, unsafe_allow_html=True)
                with c_c:
                    st.markdown(f"""
                        <div class="glass-card" style="padding:15px;">
                            <b>Saksnotat:</b><br>
                            <i>{selected_case.get('Notater', 'Ingen notater ført.')}</i>
                        </div>
                    """, unsafe_allow_html=True)

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
        selected_case_str = st.selectbox("Velg Sak for Kommunikasjon:", case_options, key="msg_case_select")
        
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
            if isinstance(chat_history, dict):
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
            new_msg_text = st.text_area("Skriv melding her...", height=80, placeholder="Skriv melding til bank eller agent...", key="msg_input_text")
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
# PART 5 / 6: OVERSIKTSTAVLE, ANSATTE & MASTER KONTROLL
# ==========================================

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
        total_volume = pd.to_numeric(df_main['Ønsket Beløp'], errors='coerce').sum() if 'Ønsket Beløp' in df_main.columns else 0
        
        approved_cases = df_main[df_main['Status'].isin(["Innvilget", "Utbetalt"])] if 'Status' in df_main.columns else pd.DataFrame()
        approved_volume = pd.to_numeric(approved_cases['Ønsket Beløp'], errors='coerce').sum() if not approved_cases.empty and 'Ønsket Beløp' in approved_cases.columns else 0

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
        display_users = [c for c in ['Username', 'Full Name', 'Role', 'Email', 'Commission Split'] if c in users_df.columns]
        st.dataframe(users_df[display_users], use_container_width=True)
    else:
        st.info("Ingen brukere funnet.")
    
    st.markdown("---")
    st.markdown("### ➕ Legg til Ny Ansatt")
    with st.form("add_new_user_form"):
        col_u1, col_u2 = st.columns(2)
        with col_u1:
            u_name = st.text_input("Brukernavn *", key="ans_u_name")
            u_pass = st.text_input("Passord *", type="password", key="ans_u_pass")
            u_fullname = st.text_input("Fullstendig Navn *", key="ans_u_fullname")
        with col_u2:
            u_role = st.selectbox("Rolle", ["Admin", "Director", "Saksbehandler", "Worker"], key="ans_u_role")
            u_email = st.text_input("E-postadresse", key="ans_u_email")
            u_split = st.number_input("Provisjonsdeling / Commission Split (%)", min_value=0, max_value=100, value=50, key="ans_u_split")

        submit_user = st.form_submit_button("➕ Opprett Bruker", use_container_width=True)
        if submit_user:
            if not u_name or not u_pass or not u_fullname:
                st.error("Fyll ut alle påkrevde felt markerte med (*).")
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
        if st.button("🧹 Tøm Cache Nå", use_container_width=True, key="btn_clear_cache_master"):
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
# PART 6 / 6: KONTAKER & SUPPORT CENTER (FINAL PART)
# ==========================================

# ==========================================
# TAB 7: KONTAKTER MODULE
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
            c_navn = st.text_input("Kontaktnavn / Bank *", key="cnt_navn")
            c_person = st.text_input("Kontaktperson", key="cnt_person")
        with col_c2:
            c_epost = st.text_input("E-postadresse *", key="cnt_epost")
            c_tlf = st.text_input("Telefonnummer", key="cnt_tlf")
            
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
# TAB 8: SUPPORT CENTER & TICKET DISPATCH
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
            sup_emne = st.text_input("Emne / Problem *", key="sup_emne")
            sup_prioritet = st.selectbox("Prioritet", ["Lav", "Medium", "Høy", "Kritisk"], key="sup_prio")
            sup_melding = st.text_area("Beskriv problemet i detalj *", height=120, key="sup_msg")
            
            submit_support = st.form_submit_button("📩 Send Support Henvendelse", use_container_width=True)
            if submit_support:
                if sup_emne and sup_melding:
                    ticket_id = f"TICK-{get_norway_now().strftime('%Y%m%d%H%M')}"
                    ticket_row = [ticket_id, get_norway_now().strftime("%Y-%m-%d %H:%M"), USER_NAME, sup_emne, sup_prioritet, sup_melding, "Åpen"]
                    
                    success = batch_append_row("Support", ticket_row)
                    if success:
                        st.balloons()
                        st.success(f"✅ Henvendelse sendt med ID: **{ticket_id}**! Supportteamet vil gi tilbakemelding snarest.")
                        st.rerun()
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
        
        support_df = fetch_sheet_data("Support")
        if not support_df.empty:
            st.markdown("### 📋 Dine Support Henvendelser")
            st.dataframe(support_df, use_container_width=True)
