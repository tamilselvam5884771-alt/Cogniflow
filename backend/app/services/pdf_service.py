import io
import re
import uuid
import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

import pypdf
from pypdf.errors import PdfReadError

from app.config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# Typed Custom Exceptions
# ============================================================================

class PDFProcessingError(Exception):
    """Base exception for all PDF processing errors."""
    pass


class PDFFileTooLargeError(PDFProcessingError):
    """Raised when the uploaded file exceeds maximum allowed size."""
    pass


class InvalidPDFFormatError(PDFProcessingError):
    """Raised when the file does not have a .pdf extension or lacks a valid PDF signature."""
    pass


class EncryptedPDFError(PDFProcessingError):
    """Raised when the PDF file is encrypted and password-protected."""
    pass


class MalformedPDFError(PDFProcessingError):
    """Raised when the PDF file structure is corrupt or unreadable."""
    pass


class EmptyPDFError(PDFProcessingError):
    """Raised when the PDF file has zero pages."""
    pass


class ScannedOrInsufficientTextPDFError(PDFProcessingError):
    """Raised when the PDF contains insufficient extractable text (e.g. scanned image)."""
    pass


# ============================================================================
# Data Models
# ============================================================================

@dataclass(frozen=True)
class PDFPageText:
    """Represents text extracted from a single PDF page."""
    page_number: int  # 1-based page number
    text: str


@dataclass(frozen=True)
class DocumentChunk:
    """Represents a text chunk created from an extracted PDF page for vector indexing."""
    chunk_id: str
    document_id: str
    page_number: int  # 1-based page number
    text: str
    chunk_index: int
    char_count: int


# ============================================================================
# Service Implementation
# ============================================================================

