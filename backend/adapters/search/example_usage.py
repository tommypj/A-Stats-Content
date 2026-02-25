"""
Example usage of Google Search Console OAuth adapter.

This file demonstrates how to integrate the GSCAdapter for fetching
SEO analytics data from Google Search Console.
"""

import asyncio
from datetime import date, timedelta
from adapters.search import (
    GSCAdapter,
    GSCCredentials,
    GSCAuthError,
    GSCAPIError,
    create_gsc_adapter,
)


async def example_oauth_flow():
    """
    Example: Complete OAuth 2.0 flow for Google Search Console.

    This demonstrates the typical OAuth flow:
    1. Generate authorization URL
    2. User authorizes and returns with code
    3. Exchange code for tokens
    4. Use tokens to access API
    """
    print("=" * 60)
    print("OAuth 2.0 Flow Example")
    print("=" * 60)

    # Create adapter instance
    adapter = create_gsc_adapter(
        client_id="your_client_id_here",
        client_secret="your_client_secret_here",
        redirect_uri="http://localhost:8000/api/v1/gsc/callback",
    )

    # Step 1: Generate authorization URL
    state = "random_state_string_123"  # Use a secure random string in production
    auth_url = adapter.get_authorization_url(state)

    print(f"\n1. Redirect user to: {auth_url}")
    print("\n2. User authorizes and is redirected back with 'code' parameter")

    # Step 2: Exchange authorization code for tokens
    # In a real application, this code comes from the OAuth callback
    authorization_code = "example_auth_code_from_callback"

    try:
        credentials = adapter.exchange_code(authorization_code)
        print(f"\n3. Successfully obtained OAuth tokens")
        print(f"   Access Token: {credentials.access_token[:20]}...")
        print(f"   Refresh Token: {credentials.refresh_token[:20]}...")
        print(f"   Expires: {credentials.token_expiry}")

        # Store these credentials in your database
        # Example: user.gsc_credentials = credentials.to_dict()

    except GSCAuthError as e:
        print(f"\n3. Authorization failed: {e}")
        return


async def example_list_sites():
    """
    Example: List all verified sites/properties.

    This should be called after OAuth to let the user select
    which site they want to fetch analytics for.
    """
    print("\n" + "=" * 60)
    print("List Verified Sites Example")
    print("=" * 60)

    adapter = create_gsc_adapter()

    # Load credentials from database
    # In a real app: credentials = GSCCredentials.from_dict(user.gsc_credentials)
    credentials = GSCCredentials(
        access_token="stored_access_token",
        refresh_token="stored_refresh_token",
        token_expiry="2024-12-31T23:59:59",
        site_url="",  # Not set yet
    )

    try:
        sites = adapter.list_sites(credentials)

        print(f"\nFound {len(sites)} verified sites:")
        for i, site in enumerate(sites, 1):
            print(f"{i}. {site['siteUrl']} ({site['permissionLevel']})")

        # Let user select a site and update credentials
        # selected_site = sites[0]['siteUrl']
        # credentials.site_url = selected_site
        # Update database with selected site

    except GSCAPIError as e:
        print(f"\nFailed to list sites: {e}")


async def example_fetch_keyword_rankings():
    """
    Example: Fetch keyword rankings for the last 28 days.

    This is one of the most common use cases - getting keyword
    performance data to show in analytics dashboards.
    """
    print("\n" + "=" * 60)
    print("Keyword Rankings Example")
    print("=" * 60)

    adapter = create_gsc_adapter()

    # Load credentials from database with selected site
    credentials = GSCCredentials(
        access_token="stored_access_token",
        refresh_token="stored_refresh_token",
        token_expiry="2024-12-31T23:59:59",
        site_url="https://example.com",
    )

    try:
        keywords = adapter.get_keyword_rankings(
            credentials=credentials,
            site_url=credentials.site_url,
            days=28,
        )

        print(f"\nTop {min(10, len(keywords))} performing keywords:")
        print(f"{'Keyword':<40} {'Clicks':<10} {'Impressions':<15} {'CTR':<10} {'Position':<10}")
        print("-" * 90)

        for keyword in keywords[:10]:
            print(
                f"{keyword['query']:<40} "
                f"{keyword['clicks']:<10} "
                f"{keyword['impressions']:<15} "
                f"{keyword['ctr']:<10.2%} "
                f"{keyword['position']:<10.1f}"
            )

    except GSCAPIError as e:
        print(f"\nFailed to fetch keyword rankings: {e}")


