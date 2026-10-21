import hashlib
import hmac
import os
import random
import sqlite3
from typing import Optional

import bcrypt

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "svmit.db")

# bcrypt only uses the first 72 bytes of a password and rejects longer input.
MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _is_legacy_hash(stored_hash: str) -> bool:
    """Old accounts were stored as unsalted SHA-256 hex digests."""
    return not stored_hash.startswith("$2")


def verify_password(password: str, stored_hash: str) -> bool:
    if _is_legacy_hash(stored_hash):
        legacy = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return hmac.compare_digest(legacy, stored_hash)
    try:
        return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
    except ValueError:
        return False


def _connect():
    conn = sqlite3.connect(DB_PATH, timeout=15, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 10000")
    return conn


def _has_column(conn, table_name: str, column_name: str) -> bool:
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    return any(row[1] == column_name for row in cursor.fetchall())


def _get_table_columns(conn, table_name: str) -> list:
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in cursor.fetchall()]


def _ensure_column(conn, table_name: str, column_name: str, definition: str):
    if not _has_column(conn, table_name, column_name):
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def init_db():
    """Create the database schema and seed a small, realistic academic dataset."""
    conn = _connect()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            classroom_id INTEGER,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    _ensure_column(conn, "materials", "classroom_id", "INTEGER")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('teacher', 'student', 'admin')),
            department TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT NOT NULL UNIQUE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS classrooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS classroom_subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            classroom_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            teacher_id INTEGER NOT NULL,
            UNIQUE(classroom_id, subject_id),
            FOREIGN KEY (classroom_id) REFERENCES classrooms (id),
            FOREIGN KEY (subject_id) REFERENCES subjects (id),
            FOREIGN KEY (teacher_id) REFERENCES users (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            classroom_id INTEGER NOT NULL,
            user_id INTEGER,
            name TEXT NOT NULL,
            student_id TEXT NOT NULL,
            FOREIGN KEY (classroom_id) REFERENCES classrooms (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    _ensure_column(conn, "students", "user_id", "INTEGER")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS class_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            classroom_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            teacher_id INTEGER NOT NULL,
            session_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_ended INTEGER NOT NULL DEFAULT 0,
            ended_at TIMESTAMP,
            FOREIGN KEY (classroom_id) REFERENCES classrooms (id),
            FOREIGN KEY (subject_id) REFERENCES subjects (id),
            FOREIGN KEY (teacher_id) REFERENCES users (id)
        )
    """)

    _ensure_column(conn, "class_sessions", "subject_id", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(conn, "class_sessions", "teacher_id", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(conn, "class_sessions", "is_ended", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(conn, "class_sessions", "ended_at", "TIMESTAMP")

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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS marks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            exam_name TEXT NOT NULL,
            marks_obtained REAL NOT NULL,
            max_marks REAL NOT NULL,
            UNIQUE(student_id, subject_id, exam_name),
            FOREIGN KEY (student_id) REFERENCES students (id),
            FOREIGN KEY (subject_id) REFERENCES subjects (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teacher_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            department TEXT NOT NULL,
            course_load TEXT NOT NULL,
            current_topic TEXT NOT NULL,
            routine TEXT NOT NULL,
            office_hours TEXT NOT NULL,
            weekly_hours INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            department TEXT NOT NULL,
            level TEXT NOT NULL,
            next_goal TEXT NOT NULL,
            last_activity TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quizzes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            subject_id INTEGER NOT NULL,
            teacher_id INTEGER NOT NULL,
            classroom_id INTEGER NOT NULL,
            questions_json TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (subject_id) REFERENCES subjects (id),
            FOREIGN KEY (teacher_id) REFERENCES users (id),
            FOREIGN KEY (classroom_id) REFERENCES classrooms (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quiz_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quiz_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            answers_json TEXT NOT NULL,
            score INTEGER NOT NULL DEFAULT 0,
            total INTEGER NOT NULL DEFAULT 0,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(quiz_id, user_id),
            FOREIGN KEY (quiz_id) REFERENCES quizzes (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    conn.commit()
    _seed_realistic_data(conn)
    conn.commit()
    conn.close()


def _get_or_create_user(cursor, name, email, password, role, department):
    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute(
        "INSERT INTO users (name, email, password_hash, role, department) VALUES (?, ?, ?, ?, ?)",
        (name, email, hash_password(password), role, department),
    )
    return cursor.lastrowid


def _get_or_create_subject(cursor, name, code):
    cursor.execute("SELECT id FROM subjects WHERE code = ?", (code,))
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute("INSERT INTO subjects (name, code) VALUES (?, ?)", (name, code))
    return cursor.lastrowid


def _get_or_create_classroom(cursor, name):
    cursor.execute("SELECT id FROM classrooms WHERE name = ?", (name,))
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute("INSERT INTO classrooms (name) VALUES (?)", (name,))
    return cursor.lastrowid


def _assign_subject_to_teacher(cursor, classroom_id, subject_id, teacher_id):
    cursor.execute(
        "SELECT id FROM classroom_subjects WHERE classroom_id = ? AND subject_id = ?",
        (classroom_id, subject_id),
    )
    if cursor.fetchone():
        return
    cursor.execute(
        "INSERT INTO classroom_subjects (classroom_id, subject_id, teacher_id) VALUES (?, ?, ?)",
        (classroom_id, subject_id, teacher_id),
    )


def _enroll_student(cursor, classroom_id, name, roll_no, user_id=None):
    cursor.execute(
        "SELECT id FROM students WHERE classroom_id = ? AND student_id = ?",
        (classroom_id, roll_no),
    )
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute(
        "INSERT INTO students (classroom_id, user_id, name, student_id) VALUES (?, ?, ?, ?)",
        (classroom_id, user_id, name, roll_no),
    )
    return cursor.lastrowid


def _seed_realistic_data(conn):
    cursor = conn.cursor()

    # Always ensure the master admin account exists
    cursor.execute("SELECT id FROM users WHERE email = 'admin@svmit.edu'")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO users (name, email, password_hash, role, department) VALUES (?, ?, ?, ?, ?)",
            ("SVMIT Admin", "admin@svmit.edu", hash_password("admin123"), "admin", "Administration"),
        )
        conn.commit()


def add_material(filename: str, classroom_id: Optional[int] = None):
    conn = _connect()
    cursor = conn.cursor()
    cid = int(classroom_id) if classroom_id and str(classroom_id).isdigit() and int(classroom_id) > 0 else None
    cursor.execute("INSERT INTO materials (filename, classroom_id) VALUES (?, ?)", (filename, cid))
    conn.commit()
    conn.close()


def get_materials(classroom_id: Optional[int] = None, user_id: Optional[int] = None):
    conn = _connect()
    cursor = conn.cursor()

    target_cid = None
    if classroom_id and str(classroom_id).isdigit() and int(classroom_id) > 0:
        target_cid = int(classroom_id)
    elif user_id:
        cursor.execute("SELECT classroom_id FROM students WHERE user_id = ?", (user_id,))
        srow = cursor.fetchone()
        if srow:
            target_cid = srow[0]

    if target_cid:
        query = """
            SELECT m.filename, m.uploaded_at, m.classroom_id, c.name as classroom_name
            FROM materials m
            LEFT JOIN classrooms c ON m.classroom_id = c.id
            WHERE m.classroom_id IS NULL OR m.classroom_id = 0 OR m.classroom_id = ?
            ORDER BY m.id DESC
        """
        cursor.execute(query, (target_cid,))
    else:
        query = """
            SELECT m.filename, m.uploaded_at, m.classroom_id, c.name as classroom_name
            FROM materials m
            LEFT JOIN classrooms c ON m.classroom_id = c.id
            ORDER BY m.id DESC
        """
        cursor.execute(query)

    rows = cursor.fetchall()
    conn.close()
    return [{
        "filename": r[0],
        "uploaded_at": r[1],
        "classroom_id": r[2],
        "classroom_name": r[3]
    } for r in rows]


def get_subjects():
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, code FROM subjects ORDER BY name")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "code": r[2]} for r in rows]


def create_subject(name: str, code: str):
    conn = _connect()
    cursor = conn.cursor()
    clean_code = code.strip().upper()
    clean_name = name.strip()
    cursor.execute("SELECT id FROM subjects WHERE code = ?", (clean_code,))
    if cursor.fetchone():
        conn.close()
        return None
    cursor.execute(
        "INSERT INTO subjects (name, code) VALUES (?, ?)",
        (clean_name, clean_code),
    )
    sid = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"id": sid, "name": clean_name, "code": clean_code}


def assign_subject_to_classroom(classroom_id: int, subject_id: int, teacher_id: int):
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM classroom_subjects WHERE classroom_id = ? AND subject_id = ?",
        (classroom_id, subject_id),
    )
    row = cursor.fetchone()
    if row:
        cursor.execute(
            "UPDATE classroom_subjects SET teacher_id = ? WHERE id = ?",
            (teacher_id, row[0]),
        )
    else:
        cursor.execute(
            "INSERT INTO classroom_subjects (classroom_id, subject_id, teacher_id) VALUES (?, ?, ?)",
            (classroom_id, subject_id, teacher_id),
        )
    conn.commit()
    conn.close()
    return True


def get_teacher_classes(teacher_id: int):
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT cs.id, c.id, c.name, s.id, s.name, s.code
           FROM classroom_subjects cs
           JOIN classrooms c ON c.id = cs.classroom_id
           JOIN subjects s ON s.id = cs.subject_id
           WHERE cs.teacher_id = ?
           ORDER BY c.name, s.name""",
        (teacher_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "assignment_id": r[0],
            "classroom_id": r[1],
            "classroom_name": r[2],
            "subject_id": r[3],
            "subject_name": r[4],
            "subject_code": r[5],
        }
        for r in rows
    ]


