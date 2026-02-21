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
        """Test successful PDF upload."""
        files = {
            'file': ('test_document.pdf', sample_pdf, 'application/pdf')
        }

        response = await async_client.post(
            "/api/knowledge/upload",
            files=files,
            headers=auth_headers
        )

        assert response.status_code == 202  # Accepted for processing
        data = response.json()
        assert 'source_id' in data
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
            "/api/knowledge/upload",
            files=files,
            headers=auth_headers
        )

        assert response.status_code == 202
        data = response.json()
        assert data['filename'] == 'notes.txt'
        assert 'source_id' in data

    @pytest.mark.asyncio
    async def test_upload_markdown_success(self, async_client, auth_headers):
        """Test successful markdown file upload."""
        md_content = b'# Therapy Notes\n\nCBT techniques for anxiety management.'
        files = {
            'file': ('therapy_guide.md', BytesIO(md_content), 'text/markdown')
        }

        response = await async_client.post(
            "/api/knowledge/upload",
            files=files,
            headers=auth_headers
        )

        assert response.status_code == 202
        data = response.json()
        assert data['filename'] == 'therapy_guide.md'

    @pytest.mark.asyncio
    async def test_upload_invalid_type(self, async_client, auth_headers):
        """Test upload rejection of unsupported file types."""
        files = {
            'file': ('video.mp4', BytesIO(b'fake video data'), 'video/mp4')
        }

        response = await async_client.post(
            "/api/knowledge/upload",
            files=files,
            headers=auth_headers
        )

        assert response.status_code == 400
        data = response.json()
        assert 'unsupported' in data['detail'].lower()

    @pytest.mark.asyncio
    async def test_upload_too_large(self, async_client, auth_headers):
        """Test upload rejection of files exceeding size limit."""
        # Create 50MB file (assuming limit is 20MB)
        large_content = b'x' * (50 * 1024 * 1024)
        files = {
            'file': ('huge.pdf', BytesIO(large_content), 'application/pdf')
        }

        response = await async_client.post(
            "/api/knowledge/upload",
            files=files,
            headers=auth_headers
        )

        assert response.status_code == 413  # Payload Too Large
        data = response.json()
        assert 'size' in data['detail'].lower() or 'large' in data['detail'].lower()

    @pytest.mark.asyncio
    async def test_upload_unauthorized(self, async_client):
        """Test upload rejection without authentication."""
        files = {
            'file': ('test.txt', BytesIO(b'content'), 'text/plain')
        }

        response = await async_client.post(
            "/api/knowledge/upload",
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
            "/api/knowledge/upload",
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
        """Test listing user's sources with pagination."""
        response = await async_client.get(
            "/api/knowledge/sources",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert 'items' in data
        assert 'total' in data
        assert 'page' in data
        assert 'size' in data
        assert len(data['items']) <= data['size']

    @pytest.mark.asyncio
    async def test_list_sources_pagination(self, async_client, auth_headers, test_sources):
        """Test sources list pagination."""
        # Get first page
        response1 = await async_client.get(
            "/api/knowledge/sources?page=1&size=2",
            headers=auth_headers
        )
        data1 = response1.json()
        assert len(data1['items']) <= 2

        # Get second page
        response2 = await async_client.get(
            "/api/knowledge/sources?page=2&size=2",
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
            "/api/knowledge/sources?search=therapy",
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
            "/api/knowledge/sources?status=completed",
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
            "/api/knowledge/sources",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data['total'] == 0
        assert len(data['items']) == 0

    @pytest.mark.asyncio
    async def test_get_source_detail(self, async_client, auth_headers, test_source):
        """Test getting detailed source information."""
        source_id = test_source['id']

        response = await async_client.get(
            f"/api/knowledge/sources/{source_id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data['id'] == source_id
        assert 'filename' in data
        assert 'status' in data
        assert 'chunks_count' in data
        assert 'created_at' in data

    @pytest.mark.asyncio
    async def test_get_source_not_found(self, async_client, auth_headers):
        """Test getting non-existent source."""
        fake_id = str(uuid4())

        response = await async_client.get(
            f"/api/knowledge/sources/{fake_id}",
            headers=auth_headers
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_source_unauthorized_other_user(
        self, async_client, auth_headers, other_auth_headers, test_source
    ):
        """Test that users cannot access other users' sources."""
        source_id = test_source['id']

        response = await async_client.get(
            f"/api/knowledge/sources/{source_id}",
            headers=other_auth_headers
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_source(self, async_client, auth_headers, test_source):
        """Test successful source deletion."""
        source_id = test_source['id']

        response = await async_client.delete(
            f"/api/knowledge/sources/{source_id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data['message'] == 'Source deleted successfully'

        # Verify source is gone
        get_response = await async_client.get(
            f"/api/knowledge/sources/{source_id}",
            headers=auth_headers
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_source_not_owner(
        self, async_client, auth_headers, other_auth_headers, test_source
    ):
        """Test that users cannot delete sources they don't own."""
        source_id = test_source['id']

        response = await async_client.delete(
            f"/api/knowledge/sources/{source_id}",
            headers=other_auth_headers
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_source_not_found(self, async_client, auth_headers):
        """Test deletion of non-existent source."""
        fake_id = str(uuid4())

        response = await async_client.delete(
            f"/api/knowledge/sources/{fake_id}",
            headers=auth_headers
        )

        assert response.status_code == 404


class TestQueryEndpoint:
    """Tests for knowledge base query endpoint."""

    @pytest.mark.asyncio
    async def test_query_success(self, async_client, auth_headers, processed_source):
        """Test successful knowledge base query."""
        query_data = {
            'query': 'What are cognitive behavioral therapy techniques?',
            'n_results': 5
        }

        response = await async_client.post(
            "/api/knowledge/query",
            json=query_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert 'answer' in data
        assert 'sources' in data
        assert isinstance(data['sources'], list)
        # Answer should contain relevant content
        assert len(data['answer']) > 0

    @pytest.mark.asyncio
    async def test_query_with_source_filter(self, async_client, auth_headers, processed_sources):
        """Test querying with specific source filtering."""
        source_ids = [processed_sources[0]['id'], processed_sources[1]['id']]
        query_data = {
            'query': 'What is mindfulness meditation?',
            'source_ids': source_ids,
            'n_results': 3
        }

        response = await async_client.post(
            "/api/knowledge/query",
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
        """Test query with no relevant results."""
        query_data = {
            'query': 'quantum physics and string theory',  # Completely unrelated
            'n_results': 5
        }

        response = await async_client.post(
            "/api/knowledge/query",
            json=query_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        # Should return "no information found" message
        assert 'answer' in data
        assert any(phrase in data['answer'].lower() for phrase in [
            'no information', 'not found', 'don\'t have', 'cannot find'
        ])

    @pytest.mark.asyncio
    async def test_query_empty_knowledge_base(self, async_client, auth_headers):
        """Test query when user has no documents."""
        query_data = {
            'query': 'any question',
            'n_results': 5
        }

        response = await async_client.post(
            "/api/knowledge/query",
            json=query_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert 'answer' in data
        # Should indicate empty knowledge base
        assert any(phrase in data['answer'].lower() for phrase in [
            'no documents', 'empty', 'no knowledge'
        ])

    @pytest.mark.asyncio
    async def test_query_validation_empty_query(self, async_client, auth_headers):
        """Test query validation for empty query string."""
        query_data = {
            'query': '',
            'n_results': 5
        }

        response = await async_client.post(
            "/api/knowledge/query",
            json=query_data,
            headers=auth_headers
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_query_validation_invalid_n_results(self, async_client, auth_headers):
        """Test query validation for invalid n_results."""
        query_data = {
            'query': 'test query',
            'n_results': 0  # Invalid
        }

        response = await async_client.post(
            "/api/knowledge/query",
            json=query_data,
            headers=auth_headers
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_query_unauthorized(self, async_client):
        """Test query rejection without authentication."""
        query_data = {
            'query': 'test query',
            'n_results': 5
        }

        response = await async_client.post(
            "/api/knowledge/query",
            json=query_data
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_query_includes_metadata(self, async_client, auth_headers, processed_source):
        """Test that query results include source metadata."""
        query_data = {
            'query': 'therapeutic techniques',
            'n_results': 5
        }

        response = await async_client.post(
            "/api/knowledge/query",
            json=query_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Each source should have metadata
        for source in data['sources']:
            assert 'source_id' in source
            assert 'filename' in source
            assert 'relevance_score' in source
            assert 'text' in source

    @pytest.mark.asyncio
    async def test_query_with_max_sources(self, async_client, auth_headers, processed_source):
        """Test query respects n_results limit."""
        query_data = {
            'query': 'therapy',
            'n_results': 2  # Limit to 2 results
        }

        response = await async_client.post(
            "/api/knowledge/query",
            json=query_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data['sources']) <= 2


class TestStatsEndpoint:
    """Tests for knowledge base statistics endpoint."""

    @pytest.mark.asyncio
    async def test_get_stats(self, async_client, auth_headers, test_sources):
        """Test getting knowledge base statistics."""
        response = await async_client.get(
            "/api/knowledge/stats",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert 'total_sources' in data
        assert 'completed_sources' in data
        assert 'pending_sources' in data
        assert 'failed_sources' in data
        assert 'total_chunks' in data
        assert 'total_size_bytes' in data

    @pytest.mark.asyncio
    async def test_get_stats_empty_knowledge_base(self, async_client, auth_headers):
        """Test stats with no documents."""
        response = await async_client.get(
            "/api/knowledge/stats",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data['total_sources'] == 0
        assert data['total_chunks'] == 0

    @pytest.mark.asyncio
    async def test_get_stats_unauthorized(self, async_client):
        """Test stats rejection without authentication."""
        response = await async_client.get("/api/knowledge/stats")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_stats_includes_recent_queries(self, async_client, auth_headers, test_sources):
        """Test that stats include recent query information."""
        response = await async_client.get(
            "/api/knowledge/stats",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert 'recent_queries' in data
        assert isinstance(data['recent_queries'], list)

    @pytest.mark.asyncio
    async def test_stats_processing_breakdown(self, async_client, auth_headers, test_sources):
        """Test stats include processing status breakdown."""
        response = await async_client.get(
            "/api/knowledge/stats",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Verify status counts add up to total
        total = data['total_sources']
        status_sum = (
            data['completed_sources'] +
            data['pending_sources'] +
            data['failed_sources']
        )
        assert status_sum == total


class TestProcessingStatus:
    """Tests for checking document processing status."""

    @pytest.mark.asyncio
    async def test_check_processing_status_pending(
        self, async_client, auth_headers, pending_source
    ):
        """Test checking status of pending document."""
        source_id = pending_source['id']

        response = await async_client.get(
            f"/api/knowledge/sources/{source_id}/status",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'pending'
        assert 'progress' in data

    @pytest.mark.asyncio
    async def test_check_processing_status_completed(
        self, async_client, auth_headers, processed_source
    ):
        """Test checking status of completed document."""
        source_id = processed_source['id']

        response = await async_client.get(
            f"/api/knowledge/sources/{source_id}/status",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'completed'
        assert data['chunks_count'] > 0

    @pytest.mark.asyncio
    async def test_check_processing_status_failed(
        self, async_client, auth_headers, failed_source
    ):
        """Test checking status of failed document."""
        source_id = failed_source['id']

        response = await async_client.get(
            f"/api/knowledge/sources/{source_id}/status",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'failed'
        assert 'error_message' in data
        assert len(data['error_message']) > 0


class TestRateLimiting:
    """Tests for API rate limiting."""

    @pytest.mark.asyncio
    async def test_upload_rate_limit(self, async_client, auth_headers):
        """Test that uploads are rate limited."""
        # Make multiple rapid uploads
        responses = []
        for i in range(15):  # Assuming limit is 10/minute
            files = {'file': (f'test{i}.txt', BytesIO(b'content'), 'text/plain')}
            response = await async_client.post(
                "/api/knowledge/upload",
                files=files,
                headers=auth_headers
            )
            responses.append(response)

        # Some requests should be rate limited
        status_codes = [r.status_code for r in responses]
        assert 429 in status_codes  # Too Many Requests

    @pytest.mark.asyncio
    async def test_query_rate_limit(self, async_client, auth_headers):
        """Test that queries are rate limited."""
        query_data = {'query': 'test', 'n_results': 5}

        # Make many rapid queries
        responses = []
        for i in range(25):  # Assuming limit is 20/minute
            response = await async_client.post(
                "/api/knowledge/query",
                json=query_data,
                headers=auth_headers
            )
            responses.append(response)

        # Some should be rate limited
        status_codes = [r.status_code for r in responses]
        assert 429 in status_codes
