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


# --- Database Functions ---
@st.cache_resource(ttl=60)
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
    return conn


@st.cache_resource
def get_db_connection():
    return sqlite3.connect('voting_system.db', check_same_thread=False)


# --- Data Fetching ---
@st.cache_data(ttl=10)
def get_vote_results():
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
    conn = get_db_connection()
    return pd.read_sql_query(
        'SELECT register_number, name, registration_time FROM students ORDER BY registration_time DESC',
        conn
    )


# --- UI Components ---
def responsive_column_layout():
    """Returns appropriate column layout based on screen size"""
    if st.session_state.get('is_mobile', False):
        return st.columns(1)
    return st.columns(2)


def load_candidate_image(candidate_name):
    image_path = f"images/{candidate_name.lower()}.jpg"
    if os.path.exists(image_path):
        return Image.open(image_path)
    return None


@st.cache_data
def get_candidate_image(candidate_name):
    return load_candidate_image(candidate_name)


def display_winner(winner):
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


# --- Time Handling ---
def get_voting_time_status():
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


# --- Page Display Functions ---
def show_home_page():
    st.title("🗳️ Online Voting System")
    st.subheader("Messi vs Ronaldo - Who's the GOAT?")

    time_status = get_voting_time_status()
    st.info(f"**Status:** {time_status['message']}", icon="⏰")

    cols = responsive_column_layout()

    with cols[0]:
        display_candidate('Messi', time_status)

    if len(cols) > 1:
        with cols[1]:
            display_candidate('Ronaldo', time_status)
    else:
        display_candidate('Ronaldo', time_status)

    nav_cols = st.columns(3 if not st.session_state.is_mobile else 1)

    with nav_cols[0]:
        if st.button("📝 Student Sign-Up", use_container_width=True):
            st.session_state.page = 'signup'
            st.rerun()

    with nav_cols[1]:
        disabled = not time_status['can_vote']
        if st.button("🗳️ Vote Now", use_container_width=True, disabled=disabled):
            st.session_state.page = 'vote'
            st.rerun()

    with nav_cols[2]:
        if st.button("👨‍💼 Admin Panel", use_container_width=True):
            st.session_state.page = 'admin_login'
            st.rerun()

    if st.session_state.get('winner_declared', False):
        display_winner(st.session_state.declared_winner)


def display_candidate(candidate, time_status):
    image = get_candidate_image(candidate)
    if image:
        st.image(image, caption=candidate, use_column_width=True)
    else:
        color = "#1f77b4" if candidate == "Messi" else "#ff7f0e"
        st.markdown(f"""
        <div style="
            width: 100%;
            height: 200px;
            background: {color};
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 24px;
            font-weight: bold;
            border-radius: 10px;
            margin: 10px 0;
        ">
            {candidate}
        </div>
        """, unsafe_allow_html=True)

    if time_status['status'] == 'ended':
        results = get_vote_results()
        total = sum(results.values())
        if total > 0:
            percent = (results[candidate] / total) * 100
            st.metric(f"{candidate} Votes", f"{results[candidate]} ({percent:.1f}%)")


def show_signup_page():
    st.title("📝 Student Registration")
    if st.button("← Back to Home"):
        st.session_state.page = 'home'
        st.session_state.registration_success = False
        st.rerun()

    st.markdown("---")
    if st.session_state.registration_success:
        st.success("✅ Registration successful!")
        if st.button("Go to Voting Page", use_container_width=True):
            st.session_state.page = 'vote'
            st.session_state.registration_success = False
            st.rerun()
        return

    with st.form("registration_form"):
        st.subheader("Register to Vote")
        register_number = st.text_input("Student Register Number", placeholder="e.g., 2021CS001")
        name = st.text_input("Full Name", placeholder="Enter your full name")
        submitted = st.form_submit_button("Register", use_container_width=True)

        if submitted:
            if not register_number or not name:
                st.error("Please fill in all fields!")
            elif len(register_number.strip()) < 3:
                st.error("Register number must be at least 3 characters long!")
            elif len(name.strip()) < 2:
                st.error("Name must be at least 2 characters long!")
            else:
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute('INSERT INTO students (register_number, name) VALUES (?, ?)',
                                   (register_number, name))
                    conn.commit()
                    st.session_state.current_student = register_number
                    st.session_state.student_logged_in = True
                    st.session_state.registration_success = True
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("This register number is already registered!")


