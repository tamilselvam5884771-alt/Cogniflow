from pathlib import Path
from unittest.mock import MagicMock
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import CitationSource
from app.services.ai_service import AIService, get_ai_service
from app.services.pdf_service import DocumentChunk
from app.services.vector_store import VectorStore


@pytest.fixture
def sample_college_chunks():
    """Create sample chunks representing official college handbook sections."""
    return [
        DocumentChunk(
            chunk_id="chunk_attendance_p12",
            document_id="handbook_test",
            page_number=12,
            text=(
                "Academic Regulations: Minimum Attendance Requirement. "
                "Students must maintain at least 75% attendance in every course to qualify for end-semester exams."
            ),
            chunk_index=0,
            char_count=138,
        ),
        DocumentChunk(
            chunk_id="chunk_malpractice_p34",
            document_id="handbook_test",
            page_number=34,
            text=(
                "Examination Protocol and Malpractice Policy. "
                "Possession of cell phones, programmable calculators, or unauthorized study material in exam halls "
                "shall lead to immediate cancellation of the paper."
            ),
            chunk_index=1,
            char_count=198,
        ),
        DocumentChunk(
            chunk_id="chunk_hostel_p55",
            document_id="handbook_test",
            page_number=55,
            text=(
                "Hostel Rules and Curfew Timings. "
                "Hostel resident students must check in before 8:30 PM on all weekdays. "
                "Night outs require written parental permission and Warden approval."
            ),
            chunk_index=2,
            char_count=172,
        ),
    ]


@pytest.fixture
def mock_gemini_client():
    """Mock Google Gemini client simulating embed_content and generate_content."""
    client = MagicMock()

    def mock_embed_content(model, contents, **kwargs):
        # Generate predictable unit vectors based on keywords
        resp = MagicMock()
        emb_list = []
        for text in contents:
            v = np.zeros(768, dtype="float32")
            if "attendance" in text.lower():
                v[0] = 1.0
            elif "malpractice" in text.lower() or "exam" in text.lower():
                v[1] = 1.0
            elif "hostel" in text.lower() or "curfew" in text.lower():
                v[2] = 1.0
            else:
                # Random / orthogonal vector
                v[10] = 1.0
            emb_obj = MagicMock()
            emb_obj.values = v.tolist()
            emb_list.append(emb_obj)
        resp.embeddings = emb_list
        return resp

    def mock_generate_content(model, contents, **kwargs):
        resp = MagicMock()
        resp.text = "Students are required to maintain a minimum of 75% attendance in each course. (Page 12)"
        return resp

    client.models.embed_content.side_effect = mock_embed_content
    client.models.generate_content.side_effect = mock_generate_content
    return client


def test_missing_pdf_raises_clear_error():
    """Verify that attempting to load a missing PDF raises FileNotFoundError with clear message."""
    service = AIService()
    missing_path = Path("non_existent_college_rules_doc_xyz.pdf")

    with pytest.raises(FileNotFoundError, match="College rules PDF not found"):
        service.load_and_index_college_rules(pdf_path=missing_path)


def test_faiss_vector_store_indexing_and_cosine_retrieval(sample_college_chunks):
    """Verify that FAISS stores normalized embeddings and computes accurate cosine similarity."""
    store = VectorStore(dimension=4)

    # 3 orthogonal unit vectors
    embeddings = np.array([
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
    ], dtype="float32")

    store.build_index(chunks=sample_college_chunks, embeddings=embeddings)
    assert store.is_indexed() is True
    assert store.count() == 3

    # Query matching vector 0 (attendance)
    query = np.array([[1.0, 0.0, 0.0, 0.0]], dtype="float32")
    results = store.search(query, top_k=2, threshold=0.5)

    assert len(results) == 1
    top_chunk, top_score = results[0]
    assert top_chunk.page_number == 12
    assert "Attendance" in top_chunk.text
    assert top_score > 0.99


def test_relevant_question_retrieval_and_citations(sample_college_chunks, mock_gemini_client):
    """Verify that relevant questions retrieve correct chunks and attach accurate page citations."""
    service = AIService(client=mock_gemini_client)

    # Embed sample chunks using the mock embedder
    chunk_texts = [c.text for c in sample_college_chunks]
    embeddings = service.embed_texts(chunk_texts)
    service.vector_store.build_index(chunks=sample_college_chunks, embeddings=embeddings)

    import asyncio
    reply, sources = asyncio.run(
        service.generate_reply(
            message="What is the mandatory attendance requirement?",
            top_k=2,
            threshold=0.50,
        )
    )

    assert "75%" in reply
    assert len(sources) > 0

    # Verify citation page metadata
    top_source = sources[0]
    assert top_source.page_number == 12
    assert top_source.chunk_id == "chunk_attendance_p12"
    assert "Minimum Attendance Requirement" in top_source.snippet


