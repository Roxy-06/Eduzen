import hashlib
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eduzen.db")


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def init_db():
    """Create the database schema and seed a few professional demo accounts."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('teacher', 'student')),
            department TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            attendance_rate REAL NOT NULL,
            progress_score REAL NOT NULL,
            topics_completed INTEGER NOT NULL,
            next_goal TEXT NOT NULL,
            last_activity TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    conn.commit()
    _seed_demo_accounts(conn)
    conn.commit()
    conn.close()


def _seed_demo_accounts(conn: sqlite3.Connection):
    cursor = conn.cursor()
    defaults = [
        ("Ava Carter", "teacher@eduzone.com", "teacher123", "teacher", "Computer Science"),
        ("Mina Shah", "student@eduzone.com", "student123", "student", "Information Systems"),
    ]
    for name, email, password, role, department in defaults:
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            continue

        cursor.execute(
            "INSERT INTO users (name, email, password_hash, role, department) VALUES (?, ?, ?, ?, ?)",
            (name, email, hash_password(password), role, department),
        )
        user_id = cursor.lastrowid

        if role == "teacher":
            cursor.execute(
                "INSERT OR IGNORE INTO teacher_profiles (user_id, department, course_load, current_topic, routine, office_hours, weekly_hours) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, department, "4 courses", "Advanced Data Structures", "08:00–09:00 planning, 11:00–13:00 lectures, 15:00–16:00 office hours", "Mon–Thu 15:00–16:00", 24),
            )
        else:
            cursor.execute(
                "INSERT OR IGNORE INTO student_profiles (user_id, department, level, attendance_rate, progress_score, topics_completed, next_goal, last_activity) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id, department, "Year 3", 92.0, 88.5, 14, "Complete the next revision cycle", "Reviewed lecture notes and attended the latest session"),
            )


def add_material(filename: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO materials (filename) VALUES (?)", (filename,))
    conn.commit()
    conn.close()


def get_materials():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT filename, uploaded_at FROM materials ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [{"filename": r[0], "uploaded_at": r[1]} for r in rows]


def create_classroom(name: str) -> int:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO classrooms (name) VALUES (?)", (name,))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def get_classrooms():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, created_at FROM classrooms ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "created_at": r[2]} for r in rows]


def add_student(classroom_id: int, name: str, student_id: str) -> int:
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


def create_user(name: str, email: str, password: str, role: str, department: str):
    conn = sqlite3.connect(DB_PATH)
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
        cursor.execute(
            "INSERT INTO teacher_profiles (user_id, department, course_load, current_topic, routine, office_hours, weekly_hours) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, department, "3 courses", "New curriculum design", "09:00–10:00 planning, 14:00–15:00 lectures", "Tue–Fri 14:00–15:00", 20),
        )
    else:
        cursor.execute(
            "INSERT INTO student_profiles (user_id, department, level, attendance_rate, progress_score, topics_completed, next_goal, last_activity) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, department, "Year 2", 88.0, 82.0, 10, "Complete the weekly revision target", "Started a new study module"),
        )

    conn.commit()
    conn.close()
    return user_id


def authenticate_user(email: str, password: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, email, role, department FROM users WHERE email = ? AND password_hash = ?",
        (email, hash_password(password)),
    )
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return None
    return {"id": row[0], "name": row[1], "email": row[2], "role": row[3], "department": row[4]}


def get_user_by_id(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, role, department FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return None
    return {"id": row[0], "name": row[1], "email": row[2], "role": row[3], "department": row[4]}


def get_student_dashboard(user_id: int):
    user = get_user_by_id(user_id)
    if user is None:
        return None

    classrooms = get_classrooms()
    attendance_values = []
    for classroom in classrooms:
        summary = get_attendance_summary(classroom["id"])
        if summary:
            average = sum(item["percentage"] for item in summary) / len(summary)
            attendance_values.append(average)

    attendance_rate = round(sum(attendance_values) / len(attendance_values), 1) if attendance_values else 91.0
    progress_score = round(min(100.0, max(60.0, attendance_rate + 7.0 + len(get_materials()) * 2.0)), 1)
    topics_completed = max(10, int(progress_score // 6))

    return {
        "id": user["id"],
        "name": user["name"],
        "role": "student",
        "department": user["department"],
        "attendance_rate": attendance_rate,
        "progress_score": progress_score,
        "topics_completed": topics_completed,
        "materials_available": len(get_materials()),
        "classroom_count": len(classrooms),
        "next_goal": "Complete the next revised study cycle",
        "latest_activity": "Reviewed course content and joined the latest session",
    }


def get_teacher_dashboard(user_id: int):
    user = get_user_by_id(user_id)
    if user is None:
        return None

    classrooms = get_classrooms()
    total_sessions = sum(len(get_sessions(classroom["id"])) for classroom in classrooms)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT department, course_load, current_topic, routine, office_hours, weekly_hours FROM teacher_profiles WHERE user_id = ?",
        (user_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return {
            "id": user["id"],
            "name": user["name"],
            "role": "teacher",
            "department": user["department"],
            "course_load": "3 courses",
            "current_topic": "Curriculum planning",
            "routine": "09:00 planning, 11:00 lectures, 15:00 mentoring",
            "office_hours": "Tue–Fri 15:00–16:00",
            "weekly_hours": 20,
            "classroom_count": len(classrooms),
            "session_count": total_sessions,
            "materials_available": len(get_materials()),
        }

    return {
        "id": user["id"],
        "name": user["name"],
        "role": "teacher",
        "department": row[0],
        "course_load": row[1],
        "current_topic": row[2],
        "routine": row[3],
        "office_hours": row[4],
        "weekly_hours": row[5],
        "classroom_count": len(classrooms),
        "session_count": total_sessions,
        "materials_available": len(get_materials()),
    }