def create_classroom(name: str) -> int:
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO classrooms (name) VALUES (?)", (name,))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def get_classrooms():
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, created_at FROM classrooms ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "created_at": r[2]} for r in rows]


def add_student(classroom_id: int, name: str, student_id: str, email: str = None) -> int:
    conn = _connect()
    cursor = conn.cursor()
    user_id = None
    if email:
        cursor.execute("SELECT id FROM users WHERE email = ? AND role = 'student'", (email,))
        row = cursor.fetchone()
        if row:
            user_id = row[0]
    cursor.execute(
        "INSERT INTO students (classroom_id, user_id, name, student_id) VALUES (?, ?, ?, ?)",
        (classroom_id, user_id, name, student_id),
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def get_students(classroom_id: int):
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, student_id, user_id FROM students WHERE classroom_id = ? ORDER BY name",
        (classroom_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "student_id": r[2], "user_id": r[3]} for r in rows]


def start_subject_session(classroom_id: int, subject_id: int, teacher_id: int) -> dict:
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO class_sessions (classroom_id, subject_id, teacher_id) VALUES (?, ?, ?)",
        (classroom_id, subject_id, teacher_id),
    )
    conn.commit()
    new_id = cursor.lastrowid
    cursor.execute("SELECT session_date FROM class_sessions WHERE id = ?", (new_id,))
    session_date = cursor.fetchone()[0]
    conn.close()
    return {"id": new_id, "session_date": session_date, "classroom_id": classroom_id, "subject_id": subject_id}


