# EduZen

EduZen is an AI-powered academic platform for teachers and students. It brings together classroom management, attendance tracking, course-material indexing, and an AI study assistant in one polished web experience.

## What this project includes

- role-based authentication for teachers and students
- classroom creation and student enrollment
- attendance session tracking and reporting
- PDF upload and indexing for AI-assisted study support
- student-facing tools for Q&A, summaries, quizzes, and flashcards

## Demo accounts

- Teacher: `teacher@eduzone.com` / `teacher123`
- Student: `student@eduzone.com` / `student123`

## Tech stack

- Python
- FastAPI
- Streamlit
- SQLite
- FAISS
- Google Gemini
- PyPDF

## Project structure

```text
EduZen/
├── backend/
│   ├── main.py
│   ├── db.py
│   └── rag_engine.py
├── frontend/
│   └── app.py
├── uploads/
├── requirements.txt
└── README.md
```

## Run locally

1. Install dependencies:

```powershell
Set-Location 'D:\EduZen'
python -m pip install -r requirements.txt
```

2. Start the backend:

```powershell
Set-Location 'D:\EduZen\backend'
python -m uvicorn main:app --reload --port 8000
```

3. Start the frontend in a separate terminal:

```powershell
Set-Location 'D:\EduZen'
python -m streamlit run frontend/app.py --server.headless true --server.port 8501
```

## Environment variables

To enable full Gemini-powered responses, set:

```powershell
setx GEMINI_API_KEY "<PASTE_YOUR_KEY_HERE>"
$env:GEMINI_API_KEY = "<PASTE_YOUR_KEY_HERE>"
```

If the key is missing, the app can still start, but the AI features may use fallback behavior.

## Notes

- The app currently stores data locally in SQLite.
- Uploaded materials are kept in the local uploads folder.
- PDF support is currently limited to `.pdf` files.

## Contributors

 - Harshika Joshi (harshikajoshi58@gmail.com)
 - Rudranil Mallick (rudranilmallick8335@gmail.com)

## License

MIT
