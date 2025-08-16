import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta, date, time as dtime
import plotly.express as px
import pytz
import os

# =========================
# App & Theme
# =========================
st.set_page_config(
    page_title="Campus Voting System",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .big-emoji {font-size: 56px; line-height: 56px}
      .metric-small .stMetricDelta {font-size: 0.8rem !important}
      .center {display:flex; align-items:center; gap:.5rem}
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================
# Constants & Timezone
# =========================
INDIA_TZ = pytz.timezone("Asia/Kolkata")
CANDIDATES = ["Alice", "Bob", "Charlie"]  # 👈 customize
ADMIN_PASSWORD = os.getenv("ADMIN_PASS", "admin")  # change in env for security

# =========================
# DB Helpers (cached)
# =========================

def _connect():
    # Single cached connection; better perf vs reopening each call
    # check_same_thread False to allow access across Streamlit threads
    conn = sqlite3.connect("voting_system.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Pragmas: better concurrency & speed for read-heavy workloads
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

@st.cache_resource(show_spinner=False)
def get_conn():
    return _connect()


def init_database():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS students (
            register_number TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            registration_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            register_number TEXT NOT NULL,
            candidate TEXT NOT NULL,
            vote_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (register_number) REFERENCES students (register_number)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS voting_settings (
            id INTEGER PRIMARY KEY,
            voting_start_time TEXT,
            voting_end_time TEXT,
            voting_enabled BOOLEAN DEFAULT 1,
            auto_declare_winner BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Helpful indices
    cur.execute("CREATE INDEX IF NOT EXISTS idx_votes_reg ON votes(register_number);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_votes_candidate ON votes(candidate);")

    conn.commit()

init_database()

# ============
# Cache utils
# ============

def _clear_data_caches():
    get_students_df.clear()
    get_votes_df.clear()
    get_results_df.clear()
    get_voting_settings.clear()
    get_voting_time_status.clear()

# =========================
# Time helpers
# =========================

def now_india():
    return datetime.now(INDIA_TZ)


def parse_tz(dt_str: str | None):
    if not dt_str:
        return None
    dt = datetime.fromisoformat(dt_str)
    if dt.tzinfo is None:
        return INDIA_TZ.localize(dt)
    return dt.astimezone(INDIA_TZ)


def format_dt(dt: datetime | None):
    if not dt:
        return "Not Set"
    if dt.tzinfo is None:
        dt = INDIA_TZ.localize(dt)
    return dt.astimezone(INDIA_TZ).strftime("%Y-%m-%d %H:%M:%S")

# =========================
# Settings (cached)
# =========================

@st.cache_data(ttl=5, show_spinner=False)
def get_voting_settings() -> dict | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM voting_settings ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    if not row:
        return None
    d = dict(row)
    return {
        "id": d["id"],
        "start_time": d["voting_start_time"],
        "end_time": d["voting_end_time"],
        "voting_enabled": bool(d["voting_enabled"]),
        "auto_declare_winner": bool(d["auto_declare_winner"]),
        "created_at": d["created_at"],
        "updated_at": d["updated_at"],
    }


def set_voting_time(start_time: datetime | None, end_time: datetime | None, auto_declare=True) -> bool:
    try:
        if start_time and start_time.tzinfo is None:
            start_time = INDIA_TZ.localize(start_time)
        if end_time and end_time.tzinfo is None:
            end_time = INDIA_TZ.localize(end_time)

        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM voting_settings")
        cur.execute(
            """
            INSERT INTO voting_settings (voting_start_time, voting_end_time, auto_declare_winner, voting_enabled)
            VALUES (?, ?, ?, 1)
            """,
            (
                start_time.isoformat() if start_time else None,
                end_time.isoformat() if end_time else None,
                1 if auto_declare else 0,
            ),
        )
        conn.commit()
        _clear_data_caches()
        return True
    except Exception as e:
        st.error(f"Error setting voting time: {e}")
        return False


@st.cache_data(ttl=5, show_spinner=False)
def get_voting_time_status():
    s = get_voting_settings()
    if not s:
        return {"status": "no_schedule", "time_remaining": None}
    if not s["voting_enabled"]:
        return {"status": "disabled", "time_remaining": None}

    now = now_india()
    start = parse_tz(s["start_time"]) if s["start_time"] else None
    end = parse_tz(s["end_time"]) if s["end_time"] else None

    if start and end:
        if now < start:
            return {"status": "not_started", "time_remaining": start - now}
        if start <= now <= end:
            return {"status": "active", "time_remaining": end - now}
        return {"status": "ended", "time_remaining": None}

    # If only enabled flag is used without schedule, treat as active
    return {"status": "active", "time_remaining": None}


def format_time_remaining(delta: timedelta) -> str:
    secs = int(delta.total_seconds())
    if secs < 0:
        return "0s"
    d, r = divmod(secs, 86400)
    h, r = divmod(r, 3600)
    m, s = divmod(r, 60)
    parts = []
    if d: parts.append(f"{d}d")
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}m")
    if s or not parts: parts.append(f"{s}s")
    return " ".join(parts)

# =========================
# Data Access (cached)
# =========================

@st.cache_data(ttl=5, show_spinner=False)
def get_students_df() -> pd.DataFrame:
    conn = get_conn()
    return pd.read_sql_query("SELECT * FROM students ORDER BY registration_time DESC", conn)


@st.cache_data(ttl=5, show_spinner=False)
def get_votes_df() -> pd.DataFrame:
    conn = get_conn()
    return pd.read_sql_query("SELECT * FROM votes ORDER BY vote_time DESC", conn)


@st.cache_data(ttl=5, show_spinner=False)
def get_results_df() -> pd.DataFrame:
    votes = get_votes_df()
    if votes.empty:
        return pd.DataFrame({"candidate": CANDIDATES, "votes": [0]*len(CANDIDATES)})
    return votes.groupby("candidate").size().reset_index(name="votes").sort_values("votes", ascending=False)

# =========================
# Write Operations
# =========================

def register_student(register_number: str, name: str) -> bool:
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO students (register_number, name) VALUES (?, ?)",
            (register_number.strip(), name.strip()),
        )
        conn.commit()
        _clear_data_caches()
        return True
    except sqlite3.IntegrityError:
        st.error("This register number is already registered!")
        return False
    except Exception as e:
        st.error(f"Registration failed: {e}")
        return False


def has_voted(register_number: str) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM votes WHERE register_number = ? LIMIT 1", (register_number.strip(),))
    return cur.fetchone() is not None


def cast_vote(register_number: str, candidate: str) -> bool:
    try:
        # Ensure student exists
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM students WHERE register_number = ?", (register_number.strip(),))
        if cur.fetchone() is None:
            st.error("Register number not found. Please register first.")
            return False
        if has_voted(register_number):
            st.warning("You have already voted.")
            return False
        cur.execute(
            "INSERT INTO votes (register_number, candidate) VALUES (?, ?)",
            (register_number.strip(), candidate),
        )
        conn.commit()
        _clear_data_caches()
        return True
    except Exception as e:
        st.error(f"Failed to cast vote: {e}")
        return False


def delete_all_students_and_votes() -> bool:
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM votes")
        cur.execute("DELETE FROM students")
        conn.commit()
        _clear_data_caches()
        return True
    except Exception as e:
        st.error(f"Error deleting students/votes: {e}")
        return False


def clear_all_votes() -> bool:
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM votes")
        conn.commit()
        _clear_data_caches()
        return True
    except Exception as e:
        st.error(f"Error clearing votes: {e}")
        return False

# =========================
# Status & Logic
# =========================

def is_voting_active() -> bool:
    status = get_voting_time_status()
    return status["status"] == "active"


def compute_winner() -> tuple[str | None, int]:
    res = get_results_df()
    if res.empty:
        return None, 0
    top = res.iloc[0]
    return top["candidate"], int(top["votes"])

# =========================
# Admin UI
# =========================

def admin_login_page():
    st.title("👨‍💼 Admin Login")
    with st.form("admin_login_form"):
        pwd = st.text_input("Password", type="password")
        ok = st.form_submit_button("Login", type="primary")
    if ok:
        if pwd == ADMIN_PASSWORD:
            st.session_state.admin_logged_in = True
            st.success("Logged in!")
            st.experimental_rerun()
        else:
            st.error("Invalid password")


def show_admin_panel():
    if not st.session_state.get("admin_logged_in"):
        admin_login_page()
        return

    st.title("👨‍💼 Admin Panel")
    c1, c2 = st.columns([6, 1])
    with c2:
        if st.button("Logout", use_container_width=True):
            st.session_state.admin_logged_in = False
            st.experimental_rerun()

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Voting Results",
        "👥 Student Data",
        "✅ Voted Students",
        "🏆 Declare Winner",
        "🔄 Re-Election",
        "⏰ Time Settings",
    ])

    # --- Results ---
    with tab1:
        st.subheader("Live Results")
        res = get_results_df()
        colA, colB = st.columns([2, 3])
        with colA:
            st.dataframe(res, use_container_width=True)
            total_votes = int(res["votes"].sum()) if not res.empty else 0
            st.metric("Total Votes", total_votes)
        with colB:
            fig = px.bar(res, x="candidate", y="votes", title="Votes by Candidate")
            st.plotly_chart(fig, use_container_width=True)

    # --- Students ---
    with tab2:
        st.subheader("Registered Students")
        df = get_students_df()
        st.dataframe(df, use_container_width=True, height=400)
        st.caption(f"Total: {len(df)}")

    # --- Voted ---
    with tab3:
        st.subheader("Voted Students")
        v = get_votes_df()[["register_number", "candidate", "vote_time"]]
        st.dataframe(v, use_container_width=True, height=400)
        st.caption(f"Total: {len(v)}")

    # --- Declare Winner ---
    with tab4:
        st.subheader("Declare Winner (Manual)")
        if st.button("Compute Winner", type="primary"):
            winner, count = compute_winner()
            if winner:
                st.success(f"🏆 Winner: {winner} with {count} votes")
            else:
                st.info("No votes yet.")

    # --- Re-Election ---
    with tab5:
        st.subheader("Re-Election Tools")
        colx, coly = st.columns(2)
        with colx:
            if st.button("🗑️ Clear All Votes", use_container_width=True):
                if clear_all_votes():
                    st.success("Cleared all votes")
        with coly:
            if st.button("🧹 Delete ALL Students + Votes", use_container_width=True):
                if delete_all_students_and_votes():
                    st.success("Deleted students and votes")

    # --- Time Settings ---
    with tab6:
        st.subheader("⏰ Voting Time Management (India Time)")

        current_settings = get_voting_settings()
        time_status = get_voting_time_status()

        c1, c2, c3 = st.columns(3)
        with c1:
            status_map = {
                "active": "🟢 Active",
                "not_started": "🟡 Not Started",
                "ended": "🔴 Ended",
                "disabled": "⚫ Disabled",
                "no_schedule": "⚪ No Schedule",
            }
            st.metric("Voting Status", status_map.get(time_status["status"], "⚪ No Schedule"))
        with c2:
            st.metric("Start Time", format_dt(parse_tz(current_settings["start_time"]) if current_settings else None))
        with c3:
            st.metric("End Time", format_dt(parse_tz(current_settings["end_time"]) if current_settings else None))

        if time_status["status"] == "active" and time_status["time_remaining"]:
            st.info(f"⏳ Time remaining: {format_time_remaining(time_status['time_remaining'])}")

        st.markdown("---")
        st.markdown("### ⚙️ Set Voting Schedule")

        with st.form("time_settings_form"):
            col1, col2 = st.columns(2)
            ni = now_india()
            with col1:
                s_date: date = st.date_input("Start Date", ni.date(), key="sdate")
                s_time: dtime = st.time_input("Start Time", ni.time().replace(microsecond=0), key="stime")
            with col2:
                e_date: date = st.date_input("End Date", (ni + timedelta(days=1)).date(), key="edate")
                e_time: dtime = st.time_input("End Time", (ni + timedelta(hours=1)).time().replace(microsecond=0), key="etime")

            auto_declare = st.checkbox("Auto-declare winner when time ends", value=True)

            colx, coly, colz = st.columns([1, 1, 2])
            set_btn = colx.form_submit_button("📅 Set Schedule", type="primary")
            enable_now_btn = coly.form_submit_button("🟢 Enable Now")
            disable_btn = colz.form_submit_button("🔴 Disable Voting")

        if set_btn:
            start_dt = INDIA_TZ.localize(datetime.combine(s_date, s_time))
            end_dt = INDIA_TZ.localize(datetime.combine(e_date, e_time))
            if end_dt <= start_dt:
                st.error("End time must be after start time!")
            elif start_dt < now_india():
                st.error("Start time cannot be in the past!")
            else:
                if set_voting_time(start_dt, end_dt, auto_declare):
                    st.success("✅ Voting schedule updated!")
                    st.experimental_rerun()

        if enable_now_btn:
            if set_voting_time(now_india(), None, False):
                st.success("✅ Voting enabled immediately!")
                st.experimental_rerun()

        if disable_btn:
            conn = get_conn()
            conn.execute("UPDATE voting_settings SET voting_enabled = 0")
            conn.commit()
            _clear_data_caches()
            st.success("✅ Voting disabled")
            st.experimental_rerun()

        st.markdown("---")
        st.markdown("### ⚡ Quick Presets")
        p1, p2, p3 = st.columns(3)
        if p1.button("⏰ 15 Mins", use_container_width=True):
            start = now_india(); end = start + timedelta(minutes=15)
            if set_voting_time(start, end, True): st.success("15-minute voting set!"); st.experimental_rerun()
        if p2.button("🕧 30 Mins", use_container_width=True):
            start = now_india(); end = start + timedelta(minutes=30)
            if set_voting_time(start, end, True): st.success("30-minute voting set!"); st.experimental_rerun()
        if p3.button("🕐 45 Mins", use_container_width=True):
            start = now_india(); end = start + timedelta(minutes=45)
            if set_voting_time(start, end, True): st.success("45-minute voting set!"); st.experimental_rerun()

        st.markdown("---")
        st.markdown("### 🔧 Advanced Settings")
        cA, cB = st.columns(2)
        with cA:
            if st.button("🗑️ Clear Schedule", use_container_width=True):
                conn = get_conn()
                conn.execute("DELETE FROM voting_settings")
                conn.commit()
                _clear_data_caches()
                st.success("Schedule cleared")
                st.experimental_rerun()
        with cB:
            if current_settings:
                current_auto = current_settings.get("auto_declare_winner", True)
                if st.button(("🔴 Disable" if current_auto else "🟢 Enable") + " Auto-Declaration", use_container_width=True):
                    conn = get_conn()
                    conn.execute("UPDATE voting_settings SET auto_declare_winner = ?", (0 if current_auto else 1,))
                    conn.commit()
                    _clear_data_caches()
                    st.success("Auto-declaration toggled")
                    st.experimental_rerun()

        st.markdown("---")
        st.markdown("### 🧑‍🎓 Student Database")
        if st.button("🗑️ Delete All Students & Votes", use_container_width=True):
            if delete_all_students_and_votes():
                st.success("All student records and votes deleted")
                st.experimental_rerun()

