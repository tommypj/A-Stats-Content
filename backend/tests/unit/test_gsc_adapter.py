"""
Tests for Google Search Console OAuth adapter.
"""

import pytest
from datetime import datetime, date, timedelta
from unittest.mock import Mock, patch, MagicMock
from urllib.parse import urlparse, parse_qs

from adapters.search.gsc_adapter import (
    GSCAdapter,
    GSCCredentials,
    GSCAuthError,
    GSCAPIError,
    GSCQuotaError,
    create_gsc_adapter,
)


class TestGSCCredentials:
    """Tests for GSCCredentials dataclass."""

    def test_credentials_initialization(self):
        """Test GSCCredentials initialization."""
        token_expiry = datetime.utcnow() + timedelta(hours=1)
        creds = GSCCredentials(
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            token_expiry=token_expiry,
            site_url="https://example.com",
        )

        assert creds.access_token == "test_access_token"
        assert creds.refresh_token == "test_refresh_token"
        assert creds.token_expiry == token_expiry
        assert creds.site_url == "https://example.com"

    def test_credentials_to_dict(self):
        """Test converting credentials to dictionary."""
        token_expiry = datetime(2024, 1, 1, 12, 0, 0)
        creds = GSCCredentials(
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            token_expiry=token_expiry,
            site_url="https://example.com",
        )

        data = creds.to_dict()
        assert data["access_token"] == "test_access_token"
        assert data["refresh_token"] == "test_refresh_token"
        assert data["token_expiry"] == "2024-01-01T12:00:00"
        assert data["site_url"] == "https://example.com"

    def test_credentials_from_dict(self):
        """Test creating credentials from dictionary."""
        data = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "token_expiry": "2024-01-01T12:00:00",
            "site_url": "https://example.com",
        }

        creds = GSCCredentials.from_dict(data)
        assert creds.access_token == "test_access_token"
        assert creds.refresh_token == "test_refresh_token"
        assert creds.token_expiry == datetime(2024, 1, 1, 12, 0, 0)
        assert creds.site_url == "https://example.com"


