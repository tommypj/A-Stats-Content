# Admin Platform Analytics API - Phase 9

Comprehensive admin analytics API for monitoring platform health, user activity, content generation, revenue, and system metrics.

## Overview

The Admin Analytics API provides 5 main endpoints for platform administrators to monitor and analyze all aspects of the A-Stats platform.

**Base URL:** `/admin/analytics`
**Authentication:** Admin role required (`get_current_admin_user` dependency)
**Tags:** `["Admin - Analytics"]`

---

## Endpoints

### 1. GET `/admin/analytics/dashboard`

Main admin dashboard with comprehensive platform statistics.

**Response Schema:** `DashboardStatsResponse`

**Returns:**
- **User Stats:**
  - Total users
  - New users this week/month
  - Active users this week
  - Verified/pending users

- **Content Stats:**
  - Total articles, outlines, images
  - Content created this month

- **Subscription Stats:**
  - Users per tier (free, starter, professional, enterprise)
  - Active paid subscriptions
  - Cancelled subscriptions

- **Revenue Stats:**
  - Monthly Recurring Revenue (MRR)
  - Annual Recurring Revenue (ARR)
  - Revenue this month

- **Platform Usage Trends:**
  - 7-day active user trend
  - 30-day active user trend

**Example Response:**
```json
{
  "users": {
    "total_users": 1250,
    "new_users_this_week": 42,
    "new_users_this_month": 168,
    "active_users_this_week": 523,
    "verified_users": 1100,
    "pending_users": 150
  },
  "content": {
    "total_articles": 3420,
    "total_outlines": 4100,
    "total_images": 8640,
    "articles_this_month": 320,
    "outlines_this_month": 410,
    "images_this_month": 890
  },
  "subscriptions": {
    "free_tier": 800,
    "starter_tier": 250,
    "professional_tier": 150,
    "enterprise_tier": 50,
    "active_subscriptions": 450,
    "cancelled_subscriptions": 25
  },
  "revenue": {
    "monthly_recurring_revenue": 27950.0,
    "annual_recurring_revenue": 335400.0,
    "revenue_this_month": 27950.0
  },
  "platform_usage_7d": [
    {"date": "2026-02-14", "value": 489},
    {"date": "2026-02-15", "value": 512},
    ...
  ],
  "platform_usage_30d": [...]
}
```

---

### 2. GET `/admin/analytics/users`

Detailed user analytics including signups, retention, and conversion metrics.

**Response Schema:** `UserAnalyticsResponse`

**Returns:**
- **Signup Trends:** Daily signups for past 30 days (with verification count)
- **Retention Metrics:**
  - Day 1 retention (% users active after 1 day)
  - Day 7 retention
  - Day 30 retention
- **Conversion Metrics:**
  - Free to Starter conversion rate
  - Free to Professional conversion rate
  - Free to Enterprise conversion rate
  - Overall conversion rate (free to any paid tier)
- **Geographic Distribution:** Placeholder (requires IP geolocation data)

**Example Response:**
```json
{
  "signup_trends": [
    {"date": "2026-01-21", "signups": 12, "verified": 8},
    {"date": "2026-01-22", "signups": 15, "verified": 11},
    ...
  ],
  "retention_metrics": {
    "day_1_retention": 68.5,
    "day_7_retention": 45.2,
    "day_30_retention": 32.8
  },
  "conversion_metrics": {
    "free_to_starter": 20.0,
    "free_to_professional": 12.0,
    "free_to_enterprise": 4.0,
    "overall_conversion_rate": 36.0
  },
  "geographic_distribution": [],
  "total_users": 1250
}
```

**Note:** This endpoint is resource-intensive. Consider implementing Redis caching for production.

---

### 3. GET `/admin/analytics/content`

Detailed content analytics including creation trends and top users.

**Response Schema:** `ContentAnalyticsResponse`

**Returns:**
- **Content Trends:** Daily articles/outlines/images created (past 30 days)
- **Top Users:** Top 10 users by content created (includes all content types)
- **Status Breakdowns:**
  - Articles by status (draft, completed, published, failed)
  - Outlines by status
- **Totals:** Total counts for articles, outlines, images

**Example Response:**
```json
{
  "content_trends": [
    {"date": "2026-01-21", "articles": 28, "outlines": 32, "images": 65},
    {"date": "2026-01-22", "articles": 31, "outlines": 35, "images": 72},
    ...
  ],
  "top_users": [
    {
      "user_id": "uuid-here",
      "email": "user@example.com",
      "name": "John Doe",
      "articles_count": 45,
      "outlines_count": 52,
      "images_count": 120,
      "total_content": 217,
      "subscription_tier": "professional"
    },
    ...
  ],
  "article_status_breakdown": [
    {"status": "draft", "count": 1200, "percentage": 35.08},
    {"status": "completed", "count": 1500, "percentage": 43.86},
    {"status": "published", "count": 720, "percentage": 21.05}
  ],
  "outline_status_breakdown": [...],
  "total_articles": 3420,
  "total_outlines": 4100,
  "total_images": 8640
}
```

