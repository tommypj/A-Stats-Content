"""
Integration tests for analytics API routes.
"""

from datetime import UTC, date, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import User
from infrastructure.database.models.analytics import (
    DailyAnalytics,
    GSCConnection,
    KeywordRanking,
    PagePerformance,
)


class TestGSCAuthUrlEndpoint:
    """Tests for GET /analytics/gsc/auth-url endpoint."""

    @pytest.mark.asyncio
    async def test_get_auth_url_success(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test successful retrieval of OAuth authorization URL.

        The analytics route reads settings from 'api.routes.analytics.settings'.
        """
        with patch("api.routes.analytics.settings") as mock_settings:
            mock_settings.google_client_id = "test_client_id"
            mock_settings.google_client_secret = "test_secret"
            mock_settings.google_redirect_uri = "http://localhost:8000/callback"

            response = await async_client.get(
                "/api/v1/analytics/gsc/auth-url",
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "auth_url" in data
        assert "state" in data
        assert "accounts.google.com" in data["auth_url"]
        assert "client_id=test_client_id" in data["auth_url"]

    @pytest.mark.asyncio
    async def test_get_auth_url_unauthorized(self, async_client: AsyncClient):
        """Test OAuth URL request without authentication."""
        response = await async_client.get("/api/v1/analytics/gsc/auth-url")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_auth_url_not_configured(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test OAuth URL when Google credentials not configured.

        The analytics route reads settings from 'api.routes.analytics.settings'.
        """
        with patch("api.routes.analytics.settings") as mock_settings:
            mock_settings.google_client_id = None
            mock_settings.google_client_secret = None

            response = await async_client.get(
                "/api/v1/analytics/gsc/auth-url",
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "not configured" in response.json()["detail"]


class TestGSCStatusEndpoint:
    """Tests for GET /analytics/gsc/status endpoint."""

    @pytest.mark.asyncio
    async def test_get_status_not_connected(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test status when GSC is not connected."""
        response = await async_client.get(
            "/api/v1/analytics/gsc/status",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["connected"] is False

    @pytest.mark.asyncio
    async def test_get_status_connected(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test status when GSC is connected."""
        # Create a GSC connection
        connection = GSCConnection(
            id=str(uuid4()),
            user_id=test_user.id,
            site_url="https://example.com",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            token_expiry=datetime.now(UTC) + timedelta(hours=1),
            is_active=True,
            last_sync=datetime.now(UTC),
        )
        db_session.add(connection)
        await db_session.commit()

        response = await async_client.get(
            "/api/v1/analytics/gsc/status",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["connected"] is True
        assert data["site_url"] == "https://example.com"
        assert "last_sync" in data
        assert "connected_at" in data

    @pytest.mark.asyncio
    async def test_get_status_unauthorized(self, async_client: AsyncClient):
        """Test status request without authentication."""
        response = await async_client.get("/api/v1/analytics/gsc/status")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestDisconnectGSCEndpoint:
    """Tests for POST /analytics/gsc/disconnect endpoint."""

    @pytest.mark.asyncio
    async def test_disconnect_success(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test successful GSC disconnection."""
        # Create a GSC connection
        connection = GSCConnection(
            id=str(uuid4()),
            user_id=test_user.id,
            site_url="https://example.com",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            token_expiry=datetime.now(UTC) + timedelta(hours=1),
            is_active=True,
        )
        db_session.add(connection)
        await db_session.commit()

        response = await async_client.post(
            "/api/v1/analytics/gsc/disconnect",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "disconnected_at" in data

        # Verify connection is inactive
        await db_session.refresh(connection)
        assert connection.is_active is False

    @pytest.mark.asyncio
    async def test_disconnect_not_connected(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test disconnect when GSC is not connected."""
        response = await async_client.post(
            "/api/v1/analytics/gsc/disconnect",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "No GSC connection found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_disconnect_unauthorized(self, async_client: AsyncClient):
        """Test disconnect without authentication."""
        response = await async_client.post("/api/v1/analytics/gsc/disconnect")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestGetKeywordsEndpoint:
    """Tests for GET /analytics/keywords endpoint."""

    @pytest.mark.asyncio
    async def test_get_keywords_no_connection(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test getting keywords when GSC is not connected."""
        response = await async_client.get(
            "/api/v1/analytics/keywords",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "GSC not connected" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_keywords_empty(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test getting keywords when none exist."""
        # Create GSC connection
        connection = GSCConnection(
            id=str(uuid4()),
            user_id=test_user.id,
            site_url="https://example.com",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            token_expiry=datetime.now(UTC) + timedelta(hours=1),
            is_active=True,
        )
        db_session.add(connection)
        await db_session.commit()

        response = await async_client.get(
            "/api/v1/analytics/keywords",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
        assert data["page"] == 1
        assert data["pages"] == 0

    @pytest.mark.asyncio
    async def test_get_keywords_with_data(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test getting keywords with existing data."""
        # Create GSC connection
        connection = GSCConnection(
            id=str(uuid4()),
            user_id=test_user.id,
            site_url="https://example.com",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            token_expiry=datetime.now(UTC) + timedelta(hours=1),
            is_active=True,
        )
        db_session.add(connection)

        # Create keyword rankings
        keywords = [
            KeywordRanking(
                id=str(uuid4()),
                user_id=test_user.id,
                site_url="https://example.com",
                keyword=f"keyword {i}",
                date=date.today() - timedelta(days=i),
                clicks=100 - i,
                impressions=1000 - i * 10,
                ctr=0.1,
                position=5.0 + i,
            )
            for i in range(5)
        ]
        for keyword in keywords:
            db_session.add(keyword)

        await db_session.commit()

        response = await async_client.get(
            "/api/v1/analytics/keywords",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 5

    @pytest.mark.asyncio
    async def test_get_keywords_pagination(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test keyword pagination."""
        # Create GSC connection
        connection = GSCConnection(
            id=str(uuid4()),
            user_id=test_user.id,
            site_url="https://example.com",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            token_expiry=datetime.now(UTC) + timedelta(hours=1),
            is_active=True,
        )
        db_session.add(connection)

        # Create 25 keyword rankings
        for i in range(25):
            keyword = KeywordRanking(
                id=str(uuid4()),
                user_id=test_user.id,
                site_url="https://example.com",
                keyword=f"keyword {i}",
                date=date.today(),
                clicks=100 - i,
                impressions=1000,
                ctr=0.1,
                position=5.0,
            )
            db_session.add(keyword)

        await db_session.commit()

        # Get first page
        response = await async_client.get(
            "/api/v1/analytics/keywords?page=1&page_size=10",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 25
        assert len(data["items"]) == 10
        assert data["page"] == 1
        assert data["pages"] == 3

    @pytest.mark.asyncio
    async def test_get_keywords_filter_by_keyword(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test filtering keywords by search term."""
        # Create GSC connection
        connection = GSCConnection(
            id=str(uuid4()),
            user_id=test_user.id,
            site_url="https://example.com",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            token_expiry=datetime.now(UTC) + timedelta(hours=1),
            is_active=True,
        )
        db_session.add(connection)

        # Create keywords with specific names
        keywords = [
            KeywordRanking(
                id=str(uuid4()),
                user_id=test_user.id,
                site_url="https://example.com",
                keyword="python tutorial",
                date=date.today(),
                clicks=100,
                impressions=1000,
                ctr=0.1,
                position=5.0,
            ),
            KeywordRanking(
                id=str(uuid4()),
                user_id=test_user.id,
                site_url="https://example.com",
                keyword="javascript guide",
                date=date.today(),
                clicks=50,
                impressions=500,
                ctr=0.1,
                position=7.0,
            ),
        ]
        for keyword in keywords:
            db_session.add(keyword)

        await db_session.commit()

        # Filter by "python"
        response = await async_client.get(
            "/api/v1/analytics/keywords?keyword=python",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["keyword"] == "python tutorial"

    @pytest.mark.asyncio
    async def test_get_keywords_unauthorized(self, async_client: AsyncClient):
        """Test getting keywords without authentication."""
        response = await async_client.get("/api/v1/analytics/keywords")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestGetPagesEndpoint:
    """Tests for GET /analytics/pages endpoint."""

    @pytest.mark.asyncio
    async def test_get_pages_no_connection(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test getting pages when GSC is not connected."""
        response = await async_client.get(
            "/api/v1/analytics/pages",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "GSC not connected" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_pages_with_data(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test getting pages with existing data."""
        # Create GSC connection
        connection = GSCConnection(
            id=str(uuid4()),
            user_id=test_user.id,
            site_url="https://example.com",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            token_expiry=datetime.now(UTC) + timedelta(hours=1),
            is_active=True,
        )
        db_session.add(connection)

        # Create page performance data
        pages = [
            PagePerformance(
                id=str(uuid4()),
                user_id=test_user.id,
                site_url="https://example.com",
                page_url=f"https://example.com/page{i}",
                date=date.today(),
                clicks=200 - i * 10,
                impressions=2000 - i * 100,
                ctr=0.1,
                position=4.0 + i,
            )
            for i in range(5)
        ]
        for page in pages:
            db_session.add(page)

        await db_session.commit()

        response = await async_client.get(
            "/api/v1/analytics/pages",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 5

    @pytest.mark.asyncio
    async def test_get_pages_filter_by_url(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test filtering pages by URL."""
        # Create GSC connection
        connection = GSCConnection(
            id=str(uuid4()),
            user_id=test_user.id,
            site_url="https://example.com",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            token_expiry=datetime.now(UTC) + timedelta(hours=1),
            is_active=True,
        )
        db_session.add(connection)

        # Create pages
        pages = [
            PagePerformance(
                id=str(uuid4()),
                user_id=test_user.id,
                site_url="https://example.com",
                page_url="https://example.com/blog/python-tutorial",
                date=date.today(),
                clicks=200,
                impressions=2000,
                ctr=0.1,
                position=4.0,
            ),
            PagePerformance(
                id=str(uuid4()),
                user_id=test_user.id,
                site_url="https://example.com",
                page_url="https://example.com/blog/javascript-guide",
                date=date.today(),
                clicks=100,
                impressions=1000,
                ctr=0.1,
                position=6.0,
            ),
        ]
        for page in pages:
            db_session.add(page)

        await db_session.commit()

        # Filter by "python"
        response = await async_client.get(
            "/api/v1/analytics/pages?page_url=python",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert "python-tutorial" in data["items"][0]["page_url"]


class TestGetDailyAnalyticsEndpoint:
    """Tests for GET /analytics/daily endpoint."""

    @pytest.mark.asyncio
    async def test_get_daily_no_connection(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test getting daily analytics when GSC is not connected."""
        response = await async_client.get(
            "/api/v1/analytics/daily",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "GSC not connected" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_daily_with_data(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test getting daily analytics with existing data."""
        # Create GSC connection
        connection = GSCConnection(
            id=str(uuid4()),
            user_id=test_user.id,
            site_url="https://example.com",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            token_expiry=datetime.now(UTC) + timedelta(hours=1),
            is_active=True,
        )
        db_session.add(connection)

        # Create daily analytics data
        for i in range(7):
            daily = DailyAnalytics(
                id=str(uuid4()),
                user_id=test_user.id,
                site_url="https://example.com",
                date=date.today() - timedelta(days=i),
                total_clicks=100 + i * 10,
                total_impressions=1000 + i * 100,
                avg_ctr=0.1,
                avg_position=5.0,
            )
            db_session.add(daily)

        await db_session.commit()

        response = await async_client.get(
            "/api/v1/analytics/daily",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 7
        assert len(data["items"]) == 7

    @pytest.mark.asyncio
    async def test_get_daily_date_range(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test filtering daily analytics by date range."""
        # Create GSC connection
        connection = GSCConnection(
            id=str(uuid4()),
            user_id=test_user.id,
            site_url="https://example.com",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            token_expiry=datetime.now(UTC) + timedelta(hours=1),
            is_active=True,
        )
        db_session.add(connection)

        # Create 30 days of data
        for i in range(30):
            daily = DailyAnalytics(
                id=str(uuid4()),
                user_id=test_user.id,
                site_url="https://example.com",
                date=date.today() - timedelta(days=i),
                total_clicks=100,
                total_impressions=1000,
                avg_ctr=0.1,
                avg_position=5.0,
            )
            db_session.add(daily)

        await db_session.commit()

        # Filter to last 7 days
        start = date.today() - timedelta(days=6)
        end = date.today()

        response = await async_client.get(
            f"/api/v1/analytics/daily?start_date={start}&end_date={end}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 7


class TestGetAnalyticsSummaryEndpoint:
    """Tests for GET /analytics/summary endpoint."""

    @pytest.mark.asyncio
    async def test_get_summary_no_connection(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test getting summary when GSC is not connected."""
        response = await async_client.get(
            "/api/v1/analytics/summary",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "GSC not connected" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_summary_with_data(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test getting analytics summary with data."""
        # Create GSC connection
        connection = GSCConnection(
            id=str(uuid4()),
            user_id=test_user.id,
            site_url="https://example.com",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            token_expiry=datetime.now(UTC) + timedelta(hours=1),
            is_active=True,
        )
        db_session.add(connection)

        # Create daily analytics for current period (last 30 days)
        for i in range(30):
            daily = DailyAnalytics(
                id=str(uuid4()),
                user_id=test_user.id,
                site_url="https://example.com",
                date=date.today() - timedelta(days=i),
                total_clicks=100,
                total_impressions=1000,
                avg_ctr=0.1,
                avg_position=5.0,
            )
            db_session.add(daily)

        # Create some keyword rankings
        for i in range(5):
            keyword = KeywordRanking(
                id=str(uuid4()),
                user_id=test_user.id,
                site_url="https://example.com",
                keyword=f"keyword {i}",
                date=date.today(),
                clicks=100 - i * 10,
                impressions=1000,
                ctr=0.1,
                position=5.0,
            )
            db_session.add(keyword)

        # Create some page performance data
        for i in range(5):
            page = PagePerformance(
                id=str(uuid4()),
                user_id=test_user.id,
                site_url="https://example.com",
                page_url=f"https://example.com/page{i}",
                date=date.today(),
                clicks=200 - i * 20,
                impressions=2000,
                ctr=0.1,
                position=4.0,
            )
            db_session.add(page)

        await db_session.commit()

        response = await async_client.get(
            "/api/v1/analytics/summary",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check aggregated metrics
        assert "total_clicks" in data
        assert "total_impressions" in data
        assert "avg_ctr" in data
        assert "avg_position" in data

        # Check trends
        assert "clicks_trend" in data
        assert "impressions_trend" in data
        assert "ctr_trend" in data
        assert "position_trend" in data

        # Check trend structure
        assert data["clicks_trend"]["current"] == 3000  # 100 clicks * 30 days
        assert data["clicks_trend"]["trend"] in ["up", "down", "stable"]

        # Check top performers
        assert "top_keywords" in data
        assert "top_pages" in data
        assert len(data["top_keywords"]) <= 10
        assert len(data["top_pages"]) <= 10

        # Check metadata
        assert data["site_url"] == "https://example.com"
        assert "start_date" in data
        assert "end_date" in data

    @pytest.mark.asyncio
    async def test_get_summary_empty_data(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test summary with no analytics data."""
        # Create GSC connection but no data
        connection = GSCConnection(
            id=str(uuid4()),
            user_id=test_user.id,
            site_url="https://example.com",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            token_expiry=datetime.now(UTC) + timedelta(hours=1),
            is_active=True,
        )
        db_session.add(connection)
        await db_session.commit()

        response = await async_client.get(
            "/api/v1/analytics/summary",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should return zeros
        assert data["total_clicks"] == 0
        assert data["total_impressions"] == 0
        assert data["top_keywords"] == []
        assert data["top_pages"] == []

    @pytest.mark.asyncio
    async def test_get_summary_custom_date_range(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test summary with custom date range."""
        # Create GSC connection
        connection = GSCConnection(
            id=str(uuid4()),
            user_id=test_user.id,
            site_url="https://example.com",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            token_expiry=datetime.now(UTC) + timedelta(hours=1),
            is_active=True,
        )
        db_session.add(connection)

        # Create 60 days of data
        for i in range(60):
            daily = DailyAnalytics(
                id=str(uuid4()),
                user_id=test_user.id,
                site_url="https://example.com",
                date=date.today() - timedelta(days=i),
                total_clicks=100,
                total_impressions=1000,
                avg_ctr=0.1,
                avg_position=5.0,
            )
            db_session.add(daily)

        await db_session.commit()

        # Request last 7 days
        start = date.today() - timedelta(days=6)
        end = date.today()

        response = await async_client.get(
            f"/api/v1/analytics/summary?start_date={start}&end_date={end}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should only count 7 days
        assert data["total_clicks"] == 700  # 100 * 7
        assert data["start_date"] == start.isoformat()
        assert data["end_date"] == end.isoformat()

    @pytest.mark.asyncio
    async def test_get_summary_unauthorized(self, async_client: AsyncClient):
        """Test getting summary without authentication."""
        response = await async_client.get("/api/v1/analytics/summary")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
