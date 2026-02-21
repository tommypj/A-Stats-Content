# Backend Test Suite

Comprehensive test coverage for the A-Stats Online analytics module.

## Test Structure

```
backend/tests/
├── conftest.py                      # Shared fixtures and configuration
├── BILLING_TESTS.md                 # Billing test documentation
├── KNOWLEDGE_TESTS.md               # Knowledge Vault test documentation
├── unit/                            # Unit tests (isolated component testing)
│   ├── test_gsc_adapter.py          # Google Search Console adapter tests
│   ├── test_image_storage.py        # Image storage adapter tests
│   ├── test_wordpress_adapter.py    # WordPress adapter tests
│   ├── test_lemonsqueezy_adapter.py # LemonSqueezy billing adapter tests (16)
│   ├── test_chroma_adapter.py       # ChromaDB vector database tests (16)
│   ├── test_document_processor.py   # Document processing tests (20)
│   ├── test_embedding_service.py    # Embedding generation tests (15)
│   └── test_knowledge_service.py    # Knowledge service tests (14)
└── integration/                     # Integration tests (API endpoint testing)
    ├── test_analytics_api.py        # Analytics API endpoints
    ├── test_images_api.py           # Images API endpoints
    ├── test_billing_api.py          # Billing API endpoints (~40)
    └── test_knowledge_api.py        # Knowledge Vault API endpoints (~50)
```

## Running Tests

### Run All Tests
```bash
cd backend
python -m pytest tests/ -v
```

### Run Unit Tests Only
```bash
python -m pytest tests/unit/ -v
```

### Run Integration Tests Only
```bash
python -m pytest tests/integration/ -v
```

### Run Specific Test File
```bash
python -m pytest tests/unit/test_gsc_adapter.py -v
```

### Run Specific Test Class
```bash
python -m pytest tests/unit/test_gsc_adapter.py::TestGSCAdapter -v
```

### Run Specific Test
```bash
python -m pytest tests/unit/test_gsc_adapter.py::TestGSCAdapter::test_get_authorization_url -v
```

### Show Coverage Report
```bash
python -m pytest tests/ --cov=adapters --cov=api --cov=core --cov-report=html
```

## Test Coverage

### LemonSqueezy Billing Adapter (Unit Tests) 📝

**File:** `tests/unit/test_lemonsqueezy_adapter.py`

Comprehensive unit tests for LemonSqueezy billing integration (16 tests total):

#### Core Functionality (4 tests)
- 📝 `test_adapter_initialization` - Validates adapter initialization with credentials
- 📝 `test_adapter_initialization_with_defaults` - Tests initialization from settings
- 📝 `test_get_checkout_url` - Generate checkout URL with parameters
- 📝 `test_create_lemonsqueezy_adapter_factory` - Tests factory function

#### Customer & Subscription Management (6 tests)
- 📝 `test_get_customer_success` - Mock successful customer fetch
- 📝 `test_get_customer_not_found` - Mock 404 response for missing customer
- 📝 `test_get_subscription_success` - Mock successful subscription fetch
- 📝 `test_get_subscription_not_found` - Mock 404 response for missing subscription
- 📝 `test_get_customer_portal_url` - Mock portal URL generation
- 📝 `test_cancel_subscription_success` - Mock successful cancellation

#### Subscription Operations (3 tests)
- 📝 `test_cancel_subscription_already_cancelled` - Handle already cancelled subscription
- 📝 `test_pause_subscription_success` - Mock successful pause
- 📝 `test_resume_subscription_success` - Mock successful resume

#### Webhook Processing (5 tests)
- 📝 `test_verify_webhook_signature_valid` - Validate correct HMAC signature
- 📝 `test_verify_webhook_signature_invalid` - Reject invalid signature
- 📝 `test_parse_webhook_subscription_created` - Parse subscription_created event
- 📝 `test_parse_webhook_subscription_cancelled` - Parse subscription_cancelled event
- 📝 `test_parse_webhook_payment_failed` - Parse payment_failed event

#### Error Handling (2 tests)
- 📝 `test_api_error_handling` - Handle network errors gracefully
- 📝 `test_api_authentication_error` - Handle 401 authentication errors

