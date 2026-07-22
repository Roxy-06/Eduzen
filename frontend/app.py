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