**Note:** This endpoint is resource-intensive. Consider implementing Redis caching for production.

---

### 4. GET `/admin/analytics/revenue`

Detailed revenue analytics and subscription insights.

**Response Schema:** `RevenueAnalyticsResponse`

**Returns:**
- **Monthly Revenue:** Revenue for past 12 months (with new/churned subscriptions)
- **Subscription Distribution:** Pie chart data (count, percentage, monthly value per tier)
- **Churn Indicators:** Churn data for past 6 months (count + rate)
- **Current MRR/ARR:** Current monthly and annual recurring revenue
- **Revenue Growth Rate:** Month-over-month growth percentage

**Example Response:**
```json
{
  "monthly_revenue": [
    {
      "month": "2025-03",
      "revenue": 18500.0,
      "new_subscriptions": 45,
      "churned_subscriptions": 8
    },
    {"month": "2025-04", "revenue": 21300.0, ...},
    ...
  ],
  "subscription_distribution": [
    {"tier": "free", "count": 800, "percentage": 64.0, "monthly_value": 0.0},
    {"tier": "starter", "count": 250, "percentage": 20.0, "monthly_value": 7250.0},
    {"tier": "professional", "count": 150, "percentage": 12.0, "monthly_value": 11850.0},
    {"tier": "enterprise", "count": 50, "percentage": 4.0, "monthly_value": 9950.0}
  ],
  "churn_indicators": [
    {"month": "2025-09", "churned_count": 5, "churn_rate": 1.11},
    {"month": "2025-10", "churned_count": 8, "churn_rate": 1.75},
    ...
  ],
  "current_mrr": 27950.0,
  "current_arr": 335400.0,
  "revenue_growth_rate": 8.45
}
```

**Pricing Tiers:**
- **Free:** $0/month
- **Starter:** $29/month
- **Professional:** $79/month
- **Enterprise:** $199/month

**Note:** Revenue is estimated based on subscription tier counts. For accurate revenue, integrate with LemonSqueezy webhook data.

---

### 5. GET `/admin/analytics/system`

System health metrics and background job status.

**Response Schema:** `SystemHealthResponse`

**Returns:**
- **Table Stats:** Record counts per database table
- **Storage Stats:** Total image storage usage
- **Error Rates:** Placeholder for error logging
- **Background Jobs:**
  - Social posts (pending, failed)
  - Knowledge processing (pending, failed)
- **Database Size:** Placeholder for PostgreSQL size query

**Example Response:**
```json
{
  "table_stats": [
    {"table_name": "users", "record_count": 1250},
    {"table_name": "articles", "record_count": 3420},
    {"table_name": "outlines", "record_count": 4100},
    {"table_name": "generated_images", "record_count": 8640},
    {"table_name": "scheduled_posts", "record_count": 342},
    {"table_name": "knowledge_sources", "record_count": 156}
  ],
  "storage_stats": {
    "total_images": 8640,
    "total_storage_mb": 2109.38,
    "average_image_size_kb": 250.0
  },
  "recent_error_rates": [],
  "background_jobs": [
    {
      "job_type": "social_posts",
      "pending_count": 23,
      "failed_count": 4
    },
    {
      "job_type": "knowledge_processing",
      "pending_count": 5,
      "failed_count": 1
    }
  ],
  "database_size_mb": 0.0
}
```

---

## Authentication

All endpoints require admin authentication. The `get_current_admin_user` dependency checks:
1. Valid JWT token (via `get_current_user`)
2. User has `admin` or `super_admin` role
3. User account is active

**Error Response (403 Forbidden):**
```json
{
  "detail": "Admin access required"
}
```

---

## Performance Considerations

### Heavy Queries

The following endpoints perform complex aggregations and should be cached in production:

1. **`/dashboard`** - Multiple COUNT queries across all tables
2. **`/users`** - Retention calculations with date-based filters
3. **`/content`** - Top users query with joins and aggregations

### Recommended Caching Strategy

```python
from functools import lru_cache
from datetime import timedelta

# Redis cache with 5-minute TTL
@cache(ttl=300)
async def get_dashboard_stats_cached():
    # ...
```

### Query Optimization

Current implementation uses:
- SQLAlchemy async queries
- Index-aware filtering (all date columns are indexed)
- Aggregation at database level (COUNT, GROUP BY)

**Future improvements:**
- Add Redis caching layer
- Create materialized views for daily aggregations
- Implement background jobs to pre-compute heavy metrics

---

## Database Schema Requirements

### Required Models

All endpoints depend on these SQLAlchemy models:

- `User` - User accounts with subscription and usage tracking
- `Article` - Content articles
- `Outline` - Content outlines
- `GeneratedImage` - AI-generated images
- `ScheduledPost` - Social media posts
- `KnowledgeSource` - Knowledge vault documents