**Error Classes Covered:**
- 📝 LemonSqueezyError - General API errors
- 📝 LemonSqueezyAuthError - Authentication failures
- 📝 LemonSqueezyWebhookError - Webhook signature validation errors

> **Note:** Tests will skip until adapter is implemented. See [BILLING_TESTS.md](BILLING_TESTS.md) for detailed documentation.

---

### Billing API (Integration Tests) 📝

**File:** `tests/integration/test_billing_api.py`

Complete integration test coverage for all billing endpoints (~40 tests):

#### Endpoint Coverage (8 test classes)

1. **TestPricingEndpoint** (2 tests)
   - 📝 `test_get_pricing_returns_all_plans` - Returns 4 subscription plans
   - 📝 `test_pricing_no_auth_required` - Works without authentication

2. **TestSubscriptionEndpoint** (3 tests)
   - 📝 `test_get_subscription_authenticated` - Returns subscription data with auth
   - 📝 `test_get_subscription_unauthorized` - Returns 401 without auth
   - 📝 `test_subscription_free_user` - Free user shows correct tier/status

3. **TestCheckoutEndpoint** (3 tests)
   - 📝 `test_checkout_generates_url` - Generates valid checkout URL
   - 📝 `test_checkout_invalid_plan` - Returns 400 for invalid plan
   - 📝 `test_checkout_invalid_billing_cycle` - Returns 400 for invalid cycle

4. **TestCustomerPortalEndpoint** (2 tests)
   - 📝 `test_portal_with_customer_id` - Returns portal URL for subscribed user
   - 📝 `test_portal_without_customer_id` - Returns 404 for free user

5. **TestCancelEndpoint** (2 tests)
   - 📝 `test_cancel_active_subscription` - Successfully cancels active subscription
   - 📝 `test_cancel_no_subscription` - Returns 404 for users without subscription

6. **TestWebhookEndpoint** (5 tests)
   - 📝 `test_webhook_valid_signature` - Processes events with valid signature
   - 📝 `test_webhook_invalid_signature` - Rejects invalid signatures (401)
   - 📝 `test_webhook_subscription_created` - Updates user on subscription creation
   - 📝 `test_webhook_subscription_cancelled` - Updates status on cancellation
   - 📝 `test_webhook_payment_failed` - Sets status to past_due on failure

7. **TestPauseResumeEndpoints** (2 tests)
   - 📝 `test_pause_subscription` - Pauses active subscription
   - 📝 `test_resume_subscription` - Resumes paused subscription

**Billing Fixtures Added to conftest.py:**
- ✅ `free_user` - User with free tier and no subscription
- ✅ `subscribed_user` - User with professional tier and active subscription
- ✅ `valid_webhook_payload` - Sample subscription_created webhook payload
- ✅ `valid_webhook_signature` - Generate valid HMAC-SHA256 signature
- ✅ `mock_lemonsqueezy_api` - Mock httpx client for LemonSqueezy API

> **Note:** Tests will skip until billing routes are implemented. See [BILLING_TESTS.md](BILLING_TESTS.md) for detailed documentation.

---

### Knowledge Vault Tests (Phase 7 - RAG) 📝

**Comprehensive test suite for the Knowledge Vault module with ChromaDB, document processing, embeddings, and RAG.**

See **[KNOWLEDGE_TESTS.md](KNOWLEDGE_TESTS.md)** for complete documentation.

#### Unit Tests (4 files, 65 tests)

**1. ChromaDB Adapter** (`test_chroma_adapter.py`) - 16 tests
- 📝 Collection creation and management
- 📝 Document addition with metadata
- 📝 Vector query operations with filtering
- 📝 Deletion by ID and by source
- 📝 Collection statistics
- 📝 Connection error handling
- 📝 Input validation

**2. Document Processor** (`test_document_processor.py`) - 20 tests
- 📝 File type detection (PDF, TXT, DOCX, MD, HTML)
- 📝 Text extraction from all formats
- 📝 Text chunking with overlap
- 📝 Sentence boundary preservation
- 📝 Empty document handling
- 📝 Encoding error handling
- 📝 Complete processing workflow

