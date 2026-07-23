import sqlite3
#this is db
#We working together
DB_PATH = "eduzen.db"

def init_db():
    """Sets up SQLite database table for uploaded files."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # --- NEW: Classrooms & Attendance feature ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS classrooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            classroom_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            student_id TEXT NOT NULL,
            FOREIGN KEY (classroom_id) REFERENCES classrooms (id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS class_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            classroom_id INTEGER NOT NULL,
            session_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (classroom_id) REFERENCES classrooms (id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('present', 'absent')),
            UNIQUE(session_id, student_id),
            FOREIGN KEY (session_id) REFERENCES class_sessions (id),
            FOREIGN KEY (student_id) REFERENCES students (id)
        )
    """)
    # --- END NEW ---

    conn.commit()
    conn.close()

def add_material(filename: str):
    """Saves the name of the uploaded PDF to the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO materials (filename) VALUES (?)", (filename,))
    conn.commit()
    conn.close()

def get_materials():
    """Fetches all uploaded PDFs to show on the frontend."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT filename, uploaded_at FROM materials ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [{"filename": r[0], "uploaded_at": r[1]} for r in rows]


# =========================================================================
# NEW: Classrooms & Attendance
# =========================================================================

def create_classroom(name: str) -> int:
    """Creates a new classroom/section and returns its id."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO classrooms (name) VALUES (?)", (name,))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def get_classrooms():
    """Lists all classrooms, most recently created first."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, created_at FROM classrooms ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "created_at": r[2]} for r in rows]


def add_student(classroom_id: int, name: str, student_id: str) -> int:
    """Enrolls a student into a classroom and returns the student's row id."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO students (classroom_id, name, student_id) VALUES (?, ?, ?)",
        (classroom_id, name, student_id),
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def get_students(classroom_id: int):
    """Lists all students enrolled in one classroom, alphabetically."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, student_id FROM students WHERE classroom_id = ? ORDER BY name",
        (classroom_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "student_id": r[2]} for r in rows]


def create_session(classroom_id: int) -> dict:
    """Starts a new lecture/attendance session for a classroom (timestamped now)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO class_sessions (classroom_id) VALUES (?)", (classroom_id,))
    conn.commit()
    new_id = cursor.lastrowid
    cursor.execute("SELECT session_date FROM class_sessions WHERE id = ?", (new_id,))
    session_date = cursor.fetchone()[0]
    conn.close()
    return {"id": new_id, "session_date": session_date}


def get_sessions(classroom_id: int):
    """Lists all lecture sessions held for a classroom, most recent first."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, session_date FROM class_sessions WHERE classroom_id = ? ORDER BY id DESC",
        (classroom_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "session_date": r[1]} for r in rows]


def mark_attendance(session_id: int, student_id: int, status: str):
    """Marks (or re-marks, if the teacher clicks the other button) one
    student's attendance for one session. Upserts so clicking Present then
    Absent updates the same row instead of creating duplicates."""
    if status not in ("present", "absent"):
        raise ValueError("status must be 'present' or 'absent'")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO attendance_records (session_id, student_id, status)
           VALUES (?, ?, ?)
           ON CONFLICT(session_id, student_id) DO UPDATE SET status = excluded.status""",
        (session_id, student_id, status),
    )
    conn.commit()
    conn.close()


def get_session_attendance(session_id: int):
    """Returns {student_id: 'present'|'absent'} for one session - lets the
    frontend show which buttons should already be highlighted."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT student_id, status FROM attendance_records WHERE session_id = ?",
        (session_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return {r[0]: r[1] for r in rows}


def get_attendance_summary(classroom_id: int):
    """Per-student totals for a classroom: total lectures held, how many
    the student attended, and their attendance percentage."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM class_sessions WHERE classroom_id = ?", (classroom_id,))
    total_sessions = cursor.fetchone()[0]

    cursor.execute(
        "SELECT id, name, student_id FROM students WHERE classroom_id = ? ORDER BY name",
        (classroom_id,),
    )
    students = cursor.fetchall()

    summary = []
    for sid, name, roll in students:
        cursor.execute(
            """SELECT COUNT(*) FROM attendance_records ar
               JOIN class_sessions cs ON ar.session_id = cs.id
               WHERE cs.classroom_id = ? AND ar.student_id = ? AND ar.status = 'present'""",
            (classroom_id, sid),
        )
        attended = cursor.fetchone()[0]
        percentage = round((attended / total_sessions) * 100, 1) if total_sessions else 0.0
        summary.append({
            "student_id": sid,
            "name": name,
            "roll_no": roll,
            "total_classes": total_sessions,
            "attended": attended,
            "percentage": percentage,
        })

    conn.close()
    return summary


def get_student_session_log(classroom_id: int, student_id: int):
    """Session-by-session present/absent/not-marked history for one student -
    powers the 'which classes were present/absent' list view."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """SELECT cs.id, cs.session_date, COALESCE(ar.status, 'not marked')
           FROM class_sessions cs
           LEFT JOIN attendance_records ar
             ON ar.session_id = cs.id AND ar.student_id = ?
           WHERE cs.classroom_id = ?
           ORDER BY cs.id DESC""",
        (student_id, classroom_id),
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"session_id": r[0], "session_date": r[1], "status": r[2]} for r in rows]