def show_voting_page():
    st.title("🗳️ Voting Page")
    if st.button("← Back to Home"):
        st.session_state.page = 'home'
        st.rerun()

    time_status = get_voting_time_status()
    if time_status['status'] == 'not_started':
        st.warning(f"⏰ {time_status['message']}")
        return
    elif time_status['status'] == 'ended':
        st.error(f"⏰ {time_status['message']}")
        return
    elif time_status['status'] == 'disabled':
        st.warning("⚠️ Voting is currently disabled by admin.")
        return
    elif time_status['status'] == 'active':
        st.success(f"✅ {time_status['message']}")

    if not st.session_state.student_logged_in:
        st.warning("Please verify your registration to vote.")
        register_number = st.text_input("Enter your Register Number to vote:")
        if st.button("Verify and Vote"):
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT register_number FROM students WHERE register_number = ?', (register_number,))
            if cursor.fetchone():
                cursor.execute('SELECT register_number FROM votes WHERE register_number = ?', (register_number,))
                if cursor.fetchone():
                    st.error("You have already voted!")
                else:
                    st.session_state.current_student = register_number
                    st.session_state.student_logged_in = True
                    st.rerun()
            else:
                st.error("Register number not found. Please register first!")
        return

    if has_student_voted(st.session_state.current_student):
        st.success("✅ You have already cast your vote!")
        if st.button("Logout"):
            st.session_state.student_logged_in = False
            st.session_state.current_student = None
            st.session_state.page = 'home'
            st.rerun()
        return

    if time_status['can_vote']:
        st.markdown("---")
        st.subheader("🏆 Messi vs Ronaldo - Cast Your Vote!")
        col1, col2 = responsive_column_layout()
        with col1:
            display_candidate_image('Messi')
            if st.button("⚽ Vote for Messi", use_container_width=True, type="primary"):
                cast_vote(st.session_state.current_student, "Messi")
        with col2:
            display_candidate_image('Ronaldo')
            if st.button("⚽ Vote for Ronaldo", use_container_width=True, type="primary"):
                cast_vote(st.session_state.current_student, "Ronaldo")


def show_admin_login():
    st.title("👨‍💼 Admin Login")
    if st.button("← Back to Home"):
        st.session_state.page = 'home'
        st.rerun()

    st.markdown("---")
    with st.form("admin_login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if username == "admin" and password == "admin123":
                st.session_state.admin_logged_in = True
                st.session_state.page = 'admin_panel'
                st.rerun()
            else:
                st.error("Invalid credentials!")


def show_admin_panel():
    if not st.session_state.admin_logged_in:
        st.session_state.page = 'admin_login'
        st.rerun()
        return

    st.title("👨‍💼 Admin Panel")
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("Logout"):
            st.session_state.admin_logged_in = False
            st.session_state.page = 'home'
            st.rerun()

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        ["📊 Voting Results", "👥 Student Data", "✅ Voted Students", "🏆 Declare Winner", "🔄 Re-Election",
         "⏰ Time Settings"])

    # [Rest of your admin panel tabs implementation]


# --- Helper Functions ---
def has_student_voted(register_number):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT register_number FROM votes WHERE register_number = ?', (register_number,))
    return cursor.fetchone() is not None


def cast_vote(register_number, candidate):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO votes (register_number, candidate) VALUES (?, ?)',
                       (register_number, candidate))
        conn.commit()
        st.success(f"🎉 Thank you for voting for {candidate}!")
        time.sleep(2)
        st.rerun()
        return True
    except Exception as e:
        st.error(f"Voting failed: {str(e)}")
        return False


def display_candidate_image(candidate_name):
    image = get_candidate_image(candidate_name)
    if image:
        st.image(image, caption=candidate_name, use_column_width=True)
    else:
        color = "#1f77b4" if candidate_name == "Messi" else "#ff7f0e"
        st.markdown(f"""
        <div style="
            width: 100%;
            height: 200px;
            background: {color};
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 24px;
            font-weight: bold;
            border-radius: 10px;
            margin: 10px 0;
        ">
            {candidate_name}
        </div>
        """, unsafe_allow_html=True)


# --- Main App ---
def init_session_state():
    """Initialize all required session state variables"""
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
        # Simple mobile detection (you might want to enhance this)
        st.session_state.is_mobile = False


def main():
    init_session_state()
    init_database()

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


if __name__ == "__main__":
    main()