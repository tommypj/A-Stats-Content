"""
Google Search Console OAuth adapter for fetching SEO analytics data.

Provides integration with Google Search Console API for retrieving
search performance data, keyword rankings, and page-level analytics.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from urllib.parse import urlencode

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


# Custom Exceptions
class GSCAuthError(Exception):
    """Raised when Google Search Console authentication fails."""
    pass


class GSCAPIError(Exception):
    """Raised when Google Search Console API returns an error."""
    pass


class GSCQuotaError(Exception):
    """Raised when Google Search Console API quota is exceeded."""
    pass


@dataclass
class GSCCredentials:
    """Google Search Console OAuth credentials."""

    access_token: str
    refresh_token: str
    token_expiry: datetime
    site_url: str  # The verified property URL

    def to_dict(self) -> Dict[str, Any]:
        """Convert credentials to dictionary format."""
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_expiry": self.token_expiry.isoformat(),
            "site_url": self.site_url,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GSCCredentials":
        """Create credentials from dictionary format."""
        return cls(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            token_expiry=datetime.fromisoformat(data["token_expiry"]),
            site_url=data["site_url"],
        )


class GSCAdapter:
    """
    Google Search Console API adapter for SEO analytics.

    Uses OAuth 2.0 for authentication and provides methods for fetching
    search performance data, keyword rankings, and page-level metrics.
    """

    # OAuth 2.0 settings
    OAUTH_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"
    OAUTH_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"

    # API settings
    API_SERVICE_NAME = "searchconsole"
    API_VERSION = "v1"

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
    ):
        """
        Initialize Google Search Console adapter.

        Args:
            client_id: Google OAuth client ID (defaults to settings)
            client_secret: Google OAuth client secret (defaults to settings)
            redirect_uri: OAuth redirect URI (defaults to settings)
        """
        self.client_id = client_id or settings.google_client_id
        self.client_secret = client_secret or settings.google_client_secret
        self.redirect_uri = redirect_uri or settings.google_redirect_uri

        if not all([self.client_id, self.client_secret, self.redirect_uri]):
            logger.warning(
                "Google OAuth credentials not fully configured. "
                "Set google_client_id, google_client_secret, and google_redirect_uri."
            )

    def get_authorization_url(self, state: str) -> str:
        """
        Generate OAuth 2.0 authorization URL.

        Args:
            state: Random state string for CSRF protection

        Returns:
            Authorization URL to redirect user to

        Raises:
            GSCAuthError: If OAuth credentials are not configured
        """
        if not all([self.client_id, self.redirect_uri]):
            raise GSCAuthError(
                "Google OAuth credentials not configured. "
                "Set google_client_id and google_redirect_uri in settings."
            )

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": self.OAUTH_SCOPE,
            "state": state,
            "access_type": "offline",  # Request refresh token
            "prompt": "consent",  # Force consent screen to get refresh token
        }

        authorization_url = f"{self.OAUTH_AUTH_URL}?{urlencode(params)}"
        logger.info("Generated OAuth authorization URL")
        return authorization_url

    def exchange_code(self, code: str) -> GSCCredentials:
        """
        Exchange authorization code for OAuth tokens.

        Args:
            code: Authorization code from OAuth callback

        Returns:
            GSCCredentials with access token, refresh token, and expiry

        Raises:
            GSCAuthError: If token exchange fails
        """
        if not all([self.client_id, self.client_secret, self.redirect_uri]):
            raise GSCAuthError(
                "Google OAuth credentials not configured. "
                "Set all required credentials in settings."
            )

        try:
            import httpx

            logger.info("Exchanging authorization code for tokens")

            # Exchange code for tokens
            token_data = {
                "code": code,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": self.redirect_uri,
                "grant_type": "authorization_code",
            }

            response = httpx.post(self.OAUTH_TOKEN_URL, data=token_data)
            response.raise_for_status()
            tokens = response.json()

            # Calculate token expiry
            expires_in = tokens.get("expires_in", 3600)
            token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)

            logger.info("Successfully exchanged code for tokens")

            # Note: site_url needs to be set later when user selects a property
            credentials = GSCCredentials(
                access_token=tokens["access_token"],
                refresh_token=tokens.get("refresh_token", ""),
                token_expiry=token_expiry,
                site_url="",  # Will be set when user selects a site
            )

            return credentials

        except httpx.HTTPError as e:
            logger.error(f"HTTP error during token exchange: {e}")
            raise GSCAuthError(f"Failed to exchange authorization code: {e}")
        except KeyError as e:
            logger.error(f"Missing required field in token response: {e}")
            raise GSCAuthError(f"Invalid token response: missing {e}")
        except Exception as e:
            logger.error(f"Unexpected error during token exchange: {e}")
            raise GSCAuthError(f"Token exchange failed: {e}")

    def refresh_tokens(self, credentials: GSCCredentials) -> GSCCredentials:
        """
        Refresh expired OAuth tokens.

        Args:
            credentials: Current credentials with refresh token

        Returns:
            Updated GSCCredentials with new access token and expiry

        Raises:
            GSCAuthError: If token refresh fails
        """
        if not credentials.refresh_token:
            raise GSCAuthError("No refresh token available. User must re-authenticate.")

        try:
            import httpx

            logger.info("Refreshing OAuth tokens")

            refresh_data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": credentials.refresh_token,
                "grant_type": "refresh_token",
            }

            response = httpx.post(self.OAUTH_TOKEN_URL, data=refresh_data)
            response.raise_for_status()
            tokens = response.json()

            # Calculate new token expiry
            expires_in = tokens.get("expires_in", 3600)
            token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)

            logger.info("Successfully refreshed tokens")

            # Return updated credentials
            return GSCCredentials(
                access_token=tokens["access_token"],
                refresh_token=credentials.refresh_token,  # Keep existing refresh token
                token_expiry=token_expiry,
                site_url=credentials.site_url,
            )

        except httpx.HTTPError as e:
            logger.error(f"HTTP error during token refresh: {e}")
            raise GSCAuthError(f"Failed to refresh tokens: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during token refresh: {e}")
            raise GSCAuthError(f"Token refresh failed: {e}")

    def _get_service(self, credentials: GSCCredentials):
        """
        Get authenticated Google Search Console API service.

        Args:
            credentials: OAuth credentials

        Returns:
            Google API service object

        Raises:
            GSCAuthError: If authentication fails
        """
        try:
            # Check if token is expired and refresh if needed
            if datetime.utcnow() >= credentials.token_expiry:
                logger.info("Access token expired, refreshing...")
                credentials = self.refresh_tokens(credentials)

            # Create Google OAuth credentials object
            google_creds = Credentials(
                token=credentials.access_token,
                refresh_token=credentials.refresh_token,
                token_uri=self.OAUTH_TOKEN_URL,
                client_id=self.client_id,
                client_secret=self.client_secret,
            )

            # Build the service
            service = build(
                self.API_SERVICE_NAME,
                self.API_VERSION,
                credentials=google_creds,
                cache_discovery=False,
            )

            return service, credentials

        except Exception as e:
            logger.error(f"Failed to create API service: {e}")
            raise GSCAuthError(f"Failed to authenticate with Google API: {e}")

    def list_sites(self, credentials: GSCCredentials) -> List[Dict[str, Any]]:
        """
        List all verified sites/properties for the authenticated user.

        Args:
            credentials: OAuth credentials

        Returns:
            List of site objects with siteUrl and permissionLevel

        Raises:
            GSCAPIError: If API request fails
        """
        try:
            service, updated_creds = self._get_service(credentials)

            logger.info("Fetching verified sites from Google Search Console")
            response = service.sites().list().execute()

            sites = response.get("siteEntry", [])
            logger.info(f"Retrieved {len(sites)} verified sites")

            return sites

        except HttpError as e:
            if e.resp.status == 403:
                raise GSCQuotaError("Google Search Console API quota exceeded")
            logger.error(f"Google API error while listing sites: {e}")
            raise GSCAPIError(f"Failed to list sites: {e}")
        except Exception as e:
            logger.error(f"Unexpected error while listing sites: {e}")
            raise GSCAPIError(f"Failed to list sites: {e}")

    def get_search_analytics(
        self,
        credentials: GSCCredentials,
        site_url: str,
        start_date: date,
        end_date: date,
        dimensions: List[str],
        row_limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        Fetch search analytics data from Google Search Console.

        Args:
            credentials: OAuth credentials
            site_url: The verified property URL
            start_date: Start date for the data range
            end_date: End date for the data range
            dimensions: List of dimensions (query, page, country, device, date)
            row_limit: Maximum number of rows to return (default: 1000, max: 25000)

        Returns:
            List of search analytics rows with clicks, impressions, CTR, position

        Raises:
            GSCAPIError: If API request fails
        """
        try:
            service, updated_creds = self._get_service(credentials)

            logger.info(
                f"Fetching search analytics for {site_url} "
                f"from {start_date} to {end_date}"
            )

            request_body = {
                "startDate": start_date.isoformat(),
                "endDate": end_date.isoformat(),
                "dimensions": dimensions,
                "rowLimit": min(row_limit, 25000),  # API max is 25000
                "startRow": 0,
            }

            response = (
                service.searchanalytics()
                .query(siteUrl=site_url, body=request_body)
                .execute()
            )

            rows = response.get("rows", [])
            logger.info(f"Retrieved {len(rows)} search analytics rows")

            return rows

        except HttpError as e:
            if e.resp.status == 403:
                raise GSCQuotaError("Google Search Console API quota exceeded")
            logger.error(f"Google API error while fetching search analytics: {e}")
            raise GSCAPIError(f"Failed to fetch search analytics: {e}")
        except Exception as e:
            logger.error(f"Unexpected error while fetching search analytics: {e}")
            raise GSCAPIError(f"Failed to fetch search analytics: {e}")

    def get_keyword_rankings(
        self,
        credentials: GSCCredentials,
        site_url: str,
        days: int = 28,
    ) -> List[Dict[str, Any]]:
        """
        Get keyword performance data (queries with clicks, impressions, CTR, position).

        Args:
            credentials: OAuth credentials
            site_url: The verified property URL
            days: Number of days to look back (default: 28)

        Returns:
            List of keyword performance data with:
                - query: The search query
                - clicks: Number of clicks
                - impressions: Number of impressions
                - ctr: Click-through rate
                - position: Average position in search results

        Raises:
            GSCAPIError: If API request fails
        """
        end_date = date.today() - timedelta(days=3)  # Data has 2-3 day delay
        start_date = end_date - timedelta(days=days)

        rows = self.get_search_analytics(
            credentials=credentials,
            site_url=site_url,
            start_date=start_date,
            end_date=end_date,
            dimensions=["query"],
            row_limit=1000,
        )

        # Transform the response to a more user-friendly format
        keywords = []
        for row in rows:
            keywords.append({
                "query": row["keys"][0],  # First dimension is 'query'
                "clicks": row["clicks"],
                "impressions": row["impressions"],
                "ctr": row["ctr"],
                "position": row["position"],
            })

        # Sort by clicks descending
        keywords.sort(key=lambda x: x["clicks"], reverse=True)

        logger.info(f"Retrieved {len(keywords)} keyword rankings")
        return keywords

    def get_page_performance(
        self,
        credentials: GSCCredentials,
        site_url: str,
        days: int = 28,
    ) -> List[Dict[str, Any]]:
        """
        Get page-level performance metrics.

        Args:
            credentials: OAuth credentials
            site_url: The verified property URL
            days: Number of days to look back (default: 28)

        Returns:
            List of page performance data with:
                - page: The page URL
                - clicks: Number of clicks
                - impressions: Number of impressions
                - ctr: Click-through rate
                - position: Average position in search results

        Raises:
            GSCAPIError: If API request fails
        """
        end_date = date.today() - timedelta(days=3)
        start_date = end_date - timedelta(days=days)

        rows = self.get_search_analytics(
            credentials=credentials,
            site_url=site_url,
            start_date=start_date,
            end_date=end_date,
            dimensions=["page"],
            row_limit=1000,
        )

        # Transform the response
        pages = []
        for row in rows:
            pages.append({
                "page": row["keys"][0],  # First dimension is 'page'
                "clicks": row["clicks"],
                "impressions": row["impressions"],
                "ctr": row["ctr"],
                "position": row["position"],
            })

        # Sort by clicks descending
        pages.sort(key=lambda x: x["clicks"], reverse=True)

        logger.info(f"Retrieved {len(pages)} page performance metrics")
        return pages

    def get_daily_stats(
        self,
        credentials: GSCCredentials,
        site_url: str,
        days: int = 28,
    ) -> List[Dict[str, Any]]:
        """
        Get daily aggregated statistics.

        Args:
            credentials: OAuth credentials
            site_url: The verified property URL
            days: Number of days to look back (default: 28)

        Returns:
            List of daily stats with:
                - date: The date
                - clicks: Total clicks for the day
                - impressions: Total impressions for the day
                - ctr: Average CTR for the day
                - position: Average position for the day

        Raises:
            GSCAPIError: If API request fails
        """
        end_date = date.today() - timedelta(days=3)
        start_date = end_date - timedelta(days=days)

        rows = self.get_search_analytics(
            credentials=credentials,
            site_url=site_url,
            start_date=start_date,
            end_date=end_date,
            dimensions=["date"],
            row_limit=1000,
        )

        # Transform the response
        daily_stats = []
        for row in rows:
            daily_stats.append({
                "date": row["keys"][0],  # First dimension is 'date'
                "clicks": row["clicks"],
                "impressions": row["impressions"],
                "ctr": row["ctr"],
                "position": row["position"],
            })

        # Sort by date ascending
        daily_stats.sort(key=lambda x: x["date"])

        logger.info(f"Retrieved {len(daily_stats)} days of statistics")
        return daily_stats

    def get_device_breakdown(
        self,
        credentials: GSCCredentials,
        site_url: str,
        days: int = 28,
    ) -> List[Dict[str, Any]]:
        """
        Get performance breakdown by device type (mobile, desktop, tablet).

        Args:
            credentials: OAuth credentials
            site_url: The verified property URL
            days: Number of days to look back (default: 28)

        Returns:
            List of device performance data

        Raises:
            GSCAPIError: If API request fails
        """
        end_date = date.today() - timedelta(days=3)
        start_date = end_date - timedelta(days=days)

        rows = self.get_search_analytics(
            credentials=credentials,
            site_url=site_url,
            start_date=start_date,
            end_date=end_date,
            dimensions=["device"],
            row_limit=10,  # Only 3 device types typically
        )

        # Transform the response
        devices = []
        for row in rows:
            devices.append({
                "device": row["keys"][0],  # First dimension is 'device'
                "clicks": row["clicks"],
                "impressions": row["impressions"],
                "ctr": row["ctr"],
                "position": row["position"],
            })

        logger.info(f"Retrieved device breakdown with {len(devices)} device types")
        return devices

    def get_country_breakdown(
        self,
        credentials: GSCCredentials,
        site_url: str,
        days: int = 28,
        top_n: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Get performance breakdown by country.

        Args:
            credentials: OAuth credentials
            site_url: The verified property URL
            days: Number of days to look back (default: 28)
            top_n: Number of top countries to return (default: 20)

        Returns:
            List of country performance data

        Raises:
            GSCAPIError: If API request fails
        """
        end_date = date.today() - timedelta(days=3)
        start_date = end_date - timedelta(days=days)

        rows = self.get_search_analytics(
            credentials=credentials,
            site_url=site_url,
            start_date=start_date,
            end_date=end_date,
            dimensions=["country"],
            row_limit=top_n,
        )

        # Transform the response
        countries = []
        for row in rows:
            countries.append({
                "country": row["keys"][0],  # First dimension is 'country'
                "clicks": row["clicks"],
                "impressions": row["impressions"],
                "ctr": row["ctr"],
                "position": row["position"],
            })

        # Sort by clicks descending
        countries.sort(key=lambda x: x["clicks"], reverse=True)

        logger.info(f"Retrieved top {len(countries)} countries")
        return countries


# Factory function for easy instantiation
def create_gsc_adapter(
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    redirect_uri: Optional[str] = None,
) -> GSCAdapter:
    """
    Create a Google Search Console adapter instance.

    Args:
        client_id: Google OAuth client ID (defaults to settings)
        client_secret: Google OAuth client secret (defaults to settings)
        redirect_uri: OAuth redirect URI (defaults to settings)

    Returns:
        GSCAdapter instance
    """
    return GSCAdapter(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
    )
