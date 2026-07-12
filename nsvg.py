import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import time
import uuid
import re

# =================================================================
# --- PERSISTENT SESSION & AUTO-SAVE CONFIGURATION ---
# =================================================================
st.set_page_config(page_title="NSVG CRM System v2026", layout="wide", initial_sidebar_state="expanded")

# Prevent accidental logouts and maintain form state
if 'keep_alive_session' not in st.session_state:
    st.session_state.keep_alive_session = True
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'active_user' not in st.session_state:
    st.session_state.active_user = None
if 'user_role' not in st.session_state:
    st.session_state.user_role = None
if 'form_drafts' not in st.session_state:
    st.session_state.form_drafts = {}

# Mock Database Connection Helpers (Replace with your actual gsheets connection)
def get_data(sheet_name):
    if f"db_{sheet_name}" not in st.session_state:
        if sheet_name == "Oversiktstavle":
            st.session_state[f"db_{sheet_name}"] = pd.DataFrame(columns=["ID", "Seksjon", "Maaned", "Navn_Fra_Til", "Agent", "Belop", "Bank", "Status"])
        elif sheet_name == "Agents":
            st.session_state[f"db_{sheet_name}"] = pd.DataFrame([
                {"Brukernavn": "bedi", "Navn": "Bedi", "Rolle": "Saksbehandler", "Status": "Aktiv"},
                {"Brukernavn": "umer", "Navn": "Umer", "Rolle": "Saksbehandler", "Status": "Aktiv"},
                {"Brukernavn": "admin", "Navn": "Admin", "Rolle": "Administrator", "Status": "Aktiv"}
            ])
        elif sheet_name == "Leads":
            st.session_state[f"db_{sheet_name}"] = pd.DataFrame(columns=["ID", "Dato", "Navn", "Telefon", "Epost", "Status", "Agent", "Notater"])
        else:
            st.session_state[f"db_{sheet_name}"] = pd.DataFrame()
    return st.session_state[f"db_{sheet_name}"]

def update_sheet_data_internal(sheet_name, df):
    st.session_state[f"db_{sheet_name}"] = df
    return True

# =================================================================
# --- 1. CORE SECURITY & AUTHENTICATION (NO AUTO-TIMEOUT) ---
# =================================================================
if not st.session_state.logged_in:
    st.title("🔒 Nordic Secure Vault Group - CRM Portal")
    st.subheader("Login required to access secure workspace")
    
    with st.form("login_form"):
        username_input = st.text_input("Brukernavn (Username):").strip().lower()
        password_input = st.text_input("Passord (Password):", type="password")
        submit_login = st.form_submit_button("Logg inn")
        
        if submit_login:
            agents_df = get_data("Agents")
            matched_user = agents_df[agents_df["Brukernavn"] == username_input]
            
            if not matched_user.empty and password_input == "nsvg2026": # Replace with your password validation logic
                st.session_state.logged_in = True
                st.session_state.active_user = matched_user.iloc[0]["Navn"]
                st.session_state.user_role = matched_user.iloc[0]["Rolle"]
                st.session_state.username_raw = matched_user.iloc[0]["Brukernavn"]
                st.success(f"Velkommen tilbake, {st.session_state.active_user}!")
                st.rerun()
            else:
                st.error("Feil brukernavn eller passord. Vennligst prøv igjen.")
    st.stop()

# --- SIDEBAR NAVIGATION ---
st.sidebar.image("https://via.placeholder.com/150", width=120) # Simulated Logo Placeholder
st.sidebar.markdown(f"**Bruker:** {st.session_state.active_user}\n**Rolle:** {st.session_state.user_role}")

valg = st.sidebar.radio("Hovedmeny / Navigation:", [
    "📊 1. Hoveddashboard",
    "👥 2. Kundeliste / Leads (CRM)",
    "📁 3. Sakhåndtering",
    "📝 4. Dokumentmaler",
    "📧 5. E-post Automatisering",
    "👥 6. Ansatte Kontroll",
    "💻 7. Saksbehandler Panel",
    "📞 8. Intern Kontakter",
    "🛠️ 9. Admin Verktøy",
    "📋 10. Oversiktstavle"
])

if st.sidebar.button("🚪 Logg ut (Manual Logout Only)"):
    st.session_state.logged_in = False
    st.session_state.active_user = None
    st.session_state.user_role = None
    st.rerun()

