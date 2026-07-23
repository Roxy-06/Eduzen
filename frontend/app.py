import streamlit as st
import requests

API_URL = "http://localhost:8000/api"

# ---------------------------------------------------------
# PAGE CONFIG & STYLING (HIGH CONTRAST & ACCESSIBILITY FIXES)
# ---------------------------------------------------------
st.set_page_config(
    page_title="EduZen Platform",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    * { 
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; 
    }
    
    /* Main Layout Background */
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 1250px;
    }
    
    .stApp {
        background-color: #f8fafc;
    }

    /* GLOBAL TEXT CONTRAST FIX */
    .stApp p, .stApp span, .stApp label, .stApp div, .stApp header, .stApp small, .stApp caption {
        color: #0f172a;
    }

    /* SIDEBAR STYLING & HIGH-CONTRAST OVERRIDES */
    [data-testid="stSidebar"] {
        background-color: #0f172a !important;
        border-right: 1px solid #1e293b;
    }
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] span, 
    [data-testid="stSidebar"] div, 
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #f8fafc !important;
    }
    [data-testid="stSidebar"] .stCaption {
        color: #94a3b8 !important;
    }

    /* HERO BANNER STYLING */
    .hero-banner {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #312e81 100%);
        border-radius: 14px;
        padding: 26px 30px;
        color: #ffffff !important;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.2);
        margin-bottom: 24px;
        border: 1px solid rgba(255, 255, 255, 0.08);
    }
    .hero-banner * {
        color: #ffffff !important;
    }
    .hero-title {
        font-size: 1.85rem;
        font-weight: 700;
        letter-spacing: -0.025em;
        margin: 0 0 6px 0;
    }
    .hero-subtitle {
        font-size: 0.95rem;
        color: #cbd5e1 !important;
        margin: 0;
        font-weight: 400;
    }

    /* PROFILE CARD IN SIDEBAR */
    .profile-card {
        background: #1e293b;
        border-radius: 10px;
        padding: 16px;
        border: 1px solid #334155;
        margin-bottom: 20px;
    }
    .profile-card * {
        color: #f8fafc !important;
    }

    /* METRIC CARDS */
    .metric-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 18px 20px;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 15px -3px rgba(0, 0, 0, 0.06);
        border-color: #cbd5e1;
    }
    .metric-label {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #64748b !important;
        margin-bottom: 4px;
    }
    .metric-value {
        font-size: 1.75rem;
        font-weight: 700;
        color: #0f172a !important;
        margin: 0;
        line-height: 1.2;
    }
    .metric-caption {
        font-size: 0.78rem;
        color: #64748b !important;
        margin-top: 4px;
    }

    /* CONTENT CARDS */
    .content-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 22px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.04);
        margin-bottom: 20px;
    }
    .card-title {
        font-size: 1.05rem;
        font-weight: 600;
        color: #0f172a !important;
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 1px solid #f1f5f9;
    }

    /* BADGES */
    .text-badge {
        display: inline-block;
        padding: 3px 10px;
        font-size: 0.72rem;
        font-weight: 600;
        border-radius: 6px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .badge-primary { background: #e0e7ff; color: #3730a3 !important; }
    .badge-success { background: #d1fae5; color: #065f46 !important; }
    .badge-dark { background: #334155; color: #f8fafc !important; }

    /* INPUTS, TEXTAREAS & PLACEHOLDERS FIX */
    label[data-testid="stWidgetLabel"] p, 
    label[data-testid="stWidgetLabel"] span {
        color: #0f172a !important;
        font-weight: 600 !important;
    }
    
    div[data-baseweb="input"] input, 
    div[data-baseweb="textarea"] textarea {
        color: #0f172a !important;
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 6px !important;
    }

    ::placeholder {
        color: #64748b !important;
        opacity: 1 !important;
    }

    /* FILE UPLOADER FIX (Under Course Material) */
    [data-testid="stFileUploadDropzone"] {
        background-color: #f8fafc !important;
        border: 1px dashed #94a3b8 !important;
        border-radius: 8px !important;
    }
    [data-testid="stFileUploadDropzone"] * {
        color: #0f172a !important;
    }

    /* SELECTBOX & DROPDOWN MENU FIXES */
    div[data-baseweb="select"] * {
        color: #0f172a !important;
        background-color: #ffffff !important;
    }
    ul[role="listbox"] li, 
    div[data-baseweb="menu"] * {
        color: #0f172a !important;
        background-color: #ffffff !important;
    }

    /* FORMS & EXPANDERS (Under Classroom Name) */
    [data-testid="stForm"] {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 8px !important;
        padding: 1rem !important;
    }
    [data-testid="stExpander"] {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 8px !important;
    }
    [data-testid="stExpander"] details summary p,
    [data-testid="stExpander"] details summary span,
    [data-testid="stExpander"] * {
        color: #0f172a !important;
        font-weight: 500 !important;
    }

    /* TABS FIX */
    button[data-baseweb="tab"] p, button[data-baseweb="tab"] span {
        color: #475569 !important;
        font-weight: 500 !important;
    }
    button[aria-selected="true"][data-baseweb="tab"] p, 
    button[aria-selected="true"][data-baseweb="tab"] span {
        color: #1e1b4b !important;
        font-weight: 700 !important;
    }

    /* DATAFRAME & TABLES FIX */
    [data-testid="stDataFrame"] * {
        color: #0f172a !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# SESSION STATE INITIALIZATION
# ---------------------------------------------------------
if "user" not in st.session_state:
    st.session_state.user = None


# ---------------------------------------------------------
# AUTHENTICATION SCREEN
# ---------------------------------------------------------
def show_auth_screen():
    st.markdown(
        """
        <div class="hero-banner">
            <span class="text-badge badge-dark" style="margin-bottom: 10px;">ACADEMIC MANAGEMENT PLATFORM</span>
            <div class="hero-title">EduZen Unified Portal</div>
            <div class="hero-subtitle">Role-based workspace for instruction, curriculum intelligence, and learning analytics.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_center, _ = st.columns([2, 1])

    with col_center:
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        tab_signin, tab_register = st.tabs(["Sign In", "Register Account"])

        with tab_signin:
            st.caption("Access your registered teacher or student profile.")
            email = st.text_input("Email Address", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")

            if st.button("Access Portal", type="primary", use_container_width=True):
                if not email or not password:
                    st.warning("Please enter complete login credentials.")
                else:
                    try:
                        response = requests.post(
                            f"{API_URL}/auth/login",
                            json={"email": email, "password": password},
                        )
                        if response.status_code == 200:
                            st.session_state.user = response.json()["user"]
                            st.success("Authentication successful.")
                            st.rerun()
                        else:
                            st.error("Invalid credentials provided.")
                    except Exception as exc:
                        st.error(f"Backend connectivity error: {exc}")

        with tab_register:
            st.caption("Create a new institutional profile.")
            name = st.text_input("Full Name", key="register_name")
            email = st.text_input("Email Address", key="register_email")
            password = st.text_input("Create Password", type="password", key="register_password")
            role = st.selectbox("Role Assignment", ["student", "teacher"], key="register_role")
            department = st.text_input("Academic Department", key="register_department")

            if st.button("Create Account", use_container_width=True):
                if not all([name, email, password, department]):
                    st.warning("Please complete all required fields.")
                else:
                    try:
                        response = requests.post(
                            f"{API_URL}/auth/register",
                            json={
                                "name": name,
                                "email": email,
                                "password": password,
                                "role": role,
                                "department": department,
                            },
                        )
                        if response.status_code == 200:
                            st.session_state.user = response.json()["user"]
                            st.success("Account successfully created.")
                            st.rerun()
                        else:
                            st.error(response.json().get("detail", "Registration failed."))
                    except Exception as exc:
                        st.error(f"Backend connectivity error: {exc}")

        st.markdown("</div>", unsafe_allow_html=True)


if st.session_state.user is None:
    show_auth_screen()
    st.stop()


# ---------------------------------------------------------
# SIDEBAR NAVIGATION & PROFILE SUMMARY
# ---------------------------------------------------------
user = st.session_state.user

with st.sidebar:
    st.markdown("<h2 style='margin-bottom: 0;'>EduZen</h2>", unsafe_allow_html=True)
    st.caption("System Dashboard v2.0")
    st.divider()

    st.markdown(
        f"""
        <div class="profile-card">
            <div style="font-size: 0.75rem; font-weight: 600; text-transform: uppercase;">CURRENT USER</div>
            <div style="font-size: 1rem; font-weight: 600; margin-top: 2px;">{user['name']}</div>
            <div style="margin-top: 6px;">
                <span class="text-badge badge-primary">{user['role'].upper()}</span>
            </div>
            <div style="font-size: 0.8rem; margin-top: 8px;">Department: {user['department']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("Sign Out", use_container_width=True):
        st.session_state.user = None
        st.rerun()


# ---------------------------------------------------------
# TEACHER PORTAL
# ---------------------------------------------------------
if user["role"] == "teacher":
    try:
        dashboard = requests.get(f"{API_URL}/dashboard/teacher/{user['id']}").json()
    except Exception as exc:
        st.error(f"Unable to load teacher operations data: {exc}")
        st.stop()

    st.markdown(
        f"""
        <div class="hero-banner">
            <span class="text-badge badge-primary" style="margin-bottom: 10px;">TEACHER OPERATIONS WORKSPACE</span>
            <div class="hero-title">Welcome back, {user['name']}</div>
            <div class="hero-subtitle">Active Focus: {dashboard.get('current_topic', 'N/A')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Metrics Grid
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f"""<div class="metric-card">
                <div class="metric-label">Active Classes</div>
                <div class="metric-value">{dashboard.get('classroom_count', 0)}</div>
                <div class="metric-caption">Assigned sections</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""<div class="metric-card">
                <div class="metric-label">Total Sessions</div>
                <div class="metric-value">{dashboard.get('session_count', 0)}</div>
                <div class="metric-caption">Recorded lectures</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"""<div class="metric-card">
                <div class="metric-label">Course Resources</div>
                <div class="metric-value">{dashboard.get('materials_available', 0)}</div>
                <div class="metric-caption">Indexed documents</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f"""<div class="metric-card">
                <div class="metric-label">Weekly Load</div>
                <div class="metric-value">{dashboard.get('weekly_hours', 0)}h</div>
                <div class="metric-caption">Instructional hours</div>
            </div>""",
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    col_left, col_right = st.columns([1.2, 1])

    # Left Column: Material Upload & Schedule
    with col_left:
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        st.markdown("<div class='card-title'>Course Routine & Details</div>", unsafe_allow_html=True)
        st.write(f"**Routine:** {dashboard.get('routine', 'N/A')}")
        st.write(f"**Current Topic:** {dashboard.get('current_topic', 'N/A')}")
        st.write(f"**Office Hours:** {dashboard.get('office_hours', 'N/A')}")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        st.markdown("<div class='card-title'>Upload Course Material (PDF)</div>", unsafe_allow_html=True)
        st.caption("Uploaded documents are indexed into vector storage for student AI assistance.")

        uploaded_file = st.file_uploader("Select PDF File", type=["pdf"], label_visibility="visible")
        if uploaded_file is not None:
            if st.button("Process & Index Document", type="primary", use_container_width=True):
                with st.spinner("Extracting text and indexing vector embeddings..."):
                    try:
                        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                        response = requests.post(f"{API_URL}/upload", files=files)
                        if response.status_code == 200:
                            st.success(response.json()["message"])
                            st.rerun()
                        else:
                            st.error("Document processing failed.")
                    except Exception as exc:
                        st.error(f"Backend processing error: {exc}")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        st.markdown("<div class='card-title'>Indexed Repository</div>", unsafe_allow_html=True)
        try:
            materials = requests.get(f"{API_URL}/materials").json()
            if materials:
                st.dataframe(
                    [{"Filename": m["filename"], "Uploaded Date": m["uploaded_at"]} for m in materials],
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("No course materials indexed yet.")
        except Exception as exc:
            st.warning(f"Unable to retrieve material repository: {exc}")
        st.markdown("</div>", unsafe_allow_html=True)

    # Right Column: Classroom Management Operations
    with col_right:
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        st.markdown("<div class='card-title'>Classroom Administration</div>", unsafe_allow_html=True)

        # Classroom Creation Form
        with st.form("create_classroom_form", clear_on_submit=True):
            st.caption("Create New Classroom Section")
            new_class_name = st.text_input("Classroom Name", placeholder="e.g. CS-101 Section A")
            submit_class = st.form_submit_button("Create Classroom", use_container_width=True)
            if submit_class:
                if new_class_name.strip():
                    requests.post(f"{API_URL}/classrooms", json={"name": new_class_name.strip()})
                    st.success(f"Classroom '{new_class_name.strip()}' created.")
                    st.rerun()
                else:
                    st.warning("Please provide a valid classroom name.")

        st.divider()

        # Manage Selected Classroom
        try:
            classrooms = requests.get(f"{API_URL}/classrooms").json()
        except Exception:
            classrooms = []

        if classrooms:
            class_options = {item["name"]: item["id"] for item in classrooms}
            selected_class_name = st.selectbox("Select Classroom Section", list(class_options.keys()))
            selected_class_id = class_options[selected_class_name]

            with st.expander("Enroll Student to Section"):
                with st.form("enroll_student_form", clear_on_submit=True):
                    s_name = st.text_input("Student Name", placeholder="e.g. Jane Doe")
                    s_id = st.text_input("Institutional Roll/ID", placeholder="e.g. STU-2026-001")
                    submit_enroll = st.form_submit_button("Enroll Student", use_container_width=True)
                    if submit_enroll:
                        if s_name.strip() and s_id.strip():
                            requests.post(
                                f"{API_URL}/classrooms/{selected_class_id}/students",
                                json={"name": s_name.strip(), "student_id": s_id.strip()},
                            )
                            st.success("Student assigned successfully.")
                            st.rerun()
                        else:
                            st.warning("Complete all student details.")

            # Roster Table
            try:
                students = requests.get(f"{API_URL}/classrooms/{selected_class_id}/students").json()
                if students:
                    st.write("**Enrolled Roster**")
                    st.dataframe(
                        [{"Student Name": s["name"], "Student ID": s["student_id"]} for s in students],
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.info("No students enrolled in this section yet.")
            except Exception:
                st.error("Failed to load section roster.")
        else:
            st.info("No active classrooms created.")

        st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------
# STUDENT PORTAL
# ---------------------------------------------------------
else:
    try:
        dashboard = requests.get(f"{API_URL}/dashboard/student/{user['id']}").json()
    except Exception as exc:
        st.error(f"Unable to load student workspace data: {exc}")
        st.stop()

    st.markdown(
        f"""
        <div class="hero-banner">
            <span class="text-badge badge-success" style="margin-bottom: 10px;">STUDENT ACADEMIC HUB</span>
            <div class="hero-title">Welcome, {user['name']}</div>
            <div class="hero-subtitle">Attendance Status: {dashboard.get('attendance_rate', 0)}% | Academic Progress: {dashboard.get('progress_score', 0)}%</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Metrics Grid
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f"""<div class="metric-card">
                <div class="metric-label">Attendance Rate</div>
                <div class="metric-value">{dashboard.get('attendance_rate', 0)}%</div>
                <div class="metric-caption">Current semester</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""<div class="metric-card">
                <div class="metric-label">Progress Score</div>
                <div class="metric-value">{dashboard.get('progress_score', 0)}%</div>
                <div class="metric-caption">Overall completion</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"""<div class="metric-card">
                <div class="metric-label">Modules Finished</div>
                <div class="metric-value">{dashboard.get('topics_completed', 0)}</div>
                <div class="metric-caption">Completed topics</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f"""<div class="metric-card">
                <div class="metric-label">Available Materials</div>
                <div class="metric-value">{dashboard.get('materials_available', 0)}</div>
                <div class="metric-caption">Course resources</div>
            </div>""",
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    col_left, col_right = st.columns([1.3, 1])

    # Left Column: AI Study Workbench (QA, Summarizer, Quiz, Flashcards)
    with col_left:
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        st.markdown("<div class='card-title'>AI Curriculum Assistant</div>", unsafe_allow_html=True)
        st.caption("Powered by vector retrieval grounded in your professor's uploaded syllabus.")

        tab_qa, tab_summary, tab_quiz, tab_cards = st.tabs(
            ["Q&A Assistant", "Module Summarizer", "Practice Quiz", "Flashcards"]
        )

        # Tab 1: Q&A
        with tab_qa:
            qa_query = st.text_area("Ask a question about your course materials:", height=90, key="qa_input")
            if st.button("Generate Answer", type="primary", key="btn_qa"):
                if qa_query.strip():
                    with st.spinner("Searching course materials..."):
                        try:
                            res = requests.post(
                                f"{API_URL}/ai/generate",
                                json={"mode": "qa", "query": qa_query.strip()},
                            )
                            if res.status_code == 200:
                                st.markdown("### Response")
                                st.write(res.json()["response"])
                            else:
                                st.error("Response generation failed.")
                        except Exception as exc:
                            st.error(f"Backend issue: {exc}")
                else:
                    st.warning("Please enter a question.")

        # Tab 2: Summarizer
        with tab_summary:
            st.write("Generate a structured executive summary of core concepts.")
            sum_query = st.text_input("Specific Focus (Optional)", placeholder="e.g., Chapter 3 key definitions", key="sum_input")
            if st.button("Generate Course Summary", type="primary", key="btn_summary"):
                with st.spinner("Synthesizing course materials..."):
                    try:
                        res = requests.post(
                            f"{API_URL}/ai/generate",
                            json={"mode": "summary", "query": sum_query.strip()},
                        )
                        if res.status_code == 200:
                            st.markdown("### Summary")
                            st.write(res.json()["response"])
                        else:
                            st.error("Summary generation failed.")
                    except Exception as exc:
                        st.error(f"Backend issue: {exc}")

        # Tab 3: Quiz Generator
        with tab_quiz:
            st.write("Generate a practice self-assessment quiz from lecture notes.")
            quiz_topic = st.text_input("Topic Focus (Optional)", placeholder="e.g., Data Structures", key="quiz_input")
            if st.button("Generate 3-Question Practice Quiz", type="primary", key="btn_quiz"):
                with st.spinner("Creating practice questions..."):
                    try:
                        res = requests.post(
                            f"{API_URL}/ai/generate",
                            json={"mode": "quiz", "query": quiz_topic.strip()},
                        )
                        if res.status_code == 200:
                            st.markdown("### Practice Assessment")
                            st.write(res.json()["response"])
                        else:
                            st.error("Quiz generation failed.")
                    except Exception as exc:
                        st.error(f"Backend issue: {exc}")

        # Tab 4: Flashcards Generator
        with tab_cards:
            st.write("Generate revision flashcards for key terms and definitions.")
            card_topic = st.text_input("Concept Focus (Optional)", placeholder="e.g., Formulas", key="card_input")
            if st.button("Generate Study Flashcards", type="primary", key="btn_cards"):
                with st.spinner("Building flashcards..."):
                    try:
                        res = requests.post(
                            f"{API_URL}/ai/generate",
                            json={"mode": "flashcards", "query": card_topic.strip()},
                        )
                        if res.status_code == 200:
                            st.markdown("### Revision Cards")
                            st.write(res.json()["response"])
                        else:
                            st.error("Flashcard generation failed.")
                    except Exception as exc:
                        st.error(f"Backend issue: {exc}")

        st.markdown("</div>", unsafe_allow_html=True)

    # Right Column: Performance Indicators & Activity Summary
    with col_right:
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        st.markdown("<div class='card-title'>Academic Standing</div>", unsafe_allow_html=True)
        
        progress = dashboard.get("progress_score", 0) / 100.0
        st.write("Overall Progress Completion")
        st.progress(progress)

        st.markdown("---")
        st.write(f"**Latest Activity:** {dashboard.get('latest_activity', 'N/A')}")
        st.write(f"**Next Academic Goal:** {dashboard.get('next_goal', 'N/A')}")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        st.markdown("<div class='card-title'>Course Repository Access</div>", unsafe_allow_html=True)
        try:
            materials = requests.get(f"{API_URL}/materials").json()
            if materials:
                for item in materials:
                    st.write(f"- {item['filename']} (Uploaded: {item['uploaded_at']})")
            else:
                st.info("No materials published by faculty yet.")
        except Exception:
            st.warning("Unable to sync course repository.")
        st.markdown("</div>", unsafe_allow_html=True)