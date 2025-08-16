import streamlit as st
import sqlite3
import pandas as pd
import hashlib
from datetime import datetime
import plotly.express as px
import os
from PIL import Image


# Database initialization
def init_database():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect('voting_system.db')
    cursor = conn.cursor()

    # Create students table
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

    conn.commit()
    conn.close()


# Student registration functions
def register_student(register_number, name):
    """Register a new student"""
    try:
        conn = sqlite3.connect('voting_system.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO students (register_number, name) VALUES (?, ?)',
                       (register_number, name))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False


def is_student_registered(register_number):
    """Check if student is already registered"""
    conn = sqlite3.connect('voting_system.db')
    cursor = conn.cursor()
    cursor.execute('SELECT register_number FROM students WHERE register_number = ?', (register_number,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def has_student_voted(register_number):
    """Check if student has already voted"""
    conn = sqlite3.connect('voting_system.db')
    cursor = conn.cursor()
    cursor.execute('SELECT register_number FROM votes WHERE register_number = ?', (register_number,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def cast_vote(register_number, candidate):
    """Cast a vote for a candidate"""
    try:
        conn = sqlite3.connect('voting_system.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO votes (register_number, candidate) VALUES (?, ?)',
                       (register_number, candidate))
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


# Image handling functions
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
    """Get total number of votes cast"""
    conn = sqlite3.connect('voting_system.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM votes')
    total = cursor.fetchone()[0]
    conn.close()
    return total


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


# Page navigation functions
def show_home_page():
    """Display home page with navigation options"""
    st.title("🗳️ Online Voting System")
    st.subheader("Messi vs Ronaldo - Who's the GOAT?")

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
        if st.button("🗳️ Vote Now", use_container_width=True):
            st.session_state.page = 'vote'
            st.rerun()

    with col3:
        if st.button("👨‍💼 Admin Panel", use_container_width=True):
            st.session_state.page = 'admin_login'
            st.rerun()

    # Show results if winner is declared
    if st.session_state.winner_declared and st.session_state.declared_winner:
        st.markdown("---")
        st.success(f"🏆 **WINNER DECLARED: {st.session_state.declared_winner}**")

        # Show vote breakdown
        results = get_vote_results()
        total = sum(results.values())
        if total > 0:
            messi_percent = (results['Messi'] / total) * 100
            ronaldo_percent = (results['Ronaldo'] / total) * 100

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Messi", f"{results['Messi']} votes", f"{messi_percent:.1f}%")
            with col2:
                st.metric("Ronaldo", f"{results['Ronaldo']} votes", f"{ronaldo_percent:.1f}%")


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
            elif is_student_registered(register_number):
                st.error("This register number is already registered!")
            else:
                if register_student(register_number, name):
                    st.session_state.current_student = register_number
                    st.session_state.student_logged_in = True
                    st.session_state.registration_success = True
                    st.rerun()
                else:
                    st.error("Registration failed. Please try again.")


def show_voting_page():
    """Display voting page"""
    st.title("🗳️ Voting Page")

    if st.button("← Back to Home"):
        st.session_state.page = 'home'
        st.rerun()

    # Check if student is logged in
    if not st.session_state.student_logged_in:
        st.warning("Please verify your registration to vote.")

        register_number = st.text_input("Enter your Register Number to vote:")

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

    # Voting form
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
        else:
            st.error("Voting failed. Please try again.")

    if ronaldo_vote:
        if cast_vote(st.session_state.current_student, "Ronaldo"):
            st.success("🎉 Thank you for voting for Ronaldo!")
            st.balloons()
        else:
            st.error("Voting failed. Please try again.")


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

    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("Logout"):
            st.session_state.admin_logged_in = False
            st.session_state.page = 'home'
            st.rerun()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["📊 Voting Results", "👥 Student Data", "✅ Voted Students", "🏆 Declare Winner", "🔄 Re-Election"])

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
            st.subheader("🕐 Recent Votes")
            recent_votes = voted_students_df.head(10)
            st.dataframe(recent_votes, use_container_width=True)

            # Export functionality
            if st.button("📥 Download Voting Data as CSV"):
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

            col1, col2 = st.columns(2)
            with col1:
                if st.button("🏆 Declare Messi as Winner", use_container_width=True):
                    st.session_state.winner_declared = True
                    st.session_state.declared_winner = "Messi"
                    st.success("Messi declared as winner!")

            with col2:
                if st.button("🏆 Declare Ronaldo as Winner", use_container_width=True):
                    st.session_state.winner_declared = True
                    st.session_state.declared_winner = "Ronaldo"
                    st.success("Ronaldo declared as winner!")

            if st.session_state.winner_declared:
                st.success(f"🏆 Winner declared: **{st.session_state.declared_winner}**")

                if st.button("🔄 Reset Winner Declaration"):
                    st.session_state.winner_declared = False
                    st.session_state.declared_winner = None
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