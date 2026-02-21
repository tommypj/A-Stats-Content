# Admin Dashboard Tests Documentation

Comprehensive test suite for Phase 9 Admin Dashboard functionality.

## Overview

The admin test suite covers all administrative features including user management, analytics dashboards, content moderation, and role-based access control.

**Test Coverage:**
- Unit Tests: 19 tests (admin dependencies and role validation)
- Integration Tests: ~75 tests (users API, analytics API, content API)
- Total: ~94 tests

## Test Files

### Unit Tests

#### `backend/tests/unit/test_admin_deps.py`
Tests admin authentication dependencies and role-based access control.

**Test Classes:**
- `TestGetCurrentAdminUser` - Admin/super_admin access validation (5 tests)
- `TestGetCurrentSuperAdmin` - Super admin exclusive access (4 tests)
- `TestRoleValidation` - Role comparison and validation logic (4 tests)

**Coverage:**
- Admin user can access admin endpoints
- Super admin can access admin endpoints
- Regular user denied access to admin endpoints
- Suspended admin denied access
- Soft-deleted admin denied access
- Super admin exclusive endpoint access
- Role property validation

### Integration Tests

#### `backend/tests/integration/test_admin_users.py`
Tests admin user management API endpoints.

**Test Classes:**
- `TestListUsersEndpoint` - List users with pagination and filters (9 tests)
- `TestGetUserEndpoint` - Get single user details (3 tests)
- `TestUpdateUserRoleEndpoint` - Change user roles (5 tests)
- `TestSuspendUserEndpoint` - Suspend users (4 tests)
- `TestUnsuspendUserEndpoint` - Unsuspend users (2 tests)
- `TestDeleteUserEndpoint` - Delete users (super_admin only) (4 tests)

**Endpoints Tested:**
- `GET /admin/users` - List all users with pagination
- `GET /admin/users/{user_id}` - Get user details
- `PUT /admin/users/{user_id}/role` - Update user role
- `POST /admin/users/{user_id}/suspend` - Suspend user
- `POST /admin/users/{user_id}/unsuspend` - Unsuspend user
- `DELETE /admin/users/{user_id}` - Delete user (soft delete)

**Key Test Scenarios:**
- Pagination with page and per_page parameters
- Filter by role (user, admin, super_admin)
- Filter by status (active, pending, suspended, deleted)
- Filter by subscription tier (free, starter, professional, enterprise)
- Search by email or name
- Admin cannot demote themselves
- Admin cannot promote to super_admin (super_admin only)
- Admin cannot suspend themselves
- Super admin cannot delete themselves
- Regular user cannot access admin endpoints

#### `backend/tests/integration/test_admin_analytics.py`
Tests admin analytics and reporting API endpoints.

**Test Classes:**
- `TestDashboardStatsEndpoint` - Dashboard overview statistics (5 tests)
- `TestUserAnalyticsEndpoint` - User growth and engagement (4 tests)
- `TestContentAnalyticsEndpoint` - Content generation metrics (3 tests)
- `TestRevenueAnalyticsEndpoint` - Revenue and subscription analytics (4 tests)
- `TestSystemHealthEndpoint` - System health and performance (4 tests)
- `TestAnalyticsFiltersAndPeriods` - Date range and period filters (3 tests)

**Endpoints Tested:**
- `GET /admin/analytics/dashboard` - Overview statistics
- `GET /admin/analytics/users` - User analytics
- `GET /admin/analytics/content` - Content analytics
- `GET /admin/analytics/revenue` - Revenue analytics
- `GET /admin/analytics/system` - System health

**Metrics Covered:**
- User metrics: total, active, suspended, growth rate
- Revenue metrics: MRR, ARR, churn rate, retention rate
- Content metrics: articles, outlines, images, generation trends
- System health: database, Redis, ChromaDB status, performance
- Trend data: signup trends, revenue trends, content generation trends

**Filter Options:**
- Date range: `start_date` and `end_date` parameters
- Period shorthand: 7d, 30d, 3m, 6m, 1y
- Top users: Limit content analytics to top N users