**3. Embedding Service** (`test_embedding_service.py`) - 15 tests
- 📝 OpenAI embedding generation
- 📝 Batch processing with size limits
- 📝 Mock mode (no API calls)
- 📝 Dimension consistency validation
- 📝 Error handling and retries
- 📝 Deterministic mock embeddings
- 📝 Cosine similarity utilities

**4. Knowledge Service** (`test_knowledge_service.py`) - 14 tests
- 📝 Document processing workflow
- 📝 Status updates (pending → completed)
- 📝 Error handling with failure messages
- 📝 Query operations with filtering
- 📝 Source deletion with authorization
- 📝 Statistics and analytics
- 📝 Query logging

#### Integration Tests (1 file, 50+ tests)

**Knowledge API** (`test_knowledge_api.py`) - ~50 tests

**TestUploadEndpoint** (7 tests)
- 📝 Upload PDF, TXT, Markdown
- 📝 Reject unsupported file types
- 📝 Enforce file size limits (20MB)
- 📝 Require authentication
- 📝 Validate empty files

**TestSourcesEndpoint** (9 tests)
- 📝 List sources with pagination
- 📝 Search/filter by filename
- 📝 Filter by processing status
- 📝 Get source details
- 📝 Delete sources with authorization
- 📝 Prevent cross-user access

**TestQueryEndpoint** (8 tests)
- 📝 Semantic search with embeddings
- 📝 Source filtering (multi-source queries)
- 📝 Handle no results gracefully
- 📝 Empty knowledge base handling
- 📝 Validation (empty query, invalid params)
- 📝 Include source metadata and relevance
- 📝 Respect n_results limits

**TestStatsEndpoint** (4 tests)
- 📝 Overall statistics
- 📝 Processing status breakdown
- 📝 Recent queries tracking
- 📝 Empty knowledge base stats

**TestProcessingStatus** (3 tests)
- 📝 Check pending documents
- 📝 Check completed documents
- 📝 Check failed documents with errors

**TestRateLimiting** (2 tests)
- 📝 Upload rate limits (10/minute)
- 📝 Query rate limits (20/minute)

#### Knowledge Fixtures (conftest.py)

**Data Fixtures:**
- ✅ `sample_pdf` - Minimal valid PDF with magic bytes
- ✅ `sample_txt` - Plain text with therapeutic content

**Database Fixtures:**
- ✅ `test_source` - KnowledgeSource in PENDING status
- ✅ `processed_source` - Completed source with 25 chunks
- ✅ `pending_source` - Source in PENDING status
- ✅ `failed_source` - Source in FAILED status with error
- ✅ `test_sources` - 5 sources with mixed statuses
- ✅ `processed_sources` - 3 completed sources

**Mock Fixtures:**
- ✅ `mock_chroma_client` - Mocked ChromaDB client
- ✅ `mock_embedding_service` - Deterministic embeddings

**User Fixtures:**
- ✅ `other_user` + `other_auth_headers` - For permission testing

> **Note:** Tests will skip until Knowledge Vault module is implemented. See [KNOWLEDGE_TESTS.md](KNOWLEDGE_TESTS.md) for setup guide, test patterns, and troubleshooting.

---

### Google Search Console Adapter (Unit Tests) ✅

**File:** `tests/unit/test_gsc_adapter.py`

All 24 tests passing:

#### GSCCredentials Tests (3)
- ✅ `test_credentials_initialization` - Validates credential object creation
- ✅ `test_credentials_to_dict` - Tests serialization to dictionary
- ✅ `test_credentials_from_dict` - Tests deserialization from dictionary