# =========================
# Public UI
# =========================

def show_home():
    st.title("🗳️ Campus Voting System")
    status = get_voting_time_status()
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Status", status["status"].replace("_", " ").title())
    with c2:
        s = get_voting_settings()
        st.metric("Start", format_dt(parse_tz(s["start_time"]) if s else None))
    with c3:
        s = get_voting_settings()
        st.metric("End", format_dt(parse_tz(s["end_time"]) if s else None))

    if status["status"] == "active" and status["time_remaining"]:
        st.success(f"⏳ Voting open — {format_time_remaining(status['time_remaining'])} remaining")
    elif status["status"] == "not_started":
        st.info("Voting not started yet")
    elif status["status"] == "ended":
        st.warning("Voting has ended")

    st.markdown("---")
    left, right = st.columns(2)

    with left:
        st.subheader("🧑‍🎓 Register")
        with st.form("register_form"):
            rn = st.text_input("Register Number")
            nm = st.text_input("Name")
            reg_ok = st.form_submit_button("Register", type="primary")
        if reg_ok:
            if rn.strip() and nm.strip():
                if register_student(rn, nm):
                    st.success("Registered successfully!")
            else:
                st.error("Enter both Register Number and Name")

    with right:
        st.subheader("🗳️ Vote")
        with st.form("vote_form"):
            rn2 = st.text_input("Register Number")
            cand = st.selectbox("Choose Candidate", CANDIDATES)
            vote_ok = st.form_submit_button("Cast Vote", type="primary")
        if vote_ok:
            if not is_voting_active():
                st.error("Voting is not active right now")
            elif rn2.strip():
                if cast_vote(rn2, cand):
                    st.success("Your vote has been recorded. Thank you!")
            else:
                st.error("Enter your Register Number")

    st.markdown("---")
    st.subheader("📈 Snapshot")
    res = get_results_df()
    fig = px.pie(res, names="candidate", values="votes", title="Share of Votes")
    st.plotly_chart(fig, use_container_width=True)

# =========================
# Router
# =========================

if "page" not in st.session_state:
    st.session_state.page = "home"

with st.sidebar:
    st.header("Navigation")
    choice = st.radio("Go to", ["Home", "Admin"], index=0 if st.session_state.page=="home" else 1)
    st.caption("Timezone: Asia/Kolkata")

if choice == "Home":
    st.session_state.page = "home"
    show_home()
else:
    st.session_state.page = "admin"
    show_admin_panel()
