import streamlit as st
import sqlite3
import pandas as pd
import hashlib
from datetime import datetime, timedelta
import plotly.express as px
import os
from PIL import Image
import time
import threading
import pytz

# Set timezone to India (Chennai)
INDIA_TZ = pytz.timezone('Asia/Kolkata')  # Chennai uses Kolkata timezone


def get_india_time():
    """Get current time in India timezone"""
    return datetime.now(INDIA_TZ)


def format_india_time(dt_str):
    """Format datetime string to India timezone"""
    if not dt_str:
        return "Not Set"
    try:
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is None:
            dt = INDIA_TZ.localize(dt)
        else:
            dt = dt.astimezone(INDIA_TZ)
        return dt.strftime("%Y-%m-%d %H:%M:%S IST")
    except:
        return "Invalid Time"


# Database initialization
def init_database():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect('voting_system.db')
    cursor = conn.cursor()

    # Create students table with proper primary key constraint
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            register_number TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            registration_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create votes table with proper foreign key
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            register_number TEXT NOT NULL,
            candidate TEXT NOT NULL,
            vote_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (register_number) REFERENCES students (register_number)
        )
    ''')

    # Create voting_settings table
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
    conn.close()


# Student registration functions
def register_student(register_number, name):
    """Register a new student with proper error handling"""
    try:
        conn = sqlite3.connect('voting_system.db')
        cursor = conn.cursor()

        # Clean the inputs
        register_number = register_number.strip().upper()
        name = name.strip().title()

        # Try to insert - this will fail if register_number already exists
        cursor.execute('INSERT INTO students (register_number, name) VALUES (?, ?)',
                       (register_number, name))
        conn.commit()
        conn.close()
        return True, "Registration successful!"
    except sqlite3.IntegrityError as e:
        conn.close()
        return False, "This register number is already registered!"
    except Exception as e:
        if conn:
            conn.close()
        return False, f"Registration failed: {str(e)}"


def is_student_registered(register_number):
    """Check if student is already registered"""
    conn = sqlite3.connect('voting_system.db')
    cursor = conn.cursor()
    cursor.execute('SELECT register_number FROM students WHERE register_number = ?', (register_number.strip().upper(),))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def has_student_voted(register_number):
    """Check if student has already voted"""
    conn = sqlite3.connect('voting_system.db')
    cursor = conn.cursor()
    cursor.execute('SELECT register_number FROM votes WHERE register_number = ?', (register_number.strip().upper(),))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def cast_vote(register_number, candidate):
    """Cast a vote for a candidate"""
    try:
        conn = sqlite3.connect('voting_system.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO votes (register_number, candidate) VALUES (?, ?)',
                       (register_number.strip().upper(), candidate))
        conn.commit()
        conn.close()
        return True
    except:
        return False


def get_all_students():
    """Get all registered students"""
    conn = sqlite3.connect('voting_system.db')
    df = pd.read_sql_query(
        'SELECT register_number, name, registration_time FROM students ORDER BY registration_time DESC', conn)
    conn.close()
    return df


def delete_all_students():
    """Delete all students and their votes"""
    try:
        conn = sqlite3.connect('voting_system.db')
        cursor = conn.cursor()
        # Delete votes first (foreign key constraint)
        cursor.execute('DELETE FROM votes')
        # Then delete students
        cursor.execute('DELETE FROM students')
        conn.commit()
        conn.close()
        return True, "All student records and votes deleted successfully!"
    except Exception as e:
        return False, f"Error deleting students: {str(e)}"


def get_student_count():
    """Get total number of registered students"""
    conn = sqlite3.connect('voting_system.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM students')
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_vote_results():
    """Get voting results"""
    conn = sqlite3.connect('voting_system.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT candidate, COUNT(*) as votes 
        FROM votes 
        GROUP BY candidate
    ''')
    results = cursor.fetchall()
    conn.close()

    # Convert to dictionary for easier handling
    vote_dict = {'Messi': 0, 'Ronaldo': 0}
    for candidate, votes in results:
        vote_dict[candidate] = votes

    return vote_dict


def get_total_votes():
    """Get total number of votes cast"""
    conn = sqlite3.connect('voting_system.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM votes')
    total = cursor.fetchone()[0]
    conn.close()
    return total