#### `backend/tests/integration/test_admin_content.py`
Tests admin content management API endpoints.

**Test Classes:**
- `TestAdminArticlesEndpoint` - List and filter articles (6 tests)
- `TestAdminDeleteArticleEndpoint` - Delete articles (3 tests)
- `TestAdminOutlinesEndpoint` - List and filter outlines (2 tests)
- `TestAdminDeleteOutlineEndpoint` - Delete outlines (1 test)
- `TestAdminImagesEndpoint` - List and filter images (2 tests)
- `TestAdminDeleteImageEndpoint` - Delete images (1 test)
- `TestBulkDeleteEndpoint` - Bulk delete operations (3 tests)
- `TestAuditLogging` - Admin action audit logging (3 tests)

**Endpoints Tested:**
- `GET /admin/content/articles` - List all articles
- `DELETE /admin/content/articles/{article_id}` - Delete article
- `GET /admin/content/outlines` - List all outlines
- `DELETE /admin/content/outlines/{outline_id}` - Delete outline
- `GET /admin/content/images` - List all images
- `DELETE /admin/content/images/{image_id}` - Delete image
- `POST /admin/content/bulk-delete` - Bulk delete content
- `GET /admin/audit-log` - View audit log

**Key Features:**
- Admin can view content from all users
- Filter by user_id, status, date range
- Search by title or keywords
- Pagination support
- Bulk delete with content_type parameter
- Audit logging for all admin actions
- Regular users cannot access admin content endpoints

## Test Fixtures

### Admin Fixtures (in `conftest.py`)

#### `admin_user`
Creates a user with `role="admin"` and active status.
- Email: admin@example.com
- Role: ADMIN
- Status: ACTIVE
- Subscription: professional

#### `super_admin_user`
Creates a user with `role="super_admin"` and active status.
- Email: superadmin@example.com
- Role: SUPER_ADMIN
- Status: ACTIVE
- Subscription: enterprise

#### `admin_token`
Generates JWT authentication headers for admin_user.
- Format: `{"Authorization": "Bearer <token>"}`

#### `super_admin_token`
Generates JWT authentication headers for super_admin_user.
- Format: `{"Authorization": "Bearer <token>"}`

#### `suspended_user`
Creates a suspended user for access restriction testing.
- Email: suspended@example.com
- Role: USER
- Status: SUSPENDED
- Subscription: free

### Content Fixtures

#### `sample_article`
Creates a published article owned by test_user.

#### `sample_outline`
Creates an outline owned by test_user.

## Running the Tests

### Run All Admin Tests
```bash
# From backend directory
pytest tests/unit/test_admin_deps.py tests/integration/test_admin_users.py tests/integration/test_admin_analytics.py tests/integration/test_admin_content.py -v
```

### Run Specific Test Classes
```bash
# Unit tests only
pytest tests/unit/test_admin_deps.py -v

# User management tests
pytest tests/integration/test_admin_users.py -v

# Analytics tests
pytest tests/integration/test_admin_analytics.py -v

# Content management tests
pytest tests/integration/test_admin_content.py -v
```

### Run Specific Test Methods
```bash
# Test admin can list users
pytest tests/integration/test_admin_users.py::TestListUsersEndpoint::test_admin_can_list_users -v

# Test dashboard stats
pytest tests/integration/test_admin_analytics.py::TestDashboardStatsEndpoint::test_admin_can_get_dashboard_stats -v

# Test content deletion
pytest tests/integration/test_admin_content.py::TestAdminDeleteArticleEndpoint::test_admin_can_delete_any_article -v
```

### Run with Coverage
```bash
pytest tests/unit/test_admin_deps.py tests/integration/test_admin_users.py tests/integration/test_admin_analytics.py tests/integration/test_admin_content.py --cov=api.routes.admin --cov=api.dependencies.admin --cov-report=html
```

## Test Patterns

### Authorization Testing Pattern

All admin tests follow this pattern for authorization checks:

```python
@pytest.mark.asyncio
async def test_admin_can_access(admin_token, async_client):
    """Admin should have access."""
    response = await async_client.get("/admin/endpoint", headers=admin_token)
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_regular_user_cannot_access(auth_headers, async_client):
    """Regular user should be denied."""
    response = await async_client.get("/admin/endpoint", headers=auth_headers)
    assert response.status_code == 403
```

### Pagination Testing Pattern

```python
# First page
response = await async_client.get(
    "/admin/users?page=1&per_page=10",
    headers=admin_token
)
assert response.status_code == 200
data = response.json()
assert data["page"] == 1
assert len(data["users"]) == 10
```

### Filter Testing Pattern

```python
# Filter by role
response = await async_client.get(
    "/admin/users?role=admin",
    headers=admin_token
)
assert response.status_code == 200
# Verify all results match filter
for user in response.json()["users"]:
    assert user["role"] in ["admin", "super_admin"]
```

### Database Verification Pattern

```python
# Perform action
response = await async_client.delete(
    f"/admin/users/{user_id}",
    headers=super_admin_token
)
assert response.status_code == 200

# Verify in database
await db_session.refresh(user)
assert user.deleted_at is not None
assert user.status == "deleted"
```

## Common Test Scenarios

### Role-Based Access Control

**Scenario 1: Admin Access**
- Admin can list users, view analytics, manage content
- Admin cannot delete users (super_admin only)
- Admin cannot promote to super_admin (super_admin only)
- Admin cannot change their own role

**Scenario 2: Super Admin Access**
- Super admin has all admin permissions
- Super admin can delete users (soft delete)
- Super admin can promote users to super_admin
- Super admin cannot delete themselves

**Scenario 3: Suspended Admin**
- Suspended admin cannot access any admin endpoints
- Status check happens before role check

### User Management

**Scenario 1: List Users with Filters**
```python
# Filter by subscription tier
response = await async_client.get(
    "/admin/users?subscription_tier=professional&status=active",
    headers=admin_token
)
```

**Scenario 2: Update User Role**
```python
# Promote user to admin
response = await async_client.put(
    f"/admin/users/{user_id}/role",
    headers=admin_token,
    json={"role": "admin"}
)
```

**Scenario 3: Suspend User**
```python
# Suspend user with reason
response = await async_client.post(
    f"/admin/users/{user_id}/suspend",
    headers=admin_token,
    json={"reason": "Terms of service violation"}
)
```

### Analytics

**Scenario 1: Dashboard Overview**
```python
# Get dashboard stats with date range
response = await async_client.get(
    "/admin/analytics/dashboard?start_date=2024-01-01&end_date=2024-12-31",
    headers=admin_token
)
```

**Scenario 2: Revenue Analytics**
```python
# Get revenue trends for last 6 months
response = await async_client.get(
    "/admin/analytics/revenue?period=6m",
    headers=admin_token
)
```

### Content Management

**Scenario 1: List All Articles**
```python
# List articles with user filter
response = await async_client.get(
    f"/admin/content/articles?user_id={user_id}&status=published",
    headers=admin_token
)
```

**Scenario 2: Bulk Delete**
```python
# Bulk delete articles
response = await async_client.post(
    "/admin/content/bulk-delete",
    headers=admin_token,
    json={
        "content_type": "articles",
        "ids": [article1_id, article2_id, article3_id]
    }
)
```

## Error Cases

All tests include error case coverage:

### 401 Unauthorized
- No authentication token provided
- Invalid or expired token

### 403 Forbidden
- Regular user accessing admin endpoint
- Admin attempting super_admin-only operation
- Suspended user with valid token
- Admin trying to modify themselves (role change, suspend, delete)

### 404 Not Found
- Nonexistent user_id in endpoint
- Nonexistent content item

### 422 Unprocessable Entity
- Invalid role value ("invalid_role")
- Invalid content_type in bulk delete
- Invalid date range (end before start)
- Invalid period format

## Implementation Requirements

When implementing the admin dashboard, ensure:

