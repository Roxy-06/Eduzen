import hashlib
import os
import random
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eduzen.db")


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    # WAL + NORMAL synchronous let readers and writers avoid blocking each
    # other and skip a full disk flush on every commit. Purely a perf
    # pragma - it does not change any query result or function behavior.
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
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
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

    cursor.execute("SELECT COUNT(*) FROM classrooms")
    has_classrooms = cursor.fetchone()[0] > 0
    cursor.execute("SELECT COUNT(*) FROM subjects")
    has_subjects = cursor.fetchone()[0] > 0
    cursor.execute("SELECT COUNT(*) FROM classroom_subjects")
    has_assignments = cursor.fetchone()[0] > 0

    if has_classrooms and has_subjects and has_assignments:
        return

    ava = _get_or_create_user(cursor, "Dr. Ava Carter", "teacher@eduzone.com", "teacher123", "teacher", "Computer Science")
    reyes = _get_or_create_user(cursor, "Prof. Daniel Reyes", "reyes@eduzone.com", "teacher123", "teacher", "Computer Science")
    nair = _get_or_create_user(cursor, "Dr. Priya Nair", "nair@eduzone.com", "teacher123", "teacher", "Computer Science")

    teacher_profiles = [
        (ava, "Computer Science", "3 courses", "Trees & Graph Algorithms",
         "08:00-09:00 planning, 10:00-12:00 lectures, 15:00-16:00 office hours", "Mon-Thu 15:00-16:00", 22),
        (reyes, "Computer Science", "2 courses", "Normalization & Query Optimization",
         "09:00-10:00 planning, 13:00-15:00 lectures", "Wed-Fri 13:00-14:00", 18),
        (nair, "Computer Science", "3 courses", "TCP/IP & Routing Protocols",
         "08:30-09:30 planning, 11:00-13:00 lectures, 16:00-17:00 office hours", "Tue-Thu 16:00-17:00", 20),
    ]
    for uid, dept, load, topic, routine, hours, weekly in teacher_profiles:
        cursor.execute("SELECT id FROM teacher_profiles WHERE user_id = ?", (uid,))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO teacher_profiles (user_id, department, course_load, current_topic, routine, office_hours, weekly_hours) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (uid, dept, load, topic, routine, hours, weekly),
            )

    dsa = _get_or_create_subject(cursor, "Data Structures & Algorithms", "CS201")
    dbms = _get_or_create_subject(cursor, "Database Management Systems", "CS301")
    net = _get_or_create_subject(cursor, "Computer Networks", "CS302")

    section_a = _get_or_create_classroom(cursor, "CS-201 Section A")
    section_b = _get_or_create_classroom(cursor, "CS-201 Section B")

    for classroom_id in (section_a, section_b):
        _assign_subject_to_teacher(cursor, classroom_id, dsa, ava)
        _assign_subject_to_teacher(cursor, classroom_id, dbms, reyes)
        _assign_subject_to_teacher(cursor, classroom_id, net, nair)

    student_roster = [
        ("Mina Shah", "student@eduzone.com", "STU-2026-001", section_a),
        ("Karan Mehta", "karan.mehta@eduzone.com", "STU-2026-002", section_a),
        ("Sofia Alvarez", "sofia.alvarez@eduzone.com", "STU-2026-003", section_a),
        ("Liam Chen", "liam.chen@eduzone.com", "STU-2026-004", section_a),
        ("Riya Kapoor", "riya.kapoor@eduzone.com", "STU-2026-005", section_a),
        ("Ethan Brooks", "ethan.brooks@eduzone.com", "STU-2026-006", section_b),
        ("Aisha Khan", "aisha.khan@eduzone.com", "STU-2026-007", section_b),
        ("Noah Kim", "noah.kim@eduzone.com", "STU-2026-008", section_b),
        ("Emma Wilson", "emma.wilson@eduzone.com", "STU-2026-009", section_b),
        ("Yusuf Ali", "yusuf.ali@eduzone.com", "STU-2026-010", section_b),
    ]

    for name, email, roll_no, classroom_id in student_roster:
        uid = _get_or_create_user(cursor, name, email, "student123", "student", "Information Systems")
        cursor.execute("SELECT id FROM student_profiles WHERE user_id = ?", (uid,))
        if not cursor.fetchone():
            profile_columns = _get_table_columns(conn, "student_profiles")
            if all(col in profile_columns for col in ["attendance_rate", "progress_score", "topics_completed"]):
                cursor.execute(
                    "INSERT INTO student_profiles (user_id, department, level, attendance_rate, progress_score, topics_completed, next_goal, last_activity) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (uid, "Information Systems", "Year 2", 0.0, 0.0, 0, "Complete the next revision cycle",
                     "Reviewed lecture notes and attended the latest session"),
                )
            else:
                cursor.execute(
                    "INSERT INTO student_profiles (user_id, department, level, next_goal, last_activity) VALUES (?, ?, ?, ?, ?)",
                    (uid, "Information Systems", "Year 2", "Complete the next revision cycle",
                     "Reviewed lecture notes and attended the latest session"),
                )
        _enroll_student(cursor, classroom_id, name, roll_no, user_id=uid)

    random.seed(7)
    subjects_by_classroom = {section_a: [dsa, dbms, net], section_b: [dsa, dbms, net]}
    teacher_by_subject = {dsa: ava, dbms: reyes, net: nair}

    valid_session_count = cursor.execute(
        "SELECT COUNT(*) FROM class_sessions WHERE classroom_id > 0 AND subject_id > 0 AND teacher_id > 0"
    ).fetchone()[0]
    if valid_session_count == 0:
        for classroom_id, subject_ids in subjects_by_classroom.items():
            cursor.execute("SELECT id FROM students WHERE classroom_id = ?", (classroom_id,))
            roster_ids = [r[0] for r in cursor.fetchall()]
            for subject_id in subject_ids:
                teacher_id = teacher_by_subject[subject_id]
                for _ in range(6):
                    cursor.execute(
                        "INSERT INTO class_sessions (classroom_id, subject_id, teacher_id, is_ended, ended_at) "
                        "VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)",
                        (classroom_id, subject_id, teacher_id),
                    )
                    session_id = cursor.lastrowid
                    for sid in roster_ids:
                        status = "present" if random.random() < 0.85 else "absent"
                        cursor.execute(
                            "INSERT INTO attendance_records (session_id, student_id, status) VALUES (?, ?, ?)",
                            (session_id, sid, status),
                        )

    existing_marks_count = cursor.execute("SELECT COUNT(*) FROM marks WHERE subject_id > 0").fetchone()[0]
    if existing_marks_count == 0:
        for classroom_id, subject_ids in subjects_by_classroom.items():
            cursor.execute("SELECT id FROM students WHERE classroom_id = ?", (classroom_id,))
            roster_ids = [r[0] for r in cursor.fetchall()]
            for subject_id in subject_ids:
                for sid in roster_ids:
                    score = round(random.uniform(60, 95), 1)
                    cursor.execute(
                        "INSERT INTO marks (student_id, subject_id, exam_name, marks_obtained, max_marks) VALUES (?, ?, ?, ?, ?)",
                        (sid, subject_id, "Midterm", score, 100),
                    )


def add_material(filename: str):
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO materials (filename) VALUES (?)", (filename,))
    conn.commit()
    conn.close()


def get_materials():
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("SELECT filename, uploaded_at FROM materials ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [{"filename": r[0], "uploaded_at": r[1]} for r in rows]


def get_subjects():
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, code FROM subjects ORDER BY name")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "code": r[2]} for r in rows]


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
    if row is None:
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


def create_user(name: str, email: str, password: str, role: str, department: str):
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
        cursor.execute(
            "INSERT INTO teacher_profiles (user_id, department, course_load, current_topic, routine, office_hours, weekly_hours) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, department, "3 courses", "New curriculum design",
             "09:00-10:00 planning, 14:00-15:00 lectures", "Tue-Fri 14:00-15:00", 20),
        )
    else:
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


def authenticate_user(email: str, password: str):
    conn = _connect()
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
    conn = _connect()
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