class PDFService:
    """Service for validating, extracting, and chunking PDF documents."""

    PDF_MAGIC_BYTES = b"%PDF-"

    @classmethod
    def validate_pdf_bytes(
        cls,
        file_bytes: bytes,
        filename: Optional[str] = None,
        max_size_bytes: int = settings.MAX_UPLOAD_SIZE_BYTES,
    ) -> None:
        """Validate file size, extension, and PDF header signature.

        Args:
            file_bytes: Raw binary content of the file.
            filename: Optional original filename.
            max_size_bytes: Maximum allowed file size in bytes.

        Raises:
            PDFFileTooLargeError: If file exceeds size limit.
            InvalidPDFFormatError: If filename extension or header signature is invalid.
        """
        # Validate size
        if len(file_bytes) > max_size_bytes:
            raise PDFFileTooLargeError(
                f"File size ({len(file_bytes)} bytes) exceeds maximum limit "
                f"of {max_size_bytes} bytes."
            )

        if len(file_bytes) == 0:
            raise InvalidPDFFormatError("File is empty (0 bytes).")

        # Validate filename extension if provided
        if filename:
            clean_name = filename.strip().lower()
            if not clean_name.endswith(".pdf"):
                raise InvalidPDFFormatError("File must have a .pdf extension.")

        # Validate magic bytes (%PDF- within initial 1024 bytes per PDF standard)
        header_slice = file_bytes[:1024].lstrip()
        if not header_slice.startswith(cls.PDF_MAGIC_BYTES):
            raise InvalidPDFFormatError(
                "Invalid file signature. The file does not appear to be a valid PDF document."
            )

    @classmethod
    def normalize_text(cls, raw_text: str) -> str:
        """Normalize extracted whitespace while preserving meaningful paragraph breaks.

        Args:
            raw_text: Raw text string extracted from PDF.

        Returns:
            str: Cleaned, normalized text.
        """
        if not raw_text:
            return ""

        # Normalize line breaks
        text = raw_text.replace("\r\n", "\n").replace("\r", "\n")

        # Replace non-breaking spaces with standard space
        text = text.replace("\u00a0", " ")

        # Collapse multiple horizontal whitespace characters (spaces, tabs) into a single space
        text = re.sub(r"[ \t]+", " ", text)

        # Remove trailing and leading spaces from each line
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(lines)

        # Collapse 3 or more consecutive newlines into 2 (paragraph boundary)
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()

    @classmethod
    def extract_text_by_page(
        cls,
        file_bytes: bytes,
        min_text_chars: int = settings.MIN_EXTRACTABLE_TEXT_CHARS,
    ) -> List[PDFPageText]:
        """Extract text page-by-page using pypdf, preserving 1-based page numbering.

        Args:
            file_bytes: Validated raw bytes of the PDF.
            min_text_chars: Minimum total characters required across all pages.

        Returns:
            List[PDFPageText]: Extracted pages with 1-based page numbers.

        Raises:
            MalformedPDFError: If PDF structure cannot be parsed.
            EncryptedPDFError: If PDF is encrypted/password-protected.
            EmptyPDFError: If PDF contains 0 pages.
            ScannedOrInsufficientTextPDFError: If extractable text is below threshold.
        """
        try:
            stream = io.BytesIO(file_bytes)
            reader = pypdf.PdfReader(stream)
        except Exception as exc:
            logger.warning("Failed to parse PDF bytes: %s", exc)
            raise MalformedPDFError("Corrupted or malformed PDF file could not be parsed.") from exc

        # Check encryption
        if reader.is_encrypted:
            try:
                # Attempt empty password decryption
                decrypted = reader.decrypt("")
                if not decrypted:
                    raise EncryptedPDFError("The PDF document is encrypted and password-protected.")
            except Exception as exc:
                raise EncryptedPDFError("The PDF document is encrypted and password-protected.") from exc

        # Check page count
        total_pages = len(reader.pages)
        if total_pages == 0:
            raise EmptyPDFError("The PDF document contains 0 pages.")

        pages_extracted: List[PDFPageText] = []
        total_char_count = 0

        for page_idx, page in enumerate(reader.pages):
            page_number = page_idx + 1  # 1-based page numbering
            try:
                raw_page_text = page.extract_text() or ""
            except Exception as exc:
                logger.warning("Error extracting text from page %d: %s", page_number, exc)
                raw_page_text = ""

            cleaned_text = cls.normalize_text(raw_page_text)
            pages_extracted.append(PDFPageText(page_number=page_number, text=cleaned_text))
            total_char_count += len(cleaned_text)

        # Check for scanned / image-only PDFs
        if total_char_count < min_text_chars:
            raise ScannedOrInsufficientTextPDFError(
                f"The PDF contains insufficient extractable text ({total_char_count} characters found). "
                "The document appears to be a scanned image-only PDF which requires OCR preprocessing."
            )

        return pages_extracted

    @classmethod
    def chunk_text(
        cls,
        pages: List[PDFPageText],
        document_id: str,
        chunk_size: int = settings.DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = settings.DEFAULT_CHUNK_OVERLAP,
    ) -> List[DocumentChunk]:
        """Split page texts into overlapping chunks with complete metadata attachment.

        Args:
            pages: List of extracted PDFPageText objects.
            document_id: Unique identifier for the parent document.
            chunk_size: Maximum character length for each chunk.
            chunk_overlap: Number of characters to overlap between adjacent chunks.

        Returns:
            List[DocumentChunk]: Structured text chunks with provenance metadata.
        """
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than 0.")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be non-negative and strictly less than chunk_size.")

        chunks: List[DocumentChunk] = []
        step = chunk_size - chunk_overlap

        for page in pages:
            page_text = page.text
            if not page_text:
                continue

            # If page text fits entirely within one chunk
            if len(page_text) <= chunk_size:
                chunk = DocumentChunk(
                    chunk_id=f"{document_id}_p{page.page_number}_c0",
                    document_id=document_id,
                    page_number=page.page_number,
                    text=page_text,
                    chunk_index=0,
                    char_count=len(page_text),
                )
                chunks.append(chunk)
                continue

            # Sliding window with boundary awareness
            start = 0
            page_chunk_idx = 0

            while start < len(page_text):
                end = min(start + chunk_size, len(page_text))
                chunk_str = page_text[start:end]

                # Look for natural breakpoint if not at document end
                if end < len(page_text):
                    search_start = int(len(chunk_str) * 0.75)
                    boundary_zone = chunk_str[search_start:]
                    break_offset = -1
                    for delimiter in ("\n\n", "\n", ". ", " "):
                        pos = boundary_zone.rfind(delimiter)
                        if pos != -1:
                            break_offset = search_start + pos + len(delimiter)
                            break
                    if break_offset > 0:
                        chunk_str = chunk_str[:break_offset]
                        end = start + len(chunk_str)

                cleaned_chunk = chunk_str.strip()
                if cleaned_chunk:
                    chunks.append(
                        DocumentChunk(
                            chunk_id=f"{document_id}_p{page.page_number}_c{page_chunk_idx}",
                            document_id=document_id,
                            page_number=page.page_number,
                            text=cleaned_chunk,
                            chunk_index=page_chunk_idx,
                            char_count=len(cleaned_chunk),
                        )
                    )
                    page_chunk_idx += 1

                start += step
                if start >= len(page_text):
                    break

        return chunks

    @classmethod
    def process_pdf(
        cls,
        file_bytes: bytes,
        filename: Optional[str] = None,
        document_id: Optional[str] = None,
        chunk_size: int = settings.DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = settings.DEFAULT_CHUNK_OVERLAP,
    ) -> Tuple[List[PDFPageText], List[DocumentChunk]]:
        """End-to-end pipeline: validation -> text extraction -> metadata chunking.

        Args:
            file_bytes: Raw binary content of the PDF.
            filename: Optional filename.
            document_id: Optional document identifier (UUID generated if omitted).
            chunk_size: Chunk size in characters.
            chunk_overlap: Chunk overlap in characters.

        Returns:
            Tuple[List[PDFPageText], List[DocumentChunk]]: Extracted pages and chunk list.
        """
        cls.validate_pdf_bytes(file_bytes=file_bytes, filename=filename)
        pages = cls.extract_text_by_page(file_bytes=file_bytes)
        doc_id = document_id or str(uuid.uuid4())
        chunks = cls.chunk_text(
            pages=pages,
            document_id=doc_id,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        return pages, chunks
