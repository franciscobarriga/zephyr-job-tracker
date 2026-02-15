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
    key = st.secrets["SUPABASE_ANON_KEY"]
    return create_client(url, key)

supabase: Client = init_supabase()

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .subtitle {
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .stat-number {
        font-size: 2.5rem;
        font-weight: bold;
    }
    .stat-label {
        font-size: 1rem;
        opacity: 0.9;
    }
</style>
""", unsafe_allow_html=True)

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
                        
                        # Create profile entry
                        if response.user:
                            supabase.table("profiles").insert({
                                "id": response.user.id,
                                "username": username,
                                "full_name": full_name
                            }).execute()

                        st.success("✅ Account created! Please check your email to verify, then login.")
                    except Exception as e:
                        st.error(f"❌ Signup failed: {str(e)}")

def main_app():
    """Main application UI"""
    user = st.session_state.get("user")
    
    if not user:
        st.error("Session expired. Please login again.")
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()
        return

    # Sidebar
    with st.sidebar:
        st.markdown(f"### 👤 {user.email}")
        
        if st.button("🚪 Logout"):
            supabase.auth.sign_out()
            st.session_state.clear()
            st.rerun()

        st.markdown("---")
        page = st.radio("Navigation", ["📊 Dashboard", "🔍 Search Configs", "💼 Applications"])

    # Main content
    if page == "📊 Dashboard":
        show_dashboard(user.id)
    elif page == "🔍 Search Configs":
        show_search_configs(user.id)
    elif page == "💼 Applications":
        show_applications(user.id)

def show_dashboard(user_id):
    """Dashboard with stats and recent activity"""
    st.markdown('<div class="main-header">🌪️ Zephyr Dashboard</div>', unsafe_allow_html=True)

    # Fetch stats
    try:
        jobs = supabase.table("jobs").select("*").eq("user_id", user_id).execute()
        searches = supabase.table("search_configs").select("*").eq("user_id", user_id).execute()
        
        jobs_df = pd.DataFrame(jobs.data) if jobs.data else pd.DataFrame()
        
        # Stats cards
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{len(jobs_df)}</div>
                <div class="stat-label">Total Applications</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            applied = len(jobs_df[jobs_df["status"] == "Applied"]) if not jobs_df.empty else 0
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{applied}</div>
                <div class="stat-label">Applied</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            active_searches = len([s for s in searches.data if s.get("is_active", False)])
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{active_searches}</div>
                <div class="stat-label">Active Searches</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            recent = len(jobs_df[jobs_df["created_at"] >= week_ago]) if not jobs_df.empty else 0
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{recent}</div>
                <div class="stat-label">This Week</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # Recent applications
        if not jobs_df.empty:
            st.subheader("📋 Recent Applications")
            recent_jobs = jobs_df.sort_values("created_at", ascending=False).head(10)
            st.dataframe(recent_jobs[["title", "company", "status", "created_at"]], use_container_width=True)
        else:
            st.info("No applications yet. Start by creating a search config!")

    except Exception as e:
        st.error(f"Error loading dashboard: {str(e)}")

def show_search_configs(user_id):
    """Manage search configurations"""
    st.header("🔍 Search Configurations")

    # Add new search config
    with st.expander("➕ Add New Search", expanded=False):
        with st.form("new_search"):
            keywords = st.text_input("Keywords (e.g., 'Data Analyst')")
            location = st.text_input("Location")
            is_remote = st.checkbox("Remote only")
            experience = st.selectbox("Experience Level", ["", "Entry level", "Mid-Senior level", "Director", "Executive"])
            pages = st.number_input("Pages to scrape", min_value=1, max_value=10, value=2)
            
            if st.form_submit_button("💾 Save Search"):
                try:
                    supabase.table("search_configs").insert({
                        "user_id": user_id,
                        "keywords": keywords,
                        "location": location,
                        "is_remote": is_remote,
                        "experience_level": experience if experience else None,
                        "pages": pages,
                        "is_active": True
                    }).execute()
                    st.success("✅ Search config saved!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {str(e)}")

    # Display existing configs
    try:
        configs = supabase.table("search_configs").select("*").eq("user_id", user_id).execute()
        
        if configs.data:
            for config in configs.data:
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    status = "🟢 Active" if config["is_active"] else "🔴 Inactive"
                    st.markdown(f"**{config['keywords']}** - {config['location']} {status}")
                
                with col2:
                    if st.button("Toggle", key=f"toggle_{config['id']}"):
                        supabase.table("search_configs").update({
                            "is_active": not config["is_active"]
                        }).eq("id", config["id"]).execute()
                        st.rerun()
                
                with col3:
                    if st.button("🗑️ Delete", key=f"delete_{config['id']}"):
                        supabase.table("search_configs").delete().eq("id", config["id"]).execute()
                        st.rerun()
        else:
            st.info("No search configs yet. Add one above!")

    except Exception as e:
        st.error(f"Error loading configs: {str(e)}")

def show_applications(user_id):
    """View and manage job applications"""
    st.header("💼 Job Applications")

    try:
        jobs = supabase.table("jobs").select("*").eq("user_id", user_id).execute()
        
        if jobs.data:
            df = pd.DataFrame(jobs.data)
            
            # Filters
            col1, col2 = st.columns(2)
            with col1:
                status_filter = st.multiselect("Filter by Status", df["status"].unique())
            with col2:
                company_filter = st.text_input("Filter by Company")

            # Apply filters
            filtered_df = df.copy()
            if status_filter:
                filtered_df = filtered_df[filtered_df["status"].isin(status_filter)]
            if company_filter:
                filtered_df = filtered_df[filtered_df["company"].str.contains(company_filter, case=False, na=False)]

            st.dataframe(filtered_df, use_container_width=True)
            
            # Download button
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"zephyr_applications_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info("No applications yet. The scraper will populate this when it runs!")

    except Exception as e:
        st.error(f"Error loading applications: {str(e)}")

# Main app logic
if "user" not in st.session_state:
    login_page()
else:
    main_app()

