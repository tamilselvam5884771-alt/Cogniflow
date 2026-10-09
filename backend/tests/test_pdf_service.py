import io
import pytest
import pypdf
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

from app.services.pdf_service import (
    PDFService,
    PDFPageText,
    DocumentChunk,
    PDFFileTooLargeError,
    InvalidPDFFormatError,
    EncryptedPDFError,
    MalformedPDFError,
    EmptyPDFError,
    ScannedOrInsufficientTextPDFError,
)


# ============================================================================
# Helpers to generate in-memory test PDFs
# ============================================================================

def make_test_pdf_with_text(pages_text: list[str]) -> bytes:
    """Generate a valid in-memory PDF containing the specified text on each page."""
    writer = pypdf.PdfWriter()
    for text in pages_text:
        page = writer.add_blank_page(width=300, height=300)
        # Content stream with Helvetica font
        stream_content = f"BT /F1 12 Tf 50 250 Td ({text}) Tj ET".encode("latin-1")
        stream = DecodedStreamObject()
        stream.set_data(stream_content)

        font = DictionaryObject({
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        })
        resources = DictionaryObject({
            NameObject("/Font"): DictionaryObject({
                NameObject("/F1"): font
            })
        })
        page[NameObject("/Contents")] = stream
        page[NameObject("/Resources")] = resources

    bio = io.BytesIO()
    writer.write(bio)
    return bio.getvalue()


def make_blank_pdf(num_pages: int = 1) -> bytes:
    """Generate an in-memory PDF with blank pages (no extractable text)."""
    writer = pypdf.PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=200, height=200)
    bio = io.BytesIO()
    writer.write(bio)
    return bio.getvalue()


def make_empty_pdf() -> bytes:
    """Generate an in-memory PDF with zero pages."""
    writer = pypdf.PdfWriter()
    bio = io.BytesIO()
    writer.write(bio)
    return bio.getvalue()


def make_encrypted_pdf(text: str = "Secret institutional policy", password: str = "pass123") -> bytes:
    """Generate an encrypted and password-protected PDF."""
    writer = pypdf.PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    stream = DecodedStreamObject()
    stream.set_data(f"BT /F1 12 Tf 50 250 Td ({text}) Tj ET".encode("latin-1"))
    font = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    })
    page[NameObject("/Contents")] = stream
    page[NameObject("/Resources")] = DictionaryObject({
        NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})
    })
    writer.encrypt(password)
    bio = io.BytesIO()
    writer.write(bio)
    return bio.getvalue()


# ============================================================================
# Unit Tests
# ============================================================================

def test_multi_page_pdf_extraction_and_1based_numbering():
    """Verify that multi-page PDFs extract correctly with 1-based page numbering."""
    page_1_content = "College Rules Handbook Chapter 1: Academic Conduct and Integrity guidelines."
    page_2_content = "Attendance Policy: All students must maintain a minimum of 75 percent attendance."
    page_3_content = "Disciplinary Proceedings: Violations will be referred to the Proctorial Board."

    pdf_bytes = make_test_pdf_with_text([page_1_content, page_2_content, page_3_content])
    pages = PDFService.extract_text_by_page(pdf_bytes, min_text_chars=30)

    assert len(pages) == 3
    # Check 1-based page numbering
    assert pages[0].page_number == 1
    assert "Academic Conduct" in pages[0].text

    assert pages[1].page_number == 2
    assert "75 percent attendance" in pages[1].text

    assert pages[2].page_number == 3
    assert "Proctorial Board" in pages[2].text


def test_chunk_creation_and_overlap():
    """Verify that large text is divided into overlapping chunks according to settings."""
    long_rule = (
        "Section 4.1 Attendance Regulations for Undergraduate Students. "
        "A student shall be eligible to appear for the end-semester examination "
        "only if he or she has acquired a minimum of 75 percent attendance in each subject. "
        "Condonation of attendance up to 10 percent may be granted on medical grounds "
        "subject to approval by the Dean of Academic Affairs. "
        "Medical certificates must be submitted within seven working days of returning to campus."
    )
    pages = [PDFPageText(page_number=1, text=long_rule)]
    chunks = PDFService.chunk_text(
        pages=pages,
        document_id="doc_rules_2026",
        chunk_size=120,
        chunk_overlap=30,
    )

    assert len(chunks) > 1
    # Check that adjacent chunks share overlapping text
    for i in range(len(chunks) - 1):
        c1 = chunks[i].text
        c2 = chunks[i + 1].text
        # Every chunk must be within reasonable size
        assert len(c1) <= 150
        # Ensure continuity
        assert c1[-15:] in long_rule
        assert c2[:15] in long_rule