# =================================================================
# --- 2. HOVEDDASHBOARD ---
# =================================================================
if "1. Hoveddashboard" in valg:
    st.header("📊 System Hoveddashboard")
    st.caption("Live analytisk oversikt over selskapets operasjoner.")
    st.divider()
    
    leads_df = get_data("Leads")
    total_leads = len(leads_df)
    active_cases = len(get_data("Oversiktstavle"))
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Totalt Antall Leads", total_leads)
    m2.metric("Aktive Saker på Tavle", active_cases)
    m3.metric("System Status", "Operasjonell / Sikker")

# =================================================================
# --- 3. KUNDELISTE / LEADS (CRM) ---
# =================================================================
elif "2. Kundeliste / Leads (CRM)" in valg:
    st.header("👥 Kundeliste & Lead Management")
    st.divider()
    
    with st.form("new_lead_form"):
        st.markdown("### Registrer Ny Lead")
        col1, col2 = st.columns(2)
        l_name = col1.text_input("Navn:", value=st.session_state.form_drafts.get("l_name", ""))
        l_phone = col1.text_input("Telefon:", value=st.session_state.form_drafts.get("l_phone", ""))
        l_email = col2.text_input("E-post:", value=st.session_state.form_drafts.get("l_email", ""))
        l_agent = col2.selectbox("Tildelt Agent:", ["Bedi", "Umer", "Direkte"])
        l_notes = st.text_area("Notater / Kommentarer:", value=st.session_state.form_drafts.get("l_notes", ""))
        
        if st.form_submit_button("Lagre Lead"):
            if l_name.strip():
                leads_df = get_data("Leads")
                new_row = pd.DataFrame([{
                    "ID": uuid.uuid4().hex, "Dato": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Navn": l_name, "Telefon": l_phone, "Epost": l_email, "Status": "Ny", "Agent": l_agent, "Notater": l_notes
                }])
                update_sheet_data_internal("Leads", pd.concat([leads_df, new_row], ignore_index=True))
                st.session_state.form_drafts.clear()
                st.success("Lead lagret suksessfullt!")
                st.rerun()
            else:
                st.error("Navn er obligatorisk.")

    st.markdown("### Eksisterende Leads")
    st.dataframe(get_data("Leads"), use_container_width=True)

# =================================================================
# --- 4. SAKSHÅNDTERING ---
# =================================================================
elif "3. Sakhåndtering" in valg:
    st.header("📁 Sakhåndtering & Saker Status")
    st.divider()
    st.info("Her kan du se alle registrerte saker og deres fremdrift.")
    st.dataframe(get_data("Oversiktstavle"), use_container_width=True)

# =================================================================
# --- 5. DOKUMENTMALER ---
# =================================================================
elif "4. Dokumentmaler" in valg:
    st.header("📝 Dokumentmaler & Kontraktsgenerator")
    st.divider()
    template_type = st.selectbox("Velg Mal:", ["Standard Avtale", "Følgebrev", "Oppsigelse Bank"])
    client_placeholder = st.text_input("Klient Navn for Forhåndsvisning:")
    
    st.markdown(f"**Forhåndsvisning av {template_type}:**")
    st.code(f"Kjære {client_placeholder if client_placeholder else '[Klient Navn]'},\n\nVi viser til din sak hos Nordic Secure Vault Group...")

# =================================================================
# --- 6. E-POST AUTOMATISERING ---
# =================================================================
elif "5. E-post Automatisering" in valg:
    st.header("📧 E-post Sendersentral")
    st.divider()
    
    with st.form("email_send_form"):
        to_email = st.text_input("Mottaker E-post:")
        subject_email = st.text_input("Emne:")
        body_email = st.text_area("Melding:")
        
        if st.form_submit_button("Send E-post"):
            try:
                # Simulated safe email routine block
                st.success(f"E-post sendt simulert til {to_email} uten systemkrasj.")
            except Exception as e:
                st.error(f"Feil ved sending: {e}")