#### GSCAdapter Tests (21)
- ✅ `test_adapter_initialization` - Validates adapter initialization with custom params
- ✅ `test_adapter_initialization_with_defaults` - Tests initialization from settings
- ✅ `test_get_authorization_url` - Generates correct OAuth URL with all parameters
- ✅ `test_get_authorization_url_without_credentials` - Validates error handling
- ✅ `test_exchange_code_success` - Mocks successful token exchange
- ✅ `test_exchange_code_http_error` - Tests HTTP error handling
- ✅ `test_exchange_code_invalid_response` - Tests invalid API response handling
- ✅ `test_refresh_tokens_success` - Mocks successful token refresh
- ✅ `test_refresh_tokens_http_error` - Tests refresh failure handling
- ✅ `test_refresh_tokens_no_refresh_token` - Validates missing token error
- ✅ `test_get_service` - Tests authenticated API service creation
- ✅ `test_get_service_refreshes_expired_token` - Auto-refresh on expiry
- ✅ `test_list_sites` - Mocks GSC sites API response
- ✅ `test_list_sites_quota_error` - Tests quota error (GSCQuotaError)
- ✅ `test_get_search_analytics` - Mocks search analytics data fetch
- ✅ `test_get_keyword_rankings` - Tests keyword performance retrieval
- ✅ `test_get_page_performance` - Tests page-level metrics
- ✅ `test_get_daily_stats` - Tests daily aggregated statistics
- ✅ `test_get_device_breakdown` - Tests device type breakdown
- ✅ `test_get_country_breakdown` - Tests country breakdown
- ✅ `test_create_gsc_adapter_factory` - Tests factory function

**Error Handling Covered:**
- ✅ GSCAuthError - Authentication failures
- ✅ GSCAPIError - General API errors
- ✅ GSCQuotaError - Rate limit/quota exceeded

### Analytics API (Integration Tests) 📝

**File:** `tests/integration/test_analytics_api.py`

Created comprehensive test coverage for all analytics endpoints:

#### GSC Connection Management (4 test classes, ~15 tests)
- ✅ **GET /analytics/gsc/auth-url** - OAuth URL generation
  - Returns valid OAuth URL with state
  - Requires authentication
  - Handles unconfigured credentials

- ✅ **GET /analytics/gsc/status** - Connection status
  - Returns connected=false when not connected
  - Returns full status when connected
  - Requires authentication

- ✅ **POST /analytics/gsc/disconnect** - Disconnect GSC
  - Successfully disconnects active connection
  - Returns 404 when no connection exists
  - Requires authentication

#### Analytics Data Endpoints (4 test classes, ~25 tests)
- ✅ **GET /analytics/keywords** - Keyword rankings
  - Returns 404 when GSC not connected
  - Returns empty list when no data
  - Returns paginated keyword data
  - Supports pagination (page, page_size)
  - Supports filtering by keyword search
  - Requires authentication

- ✅ **GET /analytics/pages** - Page performance
  - Returns 404 when GSC not connected
  - Returns page performance data
  - Supports filtering by page URL
  - Requires authentication

- ✅ **GET /analytics/daily** - Daily analytics
  - Returns 404 when GSC not connected
  - Returns daily aggregated data
  - Supports date range filtering (start_date, end_date)
  - Supports pagination
  - Requires authentication

- ✅ **GET /analytics/summary** - Analytics dashboard
  - Returns 404 when GSC not connected
  - Returns full summary with trends
  - Calculates trend data (current vs previous period)
  - Returns top 10 keywords and pages
  - Supports custom date ranges
  - Returns zeros for empty data
  - Requires authentication

**Test Data Coverage:**
- Database models: GSCConnection, KeywordRanking, PagePerformance, DailyAnalytics
- Pagination logic (page, page_size, total, pages)
- Date filtering (start_date, end_date)
- Trend calculations (current, previous, change_percent, trend direction)
- Authentication enforcement (401 responses)
- Error responses (404, 503)

## Test Fixtures

### Database Fixtures (conftest.py)
- `db_engine` - In-memory SQLite database engine
- `db_session` - Async database session for each test
- `test_user` - Pre-created test user with credentials

### Authentication Fixtures
- `auth_headers` - Bearer token headers for authenticated requests
- Uses `PasswordHasher` and `TokenService` from `core.security`

### HTTP Client Fixtures
- `async_client` - AsyncClient with database dependency override
- Allows testing API endpoints without real database

## Test Patterns

### Unit Test Pattern (Adapter Tests)
```python
@patch("adapters.search.gsc_adapter.build")
@patch("adapters.search.gsc_adapter.Credentials")
def test_list_sites(self, mock_creds_class, mock_build, adapter, mock_credentials):
    """Test listing verified sites."""
    # Mock API response
    mock_service = Mock()
    mock_sites_list = Mock()
    mock_sites_list.execute.return_value = {
        "siteEntry": [
            {"siteUrl": "https://example.com", "permissionLevel": "siteOwner"}
        ]
    }
    mock_service.sites.return_value.list.return_value = mock_sites_list
    mock_build.return_value = mock_service

    # Call method
    sites = adapter.list_sites(mock_credentials)

    # Verify results
    assert len(sites) == 1
    assert sites[0]["siteUrl"] == "https://example.com"
```