# Voting time management functions (updated for India timezone)
def set_voting_time(start_time, end_time, auto_declare=True):
    """Set voting start and end time in India timezone"""
    try:
        conn = sqlite3.connect('voting_system.db')
        cursor = conn.cursor()

        # Ensure times are in India timezone
        if start_time and not isinstance(start_time, str):
            if start_time.tzinfo is None:
                start_time = INDIA_TZ.localize(start_time)
            else:
                start_time = start_time.astimezone(INDIA_TZ)
            start_time = start_time.isoformat()

        if end_time and not isinstance(end_time, str):
            if end_time.tzinfo is None:
                end_time = INDIA_TZ.localize(end_time)
            else:
                end_time = end_time.astimezone(INDIA_TZ)
            end_time = end_time.isoformat()

        # Delete existing settings
        cursor.execute('DELETE FROM voting_settings')

        # Insert new settings
        cursor.execute('''
            INSERT INTO voting_settings (voting_start_time, voting_end_time, auto_declare_winner, voting_enabled)
            VALUES (?, ?, ?, 1)
        ''', (start_time, end_time, auto_declare))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error setting voting time: {e}")
        return False


def get_voting_settings():
    """Get current voting settings"""
    conn = sqlite3.connect('voting_system.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM voting_settings ORDER BY id DESC LIMIT 1')
    result = cursor.fetchone()
    conn.close()

    if result:
        return {
            'id': result[0],
            'start_time': result[1],
            'end_time': result[2],
            'voting_enabled': result[3],
            'auto_declare_winner': result[4],
            'created_at': result[5],
            'updated_at': result[6]
        }
    return None


def is_voting_active():
    """Check if voting is currently active based on time settings"""
    settings = get_voting_settings()
    if not settings or not settings['voting_enabled']:
        return False

    current_time = get_india_time()

    if settings['start_time'] and settings['end_time']:
        start_time = datetime.fromisoformat(settings['start_time'])
        end_time = datetime.fromisoformat(settings['end_time'])

        # Ensure timezone awareness
        if start_time.tzinfo is None:
            start_time = INDIA_TZ.localize(start_time)
        if end_time.tzinfo is None:
            end_time = INDIA_TZ.localize(end_time)

        return start_time <= current_time <= end_time

    return settings['voting_enabled']


def get_voting_time_status():
    """Get detailed voting time status"""
    settings = get_voting_settings()
    current_time = get_india_time()

    if not settings:
        return {
            'status': 'no_schedule',
            'message': 'No voting schedule set',
            'can_vote': False,
            'time_remaining': None
        }

    if not settings['voting_enabled']:
        return {
            'status': 'disabled',
            'message': 'Voting is disabled',
            'can_vote': False,
            'time_remaining': None
        }

    if not settings['start_time'] or not settings['end_time']:
        return {
            'status': 'enabled' if settings['voting_enabled'] else 'disabled',
            'message': 'Voting is enabled' if settings['voting_enabled'] else 'Voting is disabled',
            'can_vote': settings['voting_enabled'],
            'time_remaining': None
        }

    start_time = datetime.fromisoformat(settings['start_time'])
    end_time = datetime.fromisoformat(settings['end_time'])

    # Ensure timezone awareness
    if start_time.tzinfo is None:
        start_time = INDIA_TZ.localize(start_time)
    if end_time.tzinfo is None:
        end_time = INDIA_TZ.localize(end_time)

    if current_time < start_time:
        return {
            'status': 'not_started',
            'message': f'Voting will start at {start_time.strftime("%Y-%m-%d %H:%M:%S IST")}',
            'can_vote': False,
            'time_remaining': None,
            'start_time': start_time
        }
    elif current_time > end_time:
        return {
            'status': 'ended',
            'message': f'Voting ended at {end_time.strftime("%Y-%m-%d %H:%M:%S IST")}',
            'can_vote': False,
            'time_remaining': None,
            'end_time': end_time
        }
    else:
        time_remaining = end_time - current_time
        return {
            'status': 'active',
            'message': f'Voting is active until {end_time.strftime("%Y-%m-%d %H:%M:%S IST")}',
            'can_vote': True,
            'time_remaining': time_remaining,
            'end_time': end_time
        }