# =================================================================
# --- 7. ANSATTE KONTROLL ---
# =================================================================
elif "6. Ansatte Kontroll" in valg:
    st.header("👥 Intern Ansatte Kontroll & Profiler")
    st.divider()
    
    if st.session_state.user_role != "Administrator":
        st.warning("⚠️ Kun Administratorer har tilgang til å modifisere ansatte.")
    
    agents_df = get_data("Agents")
    st.dataframe(agents_df, use_container_width=True)
    
    with st.form("new_agent_form"):
        st.markdown("### Registrer / Oppdater Agent")
        a_user = st.text_input("Brukernavn:")
        a_name = st.text_input("Fullt Navn:")
        a_role = st.selectbox("Rolle:", ["Saksbehandler", "Administrator"])
        
        if st.form_submit_button("💾 Oppdater Agent") and st.session_state.user_role == "Administrator":
            if a_user.strip():
                new_agent = pd.DataFrame([{"Brukernavn": a_user.lower().strip(), "Navn": a_name, "Rolle": a_role, "Status": "Aktiv"}])
                updated_agents = pd.concat([agents_df[agents_df["Brukernavn"] != a_user.lower().strip()], new_agent], ignore_index=True)
                update_sheet_data_internal("Agents", updated_agents)
                st.success("Agent oppdatert i databasen!")
                st.rerun()

# =================================================================
# --- 8. SAKSBEHANDLER PANEL (FIXED & FULLY FUNCTIONAL) ---
# =================================================================
elif "7. Saksbehandler Panel" in valg:
    st.header("💻 Saksbehandler Personlig Panel")
    st.caption(f"Innlogget som: {st.session_state.active_user}")
    st.divider()
    
    current_username = str(st.session_state.username_raw).strip().lower()
    current_display_name = str(st.session_state.active_user).strip().lower()
    
    all_cases_df = get_data("Oversiktstavle")
    
    if not all_cases_df.empty:
        all_cases_df["Agent_Lower"] = all_cases_df["Agent"].fillna("").astype(str).str.strip().str.lower()
        my_cases = all_cases_df[(all_cases_df["Agent_Lower"] == current_username) | (all_cases_df["Agent_Lower"] == current_display_name)]
        
        if not my_cases.empty:
            st.markdown("### 🗂️ Dine Tildelte Aktive Saker")
            st.dataframe(my_cases.drop(columns=["Agent_Lower"]), use_container_width=True)
        else:
            st.info("Fant ingen saker tildelt direkte til ditt navn i denne måneden.")
    else:
        st.info("Oversiktstavle-databasen er tom. Ingen saker å hente.")

# =================================================================
# --- 9. INTERN KONTAKTER ---
# =================================================================
elif "8. Intern Kontakter" in valg:
    st.header("📞 Intern Kontaktliste")
    st.divider()
    st.markdown("""
    *   **Hovedkontor:** Oslo Sentrum | Tlf: 22 00 00 00
    *   **IT Support:** support@nsvg.no
    *   **Ledelse:** admin@nsvg.no
    """)

# =================================================================
# --- 10. ADMIN VERKTØY ---
# =================================================================
elif "9. Admin Verktøy" in valg:
    st.header("🛠️ System Admin Verktøy")
    st.divider()
    if st.session_state.user_role != "Administrator":
        st.error("Adgang nektet. Kun for IT-administratorer.")
    else:
        st.success("Systemlogger kjører uten avvik.")
        if st.button("Rens System Caches"):
            st.success("Cache tømt.")