async def example_fetch_page_performance():
    """
    Example: Fetch page-level performance metrics.

    Useful for identifying which pages are driving the most traffic
    and which ones need optimization.
    """
    print("\n" + "=" * 60)
    print("Page Performance Example")
    print("=" * 60)

    adapter = create_gsc_adapter()

    credentials = GSCCredentials(
        access_token="stored_access_token",
        refresh_token="stored_refresh_token",
        token_expiry="2024-12-31T23:59:59",
        site_url="https://example.com",
    )

    try:
        pages = adapter.get_page_performance(
            credentials=credentials,
            site_url=credentials.site_url,
            days=28,
        )

        print(f"\nTop {min(10, len(pages))} performing pages:")
        print(f"{'Page URL':<60} {'Clicks':<10} {'Position':<10}")
        print("-" * 85)

        for page in pages[:10]:
            # Truncate long URLs for display
            url = page['page']
            if len(url) > 57:
                url = url[:54] + "..."
            print(
                f"{url:<60} "
                f"{page['clicks']:<10} "
                f"{page['position']:<10.1f}"
            )

    except GSCAPIError as e:
        print(f"\nFailed to fetch page performance: {e}")


async def example_fetch_daily_stats():
    """
    Example: Fetch daily aggregated statistics.

    Perfect for creating time-series charts showing traffic trends.
    """
    print("\n" + "=" * 60)
    print("Daily Statistics Example")
    print("=" * 60)

    adapter = create_gsc_adapter()

    credentials = GSCCredentials(
        access_token="stored_access_token",
        refresh_token="stored_refresh_token",
        token_expiry="2024-12-31T23:59:59",
        site_url="https://example.com",
    )

    try:
        daily_stats = adapter.get_daily_stats(
            credentials=credentials,
            site_url=credentials.site_url,
            days=7,  # Last 7 days
        )

        print(f"\nLast {len(daily_stats)} days of statistics:")
        print(f"{'Date':<15} {'Clicks':<10} {'Impressions':<15} {'CTR':<10} {'Position':<10}")
        print("-" * 65)

        for day in daily_stats:
            print(
                f"{day['date']:<15} "
                f"{day['clicks']:<10} "
                f"{day['impressions']:<15} "
                f"{day['ctr']:<10.2%} "
                f"{day['position']:<10.1f}"
            )

        # Calculate totals
        total_clicks = sum(d['clicks'] for d in daily_stats)
        total_impressions = sum(d['impressions'] for d in daily_stats)
        avg_ctr = total_clicks / total_impressions if total_impressions > 0 else 0
        avg_position = sum(d['position'] for d in daily_stats) / len(daily_stats)

        print("-" * 65)
        print(
            f"{'TOTALS/AVG':<15} "
            f"{total_clicks:<10} "
            f"{total_impressions:<15} "
            f"{avg_ctr:<10.2%} "
            f"{avg_position:<10.1f}"
        )

    except GSCAPIError as e:
        print(f"\nFailed to fetch daily stats: {e}")


async def example_device_and_country_breakdown():
    """
    Example: Fetch device and country breakdown.

    Useful for understanding your audience and optimizing for
    specific devices or geographic regions.
    """
    print("\n" + "=" * 60)
    print("Device & Country Breakdown Example")
    print("=" * 60)

    adapter = create_gsc_adapter()

    credentials = GSCCredentials(
        access_token="stored_access_token",
        refresh_token="stored_refresh_token",
        token_expiry="2024-12-31T23:59:59",
        site_url="https://example.com",
    )

    try:
        # Device breakdown
        devices = adapter.get_device_breakdown(
            credentials=credentials,
            site_url=credentials.site_url,
            days=28,
        )

        print("\nPerformance by Device:")
        print(f"{'Device':<15} {'Clicks':<10} {'Impressions':<15} {'CTR':<10}")
        print("-" * 55)

        for device in devices:
            print(
                f"{device['device']:<15} "
                f"{device['clicks']:<10} "
                f"{device['impressions']:<15} "
                f"{device['ctr']:<10.2%}"
            )

        # Country breakdown
        countries = adapter.get_country_breakdown(
            credentials=credentials,
            site_url=credentials.site_url,
            days=28,
            top_n=10,
        )

        print(f"\nTop {len(countries)} Countries:")
        print(f"{'Country':<15} {'Clicks':<10} {'Impressions':<15} {'Position':<10}")
        print("-" * 55)

        for country in countries:
            print(
                f"{country['country']:<15} "
                f"{country['clicks']:<10} "
                f"{country['impressions']:<15} "
                f"{country['position']:<10.1f}"
            )

    except GSCAPIError as e:
        print(f"\nFailed to fetch breakdowns: {e}")


