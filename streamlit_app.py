"""
Zephyr Streamlit App
Job application tracking interface
"""

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# Page config
st.set_page_config(
    page_title="Zephyr - Job Tracker",
    page_icon="🌪️",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header">🌪️ Zephyr Job Tracker</div>', unsafe_allow_html=True)
st.markdown("---")

# Connect to Google Sheets
@st.cache_resource
def get_connection():
    return st.connection("gsheets", type=GSheetsConnection)

def load_data():
    """Load data from Google Sheets"""
    conn = get_connection()
    df = conn.read(ttl=60)

    if df.empty:
        headers = ["job_id", "title", "company", "location", "posted_date", 
                   "url", "keywords", "scraped_date", "status", "notes"]
        df = pd.DataFrame(columns=headers)

    return df

def save_data(df):
    """Save data to Google Sheets"""
    conn = get_connection()
    conn.update(data=df)
    st.success("✅ Changes saved!")

# Load data
try:
    df = load_data()

    # Sidebar filters
    st.sidebar.header("🔍 Filters")

    status_options = ["All"] + df["status"].unique().tolist() if not df.empty else ["All"]
    selected_status = st.sidebar.selectbox("Status", status_options)

    company_options = ["All"] + sorted(df["company"].unique().tolist()) if not df.empty else ["All"]
    selected_company = st.sidebar.selectbox("Company", company_options)

    location_options = ["All"] + sorted(df["location"].unique().tolist()) if not df.empty else ["All"]
    selected_location = st.sidebar.selectbox("Location", location_options)

    st.sidebar.subheader("📅 Date Range")
    date_filter = st.sidebar.radio("Show jobs from:", 
                                     ["All time", "Last 7 days", "Last 30 days"])

    search_query = st.sidebar.text_input("🔎 Search (title/company)", "")

    # Apply filters
    filtered_df = df.copy()

    if selected_status != "All":
        filtered_df = filtered_df[filtered_df["status"] == selected_status]

    if selected_company != "All":
        filtered_df = filtered_df[filtered_df["company"] == selected_company]

    if selected_location != "All":
        filtered_df = filtered_df[filtered_df["location"] == selected_location]

    if date_filter != "All time" and not filtered_df.empty:
        days = 7 if date_filter == "Last 7 days" else 30
        cutoff_date = datetime.now() - timedelta(days=days)
        filtered_df["scraped_date"] = pd.to_datetime(filtered_df["scraped_date"])
        filtered_df = filtered_df[filtered_df["scraped_date"] >= cutoff_date]

    if search_query:
        mask = (filtered_df["title"].str.contains(search_query, case=False, na=False) | 
                filtered_df["company"].str.contains(search_query, case=False, na=False))
        filtered_df = filtered_df[mask]

    # Metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("📊 Total Jobs", len(df))

    with col2:
        new_count = len(df[df["status"] == "New"]) if not df.empty else 0
        st.metric("🆕 New", new_count)

    with col3:
        applied_count = len(df[df["status"] == "Applied"]) if not df.empty else 0
        st.metric("📤 Applied", applied_count)

    with col4:
        interview_count = len(df[df["status"] == "Interviewing"]) if not df.empty else 0
        st.metric("💼 Interviewing", interview_count)

    st.markdown("---")

    # Main content
    if filtered_df.empty:
        st.info("📭 No jobs found. Adjust your filters or wait for the scraper to run.")
    else:
        st.subheader(f"📋 Job Listings ({len(filtered_df)} results)")

        for idx, row in filtered_df.iterrows():
            with st.expander(f"**{row['title']}** @ {row['company']} - {row['location']}"):
                col1, col2 = st.columns([3, 1])

                with col1:
                    st.markdown(f"**Job ID:** {row['job_id']}")
                    st.markdown(f"**Posted:** {row['posted_date']}")
                    st.markdown(f"**Keywords:** {row['keywords']}")
                    st.markdown(f"**Scraped:** {row['scraped_date']}")
                    st.markdown(f"**URL:** [View Job]({row['url']})")

                with col2:
                    new_status = st.selectbox(
                        "Status",
                        ["New", "Applied", "Interviewing", "Rejected", "Offer", "Declined"],
                        index=["New", "Applied", "Interviewing", "Rejected", "Offer", "Declined"].index(row["status"]),
                        key=f"status_{idx}"
                    )

                    if new_status != row["status"]:
                        df.loc[idx, "status"] = new_status
                        save_data(df)
                        st.rerun()

                notes = st.text_area(
                    "Notes",
                    value=row["notes"] if pd.notna(row["notes"]) else "",
                    key=f"notes_{idx}",
                    height=100
                )

                if notes != row["notes"]:
                    if st.button("💾 Save Note", key=f"save_{idx}"):
                        df.loc[idx, "notes"] = notes
                        save_data(df)
                        st.rerun()

        st.markdown("---")
        st.subheader("⚡ Bulk Actions")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("📥 Export to CSV"):
                csv = filtered_df.to_csv(index=False)
                st.download_button(
                    label="⬇️ Download CSV",
                    data=csv,
                    file_name=f"zephyr_jobs_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )

        with col2:
            if st.button("🔄 Refresh Data"):
                st.cache_resource.clear()
                st.rerun()

except Exception as e:
    st.error(f"❌ Error loading data: {str(e)}")
    st.info("Make sure your Google Sheets connection is configured correctly in `.streamlit/secrets.toml`")
