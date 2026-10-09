# College Rules RAG Chatbot

A modern, full-stack AI Chatbot application powered by **FastAPI**, **React + Vite**, **FAISS**, and the **Google Gemini API** (`google-genai` SDK).

The chatbot indexes institutional handbooks (regulations, examination guidelines, attendance rules, leave policies) and answers queries with strict grounding and verifiable page citations.

---

## Architecture & Technology Stack

- **Backend:** Python 3.12+, FastAPI, Uvicorn, Pydantic v2
- **Vector Search & Retrieval:** FAISS (`IndexFlatIP`), normalized cosine similarity, in-memory query embedding cache
- **Embedding Model:** Google Gemini `gemini-embedding-2` (3072 dimensions)
- **Generation Model:** Google Gemini `gemini-3.5-flash-lite` (with multi-model fallback to `gemini-3.5-flash` / `gemini-3.8-flash`)
- **Document Processing:** PyMuPDF / `pypdf`, boundary-aware overlapping chunking with 1-based page metadata
- **Frontend:** React 19, Vite, Vanilla CSS (custom deep navy/teal theme, citation modal, suggested prompts)
- **Testing:** Pytest (29 passing regression tests)

---

## Project Structure

```text
AI-Chatbot/
├── backend/
│   ├── app/
│   │   ├── __init__.py        # Backend package marker
│   │   ├── main.py            # FastAPI entrypoint & lifecycle management
│   │   ├── config.py          # Settings and environment configuration
│   │   ├── schemas.py         # Pydantic request/response/citation models
│   │   ├── routes/            # API endpoints (chat, health)
│   │   │   └── chat.py
│   │   └── services/          # Core RAG services
│   │       ├── pdf_service.py # PDF extraction & chunking
│   │       ├── vector_store.py# FAISS vector store & persistence
│   │       └── ai_service.py  # Gemini embeddings, generation, caching
│   ├── data/                  # College handbook directory (place college_rules.pdf here)
│   │   └── .gitkeep
│   ├── tests/                 # 29 unit and integration tests
│   │   ├── test_chat.py
│   │   ├── test_health.py
│   │   ├── test_pdf_service.py
│   │   └── test_rag.py
│   ├── requirements.txt       # Python dependencies
│   └── .env.example           # Environment template
├── frontend/                  # React + Vite frontend application
│   ├── src/
│   │   ├── components/        # UI components (WelcomeScreen, ChatMessage, ChatInput, SourceModal)
│   │   ├── services/          # API fetch client
│   │   ├── utils/             # Markdown parser
│   │   ├── App.jsx
│   │   ├── App.css
│   │   └── index.css
│   ├── package.json
│   ├── vite.config.js
│   └── .env.example
├── .gitignore                 # Secrets, environments, and large binaries
└── README.md                  # Project overview and documentation
```

---

## Getting Started

### 1. Backend Setup

1. **Navigate to the backend directory:**
   ```powershell
   cd backend
   ```

2. **Create and activate a virtual environment:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```powershell
   copy .env.example .env
   ```
   Add your Google AI Studio API key in `backend/.env`:
   ```dotenv
   GEMINI_API_KEY=your_actual_gemini_api_key
   COLLEGE_RULES_PDF=backend/data/college_rules.pdf
   ```

5. **Place your College Handbook PDF:**
   Place your institution's rules handbook at:
   ```text
   backend/data/college_rules.pdf
   ```

6. **Start the FastAPI backend server:**
   ```powershell
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

- **Swagger Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Endpoint:** [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

---

### 2. Frontend Setup

1. **Navigate to the frontend directory:**
   ```powershell
   cd frontend
   ```

2. **Install dependencies:**
   ```powershell
   npm install
   ```

3. **Configure environment:**
   ```powershell
   copy .env.example .env
   ```
   *(Defaults to `VITE_API_BASE_URL=http://127.0.0.1:8000`)*

4. **Start the Vite development server:**
   ```powershell
   npm run dev
   ```

Open your browser at **[http://127.0.0.1:5173](http://127.0.0.1:5173)** to chat with the College Rules Assistant.

---

## Running the Automated Test Suite

Run all unit and integration tests from the `backend/` directory:

```powershell
cd backend
pytest tests/ -v
```

All 29 tests validate request parsing, PDF normalization, chunking, FAISS vector retrieval, cosine similarity thresholds, query embedding cache invalidation, and grounded refusal behavior.