def get_latest_open_session(classroom_id: int, subject_id: int, teacher_id: int):
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT id, session_date FROM class_sessions
           WHERE classroom_id = ? AND subject_id = ? AND teacher_id = ?
           AND date(session_date) = date('now') AND is_ended = 0
           ORDER BY id DESC LIMIT 1""",
        (classroom_id, subject_id, teacher_id),
    )
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return None
    return {"id": row[0], "session_date": row[1]}


def end_session(session_id: int):
    """Finalize a session: any enrolled student with no attendance record yet
    for this session is marked absent by default, then the session is closed
    so it stops showing up as "today's active session" and a fresh one can
    be started later. Existing attendance records are left untouched."""
    conn = _connect()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT classroom_id, is_ended FROM class_sessions WHERE id = ?", (session_id,)
    )
    row = cursor.fetchone()
    if row is None:
        conn.close()
        return None

    classroom_id, already_ended = row
    if already_ended:
        conn.close()
        return {"id": session_id, "already_ended": True, "auto_absent": 0, "total_students": 0}

    cursor.execute("SELECT id FROM students WHERE classroom_id = ?", (classroom_id,))
    roster_ids = [r[0] for r in cursor.fetchall()]

    cursor.execute("SELECT student_id FROM attendance_records WHERE session_id = ?", (session_id,))
    already_marked = {r[0] for r in cursor.fetchall()}

    auto_absent_count = 0
    for sid in roster_ids:
        if sid not in already_marked:
            cursor.execute(
                "INSERT INTO attendance_records (session_id, student_id, status) VALUES (?, ?, 'absent')",
                (session_id, sid),
            )
            auto_absent_count += 1

    cursor.execute(
        "UPDATE class_sessions SET is_ended = 1, ended_at = CURRENT_TIMESTAMP WHERE id = ?",
        (session_id,),
    )

    conn.commit()
    conn.close()
    return {
        "id": session_id,
        "already_ended": False,
        "auto_absent": auto_absent_count,
        "total_students": len(roster_ids),
    }


def get_sessions_for_subject(classroom_id: int, subject_id: int):
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, session_date, is_ended, ended_at FROM class_sessions "
        "WHERE classroom_id = ? AND subject_id = ? ORDER BY id DESC",
        (classroom_id, subject_id),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {"id": r[0], "session_date": r[1], "is_ended": bool(r[2]), "ended_at": r[3]}
        for r in rows
    ]


def mark_attendance(session_id: int, student_id: int, status: str):
    if status not in ("present", "absent"):
        raise ValueError("status must be 'present' or 'absent'")
    conn = _connect()
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
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT student_id, status FROM attendance_records WHERE session_id = ?",
        (session_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return {r[0]: r[1] for r in rows}


def get_attendance_summary(classroom_id: int, subject_id: int = None):
    conn = _connect()
    cursor = conn.cursor()

    if subject_id is not None:
        cursor.execute(
            "SELECT COUNT(*) FROM class_sessions WHERE classroom_id = ? AND subject_id = ?",
            (classroom_id, subject_id),
        )
    else:
        cursor.execute("SELECT COUNT(*) FROM class_sessions WHERE classroom_id = ?", (classroom_id,))
    total_sessions = cursor.fetchone()[0]

    cursor.execute(
        "SELECT id, name, student_id FROM students WHERE classroom_id = ? ORDER BY name",
        (classroom_id,),
    )
    students = cursor.fetchall()

    summary = []
    for sid, name, roll in students:
        if subject_id is not None:
            cursor.execute(
                """SELECT COUNT(*) FROM attendance_records ar
                   JOIN class_sessions cs ON ar.session_id = cs.id
                   WHERE cs.classroom_id = ? AND cs.subject_id = ? AND ar.student_id = ? AND ar.status = 'present'""",
                (classroom_id, subject_id, sid),
            )
        else:
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
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT cs.id, cs.session_date, sub.name, COALESCE(ar.status, 'not marked')
           FROM class_sessions cs
           JOIN subjects sub ON sub.id = cs.subject_id
           LEFT JOIN attendance_records ar
             ON ar.session_id = cs.id AND ar.student_id = ?
           WHERE cs.classroom_id = ?
           ORDER BY cs.id DESC""",
        (student_id, classroom_id),
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"session_id": r[0], "session_date": r[1], "subject_name": r[2], "status": r[3]} for r in rows]