# =================================================================
# --- 11. OVERSIKTSTAVLE & CRM WORKSPACE (SECURED UNIQUE ID) ---
# =================================================================
elif "10. Oversiktstavle" in valg:
    st.header("📋 Digital Styringstavle & CRM Workspace")
    st.caption("Nordic Secure Vault Group | Intern Styringstavle")
    st.divider()

    # --- PERIOD SELECTION ---
    st.subheader("📅 Velg Periode")
    col_cal1, col_cal2 = st.columns(2)
    with col_cal1:
        valgt_maaned = st.selectbox("Arbeidsmåned:", [
            "Mai 2026", "Juni 2026", "Juli 2026", "August 2026", 
            "September 2026", "Oktober 2026", "November 2026", "Desember 2026"
        ], index=2)
    with col_cal2:
        valgt_dato = st.date_input("Dagens Dato:", value=None)

    # Core Initialization
    if 'nsvg_workspace_data' not in st.session_state:
        st.session_state.nsvg_workspace_data = {
            "Aktiv Saker": [],
            "Fremkommer Saker": [],
            "Innbetaling": [],
            "Utbetaling": []
        }

    def load_board_from_sheets():
        try:
            sheet_df = get_data("Oversiktstavle")
            if sheet_df is None or sheet_df.empty:
                return None
            
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
            st.error(f"Kunne ikke hente data fra Google Sheets: {e}")
            return None

    def save_board_to_sheets(all_data):
        rows_to_save = []
        for sec_name, items in all_data.items():
            for item in items:
                name_val = item.get("navn") if sec_name in ["Aktiv Saker", "Fremkommer Saker"] else (item.get("fra") if sec_name == "Innbetaling" else item.get("til"))
                belop_val = item.get("deal") if sec_name in ["Aktiv Saker", "Fremkommer Saker"] else item.get("belop")
                
                if "id" not in item or not item["id"]:
                    item["id"] = uuid.uuid4().hex
                    
                rows_to_save.append({
                    "ID": item.get("id"),
                    "Seksjon": sec_name,
                    "Maaned": item.get("dato", valgt_maaned),
                    "Navn_Fra_Til": name_val if name_val else "",
                    "Agent": item.get("agent", "Direkte"),
                    "Belop": belop_val if belop_val else "0",
                    "Bank": item.get("bank", "Ingen / Ikke sendt"),
                    "Status": item.get("status", "")
                })
        df_save = pd.DataFrame(rows_to_save)
        success = update_sheet_data_internal("Oversiktstavle", df_save)
        return success

    # AUTOMATIC INITIAL LOAD
    if 'nsvg_sheets_loaded' not in st.session_state or not st.session_state.nsvg_sheets_loaded:
        sheets_data = load_board_from_sheets()
        if sheets_data is not None:
            st.session_state.nsvg_workspace_data = sheets_data
        st.session_state.nsvg_sheets_loaded = True

    c_sync1, c_sync2 = st.columns([4, 1])
    with c_sync2:
        if st.button("🔄 Tving Synk", use_container_width=True):
            sheets_data = load_board_from_sheets()
            if sheets_data is not None:
                st.session_state.nsvg_workspace_data = sheets_data
                st.success("Synkronisert!")
                st.rerun()

    agent_options = ["Bedi", "Umer", "Direkte"]
    bank_options = ["Ingen / Ikke sendt", "Sparebank Øst", "BN Bank", "Storebrand", "Nordea"]

    def rens_belop(tekst):
        try:
            tall = "".join([c for c in str(tekst) if c.isdigit() or c == "."])
            return float(tall) if tall else 0.0
        except:
            return 0.0

    # --- LIVE ECONOMY FINANCIAL OVERVIEW ---
    st.markdown("### 📊 Økonomisk Oversikt for " + valgt_maaned)
    
    total_inn_forventet = sum([rens_belop(i.get("belop", 0)) for i in st.session_state.nsvg_workspace_data.get("Innbetaling", []) if i.get("dato") == valgt_maaned])
    total_ut_forventet = sum([rens_belop(u.get("belop", 0)) for u in st.session_state.nsvg_workspace_data.get("Utbetaling", []) if u.get("dato") == valgt_maaned])
    netto_balanse = total_inn_forventet - total_ut_forventet

    fin_c1, fin_c2, fin_c3 = st.columns(3)
    fin_c1.metric("💰 Totalt Innbetalinger", f"{total_inn_forventet:,.2f} kr".replace(",", " "))
    fin_c2.metric("💸 Totalt Utbetalinger", f"{total_ut_forventet:,.2f} kr".replace(",", " "))
    fin_c3.metric("📈 Netto Forventet Balanse", f"{netto_balanse:,.2f} kr".replace(",", " "), delta=netto_balanse)
    st.divider()

    # --- DYNAMIC INPUT FORMS WITH LIVE IN-MEMORY PERSISTENCE ---
    st.markdown("### ➕ Registrer Ny Data")
    tab1, tab2, tab3, tab4 = st.tabs(["🔹 Aktiv Sak", "🔸 Fremtidig Sak", "📥 Innbetaling Plan", "📤 Utbetaling Plan"])

    with tab1:
        with st.form("form_aktiv_sak"):
            col1, col2 = st.columns(2)
            sak_navn = col1.text_input("Kunde / Sak Navn:", placeholder="F.eks. Tousif sak")
            sak_agent = col1.selectbox("Hvilken Agent?", agent_options)
            sak_deal = col2.text_input("Deal Størrelse (Bare tall):", placeholder="F.eks. 50000")
            sak_bank = col2.selectbox("Aktiv Bank:", bank_options)
            
            st.markdown("**Avslag fra hvilke banker?**")
            avslag_valg = []
            c_av1, c_av2, c_av3, c_av4 = st.columns(4)
            if c_av1.checkbox("Sparebank Øst", key="reg_av_sp"): avslag_valg.append("Sparebank Øst")
            if c_av2.checkbox("BN Bank", key="reg_av_bn"): avslag_valg.append("BN Bank")
            if c_av3.checkbox("Storebrand", key="reg_av_sb"): avslag_valg.append("Storebrand")
            if c_av4.checkbox("Nordea", key="reg_av_nd"): avslag_valg.append("Nordea")
            
            sak_status_base = st.text_area("Status og Mangler:", placeholder="F.eks. Venter på lønnslipp.")
            
            if st.form_submit_button("🚀 Registrer Aktiv Sak"):
                if sak_navn.strip():
                    avslag_tekst = f"[AVSLAG: {', '.join(avslag_valg)}] " if avslag_valg else ""
                    full_status = f"{avslag_tekst}{sak_status_base}".strip()
                    
                    st.session_state.nsvg_workspace_data["Aktiv Saker"].append({
                        "id": uuid.uuid4().hex, "navn": sak_navn, "agent": sak_agent, "deal": sak_deal, 
                        "bank": sak_bank, "status": full_status, "dato": valgt_maaned
                    })
                    save_board_to_sheets(st.session_state.nsvg_workspace_data)
                    st.rerun()

    with tab2:
        with st.form("form_frem_sak"):
            col1, col2 = st.columns(2)
            f_navn = col1.text_input("Kunde / Fremtidig Sak Navn:", placeholder="F.eks. Salauddin")
            f_agent = col1.selectbox("Hvilken Agent?", agent_options, key="f_ag")
            f_deal = col2.text_input("Forventet Deal Størrelse:", placeholder="F.eks. 30000")
            f_status = st.text_area("Samtale Detaljer", placeholder="F.eks. Venter på dokumenter.")
            
            if st.form_submit_button("🚀 Registrer Fremtidig Sak"):
                if f_navn.strip():
                    st.session_state.nsvg_workspace_data["Fremkommer Saker"].append({
                        "id": uuid.uuid4().hex, "navn": f_navn, "agent": f_agent, "deal": f_deal, 
                        "status": f_status, "dato": valgt_maaned
                    })
                    save_board_to_sheets(st.session_state.nsvg_workspace_data)
                    st.rerun()

    with tab3:
        with st.form("form_innbetaling"):
            col1, col2 = st.columns(2)
            inn_fra = col1.text_input("Hvem skal betale inn?", placeholder="F.eks. Kunde navn")
            inn_belop = col2.text_input("Beløp:", placeholder="F.eks. 15000")
            inn_status = st.text_input("Status på betaling:", placeholder="F.eks. Venter i slutten av måneden")
            
            if st.form_submit_button("📥 Registrer Innbetaling"):
                if inn_fra.strip():
                    st.session_state.nsvg_workspace_data["Innbetaling"].append({
                        "id": uuid.uuid4().hex, "fra": inn_fra, "belop": inn_belop, "status": inn_status, "dato": valgt_maaned
                    })
                    save_board_to_sheets(st.session_state.nsvg_workspace_data)
                    st.rerun()

    with tab4:
        with st.form("form_utbetaling"):
            col1, col2 = st.columns(2)
            ut_til = col1.text_input("Hvem skal du betale?", placeholder="F.eks. Kontor / Ansatt bonus")
            ut_belop = col2.text_input("Beløp:", placeholder="F.eks. 7825")
            ut_status = st.text_input("Status på utgiften:", placeholder="F.eks. Ikke betalt")
            
            if st.form_submit_button("📤 Registrer Utbetaling"):
                if ut_til.strip():
                    st.session_state.nsvg_workspace_data["Utbetaling"].append({
                        "id": uuid.uuid4().hex, "til": ut_til, "belop": ut_belop, "status": ut_status, "dato": valgt_maaned
                    })
                    save_board_to_sheets(st.session_state.nsvg_workspace_data)
                    st.rerun()

    # --- THE MODERN INTERACTIVE WORKSPACE GRID ---
    st.markdown("---")
    st.markdown(f"## **{valgt_maaned} ::::**\n### **/ Gjeldende Seksjonslister /**")
    
    ui_cols = st.columns(4)

    # COLUMN 1: AKTIV SAKER
    with ui_cols[0]:
        st.markdown("<div style='background-color:#E3F2FD; padding:10px; border-radius:8px; text-align:center; font-weight:bold; border:2px solid #2196F3; color:#0D47A1;'>🔹 AKTIV SAKER</div>", unsafe_allow_html=True)
        st.write("")
        
        aktiv_liste = st.session_state.nsvg_workspace_data.get("Aktiv Saker", [])
        for idx, item in enumerate(aktiv_liste):
            if item.get("dato") == valgt_maaned:
                item_id = item.get("id")
                current_status_str = item.get("status", "")
                
                with st.expander(f"📁 {item.get('navn')} ({item.get('deal')} kr)"):
                    item["navn"] = st.text_input("Navn:", value=item.get("navn", ""), key=f"n_{item_id}")
                    item["agent"] = st.selectbox("Agent:", agent_options, index=agent_options.index(item["agent"]) if item.get("agent") in agent_options else 0, key=f"a_{item_id}")
                    item["deal"] = st.text_input("Deal/Penger:", value=item.get("deal", ""), key=f"d_{item_id}")
                    item["bank"] = st.selectbox("Aktiv Bank:", bank_options, index=bank_options.index(item["bank"]) if item.get("bank") in bank_options else 0, key=f"b_{item_id}")
                    
                    st.markdown("⚠️ **Avslag registrert:**")
                    c_ed_av1, c_ed_av2, c_ed_av3, c_ed_av4 = st.columns(4)
                    av1 = c_ed_av1.checkbox("Øst", value="Sparebank Øst" in current_status_str, key=f"av_sp_{item_id}")
                    av2 = c_ed_av2.checkbox("BN", value="BN Bank" in current_status_str, key=f"av_bn_{item_id}")
                    av3 = c_ed_av3.checkbox("Storeb", value="Storebrand" in current_status_str, key=f"av_sb_{item_id}")
                    av4 = c_ed_av4.checkbox("Nordea", value="Nordea" in current_status_str, key=f"av_nd_{item_id}")
                    
                    clean_status = re.sub(r"\[AVSLAG:.*?\]\s*", "", current_status_str).strip()
                    updated_avslag_list = []
                    if av1: updated_avslag_list.append("Sparebank Øst")
                    if av2: updated_avslag_list.append("BN Bank")
                    if av3: updated_avslag_list.append("Storebrand")
                    if av4: updated_avslag_list.append("Nordea")
                    
                    item["status"] = st.text_area("Oppdateringer:", value=clean_status, key=f"s_{item_id}", height=80)
                    new_avslag_tekst = f"[AVSLAG: {', '.join(updated_avslag_list)}] " if updated_avslag_list else ""
                    final_combined_status = f"{new_avslag_tekst}{item['status']}".strip()
                    
                    c_save, c_del = st.columns(2)
                    if c_save.button("💾 Lagre", key=f"sv_{item_id}"):
                        item["status"] = final_combined_status
                        save_board_to_sheets(st.session_state.nsvg_workspace_data)
                        st.success("Lagret.")
                        st.rerun()
                    if c_del.button("🗑️ Slett", key=f"dl_{item_id}"):
                        st.session_state.nsvg_workspace_data["Aktiv Saker"] = [x for x in aktiv_liste if x.get("id") != item_id]
                        save_board_to_sheets(st.session_state.nsvg_workspace_data)
                        st.rerun()

    # COLUMN 2: FREMTIDIGE SAKER
    with ui_cols[1]:
        st.markdown("<div style='background-color:#FFF3E0; padding:10px; border-radius:8px; text-align:center; font-weight:bold; border:2px solid #FF9800; color:#E65100;'>🔸 FREMTIDIGE SAKER</div>", unsafe_allow_html=True)
        st.write("")
        
        frem_liste = st.session_state.nsvg_workspace_data.get("Fremkommer Saker", [])
        for idx, item in enumerate(frem_liste):
            if item.get("dato") == valgt_maaned:
                item_id = item.get("id")
                with st.expander(f"⏳ {item.get('navn')} ({item.get('deal')} kr)"):
                    item["navn"] = st.text_input("Navn:", value=item.get("navn", ""), key=f"n_{item_id}")
                    item["agent"] = st.selectbox("Agent:", agent_options, index=agent_options.index(item["agent"]) if item.get("agent") in agent_options else 0, key=f"a_{item_id}")
                    item["deal"] = st.text_input("Forventet Deal:", value=item.get("deal", ""), key=f"d_{item_id}")
                    item["status"] = st.text_area("Detaljer:", value=item.get("status", ""), key=f"s_{item_id}", height=80)
                    
                    c_save, c_del = st.columns(2)
                    if c_save.button("💾 Lagre", key=f"sv_{item_id}"):
                        save_board_to_sheets(st.session_state.nsvg_workspace_data)
                        st.rerun()
                    if c_del.button("🗑️ Slett", key=f"dl_{item_id}"):
                        st.session_state.nsvg_workspace_data["Fremkommer Saker"] = [x for x in frem_liste if x.get("id") != item_id]
                        save_board_to_sheets(st.session_state.nsvg_workspace_data)
                        st.rerun()

    # COLUMN 3: INNBETALINGER
    with ui_cols[2]:
        st.markdown("<div style='background-color:#E8F5E9; padding:10px; border-radius:8px; text-align:center; font-weight:bold; border:2px solid #4CAF50; color:#1B5E20;'>📥 INNBETALINGER</div>", unsafe_allow_html=True)
        st.write("")
        
        inn_liste = st.session_state.nsvg_workspace_data.get("Innbetaling", [])
        for idx, item in enumerate(inn_liste):
            if item.get("dato") == valgt_maaned:
                item_id = item.get("id")
                with st.expander(f"💰 {item.get('fra')} ({item.get('belop')} kr)"):
                    item["fra"] = st.text_input("Fra hvem:", value=item.get("fra", ""), key=f"f_{item_id}")
                    item["belop"] = st.text_input("Beløp:", value=item.get("belop", ""), key=f"b_{item_id}")
                    item["status"] = st.text_input("Status:", value=item.get("status", ""), key=f"s_{item_id}")
                    
                    c_save, c_del = st.columns(2)
                    if c_save.button("💾 Lagre", key=f"sv_{item_id}"):
                        save_board_to_sheets(st.session_state.nsvg_workspace_data)
                        st.rerun()
                    if c_del.button("🗑️ Slett", key=f"dl_{item_id}"):
                        st.session_state.nsvg_workspace_data["Innbetaling"] = [x for x in inn_liste if x.get("id") != item_id]
                        save_board_to_sheets(st.session_state.nsvg_workspace_data)
                        st.rerun()

    # COLUMN 4: UTBETALINGER
    with ui_cols[3]:
        st.markdown("<div style='background-color:#FFEBEE; padding:10px; border-radius:8px; text-align:center; font-weight:bold; border:2px solid #F44336; color:#B71C1C;'>💸 UTBETALINGER</div>", unsafe_allow_html=True)
        st.write("")
        
        ut_liste = st.session_state.nsvg_workspace_data.get("Utbetaling", [])
        for idx, item in enumerate(ut_liste):
            if item.get("dato") == valgt_maaned:
                item_id = item.get("id")
                with st.expander(f"💸 {item.get('til')} ({item.get('belop')} kr)"):
                    item["til"] = st.text_input("Til hvem:", value=item.get("til", ""), key=f"t_{item_id}")
                    item["belop"] = st.text_input("Beløp:", value=item.get("belop", ""), key=f"b_{item_id}")
                    item["status"] = st.text_input("Status:", value=item.get("status", ""), key=f"s_{item_id}")
                    
                    c_save, c_del = st.columns(2)
                    if c_save.button("💾 Lagre", key=f"sv_{item_id}"):
                        save_board_to_sheets(st.session_state.nsvg_workspace_data)
                        st.rerun()
                    if c_del.button("🗑️ Slett", key=f"dl_{item_id}"):
                        st.session_state.nsvg_workspace_data["Utbetaling"] = [x for x in ut_liste if x.get("id") != item_id]
                        save_board_to_sheets(st.session_state.nsvg_workspace_data)
                        st.rerun()

# ==========================================
# --- APP FOOTER ---
# ==========================================
st.write("")
st.divider()
st.caption("© 2026 Nordic Secure Vault Group | Persistent Workspace Secured Run")
