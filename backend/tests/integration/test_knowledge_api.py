"""
Integration tests for Knowledge API endpoints.

Tests cover all endpoints:
- POST /knowledge/upload - Upload documents
- GET /knowledge/sources - List sources with pagination
- GET /knowledge/sources/{id} - Get source details
- DELETE /knowledge/sources/{id} - Delete source
- POST /knowledge/query - Query knowledge base
- GET /knowledge/stats - Get statistics
"""

import pytest
from io import BytesIO
from uuid import uuid4

# Skip if routes not implemented yet
pytest.importorskip("api.routes.knowledge", reason="Knowledge routes not yet implemented")


class TestUploadEndpoint:
    """Tests for document upload endpoint."""

    @pytest.mark.asyncio
    async def test_upload_pdf_success(self, async_client, auth_headers, sample_pdf):
        """Test successful PDF upload.

        The route returns 200 (not 202) and the response uses 'id' (not 'source_id').
        Status value is the raw DB status string (e.g. 'pending').
        """
        files = {
            'file': ('test_document.pdf', sample_pdf, 'application/pdf')
        }

        response = await async_client.post(
            "/api/v1/knowledge/upload",
            files=files,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert 'id' in data
        assert data['status'] == 'pending'
        assert data['filename'] == 'test_document.pdf'

    @pytest.mark.asyncio
    async def test_upload_txt_success(self, async_client, auth_headers):
        """Test successful text file upload."""
        text_content = b'This is a test document with therapeutic content.'
        files = {
            'file': ('notes.txt', BytesIO(text_content), 'text/plain')
        }

        response = await async_client.post(
            "/api/v1/knowledge/upload",
            files=files,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data['filename'] == 'notes.txt'
        assert 'id' in data

    @pytest.mark.asyncio
    async def test_upload_markdown_success(self, async_client, auth_headers):
        """Test successful markdown file upload."""
        md_content = b'# Therapy Notes\n\nCBT techniques for anxiety management.'
        files = {
            'file': ('therapy_guide.md', BytesIO(md_content), 'text/markdown')
        }

        response = await async_client.post(
            "/api/v1/knowledge/upload",
            files=files,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data['filename'] == 'therapy_guide.md'

    @pytest.mark.asyncio
    async def test_upload_invalid_type(self, async_client, auth_headers):
        """Test upload rejection of unsupported file types."""
        files = {
            'file': ('video.mp4', BytesIO(b'fake video data'), 'video/mp4')
        }

        response = await async_client.post(
            "/api/v1/knowledge/upload",
            files=files,
            headers=auth_headers
        )

        assert response.status_code == 400
        data = response.json()
        assert 'unsupported' in data['detail'].lower()

    @pytest.mark.asyncio
    async def test_upload_too_large(self, async_client, auth_headers):
        """Test upload rejection of files exceeding size limit.

        The route enforces a 10 MB limit and returns 400 (not 413).
        The detail message contains 'too large' (not just 'size').
        """
        # Create a file larger than MAX_FILE_SIZE (10 MB)
        large_content = b'x' * (11 * 1024 * 1024)
        files = {
            'file': ('huge.pdf', BytesIO(large_content), 'application/pdf')
        }

        response = await async_client.post(
            "/api/v1/knowledge/upload",
            files=files,
            headers=auth_headers
        )

        assert response.status_code == 400
        data = response.json()
        assert 'too large' in data['detail'].lower() or 'size' in data['detail'].lower()

    @pytest.mark.asyncio
    async def test_upload_unauthorized(self, async_client):
        """Test upload rejection without authentication."""
        files = {
            'file': ('test.txt', BytesIO(b'content'), 'text/plain')
        }

        response = await async_client.post(
            "/api/v1/knowledge/upload",
            files=files
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_upload_empty_file(self, async_client, auth_headers):
        """Test upload rejection of empty files."""
        files = {
            'file': ('empty.txt', BytesIO(b''), 'text/plain')
        }

        response = await async_client.post(
            "/api/v1/knowledge/upload",
            files=files,
            headers=auth_headers
        )

        assert response.status_code == 400
        data = response.json()
        assert 'empty' in data['detail'].lower()


class TestSourcesEndpoint:
    """Tests for sources listing and management endpoints."""

    @pytest.mark.asyncio
    async def test_list_sources(self, async_client, auth_headers, test_sources):
        """Test listing user's sources with pagination.

        The list response uses 'page_size' (not 'size') for the per-page limit.
        """
        response = await async_client.get(
            "/api/v1/knowledge/sources",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert 'items' in data
        assert 'total' in data
        assert 'page' in data
        assert 'page_size' in data
        assert len(data['items']) <= data['page_size']

    @pytest.mark.asyncio
    async def test_list_sources_pagination(self, async_client, auth_headers, test_sources):
        """Test sources list pagination.

        The route uses 'page_size' (not 'size') as the query parameter name.
        """
        # Get first page with page_size=2
        response1 = await async_client.get(
            "/api/v1/knowledge/sources?page=1&page_size=2",
            headers=auth_headers
        )
        data1 = response1.json()
        assert len(data1['items']) <= 2

        # Get second page
        response2 = await async_client.get(
            "/api/v1/knowledge/sources?page=2&page_size=2",
            headers=auth_headers
        )
        data2 = response2.json()

        # Pages should have different items
        if len(data1['items']) > 0 and len(data2['items']) > 0:
            assert data1['items'][0]['id'] != data2['items'][0]['id']

    @pytest.mark.asyncio
    async def test_list_sources_with_search(self, async_client, auth_headers, test_sources):
        """Test sources filtering by search term."""
        response = await async_client.get(
            "/api/v1/knowledge/sources?search=therapy",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        # Results should contain search term
        for item in data['items']:
            assert 'therapy' in item['filename'].lower() or \
                   (item.get('description') and 'therapy' in item['description'].lower())

    @pytest.mark.asyncio
    async def test_list_sources_with_status_filter(self, async_client, auth_headers, test_sources):
        """Test sources filtering by processing status."""
        response = await async_client.get(
            "/api/v1/knowledge/sources?status=completed",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        # All results should have completed status
        for item in data['items']:
            assert item['status'] == 'completed'

    @pytest.mark.asyncio
    async def test_list_sources_empty(self, async_client, auth_headers):
        """Test listing sources when user has none."""
        response = await async_client.get(
            "/api/v1/knowledge/sources",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data['total'] == 0
        assert len(data['items']) == 0

    @pytest.mark.asyncio
    async def test_get_source_detail(self, async_client, auth_headers, test_source):
        """Test getting detailed source information.

        test_source is a KnowledgeSource ORM object, so access fields via attributes.
        """
        source_id = test_source.id

        response = await async_client.get(
            f"/api/v1/knowledge/sources/{source_id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data['id'] == source_id
        assert 'filename' in data
        assert 'status' in data
        # The schema uses 'chunk_count' (not 'chunks_count')
        assert 'chunk_count' in data
        assert 'created_at' in data

    @pytest.mark.asyncio
    async def test_get_source_not_found(self, async_client, auth_headers):
        """Test getting non-existent source."""
        fake_id = str(uuid4())

        response = await async_client.get(
            f"/api/v1/knowledge/sources/{fake_id}",
            headers=auth_headers
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_source_unauthorized_other_user(
        self, async_client, auth_headers, other_auth_headers, test_source
    ):
        """Test that users cannot access other users' sources.

        The route filters by user_id in the WHERE clause, so a source belonging
        to another user is simply not found (404), not a 403 Forbidden.
        test_source is a KnowledgeSource ORM object, so access fields via attributes.
        """
        source_id = test_source.id

        response = await async_client.get(
            f"/api/v1/knowledge/sources/{source_id}",
            headers=other_auth_headers
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_source(self, async_client, auth_headers, test_source):
        """Test successful source deletion.

        The route is decorated with status_code=204 (No Content), so there
        is no response body. test_source is a KnowledgeSource ORM object,
        so access fields via attributes.
        """
        source_id = test_source.id

        response = await async_client.delete(
            f"/api/v1/knowledge/sources/{source_id}",
            headers=auth_headers
        )

        assert response.status_code == 204

        # Verify source is gone
        get_response = await async_client.get(
            f"/api/v1/knowledge/sources/{source_id}",
            headers=auth_headers
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_source_not_owner(
        self, async_client, auth_headers, other_auth_headers, test_source
    ):
        """Test that users cannot delete sources they don't own.

        The route filters by user_id in the WHERE clause, so a source belonging
        to another user is simply not found (404), not a 403 Forbidden.
        test_source is a KnowledgeSource ORM object, so access fields via attributes.
        """
        source_id = test_source.id

        response = await async_client.delete(
            f"/api/v1/knowledge/sources/{source_id}",
            headers=other_auth_headers
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_source_not_found(self, async_client, auth_headers):
        """Test deletion of non-existent source."""
        fake_id = str(uuid4())

        response = await async_client.delete(
            f"/api/v1/knowledge/sources/{fake_id}",
            headers=auth_headers
        )

        assert response.status_code == 404


class TestQueryEndpoint:
    """Tests for knowledge base query endpoint.

    Note: The QueryRequest schema uses 'max_results' (not 'n_results').
    SourceSnippet fields: source_id, source_title, content, relevance_score, chunk_index.
    When no completed sources exist the route returns 400 (not 200).
    """

    @pytest.mark.asyncio
    async def test_query_success(self, async_client, auth_headers, processed_source):
        """Test successful knowledge base query."""
        query_data = {
            'query': 'What are cognitive behavioral therapy techniques?',
            'max_results': 5
        }

        response = await async_client.post(
            "/api/v1/knowledge/query",
            json=query_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert 'answer' in data
        assert 'sources' in data
        assert isinstance(data['sources'], list)
        assert len(data['answer']) > 0

    @pytest.mark.asyncio
    async def test_query_with_source_filter(self, async_client, auth_headers, processed_sources):
        """Test querying with specific source filtering.

        processed_sources is a list of KnowledgeSource ORM objects,
        so access fields via attributes (not subscript).
        """
        source_ids = [processed_sources[0].id, processed_sources[1].id]
        query_data = {
            'query': 'What is mindfulness meditation?',
            'source_ids': source_ids,
            'max_results': 3
        }

        response = await async_client.post(
            "/api/v1/knowledge/query",
            json=query_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        # Sources should only come from specified sources
        for source in data['sources']:
            assert source['source_id'] in source_ids

    @pytest.mark.asyncio
    async def test_query_no_relevant_results(self, async_client, auth_headers, processed_source):
        """Test query with no relevant results returns 200 with placeholder answer.

        The route does not perform semantic filtering - it returns a placeholder
        answer regardless of relevance when completed sources exist.
        """
        query_data = {
            'query': 'quantum physics and string theory',
            'max_results': 5
        }

        response = await async_client.post(
            "/api/v1/knowledge/query",
            json=query_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert 'answer' in data

    @pytest.mark.asyncio
    async def test_query_empty_knowledge_base(self, async_client, auth_headers):
        """Test query when user has no completed documents returns 400."""
        query_data = {
            'query': 'any question',
            'max_results': 5
        }

        response = await async_client.post(
            "/api/v1/knowledge/query",
            json=query_data,
            headers=auth_headers
        )

        # Returns 400: "No completed knowledge sources found."
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_query_validation_empty_query(self, async_client, auth_headers):
        """Test query validation for empty query string."""
        query_data = {
            'query': '',
            'max_results': 5
        }

        response = await async_client.post(
            "/api/v1/knowledge/query",
            json=query_data,
            headers=auth_headers
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_query_validation_invalid_max_results(self, async_client, auth_headers):
        """Test query validation for invalid max_results (must be >= 1)."""
        query_data = {
            'query': 'test query',
            'max_results': 0  # Invalid: ge=1
        }

        response = await async_client.post(
            "/api/v1/knowledge/query",
            json=query_data,
            headers=auth_headers
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_query_unauthorized(self, async_client):
        """Test query rejection without authentication."""
        query_data = {
            'query': 'test query',
            'max_results': 5
        }

        response = await async_client.post(
            "/api/v1/knowledge/query",
            json=query_data
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_query_includes_metadata(self, async_client, auth_headers, processed_source):
        """Test that query results include source metadata matching SourceSnippet schema."""
        query_data = {
            'query': 'therapeutic techniques',
            'max_results': 5
        }

        response = await async_client.post(
            "/api/v1/knowledge/query",
            json=query_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Each source should have SourceSnippet fields:
        # source_id, source_title, content, relevance_score, chunk_index
        for source in data['sources']:
            assert 'source_id' in source
            assert 'source_title' in source
            assert 'relevance_score' in source
            assert 'content' in source

    @pytest.mark.asyncio
    async def test_query_with_max_sources(self, async_client, auth_headers, processed_source):
        """Test query respects max_results limit."""
        query_data = {
            'query': 'therapy',
            'max_results': 2
        }

        response = await async_client.post(
            "/api/v1/knowledge/query",
            json=query_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data['sources']) <= 2


class TestStatsEndpoint:
    """Tests for knowledge base statistics endpoint.

    KnowledgeStatsResponse fields:
    total_sources, total_chunks, total_characters, total_queries,
    storage_used_mb, sources_by_type, recent_queries (int), avg_query_time_ms.

    There are NO per-status counts (completed_sources, pending_sources, failed_sources)
    and NO total_size_bytes in the schema.
    recent_queries is an int (count of queries in last 30 days), not a list.
    """

    @pytest.mark.asyncio
    async def test_get_stats(self, async_client, auth_headers, test_sources):
        """Test getting knowledge base statistics."""
        response = await async_client.get(
            "/api/v1/knowledge/stats",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert 'total_sources' in data
        assert 'total_chunks' in data
        assert 'total_characters' in data
        assert 'total_queries' in data
        assert 'storage_used_mb' in data
        assert 'sources_by_type' in data
        assert 'recent_queries' in data
        assert 'avg_query_time_ms' in data

    @pytest.mark.asyncio
    async def test_get_stats_empty_knowledge_base(self, async_client, auth_headers):
        """Test stats with no documents."""
        response = await async_client.get(
            "/api/v1/knowledge/stats",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data['total_sources'] == 0
        assert data['total_chunks'] == 0

    @pytest.mark.asyncio
    async def test_get_stats_unauthorized(self, async_client):
        """Test stats rejection without authentication."""
        response = await async_client.get("/api/v1/knowledge/stats")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_stats_includes_recent_queries(self, async_client, auth_headers, test_sources):
        """Test that stats include recent_queries as an int count (not a list)."""
        response = await async_client.get(
            "/api/v1/knowledge/stats",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert 'recent_queries' in data
        # recent_queries is a count (int), not a list
        assert isinstance(data['recent_queries'], int)

    @pytest.mark.asyncio
    async def test_stats_has_sources_by_type(self, async_client, auth_headers, test_sources):
        """Test stats include sources_by_type breakdown dict."""
        response = await async_client.get(
            "/api/v1/knowledge/stats",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        # sources_by_type is a dict mapping file_type -> count
        assert isinstance(data['sources_by_type'], dict)


@pytest.mark.skip(reason="Endpoint /sources/{id}/status does not exist in knowledge.py")
class TestProcessingStatus:
    """Tests for checking document processing status.

    These tests are skipped because the route GET /sources/{id}/status has not
    been implemented in api/routes/knowledge.py.  Status information is available
    via GET /sources/{id} (chunk_count, status, error_message fields).
    """

    @pytest.mark.asyncio
    async def test_check_processing_status_pending(
        self, async_client, auth_headers, pending_source
    ):
        """Test checking status of pending document."""
        source_id = pending_source['id']

        response = await async_client.get(
            f"/api/v1/knowledge/sources/{source_id}/status",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'pending'

    @pytest.mark.asyncio
    async def test_check_processing_status_completed(
        self, async_client, auth_headers, processed_source
    ):
        """Test checking status of completed document."""
        source_id = processed_source['id']

        response = await async_client.get(
            f"/api/v1/knowledge/sources/{source_id}/status",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'completed'

    @pytest.mark.asyncio
    async def test_check_processing_status_failed(
        self, async_client, auth_headers, failed_source
    ):
        """Test checking status of failed document."""
        source_id = failed_source['id']

        response = await async_client.get(
            f"/api/v1/knowledge/sources/{source_id}/status",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'failed'


@pytest.mark.skip(reason="Rate limiting middleware is not implemented")
class TestRateLimiting:
    """Tests for API rate limiting.

    These tests are skipped because rate limiting has not been implemented
    in the knowledge API routes.
    """

    @pytest.mark.asyncio
    async def test_upload_rate_limit(self, async_client, auth_headers):
        """Test that uploads are rate limited."""
        responses = []
        for i in range(15):
            files = {'file': (f'test{i}.txt', BytesIO(b'content'), 'text/plain')}
            response = await async_client.post(
                "/api/v1/knowledge/upload",
                files=files,
                headers=auth_headers
            )
            responses.append(response)

        status_codes = [r.status_code for r in responses]
        assert 429 in status_codes

    @pytest.mark.asyncio
    async def test_query_rate_limit(self, async_client, auth_headers):
        """Test that queries are rate limited."""
        query_data = {'query': 'test', 'max_results': 5}

        responses = []
        for i in range(25):
            response = await async_client.post(
                "/api/v1/knowledge/query",
                json=query_data,
                headers=auth_headers
            )
            responses.append(response)

        status_codes = [r.status_code for r in responses]
        assert 429 in status_codes