### Integration Test Pattern (API Tests)
```python
@pytest.mark.asyncio
async def test_get_keywords_with_data(
    self,
    async_client: AsyncClient,
    test_user: User,
    auth_headers: dict,
    db_session: AsyncSession,
):
    """Test getting keywords with existing data."""
    # Create test data
    connection = GSCConnection(...)
    db_session.add(connection)

    keyword = KeywordRanking(...)
    db_session.add(keyword)
    await db_session.commit()

    # Make API request
    response = await async_client.get(
        "/api/v1/analytics/keywords",
        headers=auth_headers,
    )

    # Verify response
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 1
```

## Known Issues

### Integration Tests - App Import Error
Integration tests require the FastAPI app to be importable. Currently, there's a circular import issue:
```
api/routes/health.py:7: ImportError: attempted relative import beyond top-level package
```

**Workaround:**
Unit tests are fully functional and provide comprehensive coverage of the GSC adapter logic. Integration tests are ready but need the app import issue to be resolved first.

## Next Steps

1. ✅ **Phase 5a: GSC Adapter Unit Tests** - Complete (24/24 passing)
2. ✅ **Phase 5b: Analytics API Integration Tests** - Created (pending app import fix)
3. ⏳ **Phase 5c: Fix app import issue** - Required for integration tests
4. ⏳ **Phase 5d: Add coverage reporting** - Run with `--cov` flags
5. ⏳ **Phase 5e: Add CI/CD test automation** - Update `.github/workflows/ci.yml`

## Test Metrics

| Category | Files | Tests | Status |
|----------|-------|-------|--------|
| GSC Adapter (Unit) | 1 | 24 | ✅ Passing |
| WordPress Adapter (Unit) | 1 | 26 | ✅ Passing |
| Image Storage (Unit) | 1 | 23 | ✅ Passing |
| LemonSqueezy Adapter (Unit) | 1 | 16 | 📝 Created |
| **ChromaDB Adapter (Unit)** | 1 | 16 | 📝 Created |
| **Document Processor (Unit)** | 1 | 20 | 📝 Created |
| **Embedding Service (Unit)** | 1 | 15 | 📝 Created |
| **Knowledge Service (Unit)** | 1 | 14 | 📝 Created |
| Analytics API (Integration) | 1 | ~40 | 📝 Created |
| Images API (Integration) | 1 | 18 | ✅ Passing |
| Billing API (Integration) | 1 | ~40 | 📝 Created |
| **Knowledge API (Integration)** | 1 | ~50 | 📝 Created |
| **Social Adapters (Unit)** | 1 | ~35 | 📝 Created |
| **Social Scheduler (Unit)** | 1 | ~30 | 📝 Created |
| **Post Queue (Unit)** | 1 | ~20 | 📝 Created |
| **Social API (Integration)** | 1 | ~45 | 📝 Created |
| **Admin Dependencies (Unit)** | 1 | 19 | 📝 Created |
| **Admin Users API (Integration)** | 1 | 27 | 📝 Created |
| **Admin Analytics API (Integration)** | 1 | 23 | 📝 Created |
| **Admin Content API (Integration)** | 1 | 21 | 📝 Created |
| **Team Permissions (Unit)** | 1 | 53 | 📝 Created |
| **Teams API (Integration)** | 1 | 25 | 📝 Created |
| **Team Members API (Integration)** | 1 | 25 | 📝 Created |
| **Team Invitations API (Integration)** | 1 | 20 | 📝 Created |
| **Team Content API (Integration)** | 1 | 20 | 📝 Created |
| **Team Billing API (Integration)** | 1 | 15 | 📝 Created |
| **Total** | **26** | **~684** | 📊 Ready |


---

### Team Multi-tenancy Tests (Phase 10) 📝

**Comprehensive test suite for team-based multi-tenancy with role-based access control.**