def get_student_subject_report(user_id: int):
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("SELECT id, classroom_id FROM students WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row is None or not row[1]:
        conn.close()
        return {"subjects": [], "overall_attendance": 0.0, "overall_marks_pct": 0.0}

    student_id, classroom_id = row

    cursor.execute(
        """SELECT s.id, s.name, s.code
           FROM classroom_subjects cs
           JOIN subjects s ON s.id = cs.subject_id
           WHERE cs.classroom_id = ?
           ORDER BY s.name""",
        (classroom_id,),
    )
    subject_rows = cursor.fetchall()

    subjects = []
    total_attended, total_sessions = 0, 0
    total_marks_obtained, total_max_marks = 0.0, 0.0

    for subject_id, subject_name, subject_code in subject_rows:
        cursor.execute(
            "SELECT COUNT(*) FROM class_sessions WHERE classroom_id = ? AND subject_id = ?",
            (classroom_id, subject_id),
        )
        sessions_held = cursor.fetchone()[0]

        cursor.execute(
            """SELECT COUNT(*) FROM attendance_records ar
               JOIN class_sessions cs ON ar.session_id = cs.id
               WHERE cs.classroom_id = ? AND cs.subject_id = ? AND ar.student_id = ? AND ar.status = 'present'""",
            (classroom_id, subject_id, student_id),
        )
        attended = cursor.fetchone()[0]
        attendance_pct = round((attended / sessions_held) * 100, 1) if sessions_held else 0.0

        cursor.execute(
            "SELECT exam_name, marks_obtained, max_marks FROM marks WHERE student_id = ? AND subject_id = ?",
            (student_id, subject_id),
        )
        marks_rows = cursor.fetchall()
        marks_list = [{"exam_name": m[0], "marks_obtained": m[1], "max_marks": m[2]} for m in marks_rows]
        subject_marks_obtained = sum(m[1] for m in marks_rows)
        subject_max_marks = sum(m[2] for m in marks_rows)

        subjects.append({
            "subject_id": subject_id,
            "subject_name": subject_name,
            "subject_code": subject_code,
            "sessions_held": sessions_held,
            "attended": attended,
            "attendance_pct": attendance_pct,
            "marks": marks_list,
            "marks_pct": round((subject_marks_obtained / subject_max_marks) * 100, 1) if subject_max_marks else 0.0,
        })

        total_attended += attended
        total_sessions += sessions_held
        total_marks_obtained += subject_marks_obtained
        total_max_marks += subject_max_marks

    conn.close()
    return {
        "subjects": subjects,
        "overall_attendance": round((total_attended / total_sessions) * 100, 1) if total_sessions else 0.0,
        "overall_marks_pct": round((total_marks_obtained / total_max_marks) * 100, 1) if total_max_marks else 0.0,
    }


def create_user(name: str, email: str, password: str, role: str, department: str, enrollment_no: str = None, classroom_id: int = None):
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    if cursor.fetchone():
        conn.close()
        return None

    cursor.execute(
        "INSERT INTO users (name, email, password_hash, role, department) VALUES (?, ?, ?, ?, ?)",
        (name, email, hash_password(password), role, department),
    )
    user_id = cursor.lastrowid

    if role == "teacher":
        faculty_id = enrollment_no.strip() if enrollment_no and enrollment_no.strip() else f"SVMITF{user_id:05d}"
        cursor.execute(
            "INSERT INTO teacher_profiles (user_id, department, course_load, current_topic, routine, office_hours, weekly_hours, faculty_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, department, "3 courses", "New curriculum design",
             "09:00-10:00 planning, 14:00-15:00 lectures", "Tue-Fri 14:00-15:00", 20, faculty_id),
        )
    else:
        enroll = enrollment_no.strip() if enrollment_no and enrollment_no.strip() else f"SVMIT{user_id:05d}"

        target_cid = None
        if classroom_id and str(classroom_id).isdigit() and int(classroom_id) > 0:
            target_cid = int(classroom_id)
        else:
            cursor.execute("SELECT id FROM classrooms ORDER BY id LIMIT 1")
            crow = cursor.fetchone()
            target_cid = crow[0] if crow else None

        cursor.execute(
            "INSERT INTO students (classroom_id, user_id, name, student_id) VALUES (?, ?, ?, ?)",
            (target_cid, user_id, name, enroll),
        )

        profile_columns = _get_table_columns(conn, "student_profiles")
        if all(col in profile_columns for col in ["attendance_rate", "progress_score", "topics_completed"]):
            cursor.execute(
                "INSERT INTO student_profiles (user_id, department, level, attendance_rate, progress_score, topics_completed, next_goal, last_activity) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id, department, "Year 2", 0.0, 0.0, 0, "Complete the weekly revision target", "Started a new study module"),
            )
        else:
            cursor.execute(
                "INSERT INTO student_profiles (user_id, department, level, next_goal, last_activity) VALUES (?, ?, ?, ?, ?)",
                (user_id, department, "Year 2", "Complete the weekly revision target", "Started a new study module"),
            )

    conn.commit()
    conn.close()
    return user_id



