import streamlit as st
import sqlite3
import pandas as pd
import hashlib
from datetime import datetime, timedelta
import plotly.express as px
import os
from PIL import Image
import time
import pytz  # Added for timezone support

# Set India timezone
INDIA_TZ = pytz.timezone('Asia/Kolkata')


# Database initialization
def init_database():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect('voting_system.db')
    cursor = conn.cursor()

    # Create students table (register_number is PRIMARY KEY to prevent duplicates)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            register_number TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            registration_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create votes table
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


# Modified time-related functions to use India timezone
def get_current_india_time():
    """Get current time in India timezone"""
    return datetime.now(INDIA_TZ)


def format_datetime_for_display(dt):
    """Format datetime for display in India timezone"""
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)
    if not dt.tzinfo:
        dt = INDIA_TZ.localize(dt)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def set_voting_time(start_time, end_time, auto_declare=True):
    """Set voting start and end time with timezone awareness"""
    try:
        # Convert to India timezone if not already
        if not start_time.tzinfo:
            start_time = INDIA_TZ.localize(start_time)
        if end_time and not end_time.tzinfo:
            end_time = INDIA_TZ.localize(end_time)

        conn = sqlite3.connect('voting_system.db')
        cursor = conn.cursor()

        # Delete existing settings
        cursor.execute('DELETE FROM voting_settings')

        # Insert new settings
        cursor.execute('''
            INSERT INTO voting_settings (voting_start_time, voting_end_time, auto_declare_winner, voting_enabled)
            VALUES (?, ?, ?, 1)
        ''', (start_time.isoformat(), end_time.isoformat() if end_time else None, auto_declare))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error setting voting time: {str(e)}")
        return False


def get_voting_settings():
    """Get current voting settings with timezone awareness"""
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
    """Check if voting is currently active based on time settings (using India time)"""
    settings = get_voting_settings()
    if not settings or not settings['voting_enabled']:
        return False

    current_time = get_current_india_time()

    if settings['start_time'] and settings['end_time']:
        start_time = INDIA_TZ.localize(datetime.fromisoformat(settings['start_time']))
        end_time = INDIA_TZ.localize(datetime.fromisoformat(settings['end_time']))
        return start_time <= current_time <= end_time

    return settings['voting_enabled']


# Modified student registration to prevent duplicates (already handled by PRIMARY KEY)
def register_student(register_number, name):
    """Register a new student - duplicates prevented by PRIMARY KEY constraint"""
    try:
        conn = sqlite3.connect('voting_system.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO students (register_number, name) VALUES (?, ?)',
                       (register_number, name))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        st.error("This register number is already registered!")
        return False


# New function to delete all students
def delete_all_students():
    """Delete all student records"""
    try:
        conn = sqlite3.connect('voting_system.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM students')
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error deleting students: {str(e)}")
        return False


# Modified show_admin_panel function to include student deletion
def show_admin_panel():
    """Display admin panel with all administrative functions"""
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

    # ... [previous tab content remains the same until tab6] ...

    with tab6:
        st.subheader("⏰ Voting Time Management")

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
                start_time = INDIA_TZ.localize(datetime.fromisoformat(current_settings['start_time']))
                st.metric("Start Time", start_time.strftime("%Y-%m-%d %H:%M"))
            else:
                st.metric("Start Time", "Not Set")

        with col3:
            if current_settings and current_settings['end_time']:
                end_time = INDIA_TZ.localize(datetime.fromisoformat(current_settings['end_time']))
                st.metric("End Time", end_time.strftime("%Y-%m-%d %H:%M"))
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

            with col1:
                start_date = st.date_input("Start Date", get_current_india_time().date())
                start_time_input = st.time_input("Start Time", get_current_india_time().time())

            with col2:
                end_date = st.date_input("End Date", (get_current_india_time() + timedelta(days=1)).date())
                end_time_input = st.time_input("End Time", (get_current_india_time() + timedelta(hours=1)).time())

            auto_declare = st.checkbox("Auto-declare winner when time ends", value=True)

            col1, col2, col3 = st.columns([1, 1, 2])

            with col1:
                if st.form_submit_button("📅 Set Schedule", type="primary"):
                    start_datetime = INDIA_TZ.localize(datetime.combine(start_date, start_time_input))
                    end_datetime = INDIA_TZ.localize(datetime.combine(end_date, end_time_input))

                    if end_datetime <= start_datetime:
                        st.error("End time must be after start time!")
                    elif start_datetime < get_current_india_time():
                        st.error("Start time cannot be in the past!")
                    else:
                        if set_voting_time(start_datetime, end_datetime, auto_declare):
                            st.session_state.auto_declaration_processed = False
                            st.success("✅ Voting schedule updated successfully!")
                            st.rerun()
                        else:
                            st.error("❌ Failed to update schedule!")

            with col2:
                if st.form_submit_button("🟢 Enable Now"):
                    if set_voting_time(get_current_india_time(), None, False):
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

        # Quick time presets - modified options
        st.markdown("### ⚡ Quick Presets")
        col1, col2, col3 = st.columns(3)  # Changed to 3 columns for 15, 30, 45 mins

        with col1:
            if st.button("⏰ 15 Mins", use_container_width=True):
                start_time = get_current_india_time()
                end_time = start_time + timedelta(minutes=15)
                if set_voting_time(start_time, end_time, True):
                    st.session_state.auto_declaration_processed = False
                    st.success("✅ 15-minute voting set!")
                    st.rerun()

        with col2:
            if st.button("🕧 30 Mins", use_container_width=True):
                start_time = get_current_india_time()
                end_time = start_time + timedelta(minutes=30)
                if set_voting_time(start_time, end_time, True):
                    st.session_state.auto_declaration_processed = False
                    st.success("✅ 30-minute voting set!")
                    st.rerun()

        with col3:
            if st.button("🕐 45 Mins", use_container_width=True):
                start_time = get_current_india_time()
                end_time = start_time + timedelta(minutes=45)
                if set_voting_time(start_time, end_time, True):
                    st.session_state.auto_declaration_processed = False
                    st.success("✅ 45-minute voting set!")
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

        # Add student database management
        st.markdown("---")
        st.markdown("### 🧑‍🎓 Student Database")

        if st.button("🗑️ Delete All Students", type="secondary", use_container_width=True):
            if delete_all_students():
                st.success("✅ All student records deleted!")
                st.rerun()
            else:
                st.error("❌ Failed to delete student records")

# ... [rest of the code remains the same] ...