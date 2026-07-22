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