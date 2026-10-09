import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.ai_service import AIService, get_ai_service

client = TestClient(app)


class MockChatAIService(AIService):
    """Mock AI Service for regression testing the HTTP endpoint layer without Gemini API."""

    async def generate_reply(self, message: str, session_id: str = None, **kwargs):
        return "Hello! How can I help you?", []


@pytest.fixture(autouse=True)
def setup_mock_ai():
    """Ensure endpoint tests use MockChatAIService instance by default."""
    mock_instance = MockChatAIService()
    app.dependency_overrides[get_ai_service] = lambda: mock_instance
    yield
    app.dependency_overrides.clear()


def test_valid_message():
    """Case 1: Test valid message returns HTTP 200, reply, and matching session."""
    payload = {
        "message": "Hello, how are you?",
        "session_id": "test-session-123",
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["reply"] == "Hello! How can I help you?"
    assert data["session_id"] == "test-session-123"
    assert "sources" in data


def test_empty_message():
    """Case 2: Test empty message is rejected with HTTP 422 Unprocessable Entity."""
    payload = {
        "message": "",
        "session_id": "test-session-123",
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 422

    data = response.json()
    assert "detail" in data
    assert any("message" in str(err.get("loc", [])) for err in data["detail"])


def test_message_only_spaces():
    """Case 3: Test message containing only whitespace is rejected with HTTP 422."""
    payload = {
        "message": "     \n\t  ",
        "session_id": "test-session-123",
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 422

    data = response.json()
    assert "detail" in data
    assert any(
        "cannot be empty or contain only whitespace" in str(err.get("msg", ""))
        for err in data["detail"]
    )


def test_message_exceeding_max_length():
    """Case 4: Test message exceeding maximum allowed length is rejected with HTTP 422."""
    too_long_message = "x" * 4001
    payload = {
        "message": too_long_message,
        "session_id": "test-session-123",
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 422

    data = response.json()
    assert "detail" in data
    assert any(
        "cannot exceed 4000 characters" in str(err.get("msg", ""))
        for err in data["detail"]
    )


def test_request_without_session_id():
    """Case 5: Test request without session_id (or with null) generates a new session ID."""
    # Subtest 1: Omitted session_id field
    response1 = client.post("/api/chat", json={"message": "Hello there!"})
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["success"] is True
    assert data1["session_id"] is not None
    assert len(data1["session_id"]) > 0
    uuid.UUID(data1["session_id"])

    # Subtest 2: session_id passed as null
    response2 = client.post(
        "/api/chat", json={"message": "Hello again!", "session_id": None}
    )
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["success"] is True
    assert data2["session_id"] is not None
    assert len(data2["session_id"]) > 0
    uuid.UUID(data2["session_id"])


def test_request_with_existing_session_id():
    """Case 6: Test request with existing session ID preserves the provided ID."""
    existing_id = "user-custom-session-987"
    payload = {
        "message": "Continuing conversation",
        "session_id": existing_id,
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["reply"] == "Hello! How can I help you?"
    assert data["session_id"] == existing_id


def test_unexpected_service_error():
    """Case 7: Test unexpected service failure returns safe HTTP 500 without leaking stack traces."""

    class FailingAIService(AIService):
        async def generate_reply(self, message: str, session_id: str = None, **kwargs):
            raise Exception("Database connection suddenly dropped")

    failing_instance = FailingAIService()
    app.dependency_overrides[get_ai_service] = lambda: failing_instance
    try:
        payload = {"message": "Hello world"}
        response = client.post("/api/chat", json=payload)
        assert response.status_code == 500

        data = response.json()
        assert data["detail"] == "An unexpected error occurred while processing your request."
        assert "Database connection suddenly dropped" not in response.text
    finally:
        app.dependency_overrides.clear()


def test_message_whitespace_stripping():
    """Verify that leading and trailing whitespace are trimmed from valid messages."""
    payload = {
        "message": "   Hello with whitespace   ",
        "session_id": "sess-trim",
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["session_id"] == "sess-trim"