async def example_custom_search_analytics():
    """
    Example: Custom search analytics query with multiple dimensions.

    Demonstrates the low-level API for advanced queries combining
    multiple dimensions like query + device or page + country.
    """
    print("\n" + "=" * 60)
    print("Custom Search Analytics Example")
    print("=" * 60)

    adapter = create_gsc_adapter()

    credentials = GSCCredentials(
        access_token="stored_access_token",
        refresh_token="stored_refresh_token",
        token_expiry="2024-12-31T23:59:59",
        site_url="https://example.com",
    )

    try:
        # Query for keywords by device type
        end_date = date.today() - timedelta(days=3)
        start_date = end_date - timedelta(days=28)

        rows = adapter.get_search_analytics(
            credentials=credentials,
            site_url=credentials.site_url,
            start_date=start_date,
            end_date=end_date,
            dimensions=["query", "device"],  # Multiple dimensions
            row_limit=100,
        )

        print(f"\nTop queries by device (showing first 10):")
        print(f"{'Query':<30} {'Device':<10} {'Clicks':<10} {'Position':<10}")
        print("-" * 65)

        for row in rows[:10]:
            query = row['keys'][0]  # First dimension
            device = row['keys'][1]  # Second dimension

            if len(query) > 27:
                query = query[:24] + "..."

            print(
                f"{query:<30} "
                f"{device:<10} "
                f"{row['clicks']:<10} "
                f"{row['position']:<10.1f}"
            )

    except GSCAPIError as e:
        print(f"\nFailed to fetch custom analytics: {e}")


async def example_token_refresh():
    """
    Example: Automatic token refresh handling.

    The adapter automatically refreshes expired tokens, but you can
    also manually refresh them if needed.
    """
    print("\n" + "=" * 60)
    print("Token Refresh Example")
    print("=" * 60)

    adapter = create_gsc_adapter()

    # Simulate expired credentials
    from datetime import datetime, timezone
    credentials = GSCCredentials(
        access_token="expired_token",
        refresh_token="valid_refresh_token",
        token_expiry=datetime.now(timezone.utc) - timedelta(hours=1),  # Expired
        site_url="https://example.com",
    )

    print("\nCredentials are expired!")
    print(f"Token expiry: {credentials.token_expiry}")

    try:
        # The adapter will automatically refresh when making API calls
        # Or you can manually refresh:
        new_credentials = adapter.refresh_tokens(credentials)

        print(f"\nTokens refreshed successfully!")
        print(f"New expiry: {new_credentials.token_expiry}")
        print(f"New access token: {new_credentials.access_token[:20]}...")

        # Update database with new credentials
        # user.gsc_credentials = new_credentials.to_dict()

    except GSCAuthError as e:
        print(f"\nFailed to refresh tokens: {e}")
        print("User needs to re-authenticate via OAuth flow")


# Main execution
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Google Search Console Adapter - Usage Examples")
    print("=" * 60)
    print("\nNOTE: These examples use placeholder credentials.")
    print("In production, replace with real OAuth credentials and API calls.")
    print("=" * 60)

    # Run all examples
    # Note: Most will fail without real credentials, but they demonstrate usage
    asyncio.run(example_oauth_flow())
    # asyncio.run(example_list_sites())
    # asyncio.run(example_fetch_keyword_rankings())
    # asyncio.run(example_fetch_page_performance())
    # asyncio.run(example_fetch_daily_stats())
    # asyncio.run(example_device_and_country_breakdown())
    # asyncio.run(example_custom_search_analytics())
    # asyncio.run(example_token_refresh())
