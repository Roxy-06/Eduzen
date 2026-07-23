import streamlit as st
import requests

API_URL = "http://localhost:8000/api"

st.set_page_config(page_title="EduZen - Smart Campus", page_icon="🎓", layout="wide")

st.title("🎓 EduZen: AI-Powered Smart University Platform")
st.caption("Next-Generation Academic Knowledge Base & AI Tutor")

# Navigation Sidebar
role = st.sidebar.radio("Select Portal Role", ["👩‍🏫 Teacher Portal", "👨‍🎓 Student Portal"])

# ---------------------------------------------------------
# TEACHER PORTAL
# ---------------------------------------------------------
if role == "👩‍🏫 Teacher Portal":
    st.header("Faculty Material Upload & Repository")
    st.write("Upload lecture slides, course notes, or syllabi in PDF format to train the AI assistant.")

    uploaded_file = st.file_uploader("Upload Course PDF", type=["pdf"])
    if uploaded_file is not None:
        if st.button("Upload & Process Material", type="primary"):
            with st.spinner("Parsing PDF & Generating Vector Embeddings..."):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                try:
                    res = requests.post(f"{API_URL}/upload", files=files)
                    if res.status_code == 200:
                        st.success(res.json()["message"])
                    else:
                        st.error("Failed to process document.")
                except Exception as e:
                    st.error(f"Could not connect to backend server. Make sure FastAPI is running! Error: {e}")

    st.divider()
    st.subheader("📚 Active Course Repository")
    try:
        res = requests.get(f"{API_URL}/materials")
        if res.status_code == 200:
            materials = res.json()
            if materials:
                for item in materials:
                    st.text(f"• {item['filename']} (Uploaded: {item['uploaded_at']})")
            else:
                st.info("No materials uploaded yet.")
    except Exception:
        st.warning("Unable to fetch materials. Ensure the backend server is running.")

    # -----------------------------------------------------
    # NEW: Classrooms & Attendance
    # -----------------------------------------------------
    st.divider()
    st.subheader("🏫 Classrooms & Attendance")
    st.write("Create a classroom, add your students, and take attendance lecture by lecture.")

    try:
        classrooms = requests.get(f"{API_URL}/classrooms").json()
    except Exception:
        classrooms = []
        st.warning("Unable to fetch classrooms. Ensure the backend server is running.")

    with st.expander("➕ Create a new classroom"):
        new_classroom_name = st.text_input(
            "Classroom name (e.g. 'CS101 - Section A')", key="new_classroom_name"
        )
        if st.button("Create Classroom"):
            if new_classroom_name.strip():
                requests.post(f"{API_URL}/classrooms", json={"name": new_classroom_name.strip()})
                st.success(f"Classroom '{new_classroom_name}' created!")
                st.rerun()
            else:
                st.warning("Please enter a classroom name.")

    if classrooms:
        classroom_options = {c["name"]: c["id"] for c in classrooms}
        selected_classroom_name = st.selectbox("Select a classroom", list(classroom_options.keys()))
        classroom_id = classroom_options[selected_classroom_name]

        with st.expander("➕ Add a student to this classroom"):
            col1, col2 = st.columns(2)
            with col1:
                student_name = st.text_input("Student name", key="new_student_name")
            with col2:
                student_roll = st.text_input("Student ID", key="new_student_roll")
            if st.button("Add Student"):
                if student_name.strip() and student_roll.strip():
                    requests.post(
                        f"{API_URL}/classrooms/{classroom_id}/students",
                        json={"name": student_name.strip(), "student_id": student_roll.strip()},
                    )
                    st.success(f"Added {student_name} to {selected_classroom_name}")
                    st.rerun()
                else:
                    st.warning("Please enter both name and student ID.")

        students = requests.get(f"{API_URL}/classrooms/{classroom_id}/students").json()

        st.markdown("#### 📋 Take Attendance")
        if not students:
            st.info("No students added to this classroom yet - add some above.")
        else:
            if st.button("▶️ Start New Lecture (new attendance session)"):
                session = requests.post(f"{API_URL}/classrooms/{classroom_id}/sessions").json()
                st.session_state["active_session_id"] = session["id"]
                st.session_state["active_session_classroom"] = classroom_id
                st.success(f"New lecture session started at {session['session_date']}")
                st.rerun()

            active_session_id = st.session_state.get("active_session_id")
            active_for_this_classroom = (
                active_session_id is not None
                and st.session_state.get("active_session_classroom") == classroom_id
            )

            if active_for_this_classroom:
                current_marks = requests.get(
                    f"{API_URL}/sessions/{active_session_id}/attendance"
                ).json()
                # JSON object keys always come back as strings - convert to int for lookup
                current_marks = {int(k): v for k, v in current_marks.items()}

                st.write(f"Marking attendance for session #{active_session_id}:")
                for student in students:
                    sid = student["id"]
                    status = current_marks.get(sid)
                    cols = st.columns([3, 1, 1, 1])
                    cols[0].write(f"**{student['name']}** ({student['student_id']})")
                    present_label = "✅ Present" if status == "present" else "Present"
                    absent_label = "❌ Absent" if status == "absent" else "Absent"
                    if cols[1].button(present_label, key=f"present_{active_session_id}_{sid}"):
                        requests.post(
                            f"{API_URL}/sessions/{active_session_id}/attendance",
                            json={"student_id": sid, "status": "present"},
                        )
                        st.rerun()
                    if cols[2].button(absent_label, key=f"absent_{active_session_id}_{sid}"):
                        requests.post(
                            f"{API_URL}/sessions/{active_session_id}/attendance",
                            json={"student_id": sid, "status": "absent"},
                        )
                        st.rerun()
                    cols[3].write(status if status else "—")
            else:
                st.caption("Click 'Start New Lecture' above to begin taking attendance.")

        st.markdown("#### 📊 Attendance Evaluation")
        summary = requests.get(f"{API_URL}/classrooms/{classroom_id}/attendance-summary").json()
        if summary:
            st.dataframe(
                [
                    {
                        "Student": s["name"],
                        "Student ID": s["roll_no"],
                        "Classes Attended": s["attended"],
                        "Total Classes": s["total_classes"],
                        "Attendance %": s["percentage"],
                    }
                    for s in summary
                ],
                use_container_width=True,
            )
        else:
            st.info("No attendance data yet.")

        st.markdown("#### 🗂️ Session-by-Session Log")
        if students:
            log_student_name = st.selectbox(
                "View detailed log for:", [s["name"] for s in students], key="log_student_select"
            )
            log_student = next(s for s in students if s["name"] == log_student_name)
            log = requests.get(
                f"{API_URL}/classrooms/{classroom_id}/students/{log_student['id']}/log"
            ).json()
            for entry in log:
                icon = {"present": "✅", "absent": "❌"}.get(entry["status"], "⚪")
                st.write(f"{icon} {entry['session_date']} — **{entry['status']}**")
    else:
        st.info("No classrooms yet - create one above to get started.")

