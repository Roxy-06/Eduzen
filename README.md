# EduZen

Professional AI-powered campus dashboard (EduZen)

This repository contains a minimal FastAPI backend and a Streamlit frontend delivering a professional role-based dashboard for teachers and students. The app includes:

- Role-based authentication (teacher / student) with seeded demo accounts
- Classroom & attendance management
- Material upload and lightweight RAG-style study assistant (Gemini integration optional)
- Polished Streamlit UI for teacher and student dashboards

Demo accounts
- Teacher: `teacher@eduzone.com` / `teacher123`
- Student: `student@eduzone.com` / `student123`

Run locally
1. Install dependencies:

```powershell
Set-Location 'D:\EduZen'
python -m pip install -r requirements.txt
```

2. Start the backend (FastAPI):

```powershell
Set-Location 'D:\EduZen\backend'
python -m uvicorn main:app --reload --port 8000
```

3. Start the frontend (Streamlit) in a separate terminal:

```powershell
Set-Location 'D:\EduZen'
python -m streamlit run frontend/app.py --server.headless true --server.port 8501
```

Environment variables
- To enable Gemini (Google) generative features, set the `GEMINI_API_KEY` environment variable. For example on Windows (user-level persistent):

```powershell
setx GEMINI_API_KEY "<PASTE_YOUR_KEY_HERE>"
$env:GEMINI_API_KEY = "<PASTE_YOUR_KEY_HERE>"  # sets for current session
```

Notes
- The RAG engine is resilient to a missing Gemini key and will fall back to deterministic sample responses. To get full AI responses, supply a valid `GEMINI_API_KEY` and restart the backend so the new env var is picked up.

Contributing
- Small, focused PRs are welcome. If you'd like I can open a PR with the dashboard polish and tests.

License
- MIT

EduZen is an AI-powered academic assistant designed for universities and study ecosystems. It helps instructors upload course materials and enables students to interact with those materials through an intelligent tutor experience powered by FastAPI, Streamlit, and Gemini.

## Overview

EduZen combines:
- a teacher portal for uploading and organizing PDF course materials
- a student portal for asking questions, generating summaries, quizzes, and flashcards
- a retrieval-augmented generation (RAG) pipeline that grounds responses in uploaded documents

This project is built to make learning more interactive, personalized, and efficient.

## Features

### For teachers
- Upload PDF course materials
- Store uploaded materials in a local repository
- Process documents into searchable embeddings for AI-powered retrieval

### For students
- Ask questions about uploaded content
- Generate concise summaries of lecture notes
- Create practice quizzes
- Build study flashcards for revision

## Tech Stack

- Python
- FastAPI for the backend API
- Streamlit for the frontend UI
- SQLite for local metadata storage
- FAISS for vector similarity search
- Google Gemini for embeddings and text generation
- PyPDF for PDF parsing

## Project Structure

```text
EduZen/
├── backend/
│   ├── main.py
│   ├── db.py
│   ├── rag_engine.py
├── frontend/
│   └── app.py
├── uploads/
├── requirements.txt
└── README.md
```

## Prerequisites

- Python 3.10+
- A valid Google Gemini API key
- Internet access for Gemini API requests

## Environment Setup

1. Clone the repository
2. Create and activate a virtual environment
3. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

4. Set your Gemini API key

On Linux/macOS:

```bash
export GEMINI_API_KEY=your_api_key_here
```

On Windows PowerShell:

```powershell
$env:GEMINI_API_KEY="your_api_key_here"
```

## Run the Application

### Start the backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

### Start the frontend

In a separate terminal:

```bash
streamlit run frontend/app.py
```

Then open the Streamlit app in your browser.

## How It Works

1. A teacher uploads a PDF through the Streamlit interface.
2. The backend saves the file and extracts text from the PDF.
3. The text is split into chunks and embedded using Gemini.
4. The embeddings are indexed with FAISS for semantic retrieval.
5. Students ask questions or request study outputs, and the backend uses the retrieved context to generate grounded answers.

## Recent Updates

- Improved the local application workflow for uploading and querying course materials.
- Refined the backend and frontend interaction for a smoother study-assistant experience.
- Continued updates to the SQLite-backed data layer and project documentation.

## Notes

- The current implementation uses a local SQLite database and local uploads directory.
- PDF support is currently limited to `.pdf` files.
- Ensure the `GEMINI_API_KEY` environment variable is set before running the app.

## License

This project is open-source and available for educational use.
