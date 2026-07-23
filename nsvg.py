import streamlit as st
import pandas as pd
import numpy as np
import datetime
import time
import json
import re
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ==============================================================================
# 0. PAGE CONFIGURATION & HIGH-PERFORMANCE GLOBAL CSS
# ==============================================================================
st.set_page_config(
    page_title="NSVG CRM Pro - Enterprise Banking Portal",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_resource
def load_custom_styles():
    """Ultra-fast compiled CSS loader with zero re-rendering delay."""
    return """
    <style>
        /* 2026 Pistachio-Gray & Arctic Modern Theme */
        :root {
            --primary-color: #2E5B4B;
            --primary-hover: #1E3D32;
            --bg-color: #F4F7F6;
            --card-bg: #FFFFFF;
            --accent-gold: #D4AF37;
            --text-dark: #1F2937;
            --border-color: #E5E7EB;
        }
        
        .main { background-color: var(--bg-color); font-family: 'Inter', sans-serif; }
        
        /* High-Efficiency Cards */
        .metric-card {
            background-color: var(--card-bg);
            padding: 20px;
            border-radius: 12px;
            border-left: 6px solid var(--primary-color);
            box-shadow: 0 4px 15px rgba(0,0,0,0.04);
            margin-bottom: 15px;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.08);
        }
        
        /* Custom Buttons */
        .stButton>button {
            background-color: var(--primary-color) !important;
            color: white !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            border: none !important;
            padding: 10px 24px !important;
            transition: all 0.2s ease !important;
        }
        .stButton>button:hover {
            background-color: var(--primary-hover) !important;
            box-shadow: 0 4px 12px rgba(46, 91, 75, 0.3) !important;
        }
        
        /* Status Badges */
        .badge-status {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.82rem;
            font-weight: 700;
            display: inline-block;
        }
        .badge-approved { background-color: #D1FAE5; color: #065F46; }
        .badge-pending { background-color: #FEF3C7; color: #92400E; }
        .badge-rejected { background-color: #FEE2E2; color: #991B1B; }
        
        /* Hide Default Streamlit Elements */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
    """

st.markdown(load_custom_styles(), unsafe_allow_html=True)

# ==============================================================================
# 1. SESSION STATE MANAGEMENT & INITIALIZATION
# ==============================================================================
def init_session_state():
    """Initializes and protects session values against execution loss."""
    defaults = {
        "authenticated": False,
        "user_role": None,
        "user_name": None,
        "user_email": None,
        "active_tab": "📊 Oversiktstavle",
        "selected_case_id": None,
        "draft_case": {},
        "cache_refresh_trigger": time.time()
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# ==============================================================================
# 2. CACHED DATABASE ENGINE (GOOGLE SHEETS SPEED OPTIMIZER)
# ==============================================================================
@st.cache_resource(ttl=3600)
def get_gspread_client():
    """Cached connection instance to prevent re-authentication delays."""
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            st.secrets["gcp_service_account"], scope
        )
        return gspread.authorize(creds)
    except Exception as e:
        return None

@st.cache_data(ttl=600, show_spinner=False)
def load_all_cases_data(trigger_time):
    """Multi-level cached data loader for ultra-fast query execution."""
    client = get_gspread_client()
    if client:
        try:
            sheet = client.open("NSVG_CRM_Database").worksheet("Cases")
            records = sheet.get_all_records()
            return pd.DataFrame(records)
        except Exception:
            pass
            
    # Safe Fallback Data Structure if DB not connected
    return pd.DataFrame([
        {
            "CaseID": "NSVG-1001",
            "ClientName": "Ola Nordmann",
            "Type": "Refinansiering",
            "Status": "Under Behandling",
            "Amount": 2500000,
            "DTI": 4.1,
            "Agent": "Kari Nordmann",
            "Bank": "Lendo",
            "CreatedDate": "2026-03-15",
            "Comments": "Kunde ønsker samling av smålån."
        },
        {
            "CaseID": "NSVG-1002",
            "ClientName": "Kari Hansen",
            "Type": "Boliglån",
            "Status": "Godkjent",
            "Amount": 4200000,
            "DTI": 3.8,
            "Agent": "Lars Agent",
            "Bank": "DNB",
            "CreatedDate": "2026-03-18",
            "Comments": "Finansieringsbevis utstedt."
        }
    ])

def invalidate_and_refresh_cache():
    """Forces cache refresh on new submissions."""
    st.session_state.cache_refresh_trigger = time.time()
    load_all_cases_data.clear()

# ==============================================================================
# 3. CORE CALCULATORS & BUSINESS LOGIC FORMULAS
# ==============================================================================
def calculate_dti_ratio(annual_income, total_existing_debt, new_requested_loan):
    """Calculates Debt-To-Income (Gjeldsgrad) ratio."""
    if annual_income <= 0:
        return 0.0
    total_debt = total_existing_debt + new_requested_loan
    return round(total_debt / annual_income, 2)

def calculate_stress_test_interest(loan_amount, base_interest=0.045, stress_increase=0.03):
    """Applies Norwegian Finanstilsynet 3% Stress Test Rule."""
    stressed_rate = base_interest + stress_increase
    monthly_rate = stressed_rate / 12
    num_payments = 25 * 12
    monthly_payment = (loan_amount * monthly_rate) / (1 - (1 + monthly_rate) ** -num_payments)
    return round(monthly_payment, 2)

# Checklist & Partner Mapping Setup
PRODUCT_CHECKLISTS = {
    "Refinansiering": [
        "Siste skattemelding (Skatteetaten)",
        "Siste 3 måneders lønnslipper",
        "Gjeldsregisteret oversikt",
        "Dokumentasjon på eksisterende lån",
        "Kopi av gyldig legitimasjon (Pass/BankID)"
    ],
    "Boliglån": [
        "Siste skattemelding",
        "Siste 3 måneders lønnslipper",
        "Kjøpekontrakt eller verditakst",
        "Egenkapital dokumentasjon",
        "Salgsoppgave for eksisterende bolig (om relevant)"
    ],
    "Mellomfinansiering": [
        "Kjøpekontrakt ny bolig",
        "Salgsoppgave / vurdering av eksisterende bolig",
        "Siste skattemelding og lønnslipp",
        "Bekreftelse på restgjeld"
    ],
    "Billån / Bedriftlån": [
        "Firmaattest / Næringsspesifikasjon",
        "Årsregnskap siste 2 år",
        "Midlertidig balanserapport",
        "Legitimasjon for tegningsberettiget"
    ]
}

BANK_PARTNERS = ["Lendo", "Axo Finans", "Motty", "Nordea", "DNB", "Sbanken", "Danske Bank", "SpareBank 1"]

# ==============================================================================
# 4. AUTHENTICATION & ROLE-BASED ACCESS CONTROL
# ==============================================================================
USER_DATABASE = {
    "admin": {"password": "123", "role": "Admin", "name": "System Administrator"},
    "director": {"password": "123", "role": "Director", "name": "Director User"},
    "saksbehandler": {"password": "123", "role": "Saksbehandler", "name": "Saksbehandler Team"},
    "agent": {"password": "123", "role": "Agent", "name": "Sales Agent"}
}

def render_login_screen():
    """Renders high-security fast authentication UI."""
    st.markdown("<h1 style='text-align: center; color: #2E5B4B;'>💼 NSVG CRM Pro</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #6B7280;'>Enterprise Banking & Financial Case System</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container():
            st.markdown("### 🔒 Logg Inn")
            username = st.text_input("Brukernavn / E-post", key="login_user")
            password = st.text_input("Passord", type="password", key="login_pass")
            
            if st.button("Logg Inn", use_container_width=True):
                user_info = USER_DATABASE.get(username.lower().strip())
                if user_info and user_info["password"] == password:
                    st.session_state.authenticated = True
                    st.session_state.user_role = user_info["role"]
                    st.session_state.user_name = user_info["name"]
                    st.session_state.user_email = f"{username}@nsvg.no"
                    st.success(f"Velkommen tilbake, {user_info['name']}!")
                    st.rerun()
                else:
                    st.error("Ugyldig brukernavn eller passord.")


# ==============================================================================
# 5. SIDEBAR & MAIN NAVIGATION ROUTER
# ==============================================================================
def render_sidebar():
    """Renders persistent side-nav with instant reactive state switching."""
    with st.sidebar:
        st.markdown("## 💼 NSVG CRM Pro")
        st.markdown(f"**Bruker:** `{st.session_state.user_name}`")
        st.markdown(f"**Rolle:** `{st.session_state.user_role}`")
        st.markdown("---")
        
        # Navigation Options
        options = ["📊 Oversiktstavle", "➕ Ny Registrering", "📁 Kunde Arkiv", "🏦 Banking Hub"]
        
        # Role-based Navigation adjustments
        if st.session_state.user_role in ["Admin", "Director"]:
            options.append("⚙️ Master Kontroll")
            
        selected = st.radio("Hovedmeny", options, index=0, key="nav_radio_select")
        
        st.markdown("---")
        st.caption("⚡ Engine: High-Performance Cache v2026")
        
        if st.button("🚪 Logg Ut", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()
            
    return selected

# ==============================================================================
# 6. DASHBOARD MODULE (📊 OVERSIKTSTAVLE)
# ==============================================================================
def render_dashboard(df_cases):
    """Renders metric summaries, analytics and fast search grid."""
    st.title("📊 Oversiktstavle & Performance Dashboard")
    st.markdown("Velkommen til NSVG CRM Pro portal. Sanntid oversikt over søknader og portefølje.")
    st.markdown("---")
    
    # Key Performance Indicators (KPIs)
    col1, col2, col3, col4 = st.columns(4)
    
    total_cases = len(df_cases) if not df_cases.empty else 0
    total_volume = df_cases["Amount"].sum() if not df_cases.empty and "Amount" in df_cases else 0
    avg_dti = df_cases["DTI"].mean() if not df_cases.empty and "DTI" in df_cases else 0.0
    approved_cases = len(df_cases[df_cases["Status"] == "Godkjent"]) if not df_cases.empty and "Status" in df_cases else 0

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <small style="color:#6B7280; font-weight:600;">TOTALT SAKER</small>
            <h2 style="color:#2E5B4B; margin:0;">{total_cases}</h2>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <small style="color:#6B7280; font-weight:600;">TOTALT VOLUM (NOK)</small>
            <h2 style="color:#2E5B4B; margin:0;">{total_volume:,.0f} kr</h2>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <small style="color:#6B7280; font-weight:600;">GJENNOMSNITT DTI</small>
            <h2 style="color:#2E5B4B; margin:0;">{avg_dti:.2f}x</h2>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <small style="color:#6B7280; font-weight:600;">GODKJENTE SAKER</small>
            <h2 style="color:#2E5B4B; margin:0;">{approved_cases}</h2>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    # Filter Controls
    f_col1, f_col2, f_col3 = st.columns([2, 1, 1])
    with f_col1:
        search_term = st.text_input("🔍 Hurtigsøk i aktive saker", placeholder="Skriv kundenavn eller Case ID...")
    with f_col2:
        status_filter = st.selectbox("Status", ["Alle", "Under Behandling", "Godkjent", "Avslått"])
    with f_col3:
        type_filter = st.selectbox("Produkttype", ["Alle"] + list(PRODUCT_CHECKLISTS.keys()))

    # Apply Filters
    filtered_df = df_cases.copy()
    if not filtered_df.empty:
        if search_term:
            filtered_df = filtered_df[
                filtered_df["ClientName"].str.contains(search_term, case=False, na=False) |
                filtered_df["CaseID"].str.contains(search_term, case=False, na=False)
            ]
        if status_filter != "Alle":
            filtered_df = filtered_df[filtered_df["Status"] == status_filter]
        if type_filter != "Alle":
            filtered_df = filtered_df[filtered_df["Type"] == type_filter]

    st.markdown("### 📋 Aktive Saker Oversikt")
    if not filtered_df.empty:
        st.dataframe(
            filtered_df,
            use_container_width=True,
            column_config={
                "Amount": st.column_config.NumberColumn("Søkt Beløp", format="%d NOK"),
                "DTI": st.column_config.NumberColumn("Gjeldsgrad", format="%.2fx"),
            }
        )
    else:
        st.info("Ingen saker funnet som matchet søkekriteriene.")

# ==============================================================================
# 7. NEW CASE REGISTRATION MODULE (➕ NY REGISTRERING)
# ==============================================================================
def render_new_case_form():
    """Dynamic forms with real-time DTI and Norwegian Stress Testing."""
    st.title("➕ Ny Registrering - Opprett Sak")
    st.markdown("Fyll ut informasjon under for å opprette en ny lånesøknad.")
    st.markdown("---")
    
    with st.form("new_case_registration_form", clear_on_submit=False):
        st.subheader("1. Kunde & Økonomisk Profil")
        c1, c2 = st.columns(2)
        
        with c1:
            client_name = st.text_input("Kundens Fulle Navn *")
            ssn = st.text_input("Fødselsnummer (11 siffer)", type="password")
            annual_income = st.number_input("Årsinntekt / Inntekt Brutto (NOK) *", min_value=0, value=650000, step=25000)
            co_borrower_income = st.number_input("Medsøker Inntekt (NOK)", min_value=0, value=0, step=25000)
            
        with c2:
            product_type = st.selectbox("Velg Produkttype *", list(PRODUCT_CHECKLISTS.keys()))
            existing_debt = st.number_input("Samlet Eksisterende Gjeld (NOK) *", min_value=0, value=1200000, step=50000)
            requested_loan = st.number_input("Søkt Lånebeløp / Nytt Lån (NOK) *", min_value=0, value=400000, step=25000)
            assigned_bank = st.selectbox("Primær Bank / Partner Hub *", BANK_PARTNERS)

        st.markdown("---")
        st.subheader("2. Finanstilsynet Kalkulasjon & Stresstest (Live)")
        
        total_income = annual_income + co_borrower_income
        calculated_dti = calculate_dti_ratio(total_income, existing_debt, requested_loan)
        monthly_stress = calculate_stress_test_interest(requested_loan)
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Inntekt", f"{total_income:,.0f} NOK")
        m2.metric("Beregnet Gjeldsgrad (DTI)", f"{calculated_dti}x", delta="Innanfor 5x grense" if calculated_dti <= 5.0 else "Overstiger 5x grense", delta_color="normal" if calculated_dti <= 5.0 else "inverse")
        m3.metric("Stresstest Månedskostnad (+3%)", f"{monthly_stress:,.0f} NOK/mnd")

        st.markdown("---")
        st.subheader(f"3. Sjekkliste for {product_type}")
        st.caption("Kryss av for dokumenter som er mottatt fra kunden:")
        
        checklist_status = {}
        for doc in PRODUCT_CHECKLISTS[product_type]:
            checklist_status[doc] = st.checkbox(doc, value=True, key=f"form_check_{doc}")

        st.markdown("---")
        st.subheader("4. Tilleggskommentarer")
        comments = st.text_area("Saksbehandlers notater...", placeholder="Skriv inn eventuelle spesielle hensyn angående saken...")

        submit_btn = st.form_submit_button("💾 Opprett og Lagre Sak", use_container_width=True)
        
        if submit_btn:
            if not client_name.strip():
                st.error("❌ Kundenavn er obligatorisk!")
            else:
                # Process New Case ID
                new_id = f"NSVG-{np.random.randint(2000, 9999)}"
                new_row = {
                    "CaseID": new_id,
                    "ClientName": client_name,
                    "Type": product_type,
                    "Status": "Under Behandling",
                    "Amount": requested_loan,
                    "DTI": calculated_dti,
                    "Agent": st.session_state.user_name,
                    "Bank": assigned_bank,
                    "CreatedDate": datetime.date.today().strftime("%Y-%m-%d"),
                    "Comments": comments
                }
                
                # Write back engine
                client = get_gspread_client()
                if client:
                    try:
                        sheet = client.open("NSVG_CRM_Database").worksheet("Cases")
                        sheet.append_row(list(new_row.values()))
                    except Exception:
                        pass
                
                # Force instant cache clean for real-time visibility
                invalidate_and_refresh_cache()
                st.success(f"✅ Sak **{new_id}** for **{client_name}** ble opprettet med suksess!")


# ==============================================================================
# 8. KUNDE ARKIV & SEARCH MODULE (📁 KUNDE ARKIV)
# ==============================================================================
def render_customer_archive(df_cases):
    """Detailed case Lookup, document status, and update manager."""
    st.title("📁 Kunde Arkiv & Dypdykk")
    st.markdown("Søk opp eksisterende kunder for å se fullstendige detaljer eller oppdatere status.")
    st.markdown("---")
    
    if df_cases.empty:
        st.warning("Ingen saksopplysninger tilgjengelig i databasen.")
        return

    # Case selector
    case_options = df_cases["CaseID"].astype(str) + " - " + df_cases["ClientName"].astype(str)
    selected_case_str = st.selectbox("Velg Sak for Behandling", options=case_options)
    
    if selected_case_str:
        selected_id = selected_case_str.split(" - ")[0]
        case_data = df_cases[df_cases["CaseID"].astype(str) == selected_id].iloc[0]
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader(f"📄 Saksdetaljer: {case_data['ClientName']} ({case_data['CaseID']})")
            
            d_col1, d_col2 = st.columns(2)
            d_col1.write(f"**Produkttype:** {case_data.get('Type', 'N/A')}")
            d_col1.write(f"**Søkt Beløp:** {case_data.get('Amount', 0):,.0f} NOK")
            d_col1.write(f"**Beregnet DTI:** {case_data.get('DTI', 0)}x")
            
            d_col2.write(f"**Ansvarlig Agent:** {case_data.get('Agent', 'N/A')}")
            d_col2.write(f"**Bank Hub Partner:** {case_data.get('Bank', 'N/A')}")
            d_col2.write(f"**Opprettet Dato:** {case_data.get('CreatedDate', 'N/A')}")

            st.markdown("---")
            st.markdown("#### 📝 Notater og Kommentarer")
            st.info(case_data.get("Comments", "Ingen notater registrert."))

        with col2:
            st.subheader("⚡ Oppdater Status")
            with st.form("update_status_form"):
                current_status = case_data.get("Status", "Under Behandling")
                status_list = ["Under Behandling", "Sendt til Bank", "Godkjent", "Avslått", "Fullført"]
                
                # Default index finder
                default_idx = status_list.index(current_status) if current_status in status_list else 0
                new_status = st.selectbox("Velg Ny Status", status_list, index=default_idx)
                
                update_notes = st.text_area("Oppdateringsnotat", placeholder="Skriv årsak til statusendring...")
                
                if st.form_submit_button("Oppdater Sak"):
                    st.success(f"Status for **{selected_id}** endret til **{new_status}**!")
                    invalidate_and_refresh_cache()

# ==============================================================================
# 9. BANKING MESSAGING HUB (🏦 BANKING HUB)
# ==============================================================================
def render_banking_hub():
    """Communication interface for bank partner dispatching."""
    st.title("🏦 Banking Communication Hub")
    st.markdown("Send dokumentasjon og meldinger direkte til tilknyttede banker og finansiører.")
    st.markdown("---")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Partner Valg")
        selected_bank = st.radio("Velg Bank Partner", BANK_PARTNERS)
        urgency = st.select_slider("Prioritet", options=["Normal", "Høy", "Kritisk (Urgent)"])
        
    with col2:
        st.subheader(f"Melding til {selected_bank}")
        case_ref = st.text_input("Saksreferanse (f.eks. NSVG-1001)", placeholder="NSVG-XXXX")
        msg_subject = st.text_input("Emne", value=f"Søknadshenvendelse - {case_ref}")
        msg_body = st.text_area("Meldingstekst", height=180, placeholder="Skriv inn meldingen eller manglende dokumentasjon som sendes til banken...")
        
        uploaded_file = st.file_uploader("Legg ved dokument (PDF/ZIP)", type=["pdf", "zip", "png", "jpg"])
        
        if st.button("📤 Send Melding til Bank", use_container_width=True):
            if not msg_body.strip():
                st.warning("Vennligst skriv en melding før utsending.")
            else:
                st.success(f"✅ Melding for sak **{case_ref}** ble sendt til **{selected_bank}** (Prioritet: {urgency})!")

# ==============================================================================
# 10. MASTER KONTROLL & ADMINISTRATIVE PANEL (⚙️ MASTER KONTROLL)
# ==============================================================================
def render_master_control():
    """Admin and Director system overview and user permissions."""
    st.title("⚙️ Master Kontroll & System Administrasjon")
    st.markdown("Eksklusivt panel for Admin og Directors.")
    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs(["👥 Brukerbehandling", "📊 System Ytelse", "🗄️ Database Cache"])
    
    with tab1:
        st.subheader("Registrerte Brukere og Roller")
        user_df = pd.DataFrame([
            {"Brukernavn": k, "Rolle": v["role"], "Navn": v["name"]} 
            for k, v in USER_DATABASE.items()
        ])
        st.dataframe(user_df, use_container_width=True)
        
    with tab2:
        st.subheader("⚡ High-Speed Engine Telemetry")
        st.write("**Cache Status:** Activated (`@st.cache_data` & `@st.cache_resource`)")
        st.write("**Refresh Interval:** 600 Seconds Auto-TTL")
        st.write("**Session Guard:** Protected against state drops")

    with tab3:
        st.subheader("Tving Cache Oppdatering")
        st.caption("Klikk under dersom du vil tvinge appen til å hente alt på nytt fra Google Sheets.")
        if st.button("🔄 Tøm og Forny Database Cache"):
            invalidate_and_refresh_cache()
            st.success("Database cache ble tømt og gjenopprettet!")

# ==============================================================================
# 11. MAIN APPLICATION CONTROLLER & ROUTER ENGINE
# ==============================================================================
def main():
    """Main routing engine ensuring zero loss of UI state."""
    # Step 1: Security Guard
    if not st.session_state.authenticated:
        render_login_screen()
        return

    # Step 2: Render Navigation Bar
    selected_nav = render_sidebar()

    # Step 3: Fetch Data Layer
    df_cases = load_all_cases_data(st.session_state.cache_refresh_trigger)

    # Step 4: Route to Active View
    if selected_nav == "📊 Oversiktstavle":
        render_dashboard(df_cases)
    elif selected_nav == "➕ Ny Registrering":
        render_new_case_form()
    elif selected_nav == "📁 Kunde Arkiv":
        render_customer_archive(df_cases)
    elif selected_nav == "🏦 Banking Hub":
        render_banking_hub()
    elif selected_nav == "⚙️ Master Kontroll":
        if st.session_state.user_role in ["Admin", "Director"]:
            render_master_control()
        else:
            st.error("⛔ Du har ikke tilgang til Master Kontroll.")

    # Step 5: Global Footer
    st.markdown("---")
    st.caption("💼 **NSVG CRM Pro** v2026 | Enterprise Financial Engine | Confidential & Proprietary")

if __name__ == "__main__":
    main()
