"""
Zephyr Multi-User Streamlit App - Supabase Version
Job tracking with authentication and personalized searches
"""

import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta

# Page config
st.set_page_config(
    page_title="Zephyr - Job Tracker",
    page_icon="🌪️",
    layout="wide"
)

# Initialize Supabase
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_ANON_KEY"]  # Frontend uses anon key
    return create_client(url, key)

supabase: Client = init_supabase()

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 1rem;
    }
    .subtitle {
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# Authentication Functions
def login_page():
    """Login page UI"""
    st.markdown('<div class="main-header">🌪️ Zephyr</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Automated Job Application Tracker</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")

            if submit:
                try:
                    response = supabase.auth.sign_in_with_password({
                        "email": email,
                        "password": password
                    })
                    st.session_state["user"] = response.user
                    st.session_state["session"] = response.session
                    st.success("✅ Logged in successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Login failed: {str(e)}")

    with tab2:
        with st.form("signup_form"):
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Password (min 6 chars)", type="password", key="signup_password")
            username = st.text_input("Username")
            full_name = st.text_input("Full Name")
            submit = st.form_submit_button("Sign Up")

            if submit:
                if len(password) < 6:
                    st.error("Password must be at least 6 characters")
                elif not username:
                    st.error("Username is required")
                else:
                    try:
                        # Sign up user
                        response = supabase.auth.sign_up({
                            "email": email,
                            "password": password,
                            "options": {
                                "data": {
                                    "username": username,
                                    "full_name": full_name
                                }
                            }
                        })

                        st.success("✅ Account created! Please check your email to verify, then login.")
                    except Exception as e:
                        st.error(f"❌ Signup failed: {str(e)}")

def main_app():
    """Main application UI (after login)"""
    user = st.session_state["user"]
    user_id = user.id

    # Header
    col1, col2, col3 = st.columns([2, 6, 2])
    with col1:
        st.markdown("## 🌪️ Zephyr")
    with col2:
        st.markdown(f"### Welcome, {user.email.split('@')[0]}!")
    with col3:
        if st.button("🚪 Logout"):
            supabase.auth.sign_out()
            st.session_state.clear()
            st.rerun()

    st.markdown("---")

    # Sidebar: Manage Search Configs
    with st.sidebar:
        st.header("⚙️ Job Searches")

        # Add new search
        with st.expander("➕ Add New Search", expanded=False):
            with st.form("add_search"):
                keywords = st.text_input("Keywords*", placeholder="e.g., data engineer")
                location = st.text_input("Location*", placeholder="e.g., Madrid")
                is_remote = st.checkbox("Remote only")
                experience = st.selectbox("Experience Level", 
                                         ["Any", "Entry level", "Associate", "Mid-Senior level", "Director", "Executive"])
                pages = st.slider("Pages to scrape", 1, 5, 2)

                submit = st.form_submit_button("💾 Save Search")

                if submit:
                    if not keywords or not location:
                        st.error("Keywords and location are required")
                    else:
                        try:
                            supabase.table("search_configs").insert({
                                "user_id": user_id,
                                "keywords": keywords,
                                "location": location,
                                "is_remote": is_remote,
                                "experience_level": experience if experience != "Any" else None,
                                "pages": pages,
                                "is_active": True
                            }).execute()
                            st.success("✅ Search saved! Jobs will appear within 6 hours.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {str(e)}")

        st.markdown("---")

        # Show existing searches
        st.subheader("Your Active Searches")
        try:
            configs = supabase.table("search_configs")\
                             .select("*")\
                             .eq("user_id", user_id)\
                             .eq("is_active", True)\
                             .order("created_at", desc=True)\
                             .execute()

            if configs.data:
                for config in configs.data:
                    with st.container():
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.markdown(f"**{config['keywords']}**")
                            st.caption(f"📍 {config['location']}")
                        with col2:
                            if st.button("🗑️", key=f"del_{config['id']}"):
                                supabase.table("search_configs")\
                                       .update({"is_active": False})\
                                       .eq("id", config["id"])\
                                       .execute()
                                st.rerun()
                        st.markdown("---")
            else:
                st.info("No active searches yet. Add one above!")
        except Exception as e:
            st.error(f"Error loading searches: {str(e)}")

    # Main content: Jobs
    st.header("📋 Your Job Listings")

    # Filters
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        status_filter = st.selectbox("Status", ["All", "New", "Applied", "Interviewing", "Rejected", "Offer"])

    with col2:
        try:
            companies = supabase.table("jobs")\
                               .select("company")\
                               .eq("user_id", user_id)\
                               .execute()
            unique_companies = sorted(list(set([j["company"] for j in companies.data if j["company"]])))
            company_filter = st.selectbox("Company", ["All"] + unique_companies)
        except:
            company_filter = "All"

    with col3:
        date_filter = st.selectbox("Date Range", ["All time", "Last 7 days", "Last 30 days"])

    with col4:
        search_query = st.text_input("🔎 Search", placeholder="Title or company...")

    # Fetch jobs
    try:
        query = supabase.table("jobs").select("*").eq("user_id", user_id)

        if status_filter != "All":
            query = query.eq("status", status_filter)

        if company_filter != "All":
            query = query.eq("company", company_filter)

        jobs_response = query.order("scraped_date", desc=True).execute()
        jobs = jobs_response.data

        # Apply date filter
        if date_filter != "All time" and jobs:
            days = 7 if date_filter == "Last 7 days" else 30
            cutoff = datetime.now() - timedelta(days=days)
            jobs = [j for j in jobs if datetime.fromisoformat(j["scraped_date"].replace("Z", "+00:00")) >= cutoff]

        # Apply search filter
        if search_query and jobs:
            jobs = [j for j in jobs if 
                   search_query.lower() in j["title"].lower() or 
                   search_query.lower() in j["company"].lower()]

        # Metrics
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            total = len(supabase.table("jobs").select("id").eq("user_id", user_id).execute().data)
            st.metric("📊 Total Jobs", total)

        with col2:
            new = len([j for j in jobs if j["status"] == "New"])
            st.metric("🆕 New", new)

        with col3:
            applied = len([j for j in jobs if j["status"] == "Applied"])
            st.metric("📤 Applied", applied)

        with col4:
            interviewing = len([j for j in jobs if j["status"] == "Interviewing"])
            st.metric("💼 Interviewing", interviewing)

        st.markdown("---")

        # Display jobs
        if not jobs:
            st.info("📭 No jobs found. Try adjusting your filters or add a new job search!")
        else:
            st.subheader(f"Showing {len(jobs)} jobs")

            for job in jobs:
                with st.expander(f"**{job['title']}** @ {job['company']} - {job['location']}"):
                    col1, col2 = st.columns([3, 1])

                    with col1:
                        st.markdown(f"**Job ID:** {job['job_id']}")
                        st.markdown(f"**Posted:** {job['posted_date'] or 'N/A'}")
                        st.markdown(f"**Keywords:** {job['keywords']}")
                        st.markdown(f"**Scraped:** {job['scraped_date']}")
                        st.markdown(f"**URL:** [View Job]({job['url']})")

                    with col2:
                        new_status = st.selectbox(
                            "Status",
                            ["New", "Applied", "Interviewing", "Rejected", "Offer", "Declined"],
                            index=["New", "Applied", "Interviewing", "Rejected", "Offer", "Declined"].index(job["status"]),
                            key=f"status_{job['id']}"
                        )

                        if new_status != job["status"]:
                            supabase.table("jobs")\
                                   .update({"status": new_status})\
                                   .eq("id", job["id"])\
                                   .execute()
                            st.success("✅ Updated!")
                            st.rerun()

                    notes = st.text_area(
                        "Notes",
                        value=job["notes"] or "",
                        key=f"notes_{job['id']}",
                        height=100
                    )

                    if notes != (job["notes"] or ""):
                        if st.button("💾 Save Note", key=f"save_{job['id']}"):
                            supabase.table("jobs")\
                                   .update({"notes": notes})\
                                   .eq("id", job["id"])\
                                   .execute()
                            st.success("✅ Note saved!")
                            st.rerun()

            # Export
            st.markdown("---")
            if st.button("📥 Export to CSV"):
                df = pd.DataFrame(jobs)
                csv = df.to_csv(index=False)
                st.download_button(
                    label="⬇️ Download CSV",
                    data=csv,
                    file_name=f"zephyr_jobs_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )

    except Exception as e:
        st.error(f"❌ Error loading jobs: {str(e)}")

# Main app logic
if "user" not in st.session_state:
    login_page()
else:
    main_app()