### Required Indexes

Ensure these indexes exist for optimal performance:

```sql
-- Users
CREATE INDEX ix_users_created_at ON users(created_at);
CREATE INDEX ix_users_last_login ON users(last_login);
CREATE INDEX ix_users_subscription ON users(subscription_tier, subscription_status);

-- Content
CREATE INDEX ix_articles_created_at ON articles(created_at);
CREATE INDEX ix_articles_status ON articles(status);
CREATE INDEX ix_articles_user_id ON articles(user_id);

-- Similar for outlines, images, etc.
```

---

## Testing

### Manual Testing

```bash
# Get admin JWT token
TOKEN=$(curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}' \
  | jq -r '.access_token')

# Test dashboard endpoint
curl -X GET http://localhost:8000/admin/analytics/dashboard \
  -H "Authorization: Bearer $TOKEN"

# Test user analytics
curl -X GET http://localhost:8000/admin/analytics/users \
  -H "Authorization: Bearer $TOKEN"

# Test content analytics
curl -X GET http://localhost:8000/admin/analytics/content \
  -H "Authorization: Bearer $TOKEN"

# Test revenue analytics
curl -X GET http://localhost:8000/admin/analytics/revenue \
  -H "Authorization: Bearer $TOKEN"

# Test system health
curl -X GET http://localhost:8000/admin/analytics/system \
  -H "Authorization: Bearer $TOKEN"
```

### Integration Tests

See `backend/tests/integration/test_admin_analytics.py` for comprehensive test coverage.

---

## Security

### Authorization Checks

1. **JWT Token Validation:** All endpoints require valid access token
2. **Role Verification:** User must have `admin` or `super_admin` role
3. **Active Account:** Suspended or deleted admins cannot access endpoints

### Rate Limiting

Consider implementing rate limiting for production:

```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@router.get("/dashboard")
@limiter.limit("10/minute")
async def get_dashboard_stats(...):
    # ...
```

### Audit Logging

Recommended: Log all admin analytics access for compliance:

```python
await audit_log.create(
    admin_user_id=current_admin.id,
    action="VIEW_DASHBOARD",
    target_type="admin_analytics",
    ip_address=request.client.host,
)
```

---

## Future Enhancements

### 1. Real-time Updates

Implement WebSocket endpoint for live dashboard updates:

```python
@router.websocket("/admin/analytics/live")
async def analytics_websocket(websocket: WebSocket):
    # Stream real-time metrics
```

### 2. Custom Date Ranges

Add query parameters for custom date ranges:

```python
@router.get("/users")
async def get_user_analytics(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    ...
):
    # ...
```

### 3. Export Functionality

Add CSV/PDF export for all analytics:

```python
@router.get("/dashboard/export")
async def export_dashboard(format: str = "csv"):
    # Generate CSV or PDF
```

### 4. Geographic Distribution

Implement IP geolocation tracking:

```python
# Add to User model
country_code: str = mapped_column(String(2), nullable=True)

# Update signup endpoint to capture IP and resolve country
```

### 5. Error Rate Tracking

Create error logging table:

```python
class ErrorLog(Base):
    timestamp: datetime
    error_type: str
    endpoint: str
    user_id: Optional[str]
```

### 6. Database Size Tracking

Add PostgreSQL-specific query:

```python
db_size_result = await db.execute(text("""
    SELECT pg_database_size(current_database()) / 1024 / 1024 as size_mb
"""))
database_size_mb = db_size_result.scalar()
```

---

## Architecture

### Clean Architecture Compliance

```
┌─────────────────────────────────────────┐
│  API Layer (FastAPI Routes)            │
│  backend/api/routes/admin_analytics.py  │
├─────────────────────────────────────────┤
│  Schemas (Pydantic Models)             │
│  backend/api/schemas/admin.py           │
├─────────────────────────────────────────┤
│  Dependencies (Auth)                    │
│  backend/api/dependencies.py            │
├─────────────────────────────────────────┤
│  Database Models (SQLAlchemy)          │
│  backend/infrastructure/database/models │
└─────────────────────────────────────────┘
```

**No business logic in routes** - All queries are simple aggregations using SQLAlchemy ORM. For complex business logic, create a service layer:

```python
# backend/services/admin_analytics_service.py
class AdminAnalyticsService:
    async def calculate_retention(self, ...):
        # Complex retention logic
```

---

## Related Documentation

- [User Management API](./admin_users.py) - User CRUD operations
- [Billing Integration](./billing.py) - LemonSqueezy subscription handling
- [Authentication](./auth.py) - JWT token service
- [Database Models](../../infrastructure/database/models/)

---

## Support

For questions or issues with the Admin Analytics API, contact the development team or file an issue in the project repository.

**Last Updated:** 2026-02-20
**API Version:** 1.0
**Phase:** 9 - Admin Platform Analytics
