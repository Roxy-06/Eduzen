import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from db import init_db, add_material, get_materials
from rag_engine import index_document, generate_rag_response

app = FastAPI(title="EduZen API")

# Allow Streamlit frontend to communicate with this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Automatically locate the root 'uploads' folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Initialize the SQLite database table when the server starts
init_db()

# Data model for incoming AI requests
class QueryRequest(BaseModel):
    mode: str  # Options: 'qa', 'summary', 'quiz', 'flashcards'
    query: str = ""

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Receives uploaded PDF, saves it to disk, and indexes it into the vector database."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are currently supported.")
    
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    # Save the file to disk
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Process PDF into FAISS vector storage
    success = index_document(file_path)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to process document text.")
    
    # Record filename in SQLite database
    add_material(file.filename)
    return {"message": f"Successfully processed and indexed '{file.filename}'"}

@app.get("/api/materials")
def list_materials():
    """Returns the list of all uploaded course materials."""
    return get_materials()

@app.post("/api/ai/generate")
def ai_generate(req: QueryRequest):
    """Handles requests for Q&A, Summaries, Quizzes, and Flashcards."""
    result = generate_rag_response(mode=req.mode, query=req.query)
    return {"response": result}