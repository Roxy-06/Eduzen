import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from db import (
    init_db, add_material, get_materials,
    # --- NEW: classrooms & attendance ---
    create_classroom, get_classrooms,
    add_student, get_students,
    create_session, get_sessions,
    mark_attendance, get_session_attendance,
    get_attendance_summary, get_student_session_log,
)
from rag_engine import index_document, generate_rag_response

app = FastAPI(title="EduZen API")

# Allow Streamlit frontend to communicate with this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Automatically locate the root 'uploads' folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Initialize the SQLite database table when the server starts
init_db()

# Data model for incoming AI requests
class QueryRequest(BaseModel):
    mode: str  # Options: 'qa', 'summary', 'quiz', 'flashcards'
    query: str = ""

# --- NEW: request models for classrooms & attendance ---
class ClassroomCreate(BaseModel):
    name: str

class StudentCreate(BaseModel):
    name: str
    student_id: str

class AttendanceMark(BaseModel):
    student_id: int
    status: str  # 'present' or 'absent'

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Receives uploaded PDF, saves it to disk, and indexes it into the vector database."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are currently supported.")

    file_path = os.path.join(UPLOAD_DIR, file.filename)

    # Save the file to disk
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Process PDF into FAISS vector storage
    success = index_document(file_path)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to process document text.")

    # Record filename in SQLite database
    add_material(file.filename)
    return {"message": f"Successfully processed and indexed '{file.filename}'"}

@app.get("/api/materials")
def list_materials():
    """Returns the list of all uploaded course materials."""
    return get_materials()

@app.post("/api/ai/generate")
def ai_generate(req: QueryRequest):
    """Handles requests for Q&A, Summaries, Quizzes, and Flashcards."""
    result = generate_rag_response(mode=req.mode, query=req.query)
    return {"response": result}


# =========================================================================
# NEW: Classrooms & Attendance
# =========================================================================

@app.post("/api/classrooms")
def create_classroom_endpoint(payload: ClassroomCreate):
    """Creates a new classroom/section (e.g. 'CS101 - Section A')."""
    classroom_id = create_classroom(payload.name)
    return {"id": classroom_id, "name": payload.name}


@app.get("/api/classrooms")
def list_classrooms_endpoint():
    """Lists every classroom the teacher has created."""
    return get_classrooms()


@app.post("/api/classrooms/{classroom_id}/students")
def add_student_endpoint(classroom_id: int, payload: StudentCreate):
    """Enrolls one student (name + student ID) into a classroom."""
    student_id = add_student(classroom_id, payload.name, payload.student_id)
    return {"id": student_id, "name": payload.name, "student_id": payload.student_id}


@app.get("/api/classrooms/{classroom_id}/students")
def list_students_endpoint(classroom_id: int):
    """Lists all students enrolled in a classroom."""
    return get_students(classroom_id)


@app.post("/api/classrooms/{classroom_id}/sessions")
def start_session_endpoint(classroom_id: int):
    """Starts a new lecture - this is the 'take attendance now' trigger."""
    return create_session(classroom_id)


@app.get("/api/classrooms/{classroom_id}/sessions")
def list_sessions_endpoint(classroom_id: int):
    """Lists every past lecture session for a classroom."""
    return get_sessions(classroom_id)


@app.post("/api/sessions/{session_id}/attendance")
def mark_attendance_endpoint(session_id: int, payload: AttendanceMark):
    """Marks one student Present or Absent for one lecture session."""
    if payload.status not in ("present", "absent"):
        raise HTTPException(status_code=400, detail="status must be 'present' or 'absent'")
    mark_attendance(session_id, payload.student_id, payload.status)
    return {"detail": "ok"}


@app.get("/api/sessions/{session_id}/attendance")
def get_session_attendance_endpoint(session_id: int):
    """Returns current marks for one session - so buttons can reflect state."""
    return get_session_attendance(session_id)


@app.get("/api/classrooms/{classroom_id}/attendance-summary")
def attendance_summary_endpoint(classroom_id: int):
    """Per-student totals: classes attended / total classes / percentage."""
    return get_attendance_summary(classroom_id)


@app.get("/api/classrooms/{classroom_id}/students/{student_id}/log")
def student_log_endpoint(classroom_id: int, student_id: int):
    """Session-by-session present/absent history for one student."""
    return get_student_session_log(classroom_id, student_id)