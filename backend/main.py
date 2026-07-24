import os
import shutil
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from db import (
    init_db,
    add_material,
    get_materials,
    get_subjects,
    get_teacher_classes,
    create_classroom,
    get_classrooms,
    add_student,
    get_students,
    start_subject_session,
    get_latest_open_session,
    get_sessions_for_subject,
    mark_attendance,
    get_session_attendance,
    get_attendance_summary,
    get_student_session_log,
    get_student_subject_report,
    create_user,
    authenticate_user,
    get_student_dashboard,
    get_teacher_dashboard,
)
from rag_engine import index_document, generate_rag_response

app = FastAPI(title="EduZen API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

init_db()


class QueryRequest(BaseModel):
    mode: str
    query: str = ""


class ClassroomCreate(BaseModel):
    name: str


class StudentCreate(BaseModel):
    name: str
    student_id: str
    email: Optional[str] = None


class SessionCreate(BaseModel):
    teacher_id: int


class AttendanceMark(BaseModel):
    status: str


class UserRegister(BaseModel):
    name: str
    email: str
    password: str
    role: str
    department: str


class UserLogin(BaseModel):
    email: str
    password: str


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


@app.post("/api/auth/register")
def register_user(payload: UserRegister):
    if payload.role not in {"teacher", "student"}:
        raise HTTPException(status_code=400, detail="role must be teacher or student")
    user_id = create_user(payload.name, payload.email, payload.password, payload.role, payload.department)
    if user_id is None:
        raise HTTPException(status_code=409, detail="An account with that email already exists")
    return {"user": {"id": user_id, "name": payload.name, "email": payload.email, "role": payload.role, "department": payload.department}}


@app.post("/api/auth/login")
def login_user(payload: UserLogin):
    user = authenticate_user(payload.email, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"user": user}


@app.get("/api/dashboard/student/{user_id}")
def student_dashboard(user_id: int):
    dashboard = get_student_dashboard(user_id)
    if dashboard is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return dashboard


@app.get("/api/dashboard/teacher/{user_id}")
def teacher_dashboard(user_id: int):
    dashboard = get_teacher_dashboard(user_id)
    if dashboard is None:
        raise HTTPException(status_code=404, detail="Teacher not found")
    return dashboard


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are currently supported.")

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    success = index_document(file_path)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to process document text.")

    add_material(file.filename)
    return {"message": f"Successfully processed and indexed '{file.filename}'"}


@app.get("/api/materials")
def list_materials():
    return get_materials()


@app.post("/api/ai/generate")
def ai_generate(req: QueryRequest):
    result = generate_rag_response(mode=req.mode, query=req.query)
    return {"response": result}


# ---------------------------------------------------------
# SUBJECTS & TEACHER ASSIGNMENTS
# ---------------------------------------------------------
@app.get("/api/subjects")
def list_subjects_endpoint():
    return get_subjects()


@app.get("/api/teachers/{teacher_id}/classes")
def teacher_classes_endpoint(teacher_id: int):
    """All classroom+subject combinations this teacher is assigned to teach."""
    return get_teacher_classes(teacher_id)


# ---------------------------------------------------------
# CLASSROOMS & ROSTER
# ---------------------------------------------------------
@app.post("/api/classrooms")
def create_classroom_endpoint(payload: ClassroomCreate):
    classroom_id = create_classroom(payload.name)
    return {"id": classroom_id, "name": payload.name}


@app.get("/api/classrooms")
def list_classrooms_endpoint():
    return get_classrooms()


@app.post("/api/classrooms/{classroom_id}/students")
def add_student_endpoint(classroom_id: int, payload: StudentCreate):
    student_id = add_student(classroom_id, payload.name, payload.student_id, payload.email)
    return {"id": student_id, "name": payload.name, "student_id": payload.student_id}


@app.get("/api/classrooms/{classroom_id}/students")
def list_students_endpoint(classroom_id: int):
    return get_students(classroom_id)


# ---------------------------------------------------------
# SESSIONS & ATTENDANCE (per classroom + subject)
# ---------------------------------------------------------
@app.post("/api/classrooms/{classroom_id}/subjects/{subject_id}/sessions")
def start_session_endpoint(classroom_id: int, subject_id: int, payload: SessionCreate):
    return start_subject_session(classroom_id, subject_id, payload.teacher_id)


@app.get("/api/classrooms/{classroom_id}/subjects/{subject_id}/today-session")
def today_session_endpoint(classroom_id: int, subject_id: int, teacher_id: int):
    session = get_latest_open_session(classroom_id, subject_id, teacher_id)
    return session or {}


@app.get("/api/classrooms/{classroom_id}/subjects/{subject_id}/sessions")
def list_subject_sessions_endpoint(classroom_id: int, subject_id: int):
    return get_sessions_for_subject(classroom_id, subject_id)


@app.post("/api/sessions/{session_id}/attendance/{student_id}")
def mark_attendance_endpoint(session_id: int, student_id: int, payload: AttendanceMark):
    if payload.status not in ("present", "absent"):
        raise HTTPException(status_code=400, detail="status must be 'present' or 'absent'")
    mark_attendance(session_id, student_id, payload.status)
    return {"detail": "ok"}


@app.get("/api/sessions/{session_id}/attendance")
def get_session_attendance_endpoint(session_id: int):
    return get_session_attendance(session_id)


@app.get("/api/classrooms/{classroom_id}/attendance-summary")
def attendance_summary_endpoint(classroom_id: int, subject_id: Optional[int] = None):
    return get_attendance_summary(classroom_id, subject_id)


@app.get("/api/classrooms/{classroom_id}/students/{student_id}/log")
def student_log_endpoint(classroom_id: int, student_id: int):
    return get_student_session_log(classroom_id, student_id)


# ---------------------------------------------------------
# STUDENT-FACING ATTENDANCE + MARKS REPORT
# ---------------------------------------------------------
@app.get("/api/students/user/{user_id}/report")
def student_report_endpoint(user_id: int):
    return get_student_subject_report(user_id)