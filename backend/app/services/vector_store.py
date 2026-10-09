import json
import logging
from pathlib import Path
from typing import List, Optional, Tuple

import faiss
import numpy as np

from app.services.pdf_service import DocumentChunk

logger = logging.getLogger(__name__)


class VectorStore:
    """In-memory FAISS vector index using normalized cosine similarity."""

    def __init__(self, dimension: int = 3072):
        self.dimension = dimension
        self.index: Optional[faiss.IndexFlatIP] = None
        self.chunks: List[DocumentChunk] = []

    def clear(self) -> None:
        """Reset the index and stored chunks."""
        self.index = None
        self.chunks = []

    def is_indexed(self) -> bool:
        """Check if the vector index is initialized and populated."""
        return self.index is not None and self.index.ntotal > 0

    def count(self) -> int:
        """Return the number of vectors stored in the index."""
        if self.index is None:
            return 0
        return self.index.ntotal

    def build_index(self, chunks: List[DocumentChunk], embeddings: np.ndarray) -> None:
        """Build and populate the FAISS index with L2-normalized vectors.

        Args:
            chunks: List of DocumentChunk metadata objects.
            embeddings: 2D numpy array of shape (N, dimension) of float32 dtype.
        """
        if len(chunks) == 0:
            raise ValueError("Cannot build vector index with 0 chunks.")

        if embeddings.shape[0] != len(chunks):
            raise ValueError(
                f"Mismatch: {len(chunks)} chunks provided but embeddings shape is {embeddings.shape}."
            )

        dim = embeddings.shape[1]
        self.dimension = dim

        # Ensure float32 dtype for FAISS
        vecs = np.ascontiguousarray(embeddings.astype("float32"))

        # L2-normalize vectors so inner product equals cosine similarity
        faiss.normalize_L2(vecs)

        # IndexFlatIP computes exact inner product (cosine similarity on normalized vectors)
        index = faiss.IndexFlatIP(dim)
        index.add(vecs)

        self.index = index
        self.chunks = list(chunks)
        logger.info("Successfully indexed %d chunks (dimension=%d) in FAISS", index.ntotal, dim)

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 4,
        threshold: Optional[float] = None,
    ) -> List[Tuple[DocumentChunk, float]]:
        """Search the FAISS index for the top-k most similar chunks.

        Args:
            query_embedding: 1D or 2D numpy array representing the query embedding.
            top_k: Maximum number of chunks to return.
            threshold: Optional cosine similarity threshold to filter results.

        Returns:
            List of (DocumentChunk, similarity_score) tuples, sorted by descending score.
        """
        if not self.is_indexed():
            return []

        q_vec = np.ascontiguousarray(query_embedding.astype("float32"))
        if q_vec.ndim == 1:
            q_vec = np.expand_dims(q_vec, axis=0)

        # Normalize query vector
        faiss.normalize_L2(q_vec)

        k = min(top_k, self.index.ntotal)
        scores, indices = self.index.search(q_vec, k)

        results: List[Tuple[DocumentChunk, float]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.chunks):
                continue

            float_score = float(score)
            if threshold is not None and float_score < threshold:
                continue

            results.append((self.chunks[idx], float_score))

        return results

    def save(self, index_file: Path, metadata_file: Path) -> None:
        """Persist FAISS index and chunk metadata to disk."""
        if not self.is_indexed():
            raise RuntimeError("Cannot save uninitialized vector store.")

        index_file.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(index_file))

        meta_list = [
            {
                "chunk_id": c.chunk_id,
                "document_id": c.document_id,
                "page_number": c.page_number,
                "text": c.text,
                "chunk_index": c.chunk_index,
                "char_count": c.char_count,
            }
            for c in self.chunks
        ]
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(meta_list, f, indent=2)

        logger.info("Persisted FAISS index to %s and metadata to %s", index_file, metadata_file)

    def load(self, index_file: Path, metadata_file: Path) -> None:
        """Load FAISS index and chunk metadata from disk."""
        if not index_file.is_file() or not metadata_file.is_file():
            raise FileNotFoundError("Index or metadata file does not exist.")

        self.index = faiss.read_index(str(index_file))
        self.dimension = self.index.d

        with open(metadata_file, "r", encoding="utf-8") as f:
            meta_list = json.load(f)

        self.chunks = [
            DocumentChunk(
                chunk_id=item["chunk_id"],
                document_id=item["document_id"],
                page_number=item["page_number"],
                text=item["text"],
                chunk_index=item["chunk_index"],
                char_count=item["char_count"],
            )
            for item in meta_list
        ]
        logger.info(
            "Loaded FAISS index with %d vectors and %d chunks from %s",
            self.index.ntotal,
            len(self.chunks),
            index_file,
        )
