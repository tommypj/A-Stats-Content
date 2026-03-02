"""
Integration tests for admin analytics API.

Tests admin analytics endpoints:
- Dashboard statistics
- User analytics
- Content analytics
- Revenue analytics
- System health metrics
- Authorization checks
"""

from datetime import date, timedelta

import pytest
from fastapi import status
from httpx import AsyncClient

# Skip all tests if admin routes are not available
try:
    from api.routes import admin

    ADMIN_ROUTES_AVAILABLE = True
except (ImportError, AttributeError):
    ADMIN_ROUTES_AVAILABLE = False
    pytestmark = pytest.mark.skip(reason="Admin routes not implemented yet")


class TestDashboardStatsEndpoint:
    """Tests for GET /admin/analytics/dashboard endpoint."""

    @pytest.mark.asyncio
    async def test_admin_can_get_dashboard_stats(
        self,
        async_client: AsyncClient,
        admin_token: dict,
    ):
        """Test that admin can get dashboard statistics."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.get(
            "/api/v1/admin/analytics/dashboard",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify stats structure
        assert "total_users" in data
        assert "active_users" in data
        assert "suspended_users" in data
        assert "total_revenue" in data
        assert "mrr" in data  # Monthly Recurring Revenue
        assert "total_articles" in data
        assert "total_outlines" in data
        assert "total_images" in data
        assert "storage_used_gb" in data

    @pytest.mark.asyncio
    async def test_super_admin_can_get_dashboard_stats(
        self,
        async_client: AsyncClient,
        super_admin_token: dict,
    ):
        """Test that super admin can get dashboard statistics."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.get(
            "/api/v1/admin/analytics/dashboard",
            headers=super_admin_token,
        )

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_regular_user_cannot_get_dashboard_stats(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test that regular user cannot get dashboard statistics."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.get(
            "/api/v1/admin/analytics/dashboard",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_dashboard_stats_includes_growth_metrics(
        self,
        async_client: AsyncClient,
        admin_token: dict,
    ):
        """Test that dashboard includes growth metrics."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.get(
            "/api/v1/admin/analytics/dashboard",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Growth metrics should be present
        assert "user_growth_percent" in data
        assert "revenue_growth_percent" in data
        assert "content_growth_percent" in data

    @pytest.mark.asyncio
    async def test_dashboard_stats_date_range_filter(
        self,
        async_client: AsyncClient,
        admin_token: dict,
    ):
        """Test dashboard stats with date range filter."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        start_date = (date.today() - timedelta(days=30)).isoformat()
        end_date = date.today().isoformat()

        response = await async_client.get(
            f"/api/v1/admin/analytics/dashboard?start_date={start_date}&end_date={end_date}",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_200_OK


class TestUserAnalyticsEndpoint:
    """Tests for GET /admin/analytics/users endpoint."""

    @pytest.mark.asyncio
    async def test_admin_can_get_user_analytics(
        self,
        async_client: AsyncClient,
        admin_token: dict,
    ):
        """Test that admin can get user analytics."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.get(
            "/api/v1/admin/analytics/users",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify user analytics structure
        assert "total_users" in data
        assert "new_users_this_month" in data
        assert "active_users_this_month" in data
        assert "users_by_tier" in data
        assert "users_by_status" in data
        assert "signup_trend" in data

    @pytest.mark.asyncio
    async def test_user_analytics_includes_subscription_breakdown(
        self,
        async_client: AsyncClient,
        admin_token: dict,
    ):
        """Test that user analytics includes subscription tier breakdown."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.get(
            "/api/v1/admin/analytics/users",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        users_by_tier = data["users_by_tier"]
        assert "free" in users_by_tier
        assert "starter" in users_by_tier
        assert "professional" in users_by_tier
        assert "enterprise" in users_by_tier

    @pytest.mark.asyncio
    async def test_user_analytics_includes_status_breakdown(
        self,
        async_client: AsyncClient,
        admin_token: dict,
    ):
        """Test that user analytics includes status breakdown."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.get(
            "/api/v1/admin/analytics/users",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        users_by_status = data["users_by_status"]
        assert "active" in users_by_status
        assert "pending" in users_by_status
        assert "suspended" in users_by_status

    @pytest.mark.asyncio
    async def test_user_analytics_signup_trend(
        self,
        async_client: AsyncClient,
        admin_token: dict,
    ):
        """Test that user analytics includes signup trend data."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.get(
            "/api/v1/admin/analytics/users?period=30d",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        signup_trend = data["signup_trend"]
        assert isinstance(signup_trend, list)
        assert len(signup_trend) > 0

        # Each trend item should have date and count
        if signup_trend:
            assert "date" in signup_trend[0]
            assert "count" in signup_trend[0]


class TestContentAnalyticsEndpoint:
    """Tests for GET /admin/analytics/content endpoint."""

    @pytest.mark.asyncio
    async def test_admin_can_get_content_analytics(
        self,
        async_client: AsyncClient,
        admin_token: dict,
    ):
        """Test that admin can get content analytics."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.get(
            "/api/v1/admin/analytics/content",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify content analytics structure
        assert "total_articles" in data
        assert "total_outlines" in data
        assert "total_images" in data
        assert "articles_this_month" in data
        assert "outlines_this_month" in data
        assert "images_this_month" in data
        assert "content_by_user" in data
        assert "popular_topics" in data

    @pytest.mark.asyncio
    async def test_content_analytics_includes_generation_trend(
        self,
        async_client: AsyncClient,
        admin_token: dict,
    ):
        """Test that content analytics includes generation trend."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.get(
            "/api/v1/admin/analytics/content",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "article_trend" in data
        assert "outline_trend" in data
        assert "image_trend" in data

    @pytest.mark.asyncio
    async def test_content_analytics_top_users(
        self,
        async_client: AsyncClient,
        admin_token: dict,
    ):
        """Test that content analytics includes top content creators."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.get(
            "/api/v1/admin/analytics/content?top_users=10",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        content_by_user = data["content_by_user"]
        assert isinstance(content_by_user, list)
        assert len(content_by_user) <= 10


class TestRevenueAnalyticsEndpoint:
    """Tests for GET /admin/analytics/revenue endpoint."""

    @pytest.mark.asyncio
    async def test_admin_can_get_revenue_analytics(
        self,
        async_client: AsyncClient,
        admin_token: dict,
    ):
        """Test that admin can get revenue analytics."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.get(
            "/api/v1/admin/analytics/revenue",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify revenue analytics structure
        assert "total_revenue" in data
        assert "mrr" in data  # Monthly Recurring Revenue
        assert "arr" in data  # Annual Recurring Revenue
        assert "revenue_this_month" in data
        assert "revenue_last_month" in data
        assert "revenue_by_tier" in data
        assert "revenue_trend" in data
        assert "churn_rate" in data

    @pytest.mark.asyncio
    async def test_revenue_analytics_by_subscription_tier(
        self,
        async_client: AsyncClient,
        admin_token: dict,
    ):
        """Test that revenue analytics includes breakdown by subscription tier."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.get(
            "/api/v1/admin/analytics/revenue",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        revenue_by_tier = data["revenue_by_tier"]
        assert "starter" in revenue_by_tier
        assert "professional" in revenue_by_tier
        assert "enterprise" in revenue_by_tier

    @pytest.mark.asyncio
    async def test_revenue_analytics_includes_churn_metrics(
        self,
        async_client: AsyncClient,
        admin_token: dict,
    ):
        """Test that revenue analytics includes churn metrics."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.get(
            "/api/v1/admin/analytics/revenue",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "churn_rate" in data
        assert "churned_users_this_month" in data
        assert "retention_rate" in data

    @pytest.mark.asyncio
    async def test_revenue_analytics_trend_data(
        self,
        async_client: AsyncClient,
        admin_token: dict,
    ):
        """Test that revenue analytics includes trend data."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.get(
            "/api/v1/admin/analytics/revenue?period=6m",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        revenue_trend = data["revenue_trend"]
        assert isinstance(revenue_trend, list)

        # Each trend item should have date and amount
        if revenue_trend:
            assert "date" in revenue_trend[0]
            assert "amount" in revenue_trend[0]


class TestSystemHealthEndpoint:
    """Tests for GET /admin/analytics/system endpoint."""

    @pytest.mark.asyncio
    async def test_admin_can_get_system_health(
        self,
        async_client: AsyncClient,
        admin_token: dict,
    ):
        """Test that admin can get system health metrics."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.get(
            "/api/v1/admin/analytics/system",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify system health structure
        assert "database_status" in data
        assert "redis_status" in data
        assert "chromadb_status" in data
        assert "storage_used_gb" in data
        assert "storage_limit_gb" in data
        assert "api_calls_today" in data
        assert "error_rate" in data

    @pytest.mark.asyncio
    async def test_system_health_includes_service_status(
        self,
        async_client: AsyncClient,
        admin_token: dict,
    ):
        """Test that system health includes status of external services."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.get(
            "/api/v1/admin/analytics/system",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Each service status should have health indicator
        assert data["database_status"] in ["healthy", "degraded", "down"]
        assert data["redis_status"] in ["healthy", "degraded", "down"]
        assert data["chromadb_status"] in ["healthy", "degraded", "down"]

    @pytest.mark.asyncio
    async def test_system_health_includes_performance_metrics(
        self,
        async_client: AsyncClient,
        admin_token: dict,
    ):
        """Test that system health includes performance metrics."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.get(
            "/api/v1/admin/analytics/system",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "avg_response_time_ms" in data
        assert "slow_queries_count" in data
        assert "error_rate" in data
        assert "uptime_percent" in data

    @pytest.mark.asyncio
    async def test_regular_user_cannot_get_system_health(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test that regular user cannot get system health."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.get(
            "/api/v1/admin/analytics/system",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestAnalyticsFiltersAndPeriods:
    """Tests for analytics filters and period parameters."""

    @pytest.mark.asyncio
    async def test_analytics_with_custom_date_range(
        self,
        async_client: AsyncClient,
        admin_token: dict,
    ):
        """Test analytics with custom date range."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        start_date = (date.today() - timedelta(days=90)).isoformat()
        end_date = date.today().isoformat()

        response = await async_client.get(
            f"/api/v1/admin/analytics/users?start_date={start_date}&end_date={end_date}",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_analytics_with_period_shorthand(
        self,
        async_client: AsyncClient,
        admin_token: dict,
    ):
        """Test analytics with period shorthand (7d, 30d, 3m, 6m, 1y)."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        periods = ["7d", "30d", "3m", "6m", "1y"]

        for period in periods:
            response = await async_client.get(
                f"/api/v1/admin/analytics/users?period={period}",
                headers=admin_token,
            )

            assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_analytics_invalid_date_range(
        self,
        async_client: AsyncClient,
        admin_token: dict,
    ):
        """Test analytics with invalid date range (end before start)."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        start_date = date.today().isoformat()
        end_date = (date.today() - timedelta(days=30)).isoformat()

        response = await async_client.get(
            f"/api/v1/admin/analytics/users?start_date={start_date}&end_date={end_date}",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