See **[TEAM_TESTS.md](TEAM_TESTS.md)** for complete documentation.

#### Test Coverage Summary

| Test File | Test Count | Coverage Area |
|-----------|------------|---------------|
| `test_team_permissions.py` | 53 | Permission model logic |
| `test_teams.py` | 25 | Team CRUD operations |
| `test_team_members.py` | 25 | Member management |
| `test_team_invitations.py` | 20 | Invitation workflow |
| `test_team_content.py` | 20 | Content isolation |
| `test_team_billing.py` | 15 | Team subscriptions |

#### Role-Based Permission Model

| Action | OWNER | ADMIN | MEMBER | VIEWER |
|--------|-------|-------|--------|--------|
| View Team | ✅ | ✅ | ✅ | ✅ |
| View Content | ✅ | ✅ | ✅ | ✅ |
| Update Team | ✅ | ✅ | ❌ | ❌ |
| Delete Team | ✅ | ❌ | ❌ | ❌ |
| Add Member | ✅ | ✅ | ❌ | ❌ |
| Remove Member | ✅ | ✅ | ❌ | ❌ |
| Update Role | ✅ | ✅ | ❌ | ❌ |
| Create Content | ✅ | ✅ | ✅ | ❌ |
| Edit Content | ✅ | ✅ | ✅ | ❌ |
| Delete Content | ✅ | ✅ | ✅ | ❌ |
| Manage Billing | ✅ | ❌ | ❌ | ❌ |
| View Billing | ✅ | ✅ | ❌ | ❌ |

#### Team Fixtures (conftest.py)

**Team Fixtures:**
- 📝 `team` - Team with test_user as OWNER
- 📝 `team_admin` / `team_admin_auth` - User with ADMIN role
- 📝 `team_member` / `team_member_auth` - User with MEMBER role
- 📝 `team_viewer` / `team_viewer_auth` - User with VIEWER role (read-only)
- 📝 `team_invitation` - Pending invitation with token

#### Key Test Scenarios

**Unit Tests - Permission Logic**
```python
def test_owner_can_delete_team():
    """OWNER should have permission to delete the team."""
    assert TeamPermissionChecker.can_perform(TeamRole.OWNER, TeamAction.DELETE_TEAM)

def test_viewer_cannot_edit_content():
    """VIEWER should NOT have permission to edit content."""
    assert not TeamPermissionChecker.can_perform(TeamRole.VIEWER, TeamAction.EDIT_CONTENT)
```

**Integration Tests - Team API**
```python
@pytest.mark.asyncio
async def test_create_team_success(async_client, auth_headers):
    """User should be able to create a team and become OWNER."""
    payload = {"name": "My Team", "description": "Test team"}
    response = await async_client.post("/teams", json=payload, headers=auth_headers)

    assert response.status_code == 201
    assert response.json()["your_role"] == "owner"
```

**Integration Tests - Member Management**
```python
@pytest.mark.asyncio
async def test_member_cannot_add_member(async_client, team_member_auth, team, other_user):
    """MEMBER should NOT be able to add members."""
    payload = {"email": other_user["email"], "role": "member"}
    response = await async_client.post(
        f"/teams/{team['id']}/members",
        json=payload,
        headers=team_member_auth
    )
    assert response.status_code == 403  # Forbidden
```

**Integration Tests - Content Isolation**
```python
@pytest.mark.asyncio
async def test_list_team_articles_as_non_member_forbidden(
    async_client, other_auth_headers, team
):
    """Non-members should NOT be able to list team articles."""
    response = await async_client.get(
        f"/articles?team_id={team['id']}",
        headers=other_auth_headers
    )
    assert response.status_code == 403
```

#### Running Team Tests

```bash
# Run all team tests
pytest backend/tests/unit/test_team_permissions.py \
       backend/tests/integration/test_team*.py -v

# Run specific test category
pytest backend/tests/unit/test_team_permissions.py -v  # Permission logic
pytest backend/tests/integration/test_teams.py -v      # Team CRUD
pytest backend/tests/integration/test_team_members.py -v  # Member management
```

> **Note:** Tests will skip until Teams module is implemented. All tests use `pytest.importorskip` to gracefully skip when models aren't available. See [TEAM_TESTS.md](TEAM_TESTS.md) for complete documentation, test scenarios, and implementation checklist.