def is_admin(user_id: int) -> bool:
    """Return True if the given user_id belongs to an admin."""
    conn = _connect()
    row = conn.execute("SELECT role FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return bool(row and row[0] == "admin")


def get_all_users():
    """Return all non-admin users with id, name, email, role, department, created_at, classroom_id, classroom_name."""
    conn = _connect()
    cursor = conn.cursor()
    query = """
        SELECT u.id, u.name, u.email, u.role, u.department, u.created_at, s.classroom_id, c.name as classroom_name
        FROM users u
        LEFT JOIN students s ON s.user_id = u.id
        LEFT JOIN classrooms c ON c.id = s.classroom_id
        WHERE u.role != 'admin'
        ORDER BY u.created_at DESC
    """
    rows = cursor.execute(query).fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "name": r[1],
            "email": r[2],
            "role": r[3],
            "department": r[4],
            "created_at": r[5],
            "classroom_id": r[6],
            "classroom_name": r[7],
        }
        for r in rows
    ]


def update_student_classroom(user_id: int, classroom_id: int):
    conn = _connect()
    cursor = conn.cursor()
    cid = int(classroom_id) if classroom_id and str(classroom_id).isdigit() and int(classroom_id) > 0 else None
    cursor.execute("UPDATE students SET classroom_id = ? WHERE user_id = ?", (cid, user_id))
    conn.commit()
    conn.close()
    return True


def delete_user_by_id(user_id: int) -> bool:
    """Delete a user by id (non-admin only). Cascades all related records."""
    conn = _connect()
    cursor = conn.cursor()
    try:
        # Check user exists and is not admin
        cursor.execute("SELECT role FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            return False
        if row[0] == "admin":
            return False

        role = row[0]

        if role == "teacher":
            # Get sessions taught by this teacher
            cursor.execute("SELECT id FROM class_sessions WHERE teacher_id = ?", (user_id,))
            session_ids = [r[0] for r in cursor.fetchall()]
            for sid in session_ids:
                cursor.execute("DELETE FROM attendance_records WHERE session_id = ?", (sid,))
            cursor.execute("DELETE FROM class_sessions WHERE teacher_id = ?", (user_id,))
            # Remove subject assignments
            cursor.execute("DELETE FROM classroom_subjects WHERE teacher_id = ?", (user_id,))
            # Remove marks entered by this teacher (marks don't store teacher_id, skip)
            cursor.execute("DELETE FROM quizzes WHERE teacher_id = ?", (user_id,))
            cursor.execute("DELETE FROM teacher_profiles WHERE user_id = ?", (user_id,))

        if role == "student":
            # Delete quiz submissions
            cursor.execute("DELETE FROM quiz_submissions WHERE user_id = ?", (user_id,))
            cursor.execute("DELETE FROM student_profiles WHERE user_id = ?", (user_id,))
            # Get students.id for attendance/marks
            cursor.execute("SELECT id FROM students WHERE user_id = ?", (user_id,))
            student_rows = cursor.fetchall()
            for (sid,) in student_rows:
                cursor.execute("DELETE FROM attendance_records WHERE student_id = ?", (sid,))
                cursor.execute("DELETE FROM marks WHERE student_id = ?", (sid,))
            cursor.execute("DELETE FROM students WHERE user_id = ?", (user_id,))

        # Finally delete the user
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def authenticate_user(email: str, password: str):
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, email, role, department, password_hash FROM users WHERE email = ?",
        (email,),
    )
    row = cursor.fetchone()
    if row is None or not verify_password(password, row[5]):
        conn.close()
        return None
    # Upgrade old SHA-256 hashes to bcrypt the first time the user logs in.
    if _is_legacy_hash(row[5]):
        cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(password), row[0]))
        conn.commit()
    conn.close()
    return {"id": row[0], "name": row[1], "email": row[2], "role": row[3], "department": row[4]}


def get_user_by_id(user_id: int):
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, role, department FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return None
    return {"id": row[0], "name": row[1], "email": row[2], "role": row[3], "department": row[4]}


def change_password(user_id: int, current_password: str, new_password: str) -> str:
    """
    Attempt to change a user's password.
    Returns 'ok' on success, 'wrong_password' if current password is wrong,
    or 'not_found' if the user doesn't exist.
    """
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT password_hash FROM users WHERE id = ? AND role != 'admin'",
        (user_id,),
    )
    row = cursor.fetchone()
    if row is None:
        conn.close()
        return "not_found"
    if not verify_password(current_password, row[0]):
        conn.close()
        return "wrong_password"
    cursor.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (hash_password(new_password), user_id),
    )
    conn.commit()
    conn.close()
    return "ok"