def auto_declare_winner_if_time_ended():
    """Automatically declare winner if voting time has ended"""
    settings = get_voting_settings()
    if not settings or not settings['auto_declare_winner']:
        return False

    time_status = get_voting_time_status()

    # Check if voting has ended and winner hasn't been declared yet
    if (time_status['status'] == 'ended' and
            not st.session_state.get('winner_declared', False) and
            not st.session_state.get('auto_declaration_processed', False)):

        results = get_vote_results()
        total_votes = sum(results.values())

        if total_votes > 0:
            if results['Messi'] > results['Ronaldo']:
                winner = "Messi"
            elif results['Ronaldo'] > results['Messi']:
                winner = "Ronaldo"
            else:
                winner = "Tie"

            st.session_state.winner_declared = True
            st.session_state.declared_winner = winner
            st.session_state.auto_declared = True
            st.session_state.auto_declaration_processed = True
            return True

    return False


def format_time_remaining(time_delta):
    """Format time remaining in a readable format"""
    if time_delta.days > 0:
        return f"{time_delta.days} days, {time_delta.seconds // 3600} hours, {(time_delta.seconds % 3600) // 60} minutes"
    elif time_delta.seconds >= 3600:
        hours = time_delta.seconds // 3600
        minutes = (time_delta.seconds % 3600) // 60
        return f"{hours} hours, {minutes} minutes"
    elif time_delta.seconds >= 60:
        minutes = time_delta.seconds // 60
        seconds = time_delta.seconds % 60
        return f"{minutes} minutes, {seconds} seconds"
    else:
        return f"{time_delta.seconds} seconds"


def load_candidate_image(candidate_name):
    """Load candidate image from local files"""
    # Define image paths
    image_paths = {
        'messi': ['images/messi.jpg', 'images/messi.jpeg', 'images/messi.png', 'messi.jpg', 'messi.jpeg', 'messi.png'],
        'ronaldo': ['images/ronaldo.jpg', 'images/ronaldo.jpeg', 'images/ronaldo.png', 'ronaldo.jpg', 'ronaldo.jpeg',
                    'ronaldo.png']
    }

    candidate_key = candidate_name.lower()
    if candidate_key in image_paths:
        # Try to find the image in various paths
        for path in image_paths[candidate_key]:
            if os.path.exists(path):
                try:
                    image = Image.open(path)
                    return image
                except Exception as e:
                    continue

    # Return None if no image found
    return None


def display_candidate_image(candidate_name, caption, width=200):
    """Display candidate image with fallback to placeholder"""
    image = load_candidate_image(candidate_name)

    if image is not None:
        st.image(image, caption=caption, width=width)
    else:
        # Fallback to a colored placeholder
        if candidate_name.lower() == 'messi':
            st.markdown(f"""
            <div style="
                width: {width}px; 
                height: {int(width * 1.2)}px; 
                background: linear-gradient(45deg, #1f77b4, #4CAF50);
                display: flex; 
                align-items: center; 
                justify-content: center; 
                color: white; 
                font-size: 18px; 
                font-weight: bold;
                border-radius: 10px;
                margin: 10px 0;
            ">
                {caption}
            </div>
            """, unsafe_allow_html=True)
        else:  # Ronaldo
            st.markdown(f"""
            <div style="
                width: {width}px; 
                height: {int(width * 1.2)}px; 
                background: linear-gradient(45deg, #ff7f0e, #FF5722);
                display: flex; 
                align-items: center; 
                justify-content: center; 
                color: white; 
                font-size: 18px; 
                font-weight: bold;
                border-radius: 10px;
                margin: 10px 0;
            ">
                {caption}
            </div>
            """, unsafe_allow_html=True)


