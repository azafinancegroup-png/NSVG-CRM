import streamlit as st
import pandas as pd
import json
import time
from datetime import datetime

# ==========================================
# 1. PAGE CONFIGURATION & THEME
# ==========================================
st.set_page_config(
    page_title="NSVG CRM Pro",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Pistachio-Gray Custom Styling
st.markdown("""
    <style>
    .main { background-color: #F4F6F4; }
    .stButton>button {
        background-color: #93C572;
        color: white;
        border-radius: 8px;
        border: none;
        font-weight: bold;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #7BAE5B;
        color: white;
    }
    .metric-card {
        background-color: #FFFFFF;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #93C572;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .status-badge {
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 0.85em;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CACHING & SPEED OPTIMIZATION ENGINE
# ==========================================

# Connection Caching (Prevents Re-authentication Latency)
@st.cache_resource
def init_database_connection():
    # Simulated API/Google Sheets Auth Client
    time.sleep(0.05)
    return {"status": "connected", "engine": "NSVG_Core_v2"}

# Data Caching (Fast Loading via Memory)
@st.cache_data(ttl=300, show_spinner=False)
def load_crm_master_data():
    # Master Dataset Representation
    data = {
        "Saks-ID": ["NSVG-101", "NSVG-102", "NSVG-103", "NSVG-104", "NSVG-105"],
        "Kunde": ["Ola Nordmann", "Kari Hansen", "Ali Raza", "Lars Jensen", "Anita Holm"],
        "Epost": ["ola@example.no", "kari@example.no", "ali@example.no", "lars@example.no", "anita@example.no"],
        "Telefon": ["90000001", "90000002", "90000003", "90000004", "90000005"],
        "Lånetype": ["Boliglån", "Refinansiering", "Bedriftlån", "Billån", "Forbrukslån"],
        "Beløp": [3500000, 1200000, 5000000, 450000, 250000],
        "Egenkapital": [500000, 200000, 1000000, 50000, 0],
        "Status": ["Under Behandling", "Innvilget", "Nye Saker", "Under Behandling", "Avslått"],
        "Agent": ["Sara", "Ahmed", "Sara", "Unassigned", "Ahmed"],
        "Opprettet": ["2026-03-01", "2026-03-02", "2026-03-03", "2026-03-04", "2026-03-05"],
        "Notater": ["Standard vilkår", "Prioritert sak", "Krev ytterligere dok", "Venter på takst", "For høy gjeldsgrad"]
    }
    return pd.DataFrame(data)

def force_data_refresh():
    st.cache_data.clear()

# Initialize Cached Engine
db_conn = init_database_connection()
df_master = load_crm_master_data()

# ==========================================
# 3. SESSION STATE & PERSISTENCE ENGINE
# ==========================================
if 'user' not in st.session_state:
    st.session_state['user'] = {'username': 'Admin', 'role': 'Admin', 'authenticated': True}

if 'bank_messages' not in st.session_state:
    st.session_state['bank_messages'] = [
        {"id": "NSVG-101", "bank": "DNB", "msg": "Dokumenter mottatt og under vurdering.", "status": "Lest", "timestamp": "2026-03-01 10:30"},
        {"id": "NSVG-102", "bank": "Nordea", "msg": "Søknad innvilget. Finansieringsbevis sendt.", "status": "Lest", "timestamp": "2026-03-02 14:15"},
        {"id": "NSVG-103", "bank": "SpareBank 1", "msg": "Mangler siste skattemelding.", "status": "Ulest", "timestamp": "2026-03-03 09:00"}
    ]

if 'system_notifications' not in st.session_state:
    st.session_state['system_notifications'] = [
        "Ny sak NSVG-103 tildelt Sara",
        "Bankoppdatering mottatt for NSVG-102"
    ]

# ==========================================
# 4. NAVIGATION & SIDEBAR SYSTEM
# ==========================================
st.sidebar.title("🏢 NSVG CRM Pro")
st.sidebar.caption(f"Bruker: **{st.session_state['user']['username']}** | Rolle: **{st.session_state['user']['role']}**")

if st.sidebar.button("🔄 Synkroniser Data"):
    force_data_refresh()
    st.rerun()

menu = st.sidebar.radio(
    "Hovedmeny",
    [
        "📊 Dashboard", 
        "💬 Bank Messaging Hub", 
        "➕ Ny Registrering", 
        "📂 Kunde Arkiv", 
        "📋 Oversiktstavle", 
        "🛠️ Master Kontroll", 
        "📞 Support Center"
    ]
)

st.sidebar.markdown("---")
st.sidebar.caption("System Status: 🟢 Tilkoblet (Fast-Cache Active)")


# ==========================================
# 5. MODULE 1: DASHBOARD
# ==========================================
if menu == "📊 Dashboard":
    st.title("📊 CRM Dashboard")
    st.caption("Realtidsoversikt og nøkkeltall")
    
    # Notifications Expander
    if st.session_state['system_notifications']:
        with st.expander("🔔 Systemvarsler", expanded=True):
            for note in st.session_state['system_notifications']:
                st.write(f"• {note}")

    st.markdown("---")

    # Metrics Section
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-card"><h4>Totalt Saker</h4><h2>{len(df_master)}</h2></div>', unsafe_allow_html=True)
    with col2:
        tot_belop = df_master['Beløp'].sum()
        st.markdown(f'<div class="metric-card"><h4>Totalt Volum</h4><h2>{tot_belop:,.0f} NOK</h2></div>', unsafe_allow_html=True)
    with col3:
        innvilget = len(df_master[df_master['Status'] == 'Innvilget'])
        st.markdown(f'<div class="metric-card"><h4>Innvilget</h4><h2>{innvilget}</h2></div>', unsafe_allow_html=True)
    with col4:
        uleste = sum(1 for m in st.session_state['bank_messages'] if m['status'] == 'Ulest')
        st.markdown(f'<div class="metric-card"><h4>Uleste Meldinger</h4><h2>{uleste}</h2></div>', unsafe_allow_html=True)

    st.markdown("---")
    
    # Active Saker Expanders
    st.subheader("🔥 Aktive Saker Oversikt")
    for idx, row in df_master.iterrows():
        with st.expander(f"📌 {row['Saks-ID']} - {row['Kunde']} ({row['Lånetype']}) - Status: {row['Status']}"):
            c1, c2, c3, c4 = st.columns(4)
            c1.write(f"**Søkt Beløp:** {row['Beløp']:,} NOK")
            c2.write(f"**Egenkapital:** {row['Egenkapital']:,} NOK")
            c3.write(f"**Saksbehandler:** {row['Agent']}")
            c4.write(f"**Opprettet:** {row['Opprettet']}")
            st.write(f"**Notater:** {row['Notater']}")

# ==========================================
# 6. MODULE 2: BANK MESSAGING HUB
# ==========================================
elif menu == "💬 Bank Messaging Hub":
    st.title("💬 Bank Messaging Hub")
    st.caption("Kommunikasjon og dokumentutveksling med banker")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📬 Meldingshistorikk")
        for msg in st.session_state['bank_messages']:
            status_badge = "🟢 Lest" if msg['status'] == "Lest" else "🔴 Ulest"
            with st.container():
                st.markdown(f"""
                **Saks-ID:** `{msg['id']}` | **Bank:** `{msg['bank']}` | **Status:** {status_badge}  
                *Tidspunkt: {msg['timestamp']}*  
                > {msg['msg']}
                """)
                st.markdown("---")
            
    with col2:
        st.subheader("📤 Send Ny Melding")
        with st.form("send_message_form"):
            sak_id = st.selectbox("Velg Sak", df_master['Saks-ID'])
            bank_name = st.selectbox("Velg Bank", ["DNB", "Nordea", "SpareBank 1", "Danske Bank", "Eika", "SANTANDER"])
            message_text = st.text_area("Meldingstekst")
            uploaded_file = st.file_uploader("Legg ved dokument (PDF, PNG, JPG)", type=['pdf', 'png', 'jpg'])
            
            btn_send = st.form_submit_button("Send Melding Til Bank")
            if btn_send:
                if message_text.strip():
                    now = datetime.now().strftime("%Y-%m-%d %H:%M")
                    st.session_state['bank_messages'].insert(0, {
                        "id": sak_id,
                        "bank": bank_name,
                        "msg": message_text,
                        "status": "Ulest",
                        "timestamp": now
                    })
                    st.success("Melding sendt!")
                    st.rerun()
                else:
                    st.error("Meldingstekst kan ikke være tom.")

# ==========================================
# 7. MODULE 3: NY REGISTRERING
# ==========================================
elif menu == "➕ Ny Registrering":
    st.title("➕ Registrer Ny Søknad")
    st.caption("Legg inn detaljer for ny kunde og finansieringssøknad")
    
    with st.form("new_registration_form", clear_on_submit=True):
        st.subheader("📋 Kunde & Låneinformasjon")
        col1, col2 = st.columns(2)
        
        with col1:
            navn = st.text_input("Kunde Fullt Navn *")
            epost = st.text_input("E-postadresse *")
            telefon = st.text_input("Telefonnummer *")
            lanetype = st.selectbox("Lånetype", ["Boliglån", "Refinansiering", "Bedriftlån", "Billån", "Forbrukslån"])
            
        with col2:
            belop = st.number_input("Søkt Lånebeløp (NOK)", min_value=10000, step=50000, value=2000000)
            egenkapital = st.number_input("Egenkapital (NOK)", min_value=0, step=25000, value=300000)
            agent = st.selectbox("Tildel Agent", ["Sara", "Ahmed", "Unassigned"])
            notat = st.text_area("Saksnotater / Spesielle Betingelser")
            
        st.markdown("---")
        
        # Dynamic Auto-Calculations
        if belop > 0:
            belaningsgrad = ((belop - egenkapital) / belop) * 100
            st.info(f"📊 **Beregnet Belåningsgrad:** {belaningsgrad:.2f}%")
            
        submitted = st.form_submit_button("💾 Lagre og Registrer Sak")
        if submitted:
            if navn and epost:
                st.success(f"Ny sak for **{navn}** er registrert i systemet!")
                force_data_refresh()
            else:
                st.error("Vennligst fyll ut alle obligatoriske felt (*).")



# ==========================================
# 8. MODULE 4: KUNDE ARKIV
# ==========================================
elif menu == "📂 Kunde Arkiv":
    st.title("📂 Kunde Arkiv & Søk Engine")
    st.caption("Søk, filtrer og administrer registrerte kundesaker")
    
    col_search, col_filter = st.columns([3, 1])
    
    with col_search:
        search_query = st.text_input("🔍 Søk etter Kunde, Saks-ID, E-post eller Agent")
    with col_filter:
        status_filter = st.selectbox("Filtrer etter Status", ["Alle", "Nye Saker", "Under Behandling", "Innvilget", "Avslått"])
        
    filtered_df = df_master.copy()
    
    # Apply Status Filter
    if status_filter != "Alle":
        filtered_df = filtered_df[filtered_df['Status'] == status_filter]
        
    # Apply Text Search Filter
    if search_query:
        filtered_df = filtered_df[
            filtered_df['Kunde'].str.contains(search_query, case=False, na=False) |
            filtered_df['Saks-ID'].str.contains(search_query, case=False, na=False) |
            filtered_df['Epost'].str.contains(search_query, case=False, na=False) |
            filtered_df['Agent'].str.contains(search_query, case=False, na=False)
        ]
        
    st.subheader(f"Viser {len(filtered_df)} Saker")
    st.dataframe(filtered_df, use_container_width=True, hide_index=True)
    
    # Case Status Management Engine
    st.markdown("---")
    st.subheader("⚡ Hurtigoppdatering av Sak Status")
    c_id, c_stat, c_btn = st.columns([2, 2, 1])
    
    with c_id:
        selected_case = st.selectbox("Velg Sak ID for Endring", df_master['Saks-ID'])
    with c_stat:
        new_status = st.selectbox("Velg Ny Status", ["Nye Saker", "Under Behandling", "Innvilget", "Avslått"])
    with c_btn:
        st.write(" ")
        st.write(" ")
        if st.button("Oppdater Status"):
            st.success(f"Sak {selected_case} oppdatert til status: {new_status}")
            force_data_refresh()

# ==========================================
# 9. MODULE 5: OVERSIKTSTAVLE (KANBAN BOARD)
# ==========================================
elif menu == "📋 Oversiktstavle":
    st.title("📋 Live Oversiktstavle")
    st.caption("Kanban-visning for oversikt over alle saker per status")
    
    col_nye, col_behandling, col_innvilget = st.columns(3)
    
    with col_nye:
        st.markdown("### 🆕 Nye Saker")
        st.markdown("---")
        sub_df = df_master[df_master['Status'] == 'Nye Saker']
        for _, row in sub_df.iterrows():
            with st.container():
                st.info(f"**ID:** `{row['Saks-ID']}`\n\n**Kunde:** {row['Kunde']}\n\n**Beløp:** {row['Beløp']:,} NOK\n\n**Agent:** {row['Agent']}")
                
    with col_behandling:
        st.markdown("### ⚙️ Under Behandling")
        st.markdown("---")
        sub_df = df_master[df_master['Status'] == 'Under Behandling']
        for _, row in sub_df.iterrows():
            with st.container():
                st.warning(f"**ID:** `{row['Saks-ID']}`\n\n**Kunde:** {row['Kunde']}\n\n**Beløp:** {row['Beløp']:,} NOK\n\n**Agent:** {row['Agent']}")

    with col_innvilget:
        st.markdown("### ✅ Innvilget")
        st.markdown("---")
        sub_df = df_master[df_master['Status'] == 'Innvilget']
        for _, row in sub_df.iterrows():
            with st.container():
                st.success(f"**ID:** `{row['Saks-ID']}`\n\n**Kunde:** {row['Kunde']}\n\n**Beløp:** {row['Beløp']:,} NOK\n\n**Agent:** {row['Agent']}")

# ==========================================
# 10. MODULE 6: MASTER KONTROLL & ANSATTE
# ==========================================
elif menu == "🛠️ Master Kontroll":
    st.title("🛠️ Master Kontroll Panel")
    st.caption("Systemadministrasjon og brukerstyring")
    
    tab1, tab2 = st.tabs(["👥 Ansatte Kontroll", "⚙️ Systeminnstillinger"])
    
    with tab1:
        st.subheader("Oversikt over Ansatte")
        ansatte_df = pd.DataFrame({
            "Navn": ["Sara", "Ahmed", "Admin User"],
            "E-post": ["sara@nsvg.no", "ahmed@nsvg.no", "admin@nsvg.no"],
            "Rolle": ["Saksbehandler", "Saksbehandler", "System Administrator"],
            "Aktive Saker": [2, 1, 0],
            "Status": ["Aktiv", "Aktiv", "Aktiv"]
        })
        st.table(ansatte_df)
        
        st.subheader("➕ Legg til ny ansatt")
        with st.form("add_employee_form"):
            c1, c2, c3 = st.columns(3)
            c1.text_input("Fullt Navn")
            c2.text_input("E-post")
            c3.selectbox("Rolle", ["Saksbehandler", "Rådgiver", "Admin"])
            st.form_submit_button("Opprett Bruker")

    with tab2:
        st.subheader("⚙️ System Ytelse & Cache Kontroll")
        st.write("Aktiv Ytelsesmodus: **Fast-Memory Cache (TTL: 300s)**")
        
        if st.button("🗑️ Tøm System Cache (Force Reset)"):
            force_data_refresh()
            st.success("System Cache er tømt!")
            st.rerun()

# ==========================================
# 11. MODULE 7: SUPPORT CENTER
# ==========================================
elif menu == "📞 Support Center":
    st.title("📞 Support Center & Kontaktsenter")
    st.caption("Teknisk assistanse og viktig kontaktinformasjon")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏢 Intern Hjelp & Support")
        st.markdown("""
        * **IT-Support E-post:** support@nsvg.no
        * **Telefon Hotline:** +47 800 00 000
        * **Åpningstider:** Mandag - Fredag (08:00 - 16:00)
        """)
        
    with col2:
        st.subheader("🏦 Bankenes Renteliste & Direkte Linjer")
        st.markdown("""
        * **DNB Bank:** +47 915 04800 | renter@dnb.no
        * **Nordea:** +47 232 06001 | crm-partner@nordea.no
        * **SpareBank 1:** +47 915 07000 | partner@sb1.no
        """)