def get_student_dashboard(user_id: int):
    user = get_user_by_id(user_id)
    if user is None:
        return None

    report = get_student_subject_report(user_id)
    classrooms = get_classrooms()

    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT next_goal, last_activity FROM student_profiles WHERE user_id = ?", (user_id,)
    )
    row = cursor.fetchone()
    conn.close()
    next_goal = row[0] if row else "Complete the next revision cycle"
    last_activity = row[1] if row else "Reviewed course content"

    return {
        "id": user["id"],
        "name": user["name"],
        "role": "student",
        "department": user["department"],
        "attendance_rate": report["overall_attendance"],
        "progress_score": report["overall_marks_pct"],
        "topics_completed": len(report["subjects"]),
        "materials_available": len(get_materials()),
        "classroom_count": len(classrooms),
        "next_goal": next_goal,
        "latest_activity": last_activity,
    }


def get_teacher_dashboard(user_id: int):
    user = get_user_by_id(user_id)
    if user is None:
        return None

    classes = get_teacher_classes(user_id)
    classroom_ids = {c["classroom_id"] for c in classes}

    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM class_sessions WHERE teacher_id = ?", (user_id,))
    total_sessions = cursor.fetchone()[0]
    cursor.execute(
        "SELECT department, course_load, current_topic, routine, office_hours, weekly_hours "
        "FROM teacher_profiles WHERE user_id = ?",
        (user_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if row is None:
        profile = {
            "department": user["department"], "course_load": "N/A", "current_topic": "N/A",
            "routine": "N/A", "office_hours": "N/A", "weekly_hours": 0,
        }
    else:
        profile = {
            "department": row[0], "course_load": row[1], "current_topic": row[2],
            "routine": row[3], "office_hours": row[4], "weekly_hours": row[5],
        }

    return {
        "id": user["id"],
        "name": user["name"],
        "role": "teacher",
        **profile,
        "classroom_count": len(classroom_ids),
        "session_count": total_sessions,
        "materials_available": len(get_materials()),
    }


# ──────────────────────────────────────────────────────────────
# MARKS — Teacher entry
# ──────────────────────────────────────────────────────────────

def add_or_update_mark(student_id: int, subject_id: int, exam_name: str, marks_obtained: float, max_marks: float):
    """Insert or replace a student's mark entry."""
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO marks (student_id, subject_id, exam_name, marks_obtained, max_marks)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(student_id, subject_id, exam_name)
           DO UPDATE SET marks_obtained = excluded.marks_obtained, max_marks = excluded.max_marks""",
        (student_id, subject_id, exam_name, marks_obtained, max_marks),
    )
    conn.commit()
    conn.close()


def get_marks_for_classroom(classroom_id: int, subject_id: int = None):
    """Return all marks for students in a classroom, optionally filtered by subject."""
    conn = _connect()
    cursor = conn.cursor()
    if subject_id:
        cursor.execute(
            """SELECT s.id, s.name, s.student_id, m.subject_id, sub.name, m.exam_name, m.marks_obtained, m.max_marks
               FROM students s
               LEFT JOIN marks m ON m.student_id = s.id AND m.subject_id = ?
               LEFT JOIN subjects sub ON sub.id = m.subject_id
               WHERE s.classroom_id = ?
               ORDER BY s.name, m.exam_name""",
            (subject_id, classroom_id),
        )
    else:
        cursor.execute(
            """SELECT s.id, s.name, s.student_id, m.subject_id, sub.name, m.exam_name, m.marks_obtained, m.max_marks
               FROM students s
               LEFT JOIN marks m ON m.student_id = s.id
               LEFT JOIN subjects sub ON sub.id = m.subject_id
               WHERE s.classroom_id = ?
               ORDER BY s.name, sub.name, m.exam_name""",
            (classroom_id,),
        )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "student_db_id": r[0], "student_name": r[1], "enrollment_no": r[2],
            "subject_id": r[3], "subject_name": r[4],
            "exam_name": r[5], "marks_obtained": r[6], "max_marks": r[7],
        }
        for r in rows
    ]


def search_student_by_enrollment(enrollment_no: str):
    """Find a student by enrollment/roll number and return their full attendance + marks report."""
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, student_id, classroom_id, user_id FROM students WHERE student_id = ?",
        (enrollment_no,)
    )
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return None
    student_db_id, name, roll, classroom_id, user_id = row

    # Reuse subject report logic
    if user_id:
        report = get_student_subject_report(user_id)
    else:
        # Build report manually from student_db_id
        report = _build_report_for_student(student_db_id, classroom_id)

    return {
        "student_db_id": student_db_id,
        "name": name,
        "enrollment_no": roll,
        "classroom_id": classroom_id,
        "user_id": user_id,
        **report,
    }


def _build_report_for_student(student_id: int, classroom_id: int):
    """Build attendance + marks report for a student by DB id (no user_id required)."""
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT s.id, s.name, s.code
           FROM classroom_subjects cs
           JOIN subjects s ON s.id = cs.subject_id
           WHERE cs.classroom_id = ?
           ORDER BY s.name""",
        (classroom_id,),
    )
    subject_rows = cursor.fetchall()

    subjects = []
    total_attended, total_sessions = 0, 0
    total_marks_obtained, total_max_marks = 0.0, 0.0

    for subject_id, subject_name, subject_code in subject_rows:
        cursor.execute(
            "SELECT COUNT(*) FROM class_sessions WHERE classroom_id = ? AND subject_id = ?",
            (classroom_id, subject_id),
        )
        sessions_held = cursor.fetchone()[0]
        cursor.execute(
            """SELECT COUNT(*) FROM attendance_records ar
               JOIN class_sessions cs ON ar.session_id = cs.id
               WHERE cs.classroom_id = ? AND cs.subject_id = ? AND ar.student_id = ? AND ar.status = 'present'""",
            (classroom_id, subject_id, student_id),
        )
        attended = cursor.fetchone()[0]
        attendance_pct = round((attended / sessions_held) * 100, 1) if sessions_held else 0.0

        cursor.execute(
            "SELECT exam_name, marks_obtained, max_marks FROM marks WHERE student_id = ? AND subject_id = ?",
            (student_id, subject_id),
        )
        marks_rows = cursor.fetchall()
        marks_list = [{"exam_name": m[0], "marks_obtained": m[1], "max_marks": m[2]} for m in marks_rows]
        sub_obtained = sum(m[1] for m in marks_rows)
        sub_max = sum(m[2] for m in marks_rows)

        subjects.append({
            "subject_id": subject_id, "subject_name": subject_name, "subject_code": subject_code,
            "sessions_held": sessions_held, "attended": attended, "attendance_pct": attendance_pct,
            "marks": marks_list,
            "marks_pct": round((sub_obtained / sub_max) * 100, 1) if sub_max else 0.0,
        })
        total_attended += attended
        total_sessions += sessions_held
        total_marks_obtained += sub_obtained
        total_max_marks += sub_max

    conn.close()
    return {
        "subjects": subjects,
        "overall_attendance": round((total_attended / total_sessions) * 100, 1) if total_sessions else 0.0,
        "overall_marks_pct": round((total_marks_obtained / total_max_marks) * 100, 1) if total_max_marks else 0.0,
    }


# ──────────────────────────────────────────────────────────────
# QUIZZES
# ──────────────────────────────────────────────────────────────

def create_quiz(title: str, subject_id: int, teacher_id: int, classroom_id: int, questions: list) -> int:
    import json
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO quizzes (title, subject_id, teacher_id, classroom_id, questions_json) VALUES (?, ?, ?, ?, ?)",
        (title, subject_id, teacher_id, classroom_id, json.dumps(questions)),
    )
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id