# ---------------------------------------------------------
# STUDENT PORTAL
# ---------------------------------------------------------
else:
    st.header("Student Learning Hub")

    tab1, tab2, tab3, tab4 = st.tabs([
        "💬 AI Q&A Assistant",
        "📝 Instant Summarizer",
        "🧩 Quiz Generator",
        "🎴 Flashcards"
    ])

    # Tab 1: AI Q&A
    with tab1:
        st.subheader("Ask questions about your lectures")
        user_query = st.text_input("Enter your question (e.g., 'Explain the key terms from Chapter 2'):")
        if st.button("Ask AI Tutor", type="primary"):
            if user_query:
                with st.spinner("Searching course materials..."):
                    try:
                        res = requests.post(f"{API_URL}/ai/generate", json={"mode": "qa", "query": user_query})
                        if res.status_code == 200:
                            st.markdown("### Answer")
                            st.write(res.json()["response"])
                        else:
                            st.error("Failed to generate response.")
                    except Exception as e:
                        st.error(f"Connection error: {e}")
            else:
                st.warning("Please enter a question.")

    # Tab 2: Summarizer
    with tab2:
        st.subheader("Generate Course Material Summary")
        if st.button("Generate Lecture Summary"):
            with st.spinner("Analyzing uploaded notes..."):
                try:
                    res = requests.post(f"{API_URL}/ai/generate", json={"mode": "summary"})
                    if res.status_code == 200:
                        st.markdown(res.json()["response"])
                    else:
                        st.error("Failed to generate summary.")
                except Exception as e:
                    st.error(f"Connection error: {e}")

    # Tab 3: Quiz Generator
    with tab3:
        st.subheader("Generate Practice Quiz")
        if st.button("Create 3-Question Practice Quiz"):
            with st.spinner("Building custom quiz..."):
                try:
                    res = requests.post(f"{API_URL}/ai/generate", json={"mode": "quiz"})
                    if res.status_code == 200:
                        st.markdown(res.json()["response"])
                    else:
                        st.error("Failed to generate quiz.")
                except Exception as e:
                    st.error(f"Connection error: {e}")

    # Tab 4: Flashcards
    with tab4:
        st.subheader("Generate Revision Flashcards")
        if st.button("Create Study Flashcards"):
            with st.spinner("Generating flashcards..."):
                try:
                    res = requests.post(f"{API_URL}/ai/generate", json={"mode": "flashcards"})
                    if res.status_code == 200:
                        st.markdown(res.json()["response"])
                    else:
                        st.error("Failed to generate flashcards.")
                except Exception as e:
                    st.error(f"Connection error: {e}")