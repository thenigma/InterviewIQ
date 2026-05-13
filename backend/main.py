import os
import uuid
import io
import pdfplumber

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# LangChain imports
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceInferenceAPIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.messages import HumanMessage
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace

# Load environment variables from .env file (for HuggingFace API token)
load_dotenv()

app = FastAPI()

# Enable CORS so the React frontend (running on port 3000) can talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173",
                  "https://interview-iq-iota.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store
# Structure: { session_id: { "vectordb": FAISS, "job_description": str, "qa_pairs": [] } }
sessions = {}

TOTAL_QUESTIONS = 5  # Number of interview questions to ask per session


# ---------- Shared Model Setup ----------
# These are loaded ONCE at startup (heavy models — don't reload per request)

embedding_model = HuggingFaceInferenceAPIEmbeddings(
    api_key=os.getenv("HUGGINGFACEHUB_API_TOKEN"),
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# HuggingFace Inference Endpoint LLM
llm_endpoint = HuggingFaceEndpoint(
    repo_id="meta-llama/Meta-Llama-3-8B-Instruct",
    task="text-generation",
    temperature=0.01,
    max_new_tokens=512,
    huggingfacehub_api_token=os.getenv("HUGGINGFACEHUB_API_TOKEN"),
)
llm = ChatHuggingFace(llm=llm_endpoint)


# ---------- Helper Functions ----------

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract all text from a PDF file given its raw bytes."""
    text = ""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


def build_vectordb_from_text(text: str) -> FAISS:
    """
    Split the resume text using LangChain's RecursiveCharacterTextSplitter,
    embed each chunk using HuggingFace embeddings, and store in a FAISS vector DB.
    """
    # RecursiveCharacterTextSplitter splits on paragraphs -> sentences -> words in order
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,       # Max characters per chunk
        chunk_overlap=100,    # Overlap between chunks to preserve context at boundaries
        separators=["\n\n", "\n", ".", " ", ""],
    )

    # Split text into LangChain Document objects
    chunks = text_splitter.create_documents([text])

    # Build FAISS vector store from the chunks using HuggingFace embeddings
    vectordb = FAISS.from_documents(chunks, embedding_model)
    return vectordb


def retrieve_context(vectordb: FAISS, query: str, k: int = 5) -> str:
    """
    Retrieve the top-k most relevant resume chunks from FAISS for a given query.
    Returns them joined as a single string.
    """
    retriever = vectordb.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k}
    )
    docs = retriever.invoke(query)
    return "\n\n".join([doc.page_content for doc in docs])


# ---------- API Endpoints ----------

@app.post("/upload")
async def upload(
    resume: UploadFile = File(...),
    job_description: str = Form(...)
):
    """
    Upload a resume PDF and job description.
    - Extracts text from the PDF using pdfplumber
    - Splits it with RecursiveCharacterTextSplitter
    - Embeds chunks with HuggingFace sentence-transformers
    - Stores in an in-memory FAISS vector DB
    - Returns a session_id for all subsequent calls
    """
    # Step 1: Read and extract text from the uploaded PDF
    pdf_bytes = await resume.read()
    resume_text = extract_text_from_pdf(pdf_bytes)

    if not resume_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Could not extract text from the PDF. Make sure it is not a scanned/image-only PDF."
        )

    # Step 2: Split -> embed -> store in FAISS
    vectordb = build_vectordb_from_text(resume_text)

    # Step 3: Create a unique session and store everything in memory
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "vectordb": vectordb,
        "job_description": job_description,
        "qa_pairs": [],
    }

    return {
        "session_id": session_id,
        "message": "Resume uploaded, split, embedded, and indexed successfully."
    }


class AskRequest(BaseModel):
    session_id: str
    question_index: int  # 0-based index of which question to generate


@app.post("/ask")
async def ask(request: AskRequest):
    """
    Generate the next interview question using RAG:
    1. Retrieve top-5 relevant resume chunks from FAISS
    2. Combine with job description + history of previous questions
    3. Send prompt to HuggingFace LLM to generate a fresh, unique question
    """
    session = sessions.get(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found. Please upload your resume again.")

    job_description = session["job_description"]
    vectordb = session["vectordb"]
    qa_pairs = session["qa_pairs"]

    # Retrieve relevant resume context
    query = f"candidate experience and skills relevant to: {job_description}"
    context = retrieve_context(vectordb, query, k=5)

    # List previous questions so the LLM avoids repeating them
    previous_questions = "\n".join(
        [f"Q{i+1}: {pair['question']}" for i, pair in enumerate(qa_pairs)]
    ) or "None yet"

    # Build the full prompt
    prompt = f"""You are a professional job interviewer. Your task is to ask a single, specific interview question.

Job Description:
{job_description}

Relevant Resume Excerpts:
{context}

Previously asked questions (do NOT ask these again):
{previous_questions}

Instructions:
- Generate interview question number {request.question_index + 1} of {TOTAL_QUESTIONS}
- The question must be specific to the candidate's resume AND the job requirements
- Keep it open-ended and professional
- Output ONLY the question text, with no preamble, numbering, or explanation

Question:"""

    # Invoke the LLM
    response = llm.invoke([HumanMessage(content=prompt)])
    question = response.content.strip()

    return {"question": question}


class AnswerRequest(BaseModel):
    session_id: str
    question: str
    answer: str


@app.post("/answer")
async def answer(request: AnswerRequest):
    """Store the candidate's answer to the current question in the session."""
    session = sessions.get(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    session["qa_pairs"].append({
        "question": request.question,
        "answer": request.answer,
    })

    return {"status": "ok"}


@app.get("/summary/{session_id}")
async def summary(session_id: str):
    """Return all Q&A pairs collected during the interview session."""
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    return {"qa_pairs": session["qa_pairs"]}