1. **Dependencies** (`backend/api/dependencies/admin.py`):
   ```python
   async def get_current_admin_user(
       current_user: User = Depends(get_current_user)
   ) -> User:
       if current_user.role not in ["admin", "super_admin"]:
           raise HTTPException(status_code=403, detail="Admin access required")
       if current_user.status == "suspended":
           raise HTTPException(status_code=403, detail="Account suspended")
       if current_user.deleted_at is not None:
           raise HTTPException(status_code=403, detail="Account deleted")
       return current_user

   async def get_current_super_admin(
       current_user: User = Depends(get_current_user)
   ) -> User:
       if current_user.role != "super_admin":
           raise HTTPException(status_code=403, detail="Super admin access required")
       if current_user.status == "suspended":
           raise HTTPException(status_code=403, detail="Account suspended")
       return current_user
   ```

2. **Routes** (`backend/api/routes/admin.py`):
   - Use `Depends(get_current_admin_user)` for admin endpoints
   - Use `Depends(get_current_super_admin)` for super admin endpoints
   - Implement pagination with skip/limit or page/per_page
   - Support filtering with query parameters
   - Implement soft delete (set deleted_at, update status)

3. **Schemas** (`backend/api/schemas/admin.py`):
   - User list/detail responses
   - Analytics data structures
   - Audit log entries
   - Filter and pagination parameters

4. **Audit Logging**:
   - Log all admin actions to database table
   - Include: admin_id, action, target_id, timestamp, details
   - Accessible via `/admin/audit-log` endpoint

## Test Maintenance

### Adding New Admin Tests

1. Create test in appropriate file (users/analytics/content)
2. Use existing fixtures (admin_user, admin_token, etc.)
3. Follow authorization testing pattern
4. Include both success and error cases
5. Verify database state changes
6. Update this documentation

### Updating Fixtures

When adding new admin features:
1. Add new fixtures to `conftest.py` if needed
2. Document fixture usage in this file
3. Ensure fixtures are reusable across test files

### CI/CD Integration

All admin tests should pass before deployment:
```yaml
# .github/workflows/ci.yml
- name: Run Admin Tests
  run: |
    pytest tests/unit/test_admin_deps.py \
           tests/integration/test_admin_users.py \
           tests/integration/test_admin_analytics.py \
           tests/integration/test_admin_content.py \
           --cov --cov-report=xml
```

## Troubleshooting

### Tests Skipped

If tests show "Admin routes not implemented yet":
1. Check that `backend/api/routes/admin.py` exists
2. Verify routes are registered in `backend/api/routes/__init__.py`
3. Ensure `get_current_admin_user` dependency exists

### Import Errors

If seeing `ModuleNotFoundError`:
1. Ensure backend directory is in Python path
2. Check that `__init__.py` files exist
3. Verify model imports in conftest.py

### Fixture Errors

If fixtures not found:
1. Ensure pytest discovers `conftest.py`
2. Check fixture dependencies (admin_user depends on db_session)
3. Verify async fixtures use `@pytest.fixture` with `async def`

### Database Errors

If database tests fail:
1. Check SQLite in-memory database is properly created
2. Ensure Base.metadata.create_all() runs before tests
3. Verify session rollback happens after each test

## Test Statistics

**Total Test Count: ~94 tests**

### By Category
- User Management: 27 tests
- Analytics: 23 tests
- Content Management: 21 tests
- Dependencies: 19 tests
- Audit Logging: 3 tests

### By Type
- Unit Tests: 19 tests
- Integration Tests: 75 tests

### By Permission Level
- Admin tests: 60 tests
- Super Admin tests: 15 tests
- Authorization denial tests: 19 tests

### Coverage Goals
- Line Coverage: > 90%
- Branch Coverage: > 85%
- Function Coverage: 100%

## Related Documentation

- [Main Test README](./README.md) - Overview of all tests
- [Billing Tests](./BILLING_TESTS.md) - LemonSqueezy billing tests
- [Knowledge Tests](./KNOWLEDGE_TESTS.md) - Knowledge Vault RAG tests
- [Social Tests](./SOCIAL_TESTS.md) - Social media scheduling tests
- [Development Plan](../../.claude/plans/DEVELOPMENT_PLAN.md) - Phase 9 specifications
