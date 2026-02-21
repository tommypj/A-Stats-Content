"""
Unit tests for Document Processor.

Tests cover:
- File type detection
- Text extraction from various formats
- Text chunking with overlap
- Sentence boundary preservation
- Error handling
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from io import BytesIO

# Skip if processor not implemented yet
pytest.importorskip("adapters.knowledge.document_processor", reason="Document processor not yet implemented")

from adapters.knowledge.document_processor import (
    DocumentProcessor,
    DocumentType,
    UnsupportedDocumentError,
    DocumentProcessingError,
)


class TestDocumentTypeDetection:
    """Tests for document type detection."""

    @pytest.fixture
    def processor(self):
        """Create DocumentProcessor instance."""
        return DocumentProcessor(
            chunk_size=1000,
            chunk_overlap=200
        )

    def test_detect_type_pdf(self, processor):
        """Test PDF file detection."""
        pdf_content = b'%PDF-1.4\n%\xe2\xe3\xcf\xd3'  # PDF magic bytes

        file_type = processor.detect_type("document.pdf", pdf_content)

        assert file_type == DocumentType.PDF

    def test_detect_type_txt(self, processor):
        """Test plain text file detection."""
        txt_content = b'This is plain text content.'

        file_type = processor.detect_type("notes.txt", txt_content)

        assert file_type == DocumentType.TXT

    def test_detect_type_markdown(self, processor):
        """Test Markdown file detection."""
        md_content = b'# Heading\n\nThis is markdown.'

        file_type = processor.detect_type("readme.md", md_content)

        assert file_type == DocumentType.MARKDOWN

    def test_detect_type_docx(self, processor):
        """Test DOCX file detection."""
        # DOCX files are ZIP archives with specific structure
        docx_content = b'PK\x03\x04'  # ZIP magic bytes

        file_type = processor.detect_type("document.docx", docx_content)

        assert file_type == DocumentType.DOCX

    def test_detect_type_html(self, processor):
        """Test HTML file detection."""
        html_content = b'<!DOCTYPE html><html><body>Content</body></html>'

        file_type = processor.detect_type("page.html", html_content)

        assert file_type == DocumentType.HTML

    def test_detect_type_unknown_raises_error(self, processor):
        """Test that unknown file types raise an error."""
        unknown_content = b'\x00\x01\x02\x03'  # Random binary

        with pytest.raises(UnsupportedDocumentError, match="Unsupported document type"):
            processor.detect_type("unknown.xyz", unknown_content)


class TestTextChunking:
    """Tests for text chunking functionality."""

    @pytest.fixture
    def processor(self):
        """Create DocumentProcessor with specific chunk settings."""
        return DocumentProcessor(
            chunk_size=100,  # Small for testing
            chunk_overlap=20
        )

    def test_chunk_text_basic(self, processor):
        """Test basic text chunking."""
        text = "A" * 250  # 250 characters

        chunks = processor.chunk_text(text)

        # Should create multiple chunks
        assert len(chunks) > 1
        # First chunk should be ~100 chars
        assert len(chunks[0]) <= 120  # Some flexibility for sentence boundaries
        # Chunks should overlap
        assert chunks[1][:20] in chunks[0]

    def test_chunk_text_with_overlap(self, processor):
        """Test that chunks have proper overlap."""
        text = "This is sentence one. This is sentence two. This is sentence three. " * 5

        chunks = processor.chunk_text(text)

        # Verify overlap exists between consecutive chunks
        if len(chunks) > 1:
            # Last part of chunk 0 should appear in chunk 1
            overlap_found = False
            for i in range(len(chunks) - 1):
                chunk_end = chunks[i][-20:]
                chunk_start = chunks[i + 1][:30]
                if any(word in chunk_start for word in chunk_end.split()):
                    overlap_found = True
                    break
            assert overlap_found or len(chunks[0]) < 100  # Or chunks are small

    def test_chunk_text_short_document(self, processor):
        """Test chunking of document shorter than chunk_size."""
        text = "This is a short document."

        chunks = processor.chunk_text(text)

        # Should return single chunk
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunk_text_preserves_sentence_boundaries(self, processor):
        """Test that chunking tries to preserve sentence boundaries."""
        text = "First sentence. Second sentence. Third sentence. " * 10

        chunks = processor.chunk_text(text)

        # Each chunk should ideally end with a sentence
        for chunk in chunks[:-1]:  # Exclude last chunk
            # Should end with punctuation or be near chunk_size limit
            assert chunk.rstrip()[-1] in '.!?' or len(chunk) > 90

    def test_chunk_text_empty_input(self, processor):
        """Test chunking empty text."""
        text = ""

        chunks = processor.chunk_text(text)

        assert len(chunks) == 0

    def test_chunk_text_whitespace_only(self, processor):
        """Test chunking text with only whitespace."""
        text = "   \n\n   \t\t   "

        chunks = processor.chunk_text(text)

        # Should either be empty or contain minimal whitespace
        assert len(chunks) == 0 or all(not chunk.strip() for chunk in chunks)


class TestTextExtraction:
    """Tests for text extraction from various formats."""

    @pytest.fixture
    def processor(self):
        """Create DocumentProcessor instance."""
        return DocumentProcessor()

    def test_extract_text_txt(self, processor):
        """Test text extraction from plain text file."""
        content = b'This is plain text content.\nWith multiple lines.\n'

        text = processor.extract_text(content, DocumentType.TXT)

        assert text == "This is plain text content.\nWith multiple lines.\n"

    def test_extract_text_markdown(self, processor):
        """Test text extraction from Markdown file."""
        content = b'# Main Heading\n\n## Subheading\n\nThis is **bold** text.\n'

        text = processor.extract_text(content, DocumentType.MARKDOWN)

        # Should preserve markdown structure
        assert "# Main Heading" in text
        assert "**bold**" in text

    @patch('adapters.knowledge.document_processor.PyPDF2.PdfReader')
    def test_extract_text_pdf(self, mock_pdf_reader, processor):
        """Test text extraction from PDF file."""
        # Mock PDF reader
        mock_reader = Mock()
        mock_page1 = Mock()
        mock_page1.extract_text.return_value = "Page 1 content. "
        mock_page2 = Mock()
        mock_page2.extract_text.return_value = "Page 2 content."
        mock_reader.pages = [mock_page1, mock_page2]
        mock_pdf_reader.return_value = mock_reader

        pdf_content = b'%PDF-1.4\nfake pdf content'

        text = processor.extract_text(pdf_content, DocumentType.PDF)

        assert "Page 1 content" in text
        assert "Page 2 content" in text
        mock_pdf_reader.assert_called_once()

    @patch('adapters.knowledge.document_processor.docx.Document')
    def test_extract_text_docx(self, mock_docx, processor):
        """Test text extraction from DOCX file."""
        # Mock DOCX document
        mock_doc = Mock()
        mock_para1 = Mock()
        mock_para1.text = "First paragraph."
        mock_para2 = Mock()
        mock_para2.text = "Second paragraph."
        mock_doc.paragraphs = [mock_para1, mock_para2]
        mock_docx.return_value = mock_doc

        docx_content = b'PK\x03\x04fake docx'

        text = processor.extract_text(docx_content, DocumentType.DOCX)

        assert "First paragraph" in text
        assert "Second paragraph" in text

    @patch('adapters.knowledge.document_processor.BeautifulSoup')
    def test_extract_text_html(self, mock_bs, processor):
        """Test text extraction from HTML file."""
        # Mock BeautifulSoup
        mock_soup = Mock()
        mock_soup.get_text.return_value = "Extracted HTML text content."
        mock_bs.return_value = mock_soup

        html_content = b'<html><body><p>Content</p></body></html>'

        text = processor.extract_text(html_content, DocumentType.HTML)

        assert "Extracted HTML text content" in text
        mock_bs.assert_called_once()

    def test_extract_text_handles_encoding_errors(self, processor):
        """Test handling of encoding errors in text files."""
        # Invalid UTF-8 bytes
        content = b'\xff\xfe Invalid encoding'

        # Should handle gracefully or raise specific error
        try:
            text = processor.extract_text(content, DocumentType.TXT)
            # If it succeeds, it should have done error handling
            assert isinstance(text, str)
        except DocumentProcessingError:
            # Or it raises our custom error
            pass

    @patch('adapters.knowledge.document_processor.PyPDF2.PdfReader')
    def test_extract_text_pdf_error_handling(self, mock_pdf_reader, processor):
        """Test error handling for corrupted PDF."""
        mock_pdf_reader.side_effect = Exception("PDF parsing error")

        pdf_content = b'%PDF-corrupted'

        with pytest.raises(DocumentProcessingError, match="PDF parsing error"):
            processor.extract_text(pdf_content, DocumentType.PDF)


class TestDocumentProcessing:
    """Tests for complete document processing workflow."""

    @pytest.fixture
    def processor(self):
        """Create DocumentProcessor instance."""
        return DocumentProcessor(chunk_size=500, chunk_overlap=50)

    @patch('adapters.knowledge.document_processor.PyPDF2.PdfReader')
    def test_process_file_success(self, mock_pdf_reader, processor):
        """Test complete file processing workflow."""
        # Mock PDF with substantial content
        mock_reader = Mock()
        mock_page = Mock()
        mock_page.extract_text.return_value = "This is a test document. " * 100
        mock_reader.pages = [mock_page]
        mock_pdf_reader.return_value = mock_reader

        pdf_content = b'%PDF-1.4\ntest'
        filename = "test.pdf"

        result = processor.process_file(filename, pdf_content)

        # Verify result structure
        assert "chunks" in result
        assert "metadata" in result
        assert len(result["chunks"]) > 0
        assert result["metadata"]["filename"] == filename
        assert result["metadata"]["document_type"] == DocumentType.PDF
        assert result["metadata"]["total_chunks"] == len(result["chunks"])

    def test_process_file_empty_document(self, processor):
        """Test processing of empty document."""
        content = b''
        filename = "empty.txt"

        with pytest.raises(DocumentProcessingError, match="empty"):
            processor.process_file(filename, content)

    def test_process_file_extracts_metadata(self, processor):
        """Test that metadata is properly extracted."""
        content = b'Sample text content for metadata test.'
        filename = "metadata_test.txt"

        result = processor.process_file(filename, content)

        metadata = result["metadata"]
        assert metadata["filename"] == filename
        assert metadata["document_type"] == DocumentType.TXT
        assert "total_chars" in metadata
        assert "total_chunks" in metadata
        assert metadata["total_chars"] > 0

    def test_process_file_chunks_have_metadata(self, processor):
        """Test that each chunk has associated metadata."""
        content = b'Chunk metadata test. ' * 100
        filename = "chunks.txt"

        result = processor.process_file(filename, content)

        # Each chunk should have metadata
        for i, chunk in enumerate(result["chunks"]):
            assert "text" in chunk
            assert "chunk_index" in chunk
            assert chunk["chunk_index"] == i
            assert "source" in chunk
            assert chunk["source"] == filename


class TestDocumentProcessorConfiguration:
    """Tests for DocumentProcessor configuration."""

    def test_custom_chunk_size(self):
        """Test processor with custom chunk size."""
        processor = DocumentProcessor(chunk_size=200, chunk_overlap=50)

        text = "A" * 500
        chunks = processor.chunk_text(text)

        # Chunks should roughly match configured size
        for chunk in chunks[:-1]:  # Exclude last chunk which may be smaller
            assert len(chunk) <= 220  # Some flexibility

    def test_custom_overlap(self):
        """Test processor with custom overlap."""
        processor = DocumentProcessor(chunk_size=100, chunk_overlap=30)

        assert processor.chunk_overlap == 30
        assert processor.chunk_size == 100

    def test_invalid_configuration(self):
        """Test that invalid configuration raises error."""
        # Overlap larger than chunk size
        with pytest.raises(ValueError, match="overlap"):
            DocumentProcessor(chunk_size=100, chunk_overlap=150)

    def test_zero_overlap(self):
        """Test processor with no overlap."""
        processor = DocumentProcessor(chunk_size=100, chunk_overlap=0)

        text = "Word " * 50
        chunks = processor.chunk_text(text)

        # Adjacent chunks should not overlap
        if len(chunks) > 1:
            assert chunks[1][0] not in chunks[0]