class TestGSCAdapter:
    """Tests for GSCAdapter."""

    @pytest.fixture
    def adapter(self):
        """Create GSCAdapter instance with test credentials."""
        return GSCAdapter(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="http://localhost:8000/callback",
        )

    @pytest.fixture
    def mock_credentials(self):
        """Create mock credentials."""
        return GSCCredentials(
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            token_expiry=datetime.utcnow() + timedelta(hours=1),
            site_url="https://example.com",
        )

    @pytest.fixture
    def expired_credentials(self):
        """Create expired credentials."""
        return GSCCredentials(
            access_token="expired_access_token",
            refresh_token="test_refresh_token",
            token_expiry=datetime.utcnow() - timedelta(hours=1),
            site_url="https://example.com",
        )

    def test_adapter_initialization(self, adapter):
        """Test adapter initialization."""
        assert adapter.client_id == "test_client_id"
        assert adapter.client_secret == "test_client_secret"
        assert adapter.redirect_uri == "http://localhost:8000/callback"

    def test_adapter_initialization_with_defaults(self):
        """Test adapter initialization with default settings."""
        with patch("adapters.search.gsc_adapter.settings") as mock_settings:
            mock_settings.google_client_id = "settings_client_id"
            mock_settings.google_client_secret = "settings_secret"
            mock_settings.google_redirect_uri = "http://localhost:8000/settings"

            adapter = GSCAdapter()
            assert adapter.client_id == "settings_client_id"
            assert adapter.client_secret == "settings_secret"
            assert adapter.redirect_uri == "http://localhost:8000/settings"

    def test_get_authorization_url(self, adapter):
        """Test OAuth authorization URL generation."""
        state = "test_state_123"
        auth_url = adapter.get_authorization_url(state)

        # Parse URL and verify parameters
        parsed = urlparse(auth_url)
        params = parse_qs(parsed.query)

        assert parsed.scheme == "https"
        assert parsed.netloc == "accounts.google.com"
        assert params["client_id"][0] == "test_client_id"
        assert params["redirect_uri"][0] == "http://localhost:8000/callback"
        assert params["response_type"][0] == "code"
        assert params["scope"][0] == "https://www.googleapis.com/auth/webmasters.readonly"
        assert params["state"][0] == "test_state_123"
        assert params["access_type"][0] == "offline"
        assert params["prompt"][0] == "consent"

    def test_get_authorization_url_without_credentials(self):
        """Test authorization URL generation fails without credentials."""
        adapter = GSCAdapter(
            client_id=None,
            client_secret="test_secret",
            redirect_uri=None,
        )

        with pytest.raises(GSCAuthError, match="not configured"):
            adapter.get_authorization_url("test_state")

    @patch("httpx.post")
    def test_exchange_code_success(self, mock_post, adapter):
        """Test successful authorization code exchange."""
        # Mock successful token response
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }
        mock_post.return_value = mock_response

        credentials = adapter.exchange_code("test_auth_code")

        assert credentials.access_token == "new_access_token"
        assert credentials.refresh_token == "new_refresh_token"
        assert credentials.site_url == ""  # Not set yet

        # Verify the token request was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://oauth2.googleapis.com/token"
        assert call_args[1]["data"]["code"] == "test_auth_code"
        assert call_args[1]["data"]["client_id"] == "test_client_id"
        assert call_args[1]["data"]["grant_type"] == "authorization_code"

    @patch("httpx.post")
    def test_exchange_code_http_error(self, mock_post, adapter):
        """Test authorization code exchange with HTTP error."""
        import httpx

        mock_post.side_effect = httpx.HTTPError("Connection failed")

        with pytest.raises(GSCAuthError, match="Failed to exchange"):
            adapter.exchange_code("test_auth_code")

    @patch("httpx.post")
    def test_exchange_code_invalid_response(self, mock_post, adapter):
        """Test authorization code exchange with invalid response."""
        mock_response = Mock()
        mock_response.json.return_value = {"invalid": "response"}
        mock_post.return_value = mock_response

        with pytest.raises(GSCAuthError, match="Invalid token response"):
            adapter.exchange_code("test_auth_code")

    @patch("httpx.post")
    def test_refresh_tokens_success(self, mock_post, adapter, mock_credentials):
        """Test successful token refresh."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "refreshed_access_token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }
        mock_post.return_value = mock_response

        new_credentials = adapter.refresh_tokens(mock_credentials)

        assert new_credentials.access_token == "refreshed_access_token"
        assert new_credentials.refresh_token == "test_refresh_token"  # Kept
        assert new_credentials.site_url == "https://example.com"

        # Verify the refresh request
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]["data"]["refresh_token"] == "test_refresh_token"
        assert call_args[1]["data"]["grant_type"] == "refresh_token"

    @patch("httpx.post")
    def test_refresh_tokens_http_error(self, mock_post, adapter, mock_credentials):
        """Test token refresh with HTTP error."""
        import httpx

        mock_post.side_effect = httpx.HTTPError("Connection failed")

        with pytest.raises(GSCAuthError, match="Failed to refresh"):
            adapter.refresh_tokens(mock_credentials)

    def test_refresh_tokens_no_refresh_token(self, adapter):
        """Test token refresh fails without refresh token."""
        credentials = GSCCredentials(
            access_token="test_token",
            refresh_token="",  # No refresh token
            token_expiry=datetime.utcnow() + timedelta(hours=1),
            site_url="https://example.com",
        )

        with pytest.raises(GSCAuthError, match="No refresh token"):
            adapter.refresh_tokens(credentials)

    @patch("adapters.search.gsc_adapter.build")
    @patch("adapters.search.gsc_adapter.Credentials")
    def test_get_service(self, mock_creds_class, mock_build, adapter, mock_credentials):
        """Test getting authenticated API service."""
        mock_service = Mock()
        mock_build.return_value = mock_service

        service, updated_creds = adapter._get_service(mock_credentials)

        assert service == mock_service
        assert updated_creds == mock_credentials

        # Verify credentials were created correctly
        mock_creds_class.assert_called_once_with(
            token="test_access_token",
            refresh_token="test_refresh_token",
            token_uri="https://oauth2.googleapis.com/token",
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        # Verify service was built
        mock_build.assert_called_once_with(
            "searchconsole",
            "v1",
            credentials=mock_creds_class.return_value,
            cache_discovery=False,
        )

    @patch("httpx.post")
    @patch("adapters.search.gsc_adapter.build")
    @patch("adapters.search.gsc_adapter.Credentials")
    def test_get_service_refreshes_expired_token(
        self, mock_creds_class, mock_build, mock_post, adapter, expired_credentials
    ):
        """Test that expired tokens are refreshed when getting service."""
        # Mock refresh response
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "refreshed_token",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response

        mock_service = Mock()
        mock_build.return_value = mock_service

        service, updated_creds = adapter._get_service(expired_credentials)

        # Verify token was refreshed
        mock_post.assert_called_once()
        assert updated_creds.access_token == "refreshed_token"

    @patch("adapters.search.gsc_adapter.build")
    @patch("adapters.search.gsc_adapter.Credentials")
    def test_list_sites(self, mock_creds_class, mock_build, adapter, mock_credentials):
        """Test listing verified sites."""
        # Mock API response
        mock_service = Mock()
        mock_sites_list = Mock()
        mock_sites_list.execute.return_value = {
            "siteEntry": [
                {"siteUrl": "https://example.com", "permissionLevel": "siteOwner"},
                {"siteUrl": "https://example2.com", "permissionLevel": "siteFullUser"},
            ]
        }
        mock_service.sites.return_value.list.return_value = mock_sites_list
        mock_build.return_value = mock_service

        sites = adapter.list_sites(mock_credentials)

        assert len(sites) == 2
        assert sites[0]["siteUrl"] == "https://example.com"
        assert sites[1]["siteUrl"] == "https://example2.com"

    @patch("adapters.search.gsc_adapter.build")
    @patch("adapters.search.gsc_adapter.Credentials")
    def test_list_sites_quota_error(self, mock_creds_class, mock_build, adapter, mock_credentials):
        """Test quota error when listing sites."""
        from googleapiclient.errors import HttpError

        mock_service = Mock()
        mock_response = Mock()
        mock_response.status = 403
        mock_service.sites.return_value.list.return_value.execute.side_effect = HttpError(
            mock_response, b"Quota exceeded"
        )
        mock_build.return_value = mock_service

        with pytest.raises(GSCQuotaError, match="quota exceeded"):
            adapter.list_sites(mock_credentials)

    @patch("adapters.search.gsc_adapter.build")
    @patch("adapters.search.gsc_adapter.Credentials")
    def test_get_search_analytics(self, mock_creds_class, mock_build, adapter, mock_credentials):
        """Test fetching search analytics data."""
        # Mock API response
        mock_service = Mock()
        mock_query = Mock()
        mock_query.execute.return_value = {
            "rows": [
                {
                    "keys": ["keyword1"],
                    "clicks": 100,
                    "impressions": 1000,
                    "ctr": 0.1,
                    "position": 5.5,
                },
                {
                    "keys": ["keyword2"],
                    "clicks": 50,
                    "impressions": 500,
                    "ctr": 0.1,
                    "position": 7.2,
                },
            ]
        }
        mock_service.searchanalytics.return_value.query.return_value = mock_query
        mock_build.return_value = mock_service

        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)
        dimensions = ["query"]

        rows = adapter.get_search_analytics(
            credentials=mock_credentials,
            site_url="https://example.com",
            start_date=start_date,
            end_date=end_date,
            dimensions=dimensions,
            row_limit=1000,
        )

        assert len(rows) == 2
        assert rows[0]["keys"] == ["keyword1"]
        assert rows[0]["clicks"] == 100
        assert rows[1]["keys"] == ["keyword2"]

        # Verify API was called correctly
        mock_service.searchanalytics.return_value.query.assert_called_once_with(
            siteUrl="https://example.com",
            body={
                "startDate": "2024-01-01",
                "endDate": "2024-01-31",
                "dimensions": ["query"],
                "rowLimit": 1000,
                "startRow": 0,
            },
        )

    @patch("adapters.search.gsc_adapter.build")
    @patch("adapters.search.gsc_adapter.Credentials")
    def test_get_keyword_rankings(self, mock_creds_class, mock_build, adapter, mock_credentials):
        """Test getting keyword rankings."""
        # Mock API response
        mock_service = Mock()
        mock_query = Mock()
        mock_query.execute.return_value = {
            "rows": [
                {
                    "keys": ["keyword1"],
                    "clicks": 100,
                    "impressions": 1000,
                    "ctr": 0.1,
                    "position": 5.5,
                },
                {
                    "keys": ["keyword2"],
                    "clicks": 150,  # Higher clicks
                    "impressions": 800,
                    "ctr": 0.1875,
                    "position": 3.2,
                },
            ]
        }
        mock_service.searchanalytics.return_value.query.return_value = mock_query
        mock_build.return_value = mock_service

        keywords = adapter.get_keyword_rankings(
            credentials=mock_credentials,
            site_url="https://example.com",
            days=28,
        )

        assert len(keywords) == 2
        # Should be sorted by clicks descending
        assert keywords[0]["query"] == "keyword2"
        assert keywords[0]["clicks"] == 150
        assert keywords[1]["query"] == "keyword1"
        assert keywords[1]["clicks"] == 100

    @patch("adapters.search.gsc_adapter.build")
    @patch("adapters.search.gsc_adapter.Credentials")
    def test_get_page_performance(self, mock_creds_class, mock_build, adapter, mock_credentials):
        """Test getting page-level performance."""
        # Mock API response
        mock_service = Mock()
        mock_query = Mock()
        mock_query.execute.return_value = {
            "rows": [
                {
                    "keys": ["https://example.com/page1"],
                    "clicks": 200,
                    "impressions": 2000,
                    "ctr": 0.1,
                    "position": 4.0,
                },
                {
                    "keys": ["https://example.com/page2"],
                    "clicks": 50,
                    "impressions": 500,
                    "ctr": 0.1,
                    "position": 8.5,
                },
            ]
        }
        mock_service.searchanalytics.return_value.query.return_value = mock_query
        mock_build.return_value = mock_service

        pages = adapter.get_page_performance(
            credentials=mock_credentials,
            site_url="https://example.com",
            days=28,
        )

        assert len(pages) == 2
        # Should be sorted by clicks descending
        assert pages[0]["page"] == "https://example.com/page1"
        assert pages[0]["clicks"] == 200
        assert pages[1]["page"] == "https://example.com/page2"

    @patch("adapters.search.gsc_adapter.build")
    @patch("adapters.search.gsc_adapter.Credentials")
    def test_get_daily_stats(self, mock_creds_class, mock_build, adapter, mock_credentials):
        """Test getting daily aggregated statistics."""
        # Mock API response
        mock_service = Mock()
        mock_query = Mock()
        mock_query.execute.return_value = {
            "rows": [
                {
                    "keys": ["2024-01-02"],
                    "clicks": 150,
                    "impressions": 1500,
                    "ctr": 0.1,
                    "position": 6.0,
                },
                {
                    "keys": ["2024-01-01"],
                    "clicks": 100,
                    "impressions": 1000,
                    "ctr": 0.1,
                    "position": 5.5,
                },
            ]
        }
        mock_service.searchanalytics.return_value.query.return_value = mock_query
        mock_build.return_value = mock_service

        daily_stats = adapter.get_daily_stats(
            credentials=mock_credentials,
            site_url="https://example.com",
            days=7,
        )

        assert len(daily_stats) == 2
        # Should be sorted by date ascending
        assert daily_stats[0]["date"] == "2024-01-01"
        assert daily_stats[1]["date"] == "2024-01-02"

    @patch("adapters.search.gsc_adapter.build")
    @patch("adapters.search.gsc_adapter.Credentials")
    def test_get_device_breakdown(self, mock_creds_class, mock_build, adapter, mock_credentials):
        """Test getting device breakdown."""
        # Mock API response
        mock_service = Mock()
        mock_query = Mock()
        mock_query.execute.return_value = {
            "rows": [
                {
                    "keys": ["MOBILE"],
                    "clicks": 500,
                    "impressions": 5000,
                    "ctr": 0.1,
                    "position": 5.0,
                },
                {
                    "keys": ["DESKTOP"],
                    "clicks": 300,
                    "impressions": 3000,
                    "ctr": 0.1,
                    "position": 6.0,
                },
                {
                    "keys": ["TABLET"],
                    "clicks": 50,
                    "impressions": 500,
                    "ctr": 0.1,
                    "position": 7.0,
                },
            ]
        }
        mock_service.searchanalytics.return_value.query.return_value = mock_query
        mock_build.return_value = mock_service

        devices = adapter.get_device_breakdown(
            credentials=mock_credentials,
            site_url="https://example.com",
            days=28,
        )

        assert len(devices) == 3
        assert devices[0]["device"] == "MOBILE"
        assert devices[1]["device"] == "DESKTOP"
        assert devices[2]["device"] == "TABLET"

    @patch("adapters.search.gsc_adapter.build")
    @patch("adapters.search.gsc_adapter.Credentials")
    def test_get_country_breakdown(self, mock_creds_class, mock_build, adapter, mock_credentials):
        """Test getting country breakdown."""
        # Mock API response
        mock_service = Mock()
        mock_query = Mock()
        mock_query.execute.return_value = {
            "rows": [
                {
                    "keys": ["usa"],
                    "clicks": 800,
                    "impressions": 8000,
                    "ctr": 0.1,
                    "position": 5.0,
                },
                {
                    "keys": ["gbr"],
                    "clicks": 200,
                    "impressions": 2000,
                    "ctr": 0.1,
                    "position": 6.0,
                },
            ]
        }
        mock_service.searchanalytics.return_value.query.return_value = mock_query
        mock_build.return_value = mock_service

        countries = adapter.get_country_breakdown(
            credentials=mock_credentials,
            site_url="https://example.com",
            days=28,
            top_n=20,
        )

        assert len(countries) == 2
        # Should be sorted by clicks descending
        assert countries[0]["country"] == "usa"
        assert countries[0]["clicks"] == 800
        assert countries[1]["country"] == "gbr"

    def test_create_gsc_adapter_factory(self):
        """Test factory function for creating adapter."""
        adapter = create_gsc_adapter(
            client_id="factory_client_id",
            client_secret="factory_secret",
            redirect_uri="http://factory.local/callback",
        )

        assert isinstance(adapter, GSCAdapter)
        assert adapter.client_id == "factory_client_id"
        assert adapter.client_secret == "factory_secret"
        assert adapter.redirect_uri == "http://factory.local/callback"
