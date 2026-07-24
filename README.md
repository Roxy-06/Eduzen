# EduZen — Developer & User Guide

EduZen is an AI-assisted academic platform for instructors and students. It provides classroom and roster management, attendance tracking, PDF-based course-material indexing, and an AI study assistant that can produce summaries, quizzes, and flashcards from uploaded materials.

This README replaces the legacy Streamlit guide and documents the current maintained setup (FastAPI backend + React frontend).

Quick status

- Legacy Streamlit frontend (`frontend/`) has been removed. The active UI is the React app in `frontend-react/`.
- The `streamlit` dependency was removed from `requirements.txt`.

Repository layout

```
EduZen/
├── backend/                # FastAPI backend (API, DB, RAG engine)
├── frontend-react/         # Active React frontend (Vite)
├── uploads/                # Uploaded course PDFs
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

Getting started (developer)

1) Create and activate a Python virtual environment

```powershell
cd D:\EduZen
python -m venv venv
& .\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

2) Backend (FastAPI)

```powershell
cd D:\EduZen\backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Notes:
- On startup the backend scans `uploads/` and indexes any PDFs it finds so the AI can answer queries about previously uploaded chapters.
- If you plan to use a Google Gemini API key for higher-quality generation, set `GEMINI_API_KEY` in your environment.

3) Frontend (React)

```powershell
cd D:\EduZen\frontend-react
npm install
npm run dev
```

API overview (important endpoints)

- Health: `GET /api/health`
- Upload PDF: `POST /api/upload` (form file; only `.pdf`)
- List materials: `GET /api/materials`
- AI generate: `POST /api/ai/generate` — JSON body: `{"mode":"summary|quiz|flashcards|qa","query":"..."}`
- Subjects: `GET /api/subjects`
- Classrooms: `GET /api/classrooms`, `POST /api/classrooms`
- Students: `GET /api/classrooms/{id}/students`, `POST /api/classrooms/{id}/students`

Example: upload and query

1. Upload a PDF

```bash
curl -F "file=@Chapter1.pdf" http://localhost:8000/api/upload
```

2. Generate a summary

```bash
curl -X POST http://localhost:8000/api/ai/generate \
	-H "Content-Type: application/json" \
	-d '{"mode":"summary","query":""}'
```

Environment variables

- `GEMINI_API_KEY` — optional. If set, the app will attempt to use Google Gemini for embeddings and generation. Without it, the app falls back to in-memory text chunks and stub generators.
- Additional flags may be added later for persistent vector storage configuration.

Notes about AI indexing & persistence

- Current behavior: uploaded PDFs are split into in-memory text chunks and optionally embedded into a FAISS index when a working `google-genai` client is available. The code now reindexes files present in `uploads/` at startup so previously uploaded files are usable.
- For production, consider persisting the FAISS index to disk or using a managed vector DB so vectors survive restarts and scale reliably.

Removing legacy Streamlit frontend

- The previous Streamlit app (referenced historically at `frontend/app.py`) was removed because the React frontend is now the primary UI. If you need to restore it, check the branch `backup/remove-frontend` (if created) or your Git history.

Development tips

- To debug backend endpoints, use `http://localhost:8000/docs` (FastAPI interactive docs) while the backend is running.
- To inspect uploaded files, look in the `uploads/` folder. The backend will attempt to index PDFs found there on startup.

Contributing

- Fork, create a feature branch, and open a pull request with a clear description. Keep changes scoped and include tests when adding logic.

Contact

- Project contributors:
- Rudranil Mallick (rudranilmallick8335@gmail.com)
- Harshika Joshi (harshikajoshi58@gmail.com)

License

MIT
