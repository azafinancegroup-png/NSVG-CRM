import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime, date
import time
import uuid

# ---------------------------------------------------------
# 1. PAGE CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(
    page_title="Form Control System",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for UI Enhancement
st.markdown("""
    <style>
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .stMetric {
        background-color: #f8f9fa;
        padding: 10px;
        border-radius: 8px;
        border: 1px solid #e9ecef;
    }
    .stAlert {
        border-radius: 8px;
    }
    div[data-testid="stForm"] {
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. GOOGLE SHEETS AUTHENTICATION & CACHING
# ---------------------------------------------------------
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource(ttl=3600)
def get_gspread_client():
    """Authenticate with Google Sheets API using Streamlit Secrets."""
    try:
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Authentication Error: Secrets setup check karein. Detail: {e}")
        st.stop()

@st.cache_resource(ttl=3600)
def get_spreadsheet():
    """Fetch Spreadsheet Instance."""
    client = get_gspread_client()
    try:
        sheet_id = st.secrets["spreadsheet_id"]
        return client.open_by_key(sheet_id)
    except Exception as e:
        st.error(f"Spreadsheet Open Error: Spreadsheet ID check karein. Detail: {e}")
        st.stop()

# Cache data reading to make app fast
@st.cache_data(ttl=60)
def fetch_sheet_data(worksheet_name):
    """Fetch all records from a specific worksheet as Dataframe."""
    try:
        sh = get_spreadsheet()
        ws = sh.worksheet(worksheet_name)
        data = ws.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error fetching data from {worksheet_name}: {e}")
        return pd.DataFrame()

def clear_cache():
    """Clear cached data when updates are made."""
    st.cache_data.clear()

# ---------------------------------------------------------
# 3. DATA MANIPULATION & HELPER FUNCTIONS
# ---------------------------------------------------------

def append_to_sheet(worksheet_name, row_data):
    """Append a single row to a sheet and clear cache."""
    try:
        sh = get_spreadsheet()
        ws = sh.worksheet(worksheet_name)
        ws.append_row(row_data)
        clear_cache()
        return True
    except Exception as e:
        st.error(f"Error appending data to {worksheet_name}: {e}")
        return False

def update_sheet_row(worksheet_name, match_col_idx, match_val, new_row_data):
    """Find a row by unique value and update it completely."""
    try:
        sh = get_spreadsheet()
        ws = sh.worksheet(worksheet_name)
        cell = ws.find(str(match_val))
        if cell:
            row_num = cell.row
            # Update entire row range
            cell_list = ws.range(row_num, 1, row_num, len(new_row_data))
            for i, val in enumerate(new_row_data):
                cell_list[i].value = val
            ws.update_cells(cell_list)
            clear_cache()
            return True
        else:
            st.error("Matching record not found in Google Sheet.")
            return False
    except Exception as e:
        st.error(f"Error updating row in {worksheet_name}: {e}")
        return False

def generate_unique_id():
    """Generate short unique transaction ID."""
    return f"TXN-{uuid.uuid4().hex[:8].upper()}"

def get_current_timestamp():
    """Return formatted timestamp."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def initialize_session():
    """Initialize necessary Streamlit session state variables."""
    if "form_data" not in st.session_state:
        st.session_state.form_data = {}
    if "selected_record" not in st.session_state:
        st.session_state.selected_record = None

# Session setup initialize
initialize_session()

# ---------------------------------------------------------
# 4. SIDEBAR NAVIGATION
# ---------------------------------------------------------
st.sidebar.title("📌 Navigation")
page = st.sidebar.radio(
    "Select Option:",
    ["📝 New Entry Form", "📊 View & Search Records", "✏️ Edit / Update Record"]
)

st.sidebar.markdown("---")
st.sidebar.caption("System Status: 🟢 Connected")

# Refresh Button in Sidebar
if st.sidebar.button("🔄 Refresh Data"):
    clear_cache()
    st.sidebar.success("Cache cleared successfully!")
    st.rerun()

# ---------------------------------------------------------
# 5. PAGE 1: NEW ENTRY FORM
# ---------------------------------------------------------
if page == "📝 New Entry Form":
    st.title("📝 New Record Entry")
    st.markdown("Fill out the details below to add a new record to Google Sheets.")
    st.markdown("---")

    with st.form(key="entry_form", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            entry_date = st.date_input("Date", value=date.today())
            name = st.text_input("Full Name*", placeholder="Enter name")
            category = st.selectbox(
                "Category*", 
                ["Select Category", "Sales", "Purchase", "Expense", "Inventory", "Other"]
            )
            amount = st.number_input("Amount (₹)", min_value=0.0, step=10.0, format="%.2f")

        with col2:
            status = st.selectbox("Status", ["Pending", "Approved", "Completed", "Cancelled"])
            assigned_to = st.text_input("Assigned To / Managed By", placeholder="Enter staff name")
            remarks = st.text_area("Remarks / Description", placeholder="Additional notes...", height=108)

        st.markdown("---")
        submit_btn = st.form_submit_button(label="🚀 Save Record", use_container_width=True)

    if submit_btn:
        # Validation
        if not name.strip():
            st.error("⚠️ 'Full Name' is required!")
        elif category == "Select Category":
            st.error("⚠️ Please select a valid Category!")
        else:
            # Prepare row data
            record_id = generate_unique_id()
            timestamp = get_current_timestamp()
            formatted_date = entry_date.strftime("%Y-%m-%d")

            row_data = [
                record_id,
                formatted_date,
                name.strip(),
                category,
                amount,
                status,
                assigned_to.strip(),
                remarks.strip(),
                timestamp
            ]

            with st.spinner("Saving data to Google Sheets..."):
                success = append_to_sheet("MainDB", row_data)

            if success:
                st.success(f"✅ Record saved successfully! Generated ID: **{record_id}**")
                st.balloons()


# ---------------------------------------------------------
# 6. PAGE 2: VIEW & SEARCH RECORDS
# ---------------------------------------------------------
elif page == "📊 View & Search Records":
    st.title("📊 View & Search Records")
    st.markdown("Analyze, filter, and search all logged data from Google Sheets.")
    st.markdown("---")

    df = fetch_sheet_data("MainDB")

    if df.empty:
        st.info("ℹ️ No records found or database is empty.")
    else:
        # Metrics Display
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Records", len(df))
        
        if "Amount" in df.columns:
            total_amount = pd.to_numeric(df["Amount"], errors="coerce").sum()
            m2.metric("Total Amount", f"₹ {total_amount:,.2f}")
        
        if "Status" in df.columns:
            pending_cnt = len(df[df["Status"] == "Pending"])
            completed_cnt = len(df[df["Status"] == "Completed"])
            m3.metric("Pending Tasks", pending_cnt)
            m4.metric("Completed Tasks", completed_cnt)

        st.markdown("---")

        # Filters Area
        with st.expander("🔍 Filters & Search Options", expanded=True):
            f_col1, f_col2, f_col3 = st.columns(3)
            
            with f_col1:
                search_term = st.text_input("Search (Name/ID/Remarks)", "")
            
            with f_col2:
                categories = ["All"] + list(df["Category"].dropna().unique()) if "Category" in df.columns else ["All"]
                selected_cat = st.selectbox("Filter by Category", categories)
            
            with f_col3:
                statuses = ["All"] + list(df["Status"].dropna().unique()) if "Status" in df.columns else ["All"]
                selected_status = st.selectbox("Filter by Status", statuses)

        # Applying Filters
        filtered_df = df.copy()

        if search_term:
            filtered_df = filtered_df[
                filtered_df.astype(str).apply(lambda x: x.str.contains(search_term, case=False)).any(axis=1)
            ]

        if selected_cat != "All" and "Category" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["Category"] == selected_cat]

        if selected_status != "All" and "Status" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["Status"] == selected_status]

        # Display Data Table
        st.subheader(f"Results ({len(filtered_df)} items found)")
        st.dataframe(filtered_df, use_container_width=True, hide_index=True)

        # Download Data Button
        csv_data = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Data as CSV",
            data=csv_data,
            file_name=f"records_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

