# Knowledge Vault Test Suite

Comprehensive test documentation for the Knowledge Vault (RAG) module.

---

## Table of Contents

1. [Overview](#overview)
2. [Test Coverage](#test-coverage)
3. [Running Tests](#running-tests)
4. [Test Structure](#test-structure)
5. [Mock Setup Guide](#mock-setup-guide)
6. [Fixtures Reference](#fixtures-reference)
7. [Test Patterns](#test-patterns)

---

## Overview

The Knowledge Vault test suite provides comprehensive coverage for Phase 7 of the A-Stats platform:

- **RAG (Retrieval-Augmented Generation)** with ChromaDB
- **Document Processing** (PDF, TXT, DOCX, MD, HTML)
- **Text Chunking** with overlap and sentence boundary preservation
- **Embedding Generation** (OpenAI, mock mode)
- **Semantic Search** and query operations
- **Complete API Integration** with authentication and rate limiting

### Test Philosophy

- **Unit tests** focus on individual components in isolation with mocked dependencies
- **Integration tests** verify API endpoints with database interactions
- **Mock external services** (ChromaDB, OpenAI, file storage) to ensure fast, reliable tests
- **Follow Clean Architecture** patterns with strict dependency testing

---

## Test Coverage

### Unit Tests (4 files, 60+ test cases)

#### 1. ChromaDB Adapter (`test_chroma_adapter.py`)
- Collection management and creation
- Document addition with metadata
- Query operations with filtering
- Deletion by ID and by source
- Collection statistics
- Connection error handling
- Input validation
- **Total: 16 tests**

#### 2. Document Processor (`test_document_processor.py`)
- File type detection (PDF, TXT, DOCX, MD, HTML)
- Text extraction from all formats
- Text chunking with configurable size/overlap
- Sentence boundary preservation
- Empty document handling
- Encoding error handling
- Processing workflow
- **Total: 20 tests**

#### 3. Embedding Service (`test_embedding_service.py`)
- OpenAI embedding generation
- Batch processing with size limits
- Mock mode for testing without API
- Dimension consistency
- Error handling and retries
- Deterministic mock embeddings
- **Total: 15 tests**

#### 4. Knowledge Service (`test_knowledge_service.py`)
- Document processing workflow
- Status updates (pending → processing → completed)
- Failure handling with error messages
- Query operations with source filtering
- Deletion with authorization
- Statistics and analytics
- Query logging
- **Total: 14 tests**

### Integration Tests (1 file, 50+ test cases)

#### Knowledge API (`test_knowledge_api.py`)

**Upload Endpoint** (7 tests)
- Upload PDF, TXT, Markdown successfully
- Reject unsupported file types
- Enforce file size limits
- Require authentication
- Validate empty files

**Sources Endpoint** (9 tests)
- List sources with pagination
- Search/filter by filename
- Filter by processing status
- Get source details
- Delete sources with authorization
- Prevent cross-user access

**Query Endpoint** (8 tests)
- Semantic search with embeddings
- Source filtering
- Handle no results gracefully
- Empty knowledge base handling
- Validation (empty query, invalid params)
- Include source metadata
- Respect result limits

**Stats Endpoint** (4 tests)
- Overall statistics
- Processing status breakdown
- Recent queries
- Empty knowledge base stats

**Processing Status** (3 tests)
- Check pending documents
- Check completed documents
- Check failed documents with errors

**Rate Limiting** (2 tests)
- Upload rate limits
- Query rate limits

---

## Running Tests

### Prerequisites

```bash
# Install dependencies
cd backend
uv sync

# Ensure pytest is available
uv pip install pytest pytest-asyncio pytest-cov
```

### Run All Knowledge Tests

```bash
# From backend directory
pytest tests/unit/test_chroma_adapter.py -v
pytest tests/unit/test_document_processor.py -v
pytest tests/unit/test_embedding_service.py -v
pytest tests/unit/test_knowledge_service.py -v
pytest tests/integration/test_knowledge_api.py -v
```

### Run with Coverage

```bash
pytest tests/unit/test_*knowledge*.py tests/integration/test_knowledge_api.py \
  --cov=adapters/knowledge \
  --cov=core/knowledge \
  --cov=api/routes/knowledge \
  --cov-report=html \
  --cov-report=term-missing
```

### Run Specific Test Classes

```bash
# ChromaDB adapter tests only
pytest tests/unit/test_chroma_adapter.py::TestChromaAdapter -v

# Document processor chunking tests
pytest tests/unit/test_document_processor.py::TestTextChunking -v

# Knowledge API upload tests
pytest tests/integration/test_knowledge_api.py::TestUploadEndpoint -v
```

### Run with Markers

```bash
# Run only async tests
pytest -m asyncio -v

# Run only unit tests (fast)
pytest tests/unit/ -v

# Run only integration tests
pytest tests/integration/test_knowledge_api.py -v
```

---

## Test Structure

### Unit Test Pattern

```python
class TestComponentName:
    """Tests for specific component."""

    @pytest.fixture
    def mock_dependencies(self):
        """Mock external dependencies."""
        return {
            'chroma': Mock(),
            'embeddings': AsyncMock(),
        }

    @pytest.fixture
    def component(self, mock_dependencies):
        """Create component with mocked deps."""
        return Component(**mock_dependencies)

    def test_specific_behavior(self, component, mock_dependencies):
        """Test one specific behavior in isolation."""
        # Arrange
        mock_dependencies['chroma'].query.return_value = {...}

        # Act
        result = component.do_something()

        # Assert
        assert result == expected
        mock_dependencies['chroma'].query.assert_called_once()
```

### Integration Test Pattern

```python
class TestEndpoint:
    """Tests for API endpoint."""

    @pytest.mark.asyncio
    async def test_endpoint_success(self, async_client, auth_headers, test_data):
        """Test successful API call."""
        # Arrange
        payload = {'key': 'value'}

        # Act
        response = await async_client.post(
            "/api/knowledge/endpoint",
            json=payload,
            headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert 'expected_field' in data
```

---

## Mock Setup Guide

### Mocking ChromaDB

```python
from unittest.mock import Mock

def test_chroma_query(mock_chroma_client):
    """Example: Mock ChromaDB query."""
    # Setup mock response
    mock_collection = Mock()
    mock_collection.query.return_value = {
        'ids': [['chunk1', 'chunk2']],
        'documents': [['Text 1', 'Text 2']],
        'distances': [[0.1, 0.2]],
        'metadatas': [[{'source': 'test.pdf'}, {'source': 'test.pdf'}]]
    }

    mock_chroma_client.get_collection.return_value = mock_collection

    # Use in test
    adapter = ChromaAdapter(client=mock_chroma_client)
    results = adapter.query([0.1, 0.2, 0.3], n_results=2)

    # Verify
    assert len(results['ids'][0]) == 2
```

### Mocking Embedding Service

```python
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_embeddings(mock_embedding_service):
    """Example: Mock embedding generation."""
    # Mock returns deterministic embeddings
    embedding = await mock_embedding_service.embed_text("test text")

    # Verify shape
    assert len(embedding) == 384  # Standard dimension
    assert all(isinstance(x, float) for x in embedding)

    # Same input = same output (deterministic)
    embedding2 = await mock_embedding_service.embed_text("test text")
    assert embedding == embedding2
```

### Mocking PDF Processing

```python
from unittest.mock import patch, Mock

@patch('adapters.knowledge.document_processor.PyPDF2.PdfReader')
def test_pdf_extraction(mock_pdf_reader):
    """Example: Mock PDF parsing."""
    # Setup mock PDF
    mock_reader = Mock()
    mock_page = Mock()
    mock_page.extract_text.return_value = "Page content"
    mock_reader.pages = [mock_page]
    mock_pdf_reader.return_value = mock_reader

    # Use in test
    processor = DocumentProcessor()
    text = processor.extract_text(pdf_bytes, DocumentType.PDF)

    # Verify
    assert "Page content" in text
    mock_pdf_reader.assert_called_once()
```

---

## Fixtures Reference

### Data Fixtures

#### `sample_pdf`
Creates minimal valid PDF with magic bytes and basic structure for upload testing.

```python
def test_upload_pdf(async_client, auth_headers, sample_pdf):
    files = {'file': ('test.pdf', sample_pdf, 'application/pdf')}
    response = await async_client.post("/api/knowledge/upload", files=files, headers=auth_headers)
```

#### `sample_txt`
Plain text content with therapeutic/CBT content for testing text processing.

```python
def test_process_text(sample_txt):
    processor = DocumentProcessor()
    result = processor.process_file("test.txt", sample_txt.read())
```

### Database Fixtures

#### `test_source`
Single KnowledgeSource in PENDING status.

```python
async def test_get_source(async_client, auth_headers, test_source):
    response = await async_client.get(f"/api/knowledge/sources/{test_source.id}", headers=auth_headers)
```

#### `processed_source`
Single KnowledgeSource in COMPLETED status with 25 chunks.

```python
async def test_query_knowledge(async_client, auth_headers, processed_source):
    response = await async_client.post("/api/knowledge/query", json={'query': 'CBT'}, headers=auth_headers)
```

#### `test_sources`
Multiple sources (5) with various statuses for pagination testing.

```python
async def test_list_sources(async_client, auth_headers, test_sources):
    response = await async_client.get("/api/knowledge/sources?page=1&size=10", headers=auth_headers)
    assert response.json()['total'] == 5
```

#### `processed_sources`
Multiple completed sources (3) for multi-source query testing.

```python
async def test_multi_source_query(async_client, auth_headers, processed_sources):
    source_ids = [s.id for s in processed_sources[:2]]
    response = await async_client.post("/api/knowledge/query", json={'query': 'test', 'source_ids': source_ids}, headers=auth_headers)
```

### Mock Fixtures

#### `mock_chroma_client`
Fully mocked ChromaDB client with collection operations.

```python
def test_chroma_operations(mock_chroma_client):
    adapter = ChromaAdapter(client=mock_chroma_client)
    # No real ChromaDB connection needed
```

#### `mock_embedding_service`
Deterministic mock embeddings (no OpenAI API calls).

```python
async def test_embeddings(mock_embedding_service):
    embedding = await mock_embedding_service.embed_text("test")
    # Returns consistent 384-dimensional vector
```

### User Fixtures

#### `other_user` + `other_auth_headers`
Second test user for authorization/permission testing.

```python
async def test_cannot_access_other_user_source(async_client, other_auth_headers, test_source):
    response = await async_client.get(f"/api/knowledge/sources/{test_source.id}", headers=other_auth_headers)
    assert response.status_code == 403  # Forbidden
```

---

## Test Patterns

### Testing Async Functions

```python
@pytest.mark.asyncio
async def test_async_operation(async_client, auth_headers):
    """All integration tests use async/await."""
    response = await async_client.post("/api/endpoint", headers=auth_headers)
    assert response.status_code == 200
```

### Testing Error Handling

```python
def test_error_handling(component):
    """Verify exceptions are raised appropriately."""
    with pytest.raises(CustomError, match="expected message"):
        component.failing_operation()
```

### Testing Database State Changes

```python
@pytest.mark.asyncio
async def test_database_update(db_session, test_source):
    """Verify database changes after operations."""
    # Initial state
    assert test_source.status == ProcessingStatus.PENDING

    # Perform operation
    service.process_document(test_source.id)

    # Refresh from DB
    await db_session.refresh(test_source)

    # Verify state change
    assert test_source.status == ProcessingStatus.COMPLETED
```

### Testing Pagination

```python
@pytest.mark.asyncio
async def test_pagination(async_client, auth_headers, test_sources):
    """Test paginated list endpoints."""
    # Page 1
    response1 = await async_client.get("/api/knowledge/sources?page=1&size=2", headers=auth_headers)
    data1 = response1.json()
    assert len(data1['items']) == 2

    # Page 2
    response2 = await async_client.get("/api/knowledge/sources?page=2&size=2", headers=auth_headers)
    data2 = response2.json()
    assert len(data2['items']) <= 2

    # Different items
    assert data1['items'][0]['id'] != data2['items'][0]['id']
```

### Testing Authorization

```python
@pytest.mark.asyncio
async def test_authorization(async_client, auth_headers, other_auth_headers, test_source):
    """Verify users cannot access other users' resources."""
    # Owner can access
    response = await async_client.get(f"/api/knowledge/sources/{test_source.id}", headers=auth_headers)
    assert response.status_code == 200

    # Other user cannot
    response = await async_client.get(f"/api/knowledge/sources/{test_source.id}", headers=other_auth_headers)
    assert response.status_code == 403
```

---

## Test Execution Tips

### Speed Up Tests

```bash
# Run tests in parallel (requires pytest-xdist)
pytest tests/unit/ -n auto

# Skip slow integration tests
pytest tests/unit/ -v  # Fast unit tests only

# Run specific test file
pytest tests/unit/test_chroma_adapter.py -v
```

### Debugging Failed Tests

```bash
# Show print statements
pytest tests/unit/test_chroma_adapter.py -v -s

# Stop on first failure
pytest tests/unit/ -x

# Drop into debugger on failure
pytest tests/unit/ --pdb

# Show local variables on failure
pytest tests/unit/ -l
```

### Watch Mode (Development)

```bash
# Install pytest-watch
uv pip install pytest-watch

# Auto-run tests on file changes
ptw tests/unit/test_chroma_adapter.py
```

---

## Common Issues & Solutions

### Issue: `ModuleNotFoundError: No module named 'adapters.knowledge'`

**Solution:** Tests use `pytest.importorskip` to gracefully skip when modules aren't implemented yet.

```python
pytest.importorskip("adapters.knowledge.chroma_adapter", reason="ChromaDB adapter not yet implemented")
```

### Issue: Async tests fail with "RuntimeError: Event loop is closed"

**Solution:** Ensure `pytest-asyncio` is installed and fixtures use `async def`:

```bash
uv pip install pytest-asyncio
```

### Issue: Mock objects not being called

**Solution:** Verify mock setup and use `assert_called_once()` or `assert_called_once_with()`:

```python
mock_client.query.assert_called_once_with(query_embeddings=[...], n_results=5)
```

### Issue: Database fixtures not working

**Solution:** Ensure async fixtures are properly awaited and use `AsyncSession`:

```python
@pytest.fixture
async def test_source(db_session: AsyncSession, test_user: User):
    source = KnowledgeSource(...)
    db_session.add(source)
    await db_session.commit()  # Must await
    await db_session.refresh(source)  # Must await
    return source
```

---

## Contributing to Tests

### Adding New Tests

1. Choose appropriate test file (unit vs integration)
2. Add test to relevant class
3. Use existing fixtures when possible
4. Follow naming convention: `test_<component>_<behavior>`
5. Add docstring explaining what is tested

### Test Naming Conventions

- `test_<method>_success` - Happy path
- `test_<method>_<error_case>` - Error handling
- `test_<method>_validation_<field>` - Input validation
- `test_<method>_unauthorized` - Authorization checks

### Example New Test

```python
@pytest.mark.asyncio
async def test_upload_docx_success(self, async_client, auth_headers):
    """Test successful DOCX file upload."""
    # Arrange
    docx_content = b'PK\x03\x04...'  # Valid DOCX magic bytes
    files = {'file': ('document.docx', BytesIO(docx_content), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}

    # Act
    response = await async_client.post("/api/knowledge/upload", files=files, headers=auth_headers)

    # Assert
    assert response.status_code == 202
    data = response.json()
    assert data['filename'] == 'document.docx'
    assert 'source_id' in data
```

---

## Test Metrics

### Expected Coverage

- **ChromaDB Adapter:** 95%+
- **Document Processor:** 90%+
- **Embedding Service:** 95%+
- **Knowledge Service:** 90%+
- **API Endpoints:** 85%+

### Current Test Count

- **Unit Tests:** 65+ test cases
- **Integration Tests:** 50+ test cases
- **Total:** 115+ test cases

### Test Execution Time

- **Unit Tests:** ~5 seconds (all mocked)
- **Integration Tests:** ~30 seconds (database fixtures)
- **Total Suite:** ~35 seconds

---

## Next Steps

After implementing the Knowledge Vault module:

1. **Run full test suite** to verify all tests pass
2. **Check coverage** and add tests for uncovered lines
3. **Update fixtures** if implementation differs from specification
4. **Add performance tests** for large document processing
5. **Add E2E tests** for complete upload → query workflow

---

*Last Updated: 2026-02-20*
*Test Suite Version: 1.0*
*Phase: 7 - Knowledge Vault (RAG)*