def test_irrelevant_question_refusal_when_below_threshold(sample_college_chunks, mock_gemini_client):
    """Verify that questions not covered in the document are refused without hallucination."""
    service = AIService(client=mock_gemini_client)

    chunk_texts = [c.text for c in sample_college_chunks]
    embeddings = service.embed_texts(chunk_texts)
    service.vector_store.build_index(chunks=sample_college_chunks, embeddings=embeddings)

    import asyncio
    # Question on completely unrelated topic (e.g., rocket propulsion)
    reply, sources = asyncio.run(
        service.generate_reply(
            message="What is the orbital velocity of the International Space Station?",
            top_k=2,
            threshold=0.70,  # Strict threshold
        )
    )

    assert "does not provide enough information" in reply
    assert len(sources) == 0


def test_citation_correctness_never_invented(sample_college_chunks, mock_gemini_client):
    """Verify citations strictly originate from vector store chunk metadata."""
    service = AIService(client=mock_gemini_client)

    chunk_texts = [c.text for c in sample_college_chunks]
    embeddings = service.embed_texts(chunk_texts)
    service.vector_store.build_index(chunks=sample_college_chunks, embeddings=embeddings)

    import asyncio
    _, sources = asyncio.run(
        service.generate_reply(
            message="What are the penalties for exam malpractice?",
            top_k=1,
            threshold=0.50,
        )
    )

    assert len(sources) == 1
    # Page must match the indexed malpractice page (34)
    assert sources[0].page_number == 34
    assert sources[0].chunk_id == "chunk_malpractice_p34"


def test_uninitialized_index_returns_503_via_chat_endpoint():
    """Verify endpoint returns HTTP 503 when the vector store has not been indexed."""
    unindexed_service = AIService()
    unindexed_service.vector_store.clear()

    app.dependency_overrides[get_ai_service] = lambda: unindexed_service
    test_client = TestClient(app)
    try:
        response = test_client.post("/api/chat", json={"message": "What is the fee structure?"})
        assert response.status_code == 503
        data = response.json()
        assert "not initialized" in data["detail"].lower()
    finally:
        app.dependency_overrides.clear()


def test_query_embedding_cache_and_invalidation(mock_gemini_client):
    """Verify that query embeddings are cached on repeat calls and cleared on invalidation."""
    service = AIService(client=mock_gemini_client)
    q = "What is the leave policy?"

    # First call: cache miss, calls client
    emb1 = service.embed_query(q)
    assert mock_gemini_client.models.embed_content.call_count == 1
    assert q.lower() in service._query_cache

    # Second call: cache hit, does not call client again
    emb2 = service.embed_query(q)
    assert mock_gemini_client.models.embed_content.call_count == 1
    assert np.allclose(emb1, emb2)

    # Invalidation: clear cache
    service.clear_query_cache()
    assert len(service._query_cache) == 0

    # Third call after invalidation: calls client again
    emb3 = service.embed_query(q)
    assert mock_gemini_client.models.embed_content.call_count == 2
    assert np.allclose(emb1, emb3)


def test_pipeline_timing_diagnostics_instrumentation(sample_college_chunks, mock_gemini_client):
    """Verify pipeline records stage latencies and attaches diagnostic timings."""
    service = AIService(client=mock_gemini_client)
    chunk_texts = [c.text for c in sample_college_chunks]
    embeddings = service.embed_texts(chunk_texts)
    service.vector_store.build_index(chunks=sample_college_chunks, embeddings=embeddings)

    import asyncio
    _, sources = asyncio.run(service.generate_reply(message="What is the attendance rule?", top_k=2))

    assert service.last_timings is not None
    timings = service.last_timings
    assert "embedding_latency_s" in timings
    assert "faiss_latency_s" in timings
    assert "retrieved_chunks" in timings
    assert "context_latency_s" in timings
    assert "generation_latency_s" in timings
    assert "total_latency_s" in timings
    assert "cache_hit" in timings
    assert timings["retrieved_chunks"] > 0

