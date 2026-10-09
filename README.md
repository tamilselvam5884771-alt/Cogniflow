# AI Chatbot

A modern, full-stack AI Chatbot application powered by **FastAPI**, **React + Vite**, and the **Google Gemini API** (`google-genai` SDK).

---

## Project Structure

```text
AI-Chatbot/
├── backend/
│   ├── app/
│   │   ├── __init__.py        # Backend package marker
│   │   ├── main.py            # FastAPI entrypoint & health endpoints
│   │   ├── config.py          # Settings and environment configuration
│   │   ├── schemas.py         # Pydantic request/response models
│   │   ├── routes/            # API route controllers
│   │   │   └── __init__.py
│   │   └── services/          # External services (Gemini, business logic)
│   │       └── __init__.py
│   ├── tests/                 # Unit and integration test suites
│   ├── requirements.txt       # Python package dependencies
│   ├── .env.example           # Template for environment variables
│   └── .gitignore             # Git ignore rules for backend
├── frontend/                  # React + Vite frontend application
└── README.md                  # Project overview and documentation
```

---

## Step 1: Backend Setup & Health Check

### Prerequisites
- Python 3.10+ installed
- Windows Terminal / PowerShell

### Backend Setup (Windows)

1. **Navigate to the backend directory:**
   ```powershell
   cd backend
   ```

2. **Create a virtual environment:**
   ```powershell
   python -m venv .venv
   ```

3. **Activate the virtual environment:**
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
   *(If script execution is disabled in PowerShell, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` or activate with `.\.venv\Scripts\activate.bat` in CMD).*

4. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

5. **Create environment file:**
   ```powershell
   copy .env.example .env
   ```

6. **Start the FastAPI development server:**
   ```powershell
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

---

## Verifying the API

- **Interactive API Documentation (Swagger UI):**  
  [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Alternative ReDoc UI:**  
  [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Check Endpoint:**  
  [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

Response:
```json
{
  "status": "ok",
  "message": "AI Chatbot backend is up and running!",
  "version": "0.1.0",
  "environment": "development"
}
```

---

## Step 2: Chat API Implementation

### Chat Endpoint: `POST /api/chat`

Accepts user messages and returns an assistant response (mock reply in Step 2; separated for Gemini integration in Step 3).

**Request Body:**
```json
{
  "message": "Hello, how are you?",
  "session_id": null
}
```

**Response Body (`200 OK`):**
```json
{
  "success": true,
  "reply": "Hello! How can I help you?",
  "session_id": "97f6531a-e18a-41fd-a7a1-40c2ea202baa"
}
```

### Running the Tests

Run the test suite using pytest inside the `backend` folder:
```powershell
pytest -v
```