def get_students_who_voted():
    """Get detailed information about students who have voted"""
    conn = sqlite3.connect('voting_system.db')
    query = '''
        SELECT s.register_number, s.name, v.candidate, v.vote_time
        FROM students s
        JOIN votes v ON s.register_number = v.register_number
        ORDER BY v.vote_time DESC
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


def reset_election():
    """Reset the entire election - clear all votes and winner declarations"""
    try:
        conn = sqlite3.connect('voting_system.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM votes')
        conn.commit()
        conn.close()
        return True
    except:
        return False


# Initialize session state
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

    # Check for auto winner declaration on every page load
    auto_declare_winner_if_time_ended()


# Page navigation functions
def show_home_page():
    """Display home page with navigation options"""
    st.title("🗳️ Online Voting System")
    st.subheader("Messi vs Ronaldo - Who's the GOAT?")

    # Display current India time
    current_time = get_india_time()
    st.info(f"🕐 Current Time (India): {current_time.strftime('%Y-%m-%d %H:%M:%S IST')}")

    # Check and display voting status
    time_status = get_voting_time_status()

    # Display voting status banner
    if time_status['status'] == 'not_started':
        st.info(f"⏰ {time_status['message']}")
    elif time_status['status'] == 'active':
        st.success(f"✅ {time_status['message']}")
        if time_status['time_remaining']:
            remaining = format_time_remaining(time_status['time_remaining'])
            st.warning(f"⏳ Time remaining: {remaining}")
    elif time_status['status'] == 'ended':
        st.error(f"⏰ {time_status['message']}")
    elif time_status['status'] == 'disabled':
        st.warning("⚠️ Voting is currently disabled")

    col1, col2 = st.columns(2)

    with col1:
        display_candidate_image('messi', "Lionel Messi", 200)

    with col2:
        display_candidate_image('ronaldo', "Cristiano Ronaldo", 200)

    st.markdown("---")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📝 Student Sign-Up", use_container_width=True):
            st.session_state.page = 'signup'
            st.rerun()

    with col2:
        vote_button_disabled = not time_status['can_vote']
        if st.button("🗳️ Vote Now", use_container_width=True, disabled=vote_button_disabled):
            st.session_state.page = 'vote'
            st.rerun()

    with col3:
        if st.button("👨‍💼 Admin Panel", use_container_width=True):
            st.session_state.page = 'admin_login'
            st.rerun()

    # Show results if winner is declared
    if st.session_state.winner_declared and st.session_state.declared_winner:
        st.markdown("---")

        # Check if it was auto-declared
        declaration_type = "🤖 AUTOMATICALLY DECLARED" if st.session_state.get('auto_declared',
                                                                              False) else "👨‍💼 ADMIN DECLARED"

        if st.session_state.declared_winner == "Tie":
            st.info(f"🤝 **{declaration_type}: IT'S A TIE!**")
        else:
            st.success(f"🏆 **{declaration_type} WINNER: {st.session_state.declared_winner}**")

        # Show vote breakdown
        results = get_vote_results()
        total = sum(results.values())
        if total > 0:
            messi_percent = (results['Messi'] / total) * 100
            ronaldo_percent = (results['Ronaldo'] / total) * 100

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Messi", f"{results['Messi']} votes", f"{messi_percent:.1f}%")
            with col2:
                st.metric("Ronaldo", f"{results['Ronaldo']} votes", f"{ronaldo_percent:.1f}%")
            with col3:
                st.metric("Total Votes", total)

    # Auto-refresh page every 30 seconds when voting is active
    if time_status['status'] == 'active' and time_status['time_remaining']:
        time.sleep(1)  # Small delay for smoother updates
        st.rerun()


def show_signup_page():
    """Display student registration page"""
    st.title("📝 Student Registration")

    if st.button("← Back to Home"):
        st.session_state.page = 'home'
        st.session_state.registration_success = False
        st.rerun()

    st.markdown("---")

    # Show success message and navigation button if registration was successful
    if st.session_state.registration_success:
        st.success("✅ Registration successful!")
        st.info("You can now proceed to vote. Click the button below:")
        if st.button("Go to Voting Page", use_container_width=True):
            st.session_state.page = 'vote'
            st.session_state.registration_success = False
            st.rerun()
        return

    # Show current student count
    student_count = get_student_count()
    st.info(f"👥 Currently registered students: {student_count}")

    with st.form("registration_form"):
        st.subheader("Register to Vote")
        register_number = st.text_input("Student Register Number", placeholder="e.g., 2021CS001").strip().upper()
        name = st.text_input("Full Name", placeholder="Enter your full name").strip().title()

        submitted = st.form_submit_button("Register", use_container_width=True)

        if submitted:
            if not register_number or not name:
                st.error("Please fill in all fields!")
            elif len(register_number) < 3:
                st.error("Register number must be at least 3 characters long!")
            elif len(name) < 2:
                st.error("Name must be at least 2 characters long!")
            else:
                success, message = register_student(register_number, name)
                if success:
                    st.session_state.current_student = register_number
                    st.session_state.student_logged_in = True
                    st.session_state.registration_success = True
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)


def show_voting_page():
    """Display voting page"""
    st.title("🗳️ Voting Page")

    if st.button("← Back to Home"):
        st.session_state.page = 'home'
        st.rerun()

    # Display current India time
    current_time = get_india_time()
    st.info(f"🕐 Current Time (India): {current_time.strftime('%Y-%m-%d %H:%M:%S IST')}")

    # Check voting time status
    time_status = get_voting_time_status()

    # Display voting status
    if time_status['status'] == 'not_started':
        st.warning(f"⏰ {time_status['message']}")
        st.info("Please wait for the voting period to begin.")
        return
    elif time_status['status'] == 'ended':
        st.error(f"⏰ {time_status['message']}")
        st.info("Voting has ended. Thank you for your interest!")
        return
    elif time_status['status'] == 'disabled':
        st.warning("⚠️ Voting is currently disabled by admin.")
        return
    elif time_status['status'] == 'active':
        st.success(f"✅ {time_status['message']}")
        if time_status['time_remaining']:
            remaining = format_time_remaining(time_status['time_remaining'])
            st.warning(f"⏳ Time remaining: {remaining}")

    # Check if student is logged in
    if not st.session_state.student_logged_in:
        st.warning("Please verify your registration to vote.")

        register_number = st.text_input("Enter your Register Number to vote:").strip().upper()

        if st.button("Verify and Vote"):
            if is_student_registered(register_number):
                if has_student_voted(register_number):
                    st.error("You have already voted!")
                else:
                    st.session_state.current_student = register_number
                    st.session_state.student_logged_in = True
                    st.rerun()
            else:
                st.error("Register number not found. Please register first!")
        return

    # Check if student has already voted
    if has_student_voted(st.session_state.current_student):
        st.success("✅ You have already cast your vote!")
        st.info("Thank you for participating in the voting!")

        if st.button("Logout"):
            st.session_state.student_logged_in = False
            st.session_state.current_student = None
            st.session_state.page = 'home'
            st.rerun()
        return

    # Voting form - only show if voting is active
    if time_status['can_vote']:
        st.markdown("---")
        st.subheader("🏆 Messi vs Ronaldo - Cast Your Vote!")

        col1, col2 = st.columns(2)

        with col1:
            display_candidate_image('messi', "Lionel Messi", 250)
            messi_vote = st.button("⚽ Vote for Messi", use_container_width=True, type="primary")

        with col2:
            display_candidate_image('ronaldo', "Cristiano Ronaldo", 250)
            ronaldo_vote = st.button("⚽ Vote for Ronaldo", use_container_width=True, type="primary")

        if messi_vote:
            if cast_vote(st.session_state.current_student, "Messi"):
                st.success("🎉 Thank you for voting for Messi!")
                st.balloons()
                time.sleep(2)
                st.rerun()
            else:
                st.error("Voting failed. Please try again.")

        if ronaldo_vote:
            if cast_vote(st.session_state.current_student, "Ronaldo"):
                st.success("🎉 Thank you for voting for Ronaldo!")
                st.balloons()
                time.sleep(2)
                st.rerun()
            else:
                st.error("Voting failed. Please try again.")
    else:
        st.error("❌ Voting is not currently available.")


def show_admin_login():
    """Display admin login page"""
    st.title("👨‍💼 Admin Login")

    if st.button("← Back to Home"):
        st.session_state.page = 'home'
        st.rerun()

    st.markdown("---")

    with st.form("admin_login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login_button = st.form_submit_button("Login")

        if login_button:
            # Simple admin credentials (in production, use proper authentication)
            if username == "admin" and password == "admin123":
                st.session_state.admin_logged_in = True
                st.session_state.page = 'admin_panel'
                st.rerun()
            else:
                st.error("Invalid credentials!")


def show_admin_panel():
    """Display admin panel with all administrative functions"""
    if not st.session_state.admin_logged_in:
        st.session_state.page = 'admin_login'
        st.rerun()
        return

    st.title("👨‍💼 Admin Panel")

    # Display current India time
    current_time = get_india_time()
    st.info(f"🕐 Current Time (India): {current_time.strftime('%Y-%m-%d %H:%M:%S IST')}")

    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("Logout"):
            st.session_state.admin_logged_in = False
            st.session_state.page = 'home'
            st.rerun()

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        ["📊 Voting Results", "👥 Student Data", "✅ Voted Students", "🏆 Declare Winner", "🔄 Re-Election",
         "⏰ Time Settings"])

    with tab1:
        st.subheader("📊 Voting Results")

        results = get_vote_results()
        total_votes = sum(results.values())

        if total_votes > 0:
            # Display metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Votes", total_votes)
            with col2:
                st.metric("Messi", results['Messi'],
                          f"{(results['Messi'] / total_votes * 100):.1f}%")
            with col3:
                st.metric("Ronaldo", results['Ronaldo'],
                          f"{(results['Ronaldo'] / total_votes * 100):.1f}%")

            # Create visualization
            df_results = pd.DataFrame([
                {'Candidate': 'Messi', 'Votes': results['Messi']},
                {'Candidate': 'Ronaldo', 'Votes': results['Ronaldo']}
            ])

            col1, col2 = st.columns(2)

            with col1:
                fig_bar = px.bar(df_results, x='Candidate', y='Votes',
                                 title="Vote Distribution",
                                 color='Candidate',
                                 color_discrete_map={'Messi': '#1f77b4', 'Ronaldo': '#ff7f0e'})
                st.plotly_chart(fig_bar, use_container_width=True)

            with col2:
                fig_pie = px.pie(df_results, values='Votes', names='Candidate',
                                 title="Vote Percentage",
                                 color_discrete_map={'Messi': '#1f77b4', 'Ronaldo': '#ff7f0e'})
                st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No votes cast yet.")

    with tab2:
        st.subheader("👥 All Registered Students")

        students_df = get_all_students()

        if not students_df.empty:
            st.dataframe(students_df, use_container_width=True)
            st.info(f"Total registered students: {len(students_df)}")

            # Show voting status
            conn = sqlite3.connect('voting_system.db')
            cursor = conn.cursor()
            cursor.execute('SELECT DISTINCT register_number FROM votes')
            voted = [row[0] for row in cursor.fetchall()]
            conn.close()

            students_df['Voting_Status'] = students_df['register_number'].apply(
                lambda x: '✅ Voted' if x in voted else '❌ Not Voted')
            st.subheader("📊 Voting Status Overview")
            st.dataframe(students_df[['register_number', 'name', 'Voting_Status']], use_container_width=True)

            # Summary statistics
            voted_count = len(voted)
            not_voted_count = len(students_df) - voted_count
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Students", len(students_df))
            with col2:
                st.metric("Voted", voted_count, f"{(voted_count / len(students_df) * 100):.1f}%")
            with col3:
                st.metric("Not Voted", not_voted_count, f"{(not_voted_count / len(students_df) * 100):.1f}%")

            # Delete all students button
            st.markdown("---")
            st.subheader("🗑️ Student Database Management")
            st.warning("⚠️ **CAUTION**: This will permanently delete ALL student records and their votes!")

            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("🗑️ Delete All Students", type="secondary", use_container_width=True):
                    success, message = delete_all_students()
                    if success:
                        st.success(message)
                        # Reset session state
                        st.session_state.winner_declared = False
                        st.session_state.declared_winner = None
                        st.session_state.auto_declared = False
                        st.session_state.auto_declaration_processed = False
                        st.rerun()
                    else:
                        st.error(message)
            with col2:
                st.info("This will remove all student registrations and votes. Use with caution!")
        else:
            st.info("No students registered yet.")

    with tab3:
        st.subheader("✅ Students Who Have Voted")

        voted_students_df = get_students_who_voted()

        if not voted_students_df.empty:
            st.dataframe(voted_students_df, use_container_width=True)

            # Summary by candidate
            st.subheader("📊 Votes Summary by Candidate")
            candidate_summary = voted_students_df.groupby('candidate').size().reset_index(name='count')
            col1, col2 = st.columns(2)

            for idx, row in candidate_summary.iterrows():
                with col1 if idx == 0 else col2:
                    st.metric(f"{row['candidate']} Voters", row['count'])

            # Show recent votes
            st.subheader("🕒 Recent Votes")
            recent_votes = voted_students_df.head(10)
            st.dataframe(recent_votes, use_container_width=True)

            # Export functionality
            if st.button("💾 Download Voting Data as CSV"):
                csv = voted_students_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name=f"voting_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        else:
            st.info("No votes have been cast yet.")

    with tab4:
        st.subheader("🏆 Declare Winner")

        results = get_vote_results()
        total_votes = sum(results.values())

        if total_votes > 0:
            if results['Messi'] > results['Ronaldo']:
                leading = "Messi"
            elif results['Ronaldo'] > results['Messi']:
                leading = "Ronaldo"
            else:
                leading = "Tie"

            st.info(f"Current leader: **{leading}**")

            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("🏆 Declare Messi as Winner", use_container_width=True):
                    st.session_state.winner_declared = True
                    st.session_state.declared_winner = "Messi"
                    st.session_state.auto_declared = False
                    st.success("Messi declared as winner!")
                    st.rerun()

            with col2:
                if st.button("🏆 Declare Ronaldo as Winner", use_container_width=True):
                    st.session_state.winner_declared = True
                    st.session_state.declared_winner = "Ronaldo"
                    st.session_state.auto_declared = False
                    st.success("Ronaldo declared as winner!")
                    st.rerun()

            with col3:
                if st.button("🤝 Declare Tie", use_container_width=True):
                    st.session_state.winner_declared = True
                    st.session_state.declared_winner = "Tie"
                    st.session_state.auto_declared = False
                    st.success("Tie declared!")
                    st.rerun()

            if st.session_state.winner_declared:
                declaration_type = "🤖 Auto-declared" if st.session_state.get('auto_declared',
                                                                             False) else "👨‍💼 Admin-declared"
                st.success(f"🏆 {declaration_type} Winner: **{st.session_state.declared_winner}**")

                if st.button("🔄 Reset Winner Declaration", type="secondary"):
                    st.session_state.winner_declared = False
                    st.session_state.declared_winner = None
                    st.session_state.auto_declared = False
                    st.session_state.auto_declaration_processed = False
                    st.info("Winner declaration reset.")
                    st.rerun()
        else:
            st.warning("No votes cast yet. Cannot declare winner.")

    with tab5:
        st.subheader("🔄 Re-Election Management")

        st.warning("⚠️ **CAUTION**: This will permanently delete all voting data!")

        results = get_vote_results()
        total_votes = sum(results.values())

        if total_votes > 0:
            st.info(f"Current election has {total_votes} votes cast.")

            # Show current results before reset
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Messi", results['Messi'])
            with col2:
                st.metric("Ronaldo", results['Ronaldo'])

            st.markdown("---")

            # Confirmation checkboxes
            confirm1 = st.checkbox("I understand this will delete all votes")
            confirm2 = st.checkbox("I understand this action cannot be undone")
            confirm3 = st.checkbox("I want to start a new election")

            if confirm1 and confirm2 and confirm3:
                col1, col2 = st.columns([1, 2])
                with col1:
                    if st.button("🗑️ RESET ELECTION", type="primary", use_container_width=True):
                        if reset_election():
                            st.session_state.winner_declared = False
                            st.session_state.declared_winner = None
                            st.session_state.auto_declared = False
                            st.session_state.auto_declaration_processed = False
                            st.success("✅ Election reset successfully! All votes have been cleared.")
                            st.balloons()
                            st.rerun()
                        else:
                            st.error("❌ Failed to reset election. Please try again.")

                with col2:
                    st.info("Click the button to start fresh election")
            else:
                st.info("Please confirm all checkboxes above to enable election reset.")
        else:
            st.info("No votes have been cast yet. Nothing to reset.")

            if st.session_state.winner_declared:
                st.info("Winner declaration is active. You can reset it from the 'Declare Winner' tab.")

    with tab6:
        st.subheader("⏰ Voting Time Management (India Timezone)")

        # Display current settings
        current_settings = get_voting_settings()
        time_status = get_voting_time_status()

        # Current status display
        st.markdown("### 📊 Current Status")
        col1, col2, col3 = st.columns(3)

        with col1:
            status_color = {
                'active': '🟢',
                'not_started': '🟡',
                'ended': '🔴',
                'disabled': '⚫',
                'no_schedule': '⚪'
            }
            st.metric("Voting Status",
                      f"{status_color.get(time_status['status'], '⚪')} {time_status['status'].title().replace('_', ' ')}")

        with col2:
            if current_settings and current_settings['start_time']:
                st.metric("Start Time", format_india_time(current_settings['start_time']))
            else:
                st.metric("Start Time", "Not Set")

        with col3:
            if current_settings and current_settings['end_time']:
                st.metric("End Time", format_india_time(current_settings['end_time']))
            else:
                st.metric("End Time", "Not Set")

        if time_status['status'] == 'active' and time_status['time_remaining']:
            remaining = format_time_remaining(time_status['time_remaining'])
            st.info(f"⏳ Time remaining: {remaining}")

        st.markdown("---")

        # Time setting form
        st.markdown("### ⚙️ Set Voting Schedule")

        with st.form("time_settings_form"):
            col1, col2 = st.columns(2)

            # Get current India time
            india_now = get_india_time()

            with col1:
                start_date = st.date_input("Start Date", india_now.date())
                start_time_input = st.time_input("Start Time", india_now.time())

            with col2:
                end_date = st.date_input("End Date", (india_now + timedelta(days=1)).date())
                end_time_input = st.time_input("End Time", (india_now + timedelta(hours=1)).time())

            auto_declare = st.checkbox("Auto-declare winner when time ends", value=True)

            col1, col2, col3 = st.columns([1, 1, 2])

            with col1:
                if st.form_submit_button("📅 Set Schedule", type="primary"):
                    start_datetime = datetime.combine(start_date, start_time_input)
                    end_datetime = datetime.combine(end_date, end_time_input)

                    # Localize to India timezone
                    start_datetime = INDIA_TZ.localize(start_datetime)
                    end_datetime = INDIA_TZ.localize(end_datetime)

                    if end_datetime <= start_datetime:
                        st.error("End time must be after start time!")
                    elif start_datetime < india_now:
                        st.error("Start time cannot be in the past!")
                    else:
                        if set_voting_time(start_datetime, end_datetime, auto_declare):
                            # Reset auto-declaration processed flag when new schedule is set
                            st.session_state.auto_declaration_processed = False
                            st.success("✅ Voting schedule updated successfully!")
                            st.rerun()
                        else:
                            st.error("❌ Failed to update schedule!")

            with col2:
                if st.form_submit_button("🟢 Enable Now"):
                    if set_voting_time(india_now, None, False):
                        st.success("✅ Voting enabled!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to enable voting!")

            with col3:
                if st.form_submit_button("🔴 Disable Voting"):
                    conn = sqlite3.connect('voting_system.db')
                    cursor = conn.cursor()
                    cursor.execute('UPDATE voting_settings SET voting_enabled = 0')
                    conn.commit()
                    conn.close()
                    st.success("✅ Voting disabled!")
                    st.rerun()

        st.markdown("---")

        # Updated Quick time presets (15, 30, 45 minutes - removed 1 week)
        st.markdown("### ⚡ Quick Presets")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if st.button("⏰ 15 Minutes", use_container_width=True):
                start_time = get_india_time()
                end_time = start_time + timedelta(minutes=15)
                if set_voting_time(start_time, end_time, True):
                    st.session_state.auto_declaration_processed = False
                    st.success("✅ 15-minute voting set!")
                    st.rerun()

        with col2:
            if st.button("🕧 30 Minutes", use_container_width=True):
                start_time = get_india_time()
                end_time = start_time + timedelta(minutes=30)
                if set_voting_time(start_time, end_time, True):
                    st.session_state.auto_declaration_processed = False
                    st.success("✅ 30-minute voting set!")
                    st.rerun()

        with col3:
            if st.button("🕘 45 Minutes", use_container_width=True):
                start_time = get_india_time()
                end_time = start_time + timedelta(minutes=45)
                if set_voting_time(start_time, end_time, True):
                    st.session_state.auto_declaration_processed = False
                    st.success("✅ 45-minute voting set!")
                    st.rerun()

        with col4:
            if st.button("🕐 1 Hour", use_container_width=True):
                start_time = get_india_time()
                end_time = start_time + timedelta(hours=1)
                if set_voting_time(start_time, end_time, True):
                    st.session_state.auto_declaration_processed = False
                    st.success("✅ 1-hour voting set!")
                    st.rerun()

        # Advanced settings
        st.markdown("---")
        st.markdown("### 🔧 Advanced Settings")

        if current_settings:
            col1, col2 = st.columns(2)

            with col1:
                if st.button("🗑️ Clear Schedule", type="secondary", use_container_width=True):
                    conn = sqlite3.connect('voting_system.db')
                    cursor = conn.cursor()
                    cursor.execute('DELETE FROM voting_settings')
                    conn.commit()
                    conn.close()
                    st.success("✅ Schedule cleared!")
                    st.rerun()

            with col2:
                current_auto = current_settings.get('auto_declare_winner', True)
                if st.button(f"{'🔴 Disable' if current_auto else '🟢 Enable'} Auto-Declaration",
                             use_container_width=True):
                    conn = sqlite3.connect('voting_system.db')
                    cursor = conn.cursor()
                    cursor.execute('UPDATE voting_settings SET auto_declare_winner = ?', (not current_auto,))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ Auto-declaration {'disabled' if current_auto else 'enabled'}!")
                    st.rerun()


# Main application
def main():
    st.set_page_config(
        page_title="Online Voting System",
        page_icon="🗳️",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    # Initialize database and session state
    init_database()
    init_session_state()

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


if __name__ == "__main__":
    main()