def get_quizzes_for_teacher(teacher_id: int):
    import json
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT q.id, q.title, q.subject_id, s.name, q.classroom_id, c.name, q.is_active, q.created_at,
                  q.questions_json
           FROM quizzes q
           JOIN subjects s ON s.id = q.subject_id
           JOIN classrooms c ON c.id = q.classroom_id
           WHERE q.teacher_id = ?
           ORDER BY q.created_at DESC""",
        (teacher_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": r[0], "title": r[1], "subject_id": r[2], "subject_name": r[3],
            "classroom_id": r[4], "classroom_name": r[5], "is_active": bool(r[6]),
            "created_at": r[7], "question_count": len(json.loads(r[8])),
        }
        for r in rows
    ]


def get_quizzes_for_student(user_id: int):
    """Return active quizzes for classrooms the student is enrolled in."""
    import json
    conn = _connect()
    cursor = conn.cursor()
    # Find student's classrooms
    cursor.execute("SELECT classroom_id FROM students WHERE user_id = ?", (user_id,))
    classroom_ids = [r[0] for r in cursor.fetchall()]
    if not classroom_ids:
        conn.close()
        return []

    placeholders = ",".join("?" * len(classroom_ids))
    cursor.execute(
        f"""SELECT q.id, q.title, q.subject_id, s.name, q.classroom_id, c.name, q.created_at, q.questions_json,
                   qs.score, qs.total, qs.submitted_at
            FROM quizzes q
            JOIN subjects s ON s.id = q.subject_id
            JOIN classrooms c ON c.id = q.classroom_id
            LEFT JOIN quiz_submissions qs ON qs.quiz_id = q.id AND qs.user_id = ?
            WHERE q.classroom_id IN ({placeholders}) AND q.is_active = 1
            ORDER BY q.created_at DESC""",
        [user_id] + classroom_ids,
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": r[0], "title": r[1], "subject_id": r[2], "subject_name": r[3],
            "classroom_id": r[4], "classroom_name": r[5], "created_at": r[6],
            "question_count": len(json.loads(r[7])),
            # Never send the answer key to students.
            "questions": [
                {k: v for k, v in q.items() if k != "correct"}
                for q in json.loads(r[7])
            ],
            "submitted": r[8] is not None,
            "score": r[8], "total": r[9], "submitted_at": r[10],
        }
        for r in rows
    ]


def get_student_classroom_ids(user_id: int) -> list:
    conn = _connect()
    rows = conn.execute("SELECT classroom_id FROM students WHERE user_id = ?", (user_id,)).fetchall()
    conn.close()
    return [r[0] for r in rows]


def get_quiz_teacher_id(quiz_id: int):
    conn = _connect()
    row = conn.execute("SELECT teacher_id FROM quizzes WHERE id = ?", (quiz_id,)).fetchone()
    conn.close()
    return row[0] if row else None


def get_quiz_with_questions(quiz_id: int):
    import json
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT q.id, q.title, q.subject_id, s.name, q.classroom_id, c.name, q.is_active, q.teacher_id,
                  q.questions_json
           FROM quizzes q
           JOIN subjects s ON s.id = q.subject_id
           JOIN classrooms c ON c.id = q.classroom_id
           WHERE q.id = ?""",
        (quiz_id,),
    )
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return None
    return {
        "id": row[0], "title": row[1], "subject_id": row[2], "subject_name": row[3],
        "classroom_id": row[4], "classroom_name": row[5], "is_active": bool(row[6]),
        "teacher_id": row[7], "questions": json.loads(row[8]),
    }