# ---------------------------------------------------------
# 7. PAGE 3: EDIT / UPDATE RECORD
# ---------------------------------------------------------
elif page == "✏️ Edit / Update Record":
    st.title("✏️ Edit & Update Existing Record")
    st.markdown("Search for a record by Record ID or Name, select it, and update its details.")
    st.markdown("---")

    df = fetch_sheet_data("MainDB")

    if df.empty:
        st.warning("⚠️ Database is empty. No records to edit.")
    else:
        # Check if ID column exists
        id_col = "ID" if "ID" in df.columns else df.columns[0]
        
        # Select Record to Edit
        record_list = df[id_col].astype(str).tolist()
        selected_id = st.selectbox("Select Record ID to Edit:", ["-- Select ID --"] + record_list)

        if selected_id != "-- Select ID --":
            # Fetch record details
            record_row = df[df[id_col].astype(str) == str(selected_id)].iloc[0]

            st.info(f"Editing Details for Record ID: **{selected_id}**")

            with st.form(key="edit_form"):
                col1, col2 = st.columns(2)

                # Parse existing date safely
                try:
                    curr_date = datetime.strptime(str(record_row.get("Date", "")), "%Y-%m-%d").date()
                except Exception:
                    curr_date = date.today()

                with col1:
                    u_date = st.date_input("Date", value=curr_date)
                    u_name = st.text_input("Full Name*", value=str(record_row.get("Name", "")))
                    
                    cat_options = ["Sales", "Purchase", "Expense", "Inventory", "Other"]
                    curr_cat = str(record_row.get("Category", "Other"))
                    cat_idx = cat_options.index(curr_cat) if curr_cat in cat_options else 4
                    u_category = st.selectbox("Category*", cat_options, index=cat_idx)

                    try:
                        curr_amt = float(record_row.get("Amount", 0.0))
                    except ValueError:
                        curr_amt = 0.0
                    u_amount = st.number_input("Amount (₹)", min_value=0.0, value=curr_amt, step=10.0, format="%.2f")

                with col2:
                    status_options = ["Pending", "Approved", "Completed", "Cancelled"]
                    curr_status = str(record_row.get("Status", "Pending"))
                    status_idx = status_options.index(curr_status) if curr_status in status_options else 0
                    u_status = st.selectbox("Status", status_options, index=status_idx)

                    u_assigned = st.text_input("Assigned To", value=str(record_row.get("Assigned To", "")))
                    u_remarks = st.text_area("Remarks / Description", value=str(record_row.get("Remarks", "")), height=108)

                st.markdown("---")
                update_btn = st.form_submit_button(label="🔄 Update Record", use_container_width=True)

            if update_btn:
                if not u_name.strip():
                    st.error("⚠️ 'Full Name' cannot be empty!")
                else:
                    updated_date_str = u_date.strftime("%Y-%m-%d")
                    timestamp = str(record_row.get("Timestamp", get_current_timestamp()))

                    new_row_data = [
                        selected_id,
                        updated_date_str,
                        u_name.strip(),
                        u_category,
                        u_amount,
                        u_status,
                        u_assigned.strip(),
                        u_remarks.strip(),
                        timestamp
                    ]

                    with st.spinner("Updating record in Google Sheets..."):
                        success = update_sheet_row("MainDB", 1, selected_id, new_row_data)

                    if success:
                        st.success(f"✅ Record **{selected_id}** updated successfully!")
                        time.sleep(1)
                        st.rerun()

