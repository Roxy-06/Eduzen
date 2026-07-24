import json
import os
import pypdf
import faiss
import numpy as np
from google import genai
from google.genai import types


def _build_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        return genai.Client(api_key=api_key)
    except Exception:
        return None


client = _build_client()

# ---------------------------------------------------------------------
# GEMMA 4 AS THE GENERATION BRAIN
# ---------------------------------------------------------------------
GENERATION_MODEL = os.getenv("GEMMA_MODEL", "gemma-4-26b-a4b-it")
EMBEDDING_MODEL = "gemini-embedding-2"

text_chunks = []
index = None
EMBEDDING_DIM = 768

def extract_text_from_pdf(pdf_path: str) -> str:
    reader = pypdf.PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"
    return text

def chunk_text(text: str, chunk_size: int = 600, overlap: int = 100) -> list[str]:
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)
    return chunks

def index_document(pdf_path: str):
    global text_chunks, index
    raw_text = extract_text_from_pdf(pdf_path)
    new_chunks = chunk_text(raw_text)

    if not new_chunks:
        return False

    if client is None:
        text_chunks.extend(new_chunks)
        return True

    embeddings = []
    for chunk in new_chunks:
        response = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=chunk,
            config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIM)
        )
        embeddings.append(response.embeddings[0].values)

    embedding_matrix = np.array(embeddings, dtype=np.float32)

    if index is None:
        index = faiss.IndexFlatL2(EMBEDDING_DIM)

    index.add(embedding_matrix)
    text_chunks.extend(new_chunks)
    return True

def retrieve_context(query: str, top_k: int = 3) -> str:
    global index, text_chunks
    # If there are no chunks available, nothing to retrieve.
    if len(text_chunks) == 0:
        return ""

    # If an index exists (FAISS + embeddings path), use it. Otherwise
    # fall back to returning the first `top_k` in-memory chunks that
    # were stored when `client` was not configured or embeddings were
    # not generated.

    if client is None or index is None:
        return "\n\n---\n\n".join(text_chunks[:top_k])

    query_resp = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=query,
        config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIM)
    )
    query_vector = np.array([query_resp.embeddings[0].values], dtype=np.float32)

    _, indices = index.search(query_vector, min(top_k, len(text_chunks)))
    retrieved = [text_chunks[idx] for idx in indices[0] if idx < len(text_chunks)]
    return "\n\n---\n\n".join(retrieved)


def _stub_quiz() -> str:
    return json.dumps({
        "questions": [
            {
                "question": "What is the main concept discussed in the uploaded material?",
                "options": {"A": "Overview", "B": "Methodology", "C": "Practice", "D": "Review"},
                "correct": "A",
            }
        ]
    })


def _stub_flashcards() -> str:
    return json.dumps({
        "cards": [
            {"question": "Key idea", "answer": "The central theme from the uploaded material."}
        ]
    })


def generate_rag_response(mode: str, query: str = "") -> str:
    context = retrieve_context(query if query else "Overview of key concepts")

    if not context:
        return "No course materials have been uploaded yet. Please ask your instructor to upload notes."

    if client is None:
        if mode == "quiz":
            return _stub_quiz()
        if mode == "flashcards":
            return _stub_flashcards()
        if mode == "summary":
            return "Summary: The uploaded material presents a clear framework, key concepts, and supporting examples that can be reviewed for study preparation."
        return f"Based on the uploaded material, the main takeaway is that the supplied content should be reviewed carefully for understanding and revision.\n\nContext preview:\n{context[:400]}"

    prompts = {
        "qa": f"Context from course materials:\n{context}\n\nQuestion: {query}\n\nAnswer clearly and concisely based ONLY on the context provided:",
        "summary": f"Context from course materials:\n{context}\n\nGenerate a structured, bulleted summary covering the core concepts, main ideas, and important formulas/terms:",
        "quiz": (
            f"Context from course materials:\n{context}\n\n"
            "Generate a 3-question multiple-choice quiz based on this content.\n"
            "Respond ONLY with valid JSON, no markdown fences, no commentary, in exactly this shape:\n"
            '{"questions": [{"question": "...", "options": {"A": "...", "B": "...", "C": "...", "D": "..."}, "correct": "A"}]}\n'
            'The "correct" field must be one of "A", "B", "C", or "D" matching the correct option key.'
        ),
        "flashcards": (
            f"Context from course materials:\n{context}\n\n"
            "Generate 5 study flashcards covering key terms, concepts, and formulas.\n"
            "Respond ONLY with valid JSON, no markdown fences, no commentary, in exactly this shape:\n"
            '{"cards": [{"question": "...", "answer": "..."}]}'
        ),
    }

    prompt = prompts.get(mode, prompts["qa"])

    if mode in ("quiz", "flashcards"):
        config = types.GenerateContentConfig(temperature=0.3, response_mime_type="application/json")
    else:
        config = types.GenerateContentConfig(temperature=0.3)

    try:
        response = client.models.generate_content(
            model=GENERATION_MODEL,
            contents=prompt,
            config=config,
        )
        return response.text
    except Exception:
        # If the model/SDK combo doesn't support response_mime_type, retry
        # once without it rather than failing the whole request.
        if mode in ("quiz", "flashcards"):
            response = client.models.generate_content(
                model=GENERATION_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.3),
            )
            return response.text
        raise