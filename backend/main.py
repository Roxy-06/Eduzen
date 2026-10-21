import os
import re
import shutil
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from auth import (
    create_access_token,
    ensure_self_or_staff,
    get_current_user,
    get_current_user_header_or_query,
    require_admin,
    require_staff,
    require_student,
    require_teacher,
)
from db import (
    MAX_PASSWORD_BYTES,
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
    end_session,
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
    get_all_users,
    delete_user_by_id,
    change_password,
    create_subject,
    assign_subject_to_classroom,
    update_student_classroom,
    get_admin_attendance_overview,
    search_student_by_enrollment,
    add_or_update_mark,
    get_marks_for_classroom,
    create_quiz,
    get_quizzes_for_teacher,
    get_quizzes_for_student,
    get_quiz_teacher_id,
    submit_quiz,
    get_quiz_results,
    toggle_quiz_active,
)
from rag_engine import index_document, generate_rag_response

app = FastAPI(title="SVMIT API")

# The Vite dev server proxies /api, so the browser normally doesn't need CORS.
# Set CORS_ORIGINS (comma-separated) when the frontend is served from another origin.
_cors_origins = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.realpath(os.path.join(BASE_DIR, "..", "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)

init_db()

# Rebuild in-memory RAG index from any previously uploaded PDFs so that
# the AI can generate content for materials uploaded before a server
# restart. This is lightweight and safe for small course PDFs.
for _f in os.listdir(UPLOAD_DIR):
    if _f.lower().endswith(".pdf"):
        try:
            index_document(os.path.join(UPLOAD_DIR, _f))
        except Exception:
            # Don't let indexing failures prevent the app from starting.
            pass


class QueryRequest(BaseModel):
    mode: str
    query: str = ""


class ClassroomCreate(BaseModel):
    name: str


class StudentCreate(BaseModel):
    name: str
    student_id: str
    email: Optional[str] = None


class AttendanceMark(BaseModel):
    status: str


class UserLogin(BaseModel):
    email: str
    password: str


def _check_new_password(password: str):
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise HTTPException(status_code=400, detail=f"Password must be at most {MAX_PASSWORD_BYTES} bytes.")


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


# ── AUTH ────────────────────────────────────────────────────────────────────

@app.post("/api/auth/register")
def register_user():
    """Public self-registration is disabled. All accounts are created by an admin."""
    raise HTTPException(
        status_code=403,
        detail="Self-registration is disabled. Please contact your institution's administrator."
    )


@app.post("/api/auth/login")
def login_user(payload: UserLogin):
    user = authenticate_user(payload.email, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"user": user, "access_token": create_access_token(user), "token_type": "bearer"}


@app.get("/api/auth/me")
def who_am_i(user: dict = Depends(get_current_user)):
    return {"user": user}


class ChangePasswordPayload(BaseModel):
    current_password: str
    new_password: str


@app.post("/api/auth/change-password")
def change_user_password(payload: ChangePasswordPayload, user: dict = Depends(get_current_user)):
    _check_new_password(payload.new_password)
    result = change_password(user["id"], payload.current_password, payload.new_password)
    if result == "wrong_password":
        # 400, not 401: the frontend treats 401 as "session expired" and logs out.
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    if result == "not_found":
        raise HTTPException(status_code=404, detail="User not found.")
    return {"detail": "Password changed successfully."}


# ── ADMIN ENDPOINTS ─────────────────────────────────────────────────────────

class AdminCreateUser(BaseModel):
    name: str
    email: str
    password: str
    role: str
    department: str
    enrollment_no: Optional[str] = None
    classroom_id: Optional[int] = None


@app.get("/api/admin/users")
def admin_list_users(_: dict = Depends(require_admin)):
    """List all teachers and students."""
    return {"users": get_all_users()}


@app.post("/api/admin/users")
def admin_create_user(payload: AdminCreateUser, _: dict = Depends(require_admin)):
    """Create a teacher or student account."""
    if payload.role not in {"teacher", "student"}:
        raise HTTPException(status_code=400, detail="Role must be 'teacher' or 'student'.")
    _check_new_password(payload.password)
    user_id = create_user(
        payload.name,
        payload.email,
        payload.password,
        payload.role,
        payload.department,
        enrollment_no=payload.enrollment_no,
        classroom_id=payload.classroom_id,
    )
    if user_id is None:
        raise HTTPException(status_code=409, detail="An account with that email already exists.")
    return {"user": {"id": user_id, "name": payload.name, "email": payload.email, "role": payload.role, "department": payload.department}}


class AssignClassroomPayload(BaseModel):
    classroom_id: int


@app.post("/api/admin/students/{user_id}/classroom")
def update_student_classroom_endpoint(user_id: int, payload: AssignClassroomPayload, _: dict = Depends(require_admin)):
    update_student_classroom(user_id, payload.classroom_id)
    return {"message": "Student classroom updated successfully."}


@app.delete("/api/admin/users/{user_id}")
def admin_delete_user(user_id: int, _: dict = Depends(require_admin)):
    """Delete a teacher or student account."""
    deleted = delete_user_by_id(user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found or cannot delete admin accounts.")
    return {"detail": "User deleted successfully."}


@app.get("/api/admin/attendance-overview")
def admin_attendance_overview(_: dict = Depends(require_admin)):
    """Full attendance overview across all classrooms and subjects."""
    return {"classrooms": get_admin_attendance_overview()}


# ── DASHBOARDS ──────────────────────────────────────────────────────────────

@app.get("/api/dashboard/student/{user_id}")
def student_dashboard(user_id: int, user: dict = Depends(get_current_user)):
    ensure_self_or_staff(user, user_id)
    dashboard = get_student_dashboard(user_id)
    if dashboard is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return dashboard


@app.get("/api/dashboard/teacher/{user_id}")
def teacher_dashboard(user_id: int, user: dict = Depends(require_staff)):
    if user["role"] == "teacher" and user["id"] != user_id:
        raise HTTPException(status_code=403, detail="You can only view your own dashboard.")
    dashboard = get_teacher_dashboard(user_id)
    if dashboard is None:
        raise HTTPException(status_code=404, detail="Teacher not found")
    return dashboard


# ---------------------------------------------------------
# FILE UPLOAD & DOWNLOAD
# ---------------------------------------------------------

ALLOWED_EXTENSIONS = {".pdf", ".ppt", ".pptx"}
_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._ -]")


def _safe_upload_name(raw_name: str) -> str:
    """
    Strip any folder parts and odd characters from an uploaded file's name,
    and add a number if a file with that name already exists.
    """
    base = os.path.basename((raw_name or "").replace("\\", "/"))
    base = _UNSAFE_CHARS.sub("_", base).strip(" .")
    stem, ext = os.path.splitext(base)
    stem = stem[:100] or "file"
    ext = ext.lower()
    candidate = f"{stem}{ext}"
    counter = 1
    while os.path.exists(os.path.join(UPLOAD_DIR, candidate)):
        candidate = f"{stem}_{counter}{ext}"
        counter += 1
    return candidate


def _resolve_upload_path(filename: str) -> str:
    """Return the real path inside UPLOAD_DIR, or raise 404 if it points elsewhere."""
    path = os.path.realpath(os.path.join(UPLOAD_DIR, os.path.basename(filename)))
    if os.path.dirname(path) != UPLOAD_DIR or not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found.")
    return path


@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    classroom_id: Optional[int] = Form(None),
    _: dict = Depends(require_staff),
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only PDF, PPT, and PPTX files are supported.")

    safe_name = _safe_upload_name(file.filename)
    file_path = os.path.join(UPLOAD_DIR, safe_name)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Only PDF files get RAG-indexed
    if ext == ".pdf":
        try:
            success = index_document(file_path)
        except Exception:
            success = False
        if not success:
            os.remove(file_path)
            raise HTTPException(status_code=500, detail="Failed to process document text.")

    add_material(safe_name, classroom_id)
    return {"message": f"Successfully uploaded '{safe_name}'", "filename": safe_name}


@app.get("/api/uploads/{filename}")
async def download_file(filename: str, _: dict = Depends(get_current_user_header_or_query)):
    """Serve an uploaded file for download."""
    file_path = _resolve_upload_path(filename)
    return FileResponse(
        path=file_path,
        filename=os.path.basename(file_path),
        media_type="application/octet-stream"
    )


@app.get("/api/materials")
def list_materials(
    user_id: Optional[int] = None,
    classroom_id: Optional[int] = None,
    user: dict = Depends(get_current_user),
):
    if user["role"] == "student":
        # Students only see materials for their own classroom.
        return get_materials(user_id=user["id"])
    return get_materials(classroom_id=classroom_id, user_id=user_id)


@app.post("/api/ai/generate")
def ai_generate(req: QueryRequest, _: dict = Depends(get_current_user)):
    result = generate_rag_response(mode=req.mode, query=req.query)
    return {"response": result}


# ---------------------------------------------------------
# SUBJECTS & TEACHER ASSIGNMENTS
# ---------------------------------------------------------
class SubjectCreatePayload(BaseModel):
    name: str
    code: str

class AssignSubjectPayload(BaseModel):
    subject_id: int
    teacher_id: int

@app.get("/api/subjects")
def list_subjects_endpoint(_: dict = Depends(get_current_user)):
    return get_subjects()

@app.post("/api/subjects")
def create_subject_endpoint(payload: SubjectCreatePayload, _: dict = Depends(require_admin)):
    if not payload.name.strip() or not payload.code.strip():
        raise HTTPException(status_code=400, detail="Subject name and code are required.")
    sub = create_subject(payload.name, payload.code)
    if sub is None:
        raise HTTPException(status_code=409, detail="A subject with that code already exists.")
    return {"subject": sub}

@app.post("/api/classrooms/{classroom_id}/assign-subject")
def assign_subject_endpoint(classroom_id: int, payload: AssignSubjectPayload, _: dict = Depends(require_admin)):
    assign_subject_to_classroom(classroom_id, payload.subject_id, payload.teacher_id)
    return {"message": "Subject assigned successfully."}


@app.get("/api/teachers/{teacher_id}/classes")
def teacher_classes_endpoint(teacher_id: int, user: dict = Depends(require_staff)):
    """All classroom+subject combinations this teacher is assigned to teach."""
    if user["role"] == "teacher" and user["id"] != teacher_id:
        raise HTTPException(status_code=403, detail="You can only view your own classes.")
    return get_teacher_classes(teacher_id)


# ---------------------------------------------------------
# CLASSROOMS & ROSTER
# ---------------------------------------------------------
@app.post("/api/classrooms")
def create_classroom_endpoint(payload: ClassroomCreate, _: dict = Depends(require_staff)):
    classroom_id = create_classroom(payload.name)
    return {"id": classroom_id, "name": payload.name}


@app.get("/api/classrooms")
def list_classrooms_endpoint(_: dict = Depends(get_current_user)):
    return get_classrooms()


@app.post("/api/classrooms/{classroom_id}/students")
def add_student_endpoint(classroom_id: int, payload: StudentCreate, _: dict = Depends(require_staff)):
    student_id = add_student(classroom_id, payload.name, payload.student_id, payload.email)
    return {"id": student_id, "name": payload.name, "student_id": payload.student_id}


@app.get("/api/classrooms/{classroom_id}/students")
def list_students_endpoint(classroom_id: int, _: dict = Depends(require_staff)):
    return get_students(classroom_id)


# ---------------------------------------------------------
# STUDENT SEARCH BY ENROLLMENT NUMBER
# ---------------------------------------------------------
@app.get("/api/students/search")
def search_student_endpoint(enrollment_no: str, _: dict = Depends(require_staff)):
    """Search for a student by their enrollment/roll number."""
    result = search_student_by_enrollment(enrollment_no.strip())
    if result is None:
        raise HTTPException(status_code=404, detail=f"No student found with enrollment number '{enrollment_no}'.")
    return result


# ---------------------------------------------------------
# MARKS — Teacher entry
# ---------------------------------------------------------
class MarkEntry(BaseModel):
    student_db_id: int
    subject_id: int
    exam_name: str
    marks_obtained: float
    max_marks: float


@app.post("/api/marks")
def add_mark_endpoint(payload: MarkEntry, _: dict = Depends(require_staff)):
    """Add or update a student's marks for an exam."""
    if payload.marks_obtained < 0 or payload.max_marks <= 0:
        raise HTTPException(status_code=400, detail="Invalid marks values.")
    if payload.marks_obtained > payload.max_marks:
        raise HTTPException(status_code=400, detail="Marks obtained cannot exceed max marks.")
    add_or_update_mark(
        payload.student_db_id, payload.subject_id,
        payload.exam_name, payload.marks_obtained, payload.max_marks
    )
    return {"detail": "Marks saved successfully."}


@app.get("/api/classrooms/{classroom_id}/marks")
def classroom_marks_endpoint(classroom_id: int, subject_id: Optional[int] = None, _: dict = Depends(require_staff)):
    """Get all marks for a classroom, optionally filtered by subject."""
    return get_marks_for_classroom(classroom_id, subject_id)


# ---------------------------------------------------------
# SESSIONS & ATTENDANCE (per classroom + subject)
# ---------------------------------------------------------
@app.post("/api/classrooms/{classroom_id}/subjects/{subject_id}/sessions")
def start_session_endpoint(classroom_id: int, subject_id: int, user: dict = Depends(require_staff)):
    return start_subject_session(classroom_id, subject_id, user["id"])


@app.get("/api/classrooms/{classroom_id}/subjects/{subject_id}/today-session")
def today_session_endpoint(classroom_id: int, subject_id: int, user: dict = Depends(require_staff)):
    session = get_latest_open_session(classroom_id, subject_id, user["id"])
    return session or {}


@app.get("/api/classrooms/{classroom_id}/subjects/{subject_id}/sessions")
def list_subject_sessions_endpoint(classroom_id: int, subject_id: int, _: dict = Depends(require_staff)):
    return get_sessions_for_subject(classroom_id, subject_id)


@app.post("/api/sessions/{session_id}/end")
def end_session_endpoint(session_id: int, _: dict = Depends(require_staff)):
    result = end_session(session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return result


@app.post("/api/sessions/{session_id}/attendance/{student_id}")
def mark_attendance_endpoint(session_id: int, student_id: int, payload: AttendanceMark, _: dict = Depends(require_staff)):
    if payload.status not in ("present", "absent"):
        raise HTTPException(status_code=400, detail="status must be 'present' or 'absent'")
    mark_attendance(session_id, student_id, payload.status)
    return {"detail": "ok"}


@app.get("/api/sessions/{session_id}/attendance")
def get_session_attendance_endpoint(session_id: int, _: dict = Depends(require_staff)):
    return get_session_attendance(session_id)


@app.get("/api/classrooms/{classroom_id}/attendance-summary")
def attendance_summary_endpoint(classroom_id: int, subject_id: Optional[int] = None, _: dict = Depends(require_staff)):
    return get_attendance_summary(classroom_id, subject_id)


@app.get("/api/classrooms/{classroom_id}/students/{student_id}/log")
def student_log_endpoint(classroom_id: int, student_id: int, _: dict = Depends(require_staff)):
    return get_student_session_log(classroom_id, student_id)


# ---------------------------------------------------------
# STUDENT-FACING ATTENDANCE + MARKS REPORT
# ---------------------------------------------------------
@app.get("/api/students/user/{user_id}/report")
def student_report_endpoint(user_id: int, user: dict = Depends(get_current_user)):
    ensure_self_or_staff(user, user_id)
    return get_student_subject_report(user_id)


# ---------------------------------------------------------
# QUIZZES
# ---------------------------------------------------------
class QuizCreate(BaseModel):
    title: str
    subject_id: int
    classroom_id: int
    questions: list  # List of {id, question, options: {A,B,C,D}, correct}


class QuizSubmit(BaseModel):
    answers: dict  # {question_id: chosen_option}


class QuizToggle(BaseModel):
    is_active: bool


def _ensure_quiz_owner(quiz_id: int, user: dict):
    owner_id = get_quiz_teacher_id(quiz_id)
    if owner_id is None:
        raise HTTPException(status_code=404, detail="Quiz not found.")
    if user["role"] != "admin" and owner_id != user["id"]:
        raise HTTPException(status_code=403, detail="You can only manage your own quizzes.")


@app.post("/api/quizzes")
def create_quiz_endpoint(payload: QuizCreate, user: dict = Depends(require_teacher)):
    """Teacher creates a new quiz for a classroom."""
    if not payload.questions:
        raise HTTPException(status_code=400, detail="Quiz must have at least one question.")
    quiz_id = create_quiz(
        payload.title, payload.subject_id,
        user["id"], payload.classroom_id,
        payload.questions,
    )
    return {"id": quiz_id, "detail": "Quiz created successfully."}


@app.get("/api/quizzes/teacher/{teacher_id}")
def list_teacher_quizzes(teacher_id: int, user: dict = Depends(require_staff)):
    """List all quizzes created by this teacher."""
    if user["role"] == "teacher" and user["id"] != teacher_id:
        raise HTTPException(status_code=403, detail="You can only view your own quizzes.")
    return {"quizzes": get_quizzes_for_teacher(teacher_id)}


@app.get("/api/quizzes/student/{user_id}")
def list_student_quizzes(user_id: int, user: dict = Depends(require_student)):
    """List all active quizzes available to this student (without answers)."""
    if user["id"] != user_id:
        raise HTTPException(status_code=403, detail="You can only view your own quizzes.")
    return {"quizzes": get_quizzes_for_student(user_id)}


@app.post("/api/quizzes/{quiz_id}/submit")
def submit_quiz_endpoint(quiz_id: int, payload: QuizSubmit, user: dict = Depends(require_student)):
    """Student submits quiz answers. Each student gets one attempt."""
    result = submit_quiz(quiz_id, user["id"], payload.answers)
    if result is None:
        raise HTTPException(status_code=404, detail="Quiz not found.")
    if result == "not_enrolled":
        raise HTTPException(status_code=403, detail="This quiz isn't for your classroom.")
    if result == "inactive":
        raise HTTPException(status_code=400, detail="This quiz is closed.")
    if result == "already_submitted":
        raise HTTPException(status_code=409, detail="You have already submitted this quiz.")
    return result


@app.get("/api/quizzes/{quiz_id}/results")
def quiz_results_endpoint(quiz_id: int, user: dict = Depends(require_staff)):
    """Teacher views all student submissions for a quiz."""
    _ensure_quiz_owner(quiz_id, user)
    return {"results": get_quiz_results(quiz_id)}


@app.patch("/api/quizzes/{quiz_id}/toggle")
def toggle_quiz_endpoint(quiz_id: int, payload: QuizToggle, user: dict = Depends(require_staff)):
    """Activate or deactivate a quiz."""
    _ensure_quiz_owner(quiz_id, user)
    toggle_quiz_active(quiz_id, get_quiz_teacher_id(quiz_id), payload.is_active)
    return {"detail": "Quiz status updated."}
