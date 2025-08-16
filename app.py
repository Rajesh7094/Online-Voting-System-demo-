import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import os
from PIL import Image
import time
import pytz
from functools import lru_cache

# Set India timezone
INDIA_TZ = pytz.timezone('Asia/Kolkata')

# Configure page settings
st.set_page_config(
    page_title="Online Voting System",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# --- Cached Database Functions ---
@st.cache_resource(ttl=60)  # Cache for 60 seconds
def init_database():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect('voting_system.db', check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            register_number TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            registration_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            register_number TEXT NOT NULL,
            candidate TEXT NOT NULL,
            vote_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (register_number) REFERENCES students (register_number)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS voting_settings (
            id INTEGER PRIMARY KEY,
            voting_start_time TIMESTAMP,
            voting_end_time TIMESTAMP,
            voting_enabled BOOLEAN DEFAULT 1,
            auto_declare_winner BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    return conn  # Return persistent connection


# Get database connection with caching
@st.cache_resource
def get_db_connection():
    return sqlite3.connect('voting_system.db', check_same_thread=False)


# --- Cached Data Fetching ---
@st.cache_data(ttl=10)  # Refresh every 10 seconds
def get_vote_results():
    """Get voting results with caching"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT candidate, COUNT(*) as votes FROM votes GROUP BY candidate')
    results = cursor.fetchall()

    vote_dict = {'Messi': 0, 'Ronaldo': 0}
    for candidate, votes in results:
        vote_dict[candidate] = votes
    return vote_dict


@st.cache_data(ttl=30)
def get_all_students():
    """Get all registered students with caching"""
    conn = get_db_connection()
    return pd.read_sql_query(
        'SELECT register_number, name, registration_time FROM students ORDER BY registration_time DESC',
        conn
    )


# --- Improved UI Components ---
def responsive_column_layout():
    """Returns appropriate column layout based on screen size"""
    if st.session_state.get('is_mobile', False):
        return st.columns(1)  # Single column for mobile
    return st.columns(2)  # Two columns for desktop


def load_candidate_image(candidate_name):
    """Improved image loading with caching"""
    image_path = f"images/{candidate_name.lower()}.jpg"
    if os.path.exists(image_path):
        return Image.open(image_path)
    return None


@st.cache_data
def get_candidate_image(candidate_name):
    """Cached version of image loading"""
    return load_candidate_image(candidate_name)


def display_winner(winner):
    """Enhanced winner display with image"""
    st.markdown("---")

    if winner == "Tie":
        st.success("🏆 IT'S A TIE! 🏆")
    else:
        col1, col2 = responsive_column_layout()

        with col1:
            st.success(f"🏆 WINNER: {winner} 🏆")
            image = get_candidate_image(winner)
            if image:
                st.image(image, width=300)

        with col2:
            results = get_vote_results()
            total = sum(results.values())

            if winner == "Messi":
                messi_percent = (results['Messi'] / total) * 100
                st.metric("Messi", f"{results['Messi']} votes", f"{messi_percent:.1f}%")
            else:
                ronaldo_percent = (results['Ronaldo'] / total) * 100
                st.metric("Ronaldo", f"{results['Ronaldo']} votes", f"{ronaldo_percent:.1f}%")


# --- Modified Time Handling ---
def get_voting_time_status():
    """Improved time status with better caching"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM voting_settings ORDER BY id DESC LIMIT 1')
    result = cursor.fetchone()

    if not result:
        return {
            'status': 'no_schedule',
            'message': 'No voting schedule set',
            'can_vote': False,
            'time_remaining': None
        }

    settings = {
        'voting_enabled': bool(result[3]),
        'start_time': result[1],
        'end_time': result[2]
    }

    current_time = datetime.now(INDIA_TZ)

    if not settings['voting_enabled']:
        return {
            'status': 'disabled',
            'message': 'Voting is disabled',
            'can_vote': False,
            'time_remaining': None
        }

    if not settings['start_time'] or not settings['end_time']:
        return {
            'status': 'enabled',
            'message': 'Voting is enabled without time limits',
            'can_vote': True,
            'time_remaining': None
        }

    start_time = INDIA_TZ.localize(datetime.fromisoformat(settings['start_time']))
    end_time = INDIA_TZ.localize(datetime.fromisoformat(settings['end_time']))

    if current_time < start_time:
        return {
            'status': 'not_started',
            'message': f'Voting will start at {start_time.strftime("%Y-%m-%d %H:%M:%S")}',
            'can_vote': False,
            'time_remaining': None
        }
    elif current_time > end_time:
        return {
            'status': 'ended',
            'message': f'Voting ended at {end_time.strftime("%Y-%m-%d %H:%M:%S")}',
            'can_vote': False,
            'time_remaining': None
        }
    else:
        time_remaining = end_time - current_time
        return {
            'status': 'active',
            'message': f'Voting is active until {end_time.strftime("%Y-%m-%d %H:%M:%S")}',
            'can_vote': True,
            'time_remaining': time_remaining
        }


# --- Mobile Detection ---
def check_mobile():
    """Simple mobile device detection using user agent"""
    user_agent = st.query_params.get("user_agent", "")
    if isinstance(user_agent, list):
        user_agent = user_agent[0] if user_agent else ""
    return any(m in user_agent.lower() for m in ["mobile", "android", "iphone"])


# --- Session State Initialization ---
def init_session_state():
    """Initialize session state variables"""
    if 'page' not in st.session_state:
        st.session_state.page = 'home'
    if 'admin_logged_in' not in st.session_state:
        st.session_state.admin_logged_in = False
    if 'student_logged_in' not in st.session_state:
        st.session_state.student_logged_in = False
    if 'current_student' not in st.session_state:
        st.session_state.current_student = None
    if 'winner_declared' not in st.session_state:
        st.session_state.winner_declared = False
    if 'declared_winner' not in st.session_state:
        st.session_state.declared_winner = None
    if 'registration_success' not in st.session_state:
        st.session_state.registration_success = False
    if 'auto_declared' not in st.session_state:
        st.session_state.auto_declared = False
    if 'auto_declaration_processed' not in st.session_state:
        st.session_state.auto_declaration_processed = False
    if 'is_mobile' not in st.session_state:
        st.session_state.is_mobile = check_mobile()


# --- Main App Structure ---
def main():
    # Initialize session state
    init_session_state()

    # Initialize database
    init_database()

    # Route to appropriate page
    if st.session_state.page == 'home':
        show_home_page()
    elif st.session_state.page == 'signup':
        show_signup_page()
    elif st.session_state.page == 'vote':
        show_voting_page()
    elif st.session_state.page == 'admin_login':
        show_admin_login()
    elif st.session_state.page == 'admin_panel':
        show_admin_panel()


# [Rest of your page display functions (show_home_page, show_signup_page, etc.) remain the same]

if __name__ == "__main__":
    main()