**Test Coverage: ~158 tests for Phase 10 Multi-tenancy**

---

### Admin Dashboard Tests (Phase 9) 📝

**Comprehensive test suite for admin role-based access control, user management, analytics, and content moderation.**

See **[ADMIN_TESTS.md](ADMIN_TESTS.md)** for complete documentation.

#### Unit Tests (1 file, 19 tests)

**Admin Dependencies** (`test_admin_deps.py`) - 19 tests
- 📝 `get_current_admin_user` dependency (admin + super_admin access)
- 📝 `get_current_super_admin` dependency (super_admin only)
- 📝 Regular user access denial
- 📝 Suspended admin access denial
- 📝 Soft-deleted admin access denial
- 📝 Role validation properties
- 📝 Role hierarchy verification

#### Integration Tests (3 files, ~71 tests)

**1. Admin Users API** (`test_admin_users.py`) - 27 tests

**TestListUsersEndpoint** (9 tests)
- 📝 List all users with pagination
- 📝 Filter by role (user, admin, super_admin)
- 📝 Filter by status (active, pending, suspended)
- 📝 Filter by subscription tier
- 📝 Search by email or name
- 📝 Authorization enforcement

**TestUpdateUserRoleEndpoint** (5 tests)
- 📝 Promote user to admin
- 📝 Promote user to super_admin (super_admin only)
- 📝 Admin cannot promote to super_admin
- 📝 Admin cannot demote themselves
- 📝 Invalid role validation

**TestSuspendUserEndpoint** (4 tests)
- 📝 Suspend user with reason
- 📝 Admin cannot suspend themselves
- 📝 Idempotent suspension
- 📝 Unsuspend user

**TestDeleteUserEndpoint** (4 tests)
- 📝 Super admin can soft delete users
- 📝 Regular admin cannot delete users
- 📝 Super admin cannot delete themselves
- 📝 Idempotent deletion

**2. Admin Analytics API** (`test_admin_analytics.py`) - 23 tests

**Dashboard Endpoints:**
- 📝 `/admin/analytics/dashboard` - Overview statistics (5 tests)
- 📝 `/admin/analytics/users` - User growth and engagement (4 tests)
- 📝 `/admin/analytics/content` - Content generation metrics (3 tests)
- 📝 `/admin/analytics/revenue` - MRR, ARR, churn rate (4 tests)
- 📝 `/admin/analytics/system` - System health and performance (4 tests)

**Metrics Covered:**
- User metrics: total, active, suspended, growth rate
- Revenue metrics: MRR, ARR, churn rate, retention rate, revenue by tier
- Content metrics: articles, outlines, images, generation trends
- System health: database, Redis, ChromaDB status, API performance
- Trend data with date range filters (7d, 30d, 3m, 6m, 1y)

**3. Admin Content API** (`test_admin_content.py`) - 21 tests

**Content Management:**
- 📝 `/admin/content/articles` - List all articles (6 tests)
- 📝 `/admin/content/outlines` - List all outlines (2 tests)
- 📝 `/admin/content/images` - List all images (2 tests)
- 📝 Delete articles/outlines/images (5 tests)
- 📝 Bulk delete operations (3 tests)
- 📝 Audit logging (3 tests)

**Features:**
- Admin can view content from all users
- Filter by user_id, status, date range
- Search by title or keywords
- Pagination support
- Bulk delete with content_type validation
- Audit log for admin actions

#### Admin Fixtures (conftest.py)

**Role Fixtures:**
- 📝 `admin_user` - User with role="admin", professional subscription
- 📝 `super_admin_user` - User with role="super_admin", enterprise subscription
- 📝 `admin_token` - JWT authentication headers for admin
- 📝 `super_admin_token` - JWT authentication headers for super admin
- 📝 `suspended_user` - Suspended user for access restriction testing

**Content Fixtures:**
- 📝 `sample_article` - Published article owned by test_user
- 📝 `sample_outline` - Outline owned by test_user