def submit_quiz(quiz_id: int, user_id: int, answers: dict):
    """
    Grade quiz and store submission.
    Returns a score summary, None if the quiz doesn't exist, or one of
    'not_enrolled', 'inactive', 'already_submitted'.
    """
    import json
    quiz = get_quiz_with_questions(quiz_id)
    if quiz is None:
        return None
    if not quiz["is_active"]:
        return "inactive"
    if quiz["classroom_id"] not in get_student_classroom_ids(user_id):
        return "not_enrolled"
    questions = quiz["questions"]
    score = 0
    for q in questions:
        qid = str(q.get("id", q.get("question", "")))
        if answers.get(qid) == q.get("correct"):
            score += 1
    total = len(questions)
    conn = _connect()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """INSERT INTO quiz_submissions (quiz_id, user_id, answers_json, score, total)
               VALUES (?, ?, ?, ?, ?)""",
            (quiz_id, user_id, json.dumps(answers), score, total),
        )
    except sqlite3.IntegrityError:
        # UNIQUE(quiz_id, user_id): one attempt per student.
        conn.close()
        return "already_submitted"
    conn.commit()
    conn.close()
    return {"quiz_id": quiz_id, "score": score, "total": total}


def get_quiz_results(quiz_id: int):
    """Return all student submissions for a quiz (teacher view)."""
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT qs.user_id, u.name, qs.score, qs.total, qs.submitted_at
           FROM quiz_submissions qs
           JOIN users u ON u.id = qs.user_id
           WHERE qs.quiz_id = ?
           ORDER BY qs.submitted_at DESC""",
        (quiz_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {"user_id": r[0], "name": r[1], "score": r[2], "total": r[3], "submitted_at": r[4]}
        for r in rows
    ]


def toggle_quiz_active(quiz_id: int, teacher_id: int, is_active: bool):
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE quizzes SET is_active = ? WHERE id = ? AND teacher_id = ?",
        (1 if is_active else 0, quiz_id, teacher_id),
    )
    conn.commit()
    conn.close()


# ──────────────────────────────────────────────────────────────
# ADMIN — Attendance Overview
# ──────────────────────────────────────────────────────────────

def get_admin_attendance_overview():
    """
    Return per-classroom, per-subject attendance summary with overall totals.
    """
    conn = _connect()
    cursor = conn.cursor()

    cursor.execute("SELECT id, name FROM classrooms ORDER BY name")
    classrooms = cursor.fetchall()

    result = []
    for classroom_id, classroom_name in classrooms:
        # Get subjects in this classroom
        cursor.execute(
            """SELECT s.id, s.name, s.code FROM classroom_subjects cs
               JOIN subjects s ON s.id = cs.subject_id
               WHERE cs.classroom_id = ? ORDER BY s.name""",
            (classroom_id,),
        )
        subjects = cursor.fetchall()

        # Get students
        cursor.execute("SELECT id FROM students WHERE classroom_id = ?", (classroom_id,))
        roster_ids = [r[0] for r in cursor.fetchall()]
        student_count = len(roster_ids)

        subject_summaries = []
        overall_attended = 0
        overall_sessions = 0

        for subject_id, subject_name, subject_code in subjects:
            cursor.execute(
                "SELECT COUNT(*) FROM class_sessions WHERE classroom_id = ? AND subject_id = ?",
                (classroom_id, subject_id),
            )
            sessions_held = cursor.fetchone()[0]

            total_attended = 0
            for sid in roster_ids:
                cursor.execute(
                    """SELECT COUNT(*) FROM attendance_records ar
                       JOIN class_sessions cs ON ar.session_id = cs.id
                       WHERE cs.classroom_id = ? AND cs.subject_id = ? AND ar.student_id = ? AND ar.status = 'present'""",
                    (classroom_id, subject_id, sid),
                )
                total_attended += cursor.fetchone()[0]

            possible = sessions_held * student_count if student_count else 0
            pct = round((total_attended / possible) * 100, 1) if possible else 0.0
            subject_summaries.append({
                "subject_id": subject_id,
                "subject_name": subject_name,
                "subject_code": subject_code,
                "sessions_held": sessions_held,
                "avg_attendance_pct": pct,
            })
            overall_attended += total_attended
            overall_sessions += possible

        overall_pct = round((overall_attended / overall_sessions) * 100, 1) if overall_sessions else 0.0
        result.append({
            "classroom_id": classroom_id,
            "classroom_name": classroom_name,
            "student_count": student_count,
            "subjects": subject_summaries,
            "overall_attendance_pct": overall_pct,
        })

    conn.close()
    return result