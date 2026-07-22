import os
import pypdf
import faiss
import numpy as np
from google import genai
from google.genai import types

# Initialize Gemini Client (Requires GEMINI_API_KEY environment variable)
client = genai.Client()

# Global in-memory storage for FAISS index and text chunks
text_chunks = []
index = None
EMBEDDING_DIM = 768  # Standard dimension for fast vector search

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extracts raw text from an uploaded PDF file."""
    reader = pypdf.PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"
    return text

def chunk_text(text: str, chunk_size: int = 600, overlap: int = 100) -> list[str]:
    """Splits text into overlapping chunks for indexing."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)
    return chunks

def index_document(pdf_path: str):
    """Processes PDF, generates embeddings via Gemini, and indexes them into FAISS."""
    global text_chunks, index
    raw_text = extract_text_from_pdf(pdf_path)
    new_chunks = chunk_text(raw_text)
    
    if not new_chunks:
        return False
    
    # Generate Embeddings using Gemini's current embedding model
    embeddings = []
    for chunk in new_chunks:
        response = client.models.embed_content(
            model="gemini-embedding-2",
            contents=chunk,
            config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIM)
        )
        # Extract the float values from the embedding response
        embeddings.append(response.embeddings[0].values)
    
    embedding_matrix = np.array(embeddings, dtype=np.float32)
    
    # Initialize or extend FAISS Index
    if index is None:
        index = faiss.IndexFlatL2(EMBEDDING_DIM)
    
    index.add(embedding_matrix)
    text_chunks.extend(new_chunks)
    return True

def retrieve_context(query: str, top_k: int = 3) -> str:
    """Retrieves top matching text chunks for a query using FAISS vector search."""
    global index, text_chunks
    if index is None or len(text_chunks) == 0:
        return ""
    
    # Embed the query to match against our document vectors
    query_resp = client.models.embed_content(
        model="gemini-embedding-2",
        contents=query,
        config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIM)
    )
    query_vector = np.array([query_resp.embeddings[0].values], dtype=np.float32)
    
    # Search FAISS
    _, indices = index.search(query_vector, min(top_k, len(text_chunks)))
    retrieved = [text_chunks[idx] for idx in indices[0] if idx < len(text_chunks)]
    return "\n\n---\n\n".join(retrieved)

def generate_rag_response(mode: str, query: str = "") -> str:
    """Generates responses for Q&A, Summaries, Quizzes, and Flashcards using prompt templates."""
    context = retrieve_context(query if query else "Overview of key concepts")
    
    if not context:
        return "No course materials have been uploaded yet. Please ask your instructor to upload notes."
    
    # Prompt Routing based on feature mode
    prompts = {
        "qa": f"Context from course materials:\n{context}\n\nQuestion: {query}\n\nAnswer clearly and concisely based ONLY on the context provided:",
        "summary": f"Context from course materials:\n{context}\n\nGenerate a structured, bulleted summary covering the core concepts, main ideas, and important formulas/terms:",
        "quiz": f"Context from course materials:\n{context}\n\nGenerate a 3-question multiple-choice quiz based on this content. Include 4 options (A, B, C, D) per question and provide the correct answer key at the bottom.",
        "flashcards": f"Context from course materials:\n{context}\n\nGenerate 5 study flashcards in the following format:\n**Card [N]**\n**Concept:** [Concept Name]\n**Definition:** [Brief Explanation]\n---"
    }
    
    prompt = prompts.get(mode, prompts["qa"])
    
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.3)
    )
    return response.text