def test_preservation_of_page_metadata():
    """Verify that every chunk attaches document_id, 1-based page_number, chunk_id, and text."""
    pages = [
        PDFPageText(page_number=1, text="Page 1: Overview of institute guidelines and mission statement."),
        PDFPageText(page_number=2, text="Page 2: Comprehensive examination regulations and grading scale."),
    ]
    chunks = PDFService.chunk_text(pages=pages, document_id="handbook_v1", chunk_size=200, chunk_overlap=40)

    assert len(chunks) == 2

    assert chunks[0].document_id == "handbook_v1"
    assert chunks[0].page_number == 1
    assert chunks[0].chunk_id == "handbook_v1_p1_c0"
    assert "Overview of institute" in chunks[0].text

    assert chunks[1].document_id == "handbook_v1"
    assert chunks[1].page_number == 2
    assert chunks[1].chunk_id == "handbook_v1_p2_c0"
    assert "Comprehensive examination regulations" in chunks[1].text


def test_empty_pdf_detection():
    """Verify that a PDF containing 0 pages raises EmptyPDFError."""
    empty_pdf = make_empty_pdf()
    with pytest.raises(EmptyPDFError, match="contains 0 pages"):
        PDFService.extract_text_by_page(empty_pdf)


def test_malformed_pdf():
    """Verify that corrupt or invalid PDF bytes raise appropriate errors."""
    # Invalid magic signature
    with pytest.raises(InvalidPDFFormatError, match="Invalid file signature"):
        PDFService.validate_pdf_bytes(b"NOT_A_PDF_FILE_HEADER")

    # Valid header bytes followed by corrupted stream
    corrupt_pdf = b"%PDF-1.4\nCorrupted stream data that cannot be parsed by pypdf %%EOF"
    with pytest.raises(MalformedPDFError, match="Corrupted or malformed"):
        PDFService.extract_text_by_page(corrupt_pdf)


def test_encrypted_pdf():
    """Verify that an encrypted/password-protected PDF raises EncryptedPDFError."""
    enc_pdf = make_encrypted_pdf(password="secure_college_pass")
    with pytest.raises(EncryptedPDFError, match="encrypted and password-protected"):
        PDFService.extract_text_by_page(enc_pdf)


def test_scanned_or_insufficient_text_pdf():
    """Verify that image-only/blank PDFs raise ScannedOrInsufficientTextPDFError."""
    blank_pdf = make_blank_pdf(num_pages=3)
    with pytest.raises(ScannedOrInsufficientTextPDFError, match="insufficient extractable text"):
        PDFService.extract_text_by_page(blank_pdf, min_text_chars=50)


def test_file_size_validation():
    """Verify that file size limits are strictly enforced."""
    small_limit = 100
    oversized_data = b"%PDF-1.4 " + (b"X" * 200)

    with pytest.raises(PDFFileTooLargeError, match="exceeds maximum limit"):
        PDFService.validate_pdf_bytes(oversized_data, max_size_bytes=small_limit)


def test_filename_extension_validation():
    """Verify that non-PDF extensions are rejected."""
    valid_pdf_header = b"%PDF-1.4\nvalid content"
    with pytest.raises(InvalidPDFFormatError, match=r"File must have a \.pdf extension"):
        PDFService.validate_pdf_bytes(valid_pdf_header, filename="document.docx")


def test_whitespace_normalization():
    """Verify whitespace cleaning preserves paragraph breaks while collapsing redundant spaces."""
    raw = "   Rule 1:   No   smoking.\r\n\r\n\r\n\r\nRule 2:   Carry ID card.\t\tAlways.   "
    cleaned = PDFService.normalize_text(raw)
    assert cleaned == "Rule 1: No smoking.\n\nRule 2: Carry ID card. Always."


def test_end_to_end_process_pdf():
    """Verify the end-to-end process_pdf pipeline."""
    pdf_text = [
        "College Code of Conduct for Students 2026. Every student must register for each semester in person.",
        "Examination Protocol: Hall tickets must be presented along with official college identity cards.",
    ]
    pdf_bytes = make_test_pdf_with_text(pdf_text)

    pages, chunks = PDFService.process_pdf(
        file_bytes=pdf_bytes,
        filename="college_rules.pdf",
        document_id="doc_test_101",
        chunk_size=300,
        chunk_overlap=50,
    )

    assert len(pages) == 2
    assert len(chunks) == 2
    assert chunks[0].document_id == "doc_test_101"
    assert chunks[0].page_number == 1
    assert chunks[1].page_number == 2