**Key Test Patterns:**
```python
# Authorization testing pattern
@pytest.mark.asyncio
async def test_admin_access(admin_token, async_client):
    response = await async_client.get("/admin/users", headers=admin_token)
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_regular_user_denied(auth_headers, async_client):
    response = await async_client.get("/admin/users", headers=auth_headers)
    assert response.status_code == 403
```

> **Note:** Tests will skip until Admin Dashboard module is implemented. See [ADMIN_TESTS.md](ADMIN_TESTS.md) for detailed test scenarios, running instructions, and implementation requirements.

**Test Coverage: ~94 tests for Phase 9 Admin Dashboard**

---

### Social Media Scheduling Tests (Phase 8) 📝

**Comprehensive test suite for Twitter/X, LinkedIn, and Facebook integrations with post scheduling and queue management.**

See **[SOCIAL_TESTS.md](SOCIAL_TESTS.md)** for complete documentation.

#### Unit Tests (3 files, ~85 tests)

**1. Social Adapters** (\) - ~35 tests
- 📝 Twitter OAuth 2.0 with PKCE
- 📝 LinkedIn OAuth 2.0  
- 📝 Facebook OAuth 2.0
- 📝 Post creation and media upload
- 📝 Character limit validation (Twitter 280, LinkedIn 3000, Facebook 63206)
- 📝 Token refresh handling
- 📝 Rate limit error handling

**2. Social Scheduler** (\) - ~30 tests
- 📝 Processing due posts
- 📝 Publishing to platforms
- 📝 Token refresh for expired credentials
- 📝 Retry logic for failed posts
- 📝 Multiple target handling (Twitter + LinkedIn + Facebook)
- 📝 Media post workflows
- 📝 Timezone handling
- 📝 Concurrent publishing prevention

**3. Post Queue** (\) - ~20 tests
- 📝 Scheduling posts to queue
- 📝 Fetching due posts
- 📝 Marking posts as published
- 📝 Canceling pending posts
- 📝 Rescheduling posts
- 📝 Queue statistics and analytics
- 📝 User ownership enforcement

#### Integration Tests (1 file, ~45 tests)

**Social API** (\) - ~45 tests

**TestAccountsEndpoint** (9 tests)
- 📝 List connected accounts
- 📝 Initiate OAuth connection (Twitter, LinkedIn, Facebook)
- 📝 OAuth callback handling
- 📝 Disconnect accounts
- 📝 Authentication enforcement

**TestPostsEndpoint** (15 tests)
- 📝 Create scheduled posts
- 📝 List posts with pagination
- 📝 Filter by status (pending, published, failed)
- 📝 Update pending posts
- 📝 Delete posts
- 📝 Publish immediately
- 📝 Retry failed posts
- 📝 Content validation (character limits, past times)

**TestCalendarEndpoint** (3 tests)
- 📝 Get posts in date range
- 📝 Group by day
- 📝 Empty range handling

**TestStatsEndpoint** (2 tests)
- 📝 Queue statistics
- 📝 Breakdown by platform

**TestMediaUpload** (2 tests)
- 📝 Create posts with media URLs
- 📝 Upload media files

#### Social Fixtures (conftest_social_fixtures.py)

**Account Fixtures:**
- 📝 \ - Twitter account with OAuth tokens
- 📝 \ - LinkedIn account with OAuth tokens
- 📝 \ - Facebook page account
- 📝 \ - Multiple accounts (Twitter + LinkedIn)

**Post Fixtures:**
- 📝 \ - Pending scheduled post
- 📝 \ - Already published post
- 📝 \ - Failed post for retry testing
- 📝 \ - Posts with various statuses

**Mock API Fixtures:**
- 📝 \ - Mock Twitter API responses
- 📝 \ - Mock LinkedIn API responses
- 📝 \ - Mock Facebook API responses

> **Note:** Tests will skip until Social Media module is implemented. See [SOCIAL_TESTS.md](SOCIAL_TESTS.md) for detailed documentation, mock patterns, and running instructions.

**Test Coverage: ~130 tests for Phase 8 Social Media Scheduling**


## Contributing

When adding new features:
1. Write unit tests first (TDD approach)
2. Test all error conditions
3. Mock external API calls
4. Use fixtures for database objects
5. Follow existing test patterns
6. Run tests before committing: `pytest tests/ -v`
