# 🎯 InterviewIQ — AI-Powered Interview Assistant

An end-to-end **RAG (Retrieval-Augmented Generation)** application that takes a job description and a candidate's resume, then conducts a personalized AI-powered interview with context-aware questions.

![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?logo=fastapi)
![React](https://img.shields.io/badge/React-18-blue?logo=react)
![LangChain](https://img.shields.io/badge/LangChain-latest-orange)
![HuggingFace](https://img.shields.io/badge/HuggingFace-Inference-yellow?logo=huggingface)

---

## ✨ Features

- 📄 Upload any resume as a PDF and paste a job description
- 🤖 AI generates 5 personalized interview questions using RAG
- 🧠 Questions are grounded in both the resume content AND job requirements
- 💬 Answer each question in a clean, step-by-step interview flow
- 📋 Get a full Q&A summary at the end of the session
- ⚡ Powered by local HuggingFace embeddings + DeepSeek LLM via HuggingFace router

---

## 🏗️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React.js, Axios |
| Backend | FastAPI, Python |
| RAG Framework | LangChain |
| Text Splitting | RecursiveCharacterTextSplitter |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` (runs locally) |
| Vector Store | FAISS (in-memory) |
| LLM | `deepseek-ai/DeepSeek-V4-Pro` via HuggingFace Inference API |
| PDF Parsing | pdfplumber |

---

## 🧠 How the RAG Pipeline Works

```
Resume PDF
    ↓ pdfplumber extracts text
    ↓ RecursiveCharacterTextSplitter chunks it (500 chars, 100 overlap)
    ↓ all-MiniLM-L6-v2 embeds each chunk locally
    ↓ Stored in FAISS vector store
    
For each interview question:
    ↓ Top-5 relevant chunks retrieved from FAISS
    ↓ Combined with job description + previous questions
    ↓ Sent to DeepSeek-V4-Pro via HuggingFace router
    ↓ Returns a unique, context-aware interview question
```

---

## 📁 Project Structure

```
InterviewIQ/
├── backend/
│   ├── main.py              ← FastAPI app with RAG logic
│   ├── requirements.txt     ← Python dependencies
│   └── .env.example         ← Environment variable template
└── frontend/
    ├── public/
    └── src/
        ├── App.js           ← Main React component (3 screens)
        └── App.css          ← Styles
```

---

## ⚙️ Local Setup

### Prerequisites
- Python 3.9+ — https://www.python.org
- Node.js 16+ — https://nodejs.org
- HuggingFace account + API token — https://huggingface.co/settings/tokens

---

### Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
copy .env.example .env       # Windows
# cp .env.example .env       # Mac/Linux
```

Edit `.env` and add your HuggingFace token:
```
HUGGINGFACEHUB_API_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxx
```

Start the backend:
```bash
uvicorn main:app --reload
```
Backend runs at: **http://localhost:8000**
API docs at: **http://localhost:8000/docs**

---

### Frontend

```bash
cd frontend
npm install
npm install axios
npm start
```
Frontend runs at: **http://localhost:3000**

---

## 🖥️ App Flow

**Step 1 — Upload**
Paste the job description and upload the candidate's resume PDF.

**Step 2 — Interview**
Answer 5 AI-generated questions one at a time, each tailored to the resume and job role.

**Step 3 — Summary**
Review all questions and answers in a clean summary card layout.

---
