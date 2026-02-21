# Phase 10 Multi-tenancy Tests Documentation

Comprehensive test suite for team-based multi-tenancy feature with role-based access control.

## Overview

The Phase 10 test suite covers all aspects of multi-tenancy including:
- Role-based permissions (OWNER, ADMIN, MEMBER, VIEWER)
- Team CRUD operations
- Team member management
- Team invitations workflow
- Team content isolation
- Team billing and subscriptions

## Test Coverage Summary

| Test File | Test Count | Coverage Area |
|-----------|------------|---------------|
| `test_team_permissions.py` | 53 | Permission model logic |
| `test_teams.py` | 25 | Team CRUD operations |
| `test_team_members.py` | 25 | Member management |
| `test_team_invitations.py` | 20 | Invitation workflow |
| `test_team_content.py` | 20 | Content isolation |
| `test_team_billing.py` | 15 | Team subscriptions |
| **TOTAL** | **~158** | **All team features** |

## Role-Based Permission Model

### Permission Matrix

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

## Running Tests

### Run All Team Tests

```bash
# Run all team tests
pytest backend/tests/unit/test_team_permissions.py backend/tests/integration/test_teams.py backend/tests/integration/test_team_members.py backend/tests/integration/test_team_invitations.py backend/tests/integration/test_team_content.py backend/tests/integration/test_team_billing.py -v

# Run with coverage
pytest backend/tests/unit/test_team_permissions.py backend/tests/integration/test_team*.py --cov=backend --cov-report=html
```

### Run Specific Test Categories

```bash
# Unit tests only (permission logic)
pytest backend/tests/unit/test_team_permissions.py -v

# Integration tests only
pytest backend/tests/integration/test_team*.py -v

# Specific feature area
pytest backend/tests/integration/test_teams.py -v
pytest backend/tests/integration/test_team_members.py -v
pytest backend/tests/integration/test_team_invitations.py -v
```

### Run Specific Test Classes

```bash
# Test team creation
pytest backend/tests/integration/test_teams.py::TestCreateTeam -v

# Test member permissions
pytest backend/tests/integration/test_team_members.py::TestRemoveMember -v

# Test invitation flow
pytest backend/tests/integration/test_team_invitations.py::TestAcceptInvitation -v
```

## Test Fixtures

### Team Fixtures (conftest.py)

All team fixtures use `pytest.importorskip` to gracefully skip when models aren't implemented yet.

#### `team`
Creates a team with `test_user` as OWNER.

**Usage:**
```python
async def test_example(team: dict):
    # team = {"id": "...", "name": "Test Team", ...}
    assert team["name"] == "Test Team"
```

#### `team_admin` / `team_admin_auth`
Creates a user with ADMIN role in the team and auth headers.

**Usage:**
```python
async def test_admin_access(async_client, team_admin_auth: dict, team: dict):
    response = await async_client.get(f"/teams/{team['id']}", headers=team_admin_auth)
    assert response.status_code == 200
```

#### `team_member` / `team_member_auth`
Creates a user with MEMBER role in the team and auth headers.

**Usage:**
```python
async def test_member_permissions(async_client, team_member_auth: dict, team: dict):
    # Test MEMBER-level operations
    response = await async_client.post(
        "/articles",
        json={"title": "Test", "team_id": team["id"]},
        headers=team_member_auth
    )
    assert response.status_code == 201
```

#### `team_viewer` / `team_viewer_auth`
Creates a user with VIEWER role (read-only access).

**Usage:**
```python
async def test_viewer_cannot_create(async_client, team_viewer_auth: dict, team: dict):
    response = await async_client.post(
        "/articles",
        json={"title": "Test", "team_id": team["id"]},
        headers=team_viewer_auth
    )
    assert response.status_code == 403  # Forbidden
```

#### `team_invitation`
Creates a pending team invitation with token.

**Usage:**
```python
async def test_accept_invitation(async_client, other_auth_headers: dict, team_invitation: dict):
    response = await async_client.post(
        f"/invitations/{team_invitation['token']}/accept",
        headers=other_auth_headers
    )
    assert response.status_code == 200
```

## Test Scenarios

### 1. Unit Tests: Team Permissions

**File:** `backend/tests/unit/test_team_permissions.py`

Tests the permission model in isolation without database or API calls.

#### Key Tests:
- ✅ `test_owner_can_delete_team()` - OWNER has all permissions
- ✅ `test_admin_cannot_delete_team()` - ADMIN limited permissions
- ✅ `test_member_can_create_content()` - MEMBER can create
- ✅ `test_viewer_cannot_edit_content()` - VIEWER is read-only
- ✅ `test_permission_hierarchy()` - OWNER > ADMIN > MEMBER > VIEWER
- ✅ `test_only_owner_can_manage_billing()` - Billing is OWNER-only

**Pattern:**
```python
def test_owner_can_delete_team():
    """OWNER should have permission to delete the team."""
    assert TeamPermissionChecker.can_perform(TeamRole.OWNER, TeamAction.DELETE_TEAM)
```

### 2. Integration Tests: Teams API

**File:** `backend/tests/integration/test_teams.py`

Tests full CRUD operations for teams via API.

#### Test Classes:

**TestCreateTeam** (4 tests)
- Create team with name and description
- Creator becomes OWNER automatically
- Unique slug generation
- Authentication required

**TestListTeams** (5 tests)
- List user's teams (isolation)
- Show user's role in each team
- Pagination support
- Empty list for new users

**TestGetTeamDetails** (4 tests)
- View team details as member
- Non-members denied access
- 404 for non-existent teams

**TestUpdateTeam** (5 tests)
- OWNER can update team settings
- ADMIN can update team settings
- MEMBER cannot update (403)
- Name validation

**TestDeleteTeam** (5 tests)
- OWNER can delete team
- ADMIN cannot delete (403)
- Cascade deletion to members
- Team disappears after deletion

**TestSwitchTeamContext** (3 tests)
- Switch active team for multi-team users
- Non-members cannot switch to team
- Context persists in session

**TestTeamAuthorization** (3 tests)
- Non-member access denied
- Team isolation between users

**Pattern:**
```python
@pytest.mark.asyncio
async def test_create_team_success(async_client: AsyncClient, auth_headers: dict):
    """User should be able to create a team and become OWNER."""
    payload = {"name": "My Team", "description": "Test team"}
    response = await async_client.post("/teams", json=payload, headers=auth_headers)

    assert response.status_code == 201
    assert response.json()["your_role"] == "owner"
```

### 3. Integration Tests: Team Members

**File:** `backend/tests/integration/test_team_members.py`

Tests member management operations.

#### Test Classes:

**TestListTeamMembers** (6 tests)
- List members with user info
- All roles can view members
- Non-members denied access
- Pagination support

**TestAddTeamMember** (6 tests)
- OWNER/ADMIN can add members
- MEMBER cannot add (403)
- Add by email or user_id
- Prevent duplicate members
- Role validation

**TestUpdateMemberRole** (6 tests)
- OWNER/ADMIN can update roles
- MEMBER cannot update (403)
- Cannot demote OWNER
- Cannot promote to OWNER if exists

**TestRemoveMember** (5 tests)
- OWNER/ADMIN can remove members
- MEMBER cannot remove (403)
- Cannot remove OWNER
- Removed member loses access

**TestLeaveTeam** (4 tests)
- MEMBER/ADMIN can leave
- OWNER cannot leave (must transfer)
- Non-member cannot leave

**TestTransferOwnership** (4 tests)
- OWNER can transfer ownership
- Old OWNER becomes ADMIN
- Non-OWNER cannot transfer
- Cannot transfer to non-member

**Pattern:**
```python
@pytest.mark.asyncio
async def test_add_member_as_owner(
    async_client: AsyncClient,
    auth_headers: dict,
    team: dict,
    other_user: dict
):
    """OWNER should be able to add members to the team."""
    payload = {"email": other_user["email"], "role": "member"}
    response = await async_client.post(
        f"/teams/{team['id']}/members",
        json=payload,
        headers=auth_headers
    )
    assert response.status_code == 201
```

### 4. Integration Tests: Team Invitations

**File:** `backend/tests/integration/test_team_invitations.py`

Tests email-based invitation workflow.

#### Test Classes:

**TestSendInvitation** (6 tests)
- OWNER/ADMIN can send invitations
- MEMBER cannot send (403)
- Cannot invite existing members
- Custom invitation message
- Unique tokens generated

**TestListInvitations** (5 tests)
- OWNER/ADMIN can list invitations
- MEMBER cannot list (403)
- Show invitation details
- Filter by status

**TestRevokeInvitation** (4 tests)
- OWNER/ADMIN can revoke
- MEMBER cannot revoke (403)
- Cannot revoke accepted invitations

**TestResendInvitation** (2 tests)
- Resend invitation
- Extends expiry date

**TestAcceptInvitation** (6 tests)
- Logged-in user accepts invitation
- New user registration flow
- Expired invitation fails (410)
- Invalid token fails (404)
- Cannot accept twice (409)
- Email mismatch fails (403)

**TestInvitationValidation** (2 tests)
- Email must match invitee
- Default 7-day expiry

**Pattern:**
```python
@pytest.mark.asyncio
async def test_accept_invitation_logged_in_user(
    async_client: AsyncClient,
    other_auth_headers: dict,
    team_invitation: dict
):
    """Logged-in user should be able to accept invitation."""
    response = await async_client.post(
        f"/invitations/{team_invitation['token']}/accept",
        headers=other_auth_headers
    )
    assert response.status_code == 200
    assert response.json()["team_id"] == team_invitation["team_id"]
```

### 5. Integration Tests: Team Content

**File:** `backend/tests/integration/test_team_content.py`

Tests content isolation and team-scoped content management.

#### Test Classes:

**TestCreateTeamContent** (4 tests)
- Create article with team_id
- MEMBER can create content
- VIEWER cannot create (403)
- Non-member cannot create (403)

**TestListTeamContent** (4 tests)
- Members can list team content
- VIEWER can list (read-only)
- Non-members denied access (403)
- Filter shows only team content

**TestEditTeamContent** (3 tests)
- MEMBER can edit team content
- VIEWER cannot edit (403)
- Non-member cannot edit (403)

**TestDeleteTeamContent** (4 tests)
- OWNER/ADMIN can delete any content
- MEMBER can delete own content
- VIEWER cannot delete (403)

**TestTeamContentCascadeDelete** (1 test)
- Deleting team cascades to all content

**TestTeamContentIsolation** (2 tests)
- Content isolated between teams
- Personal content separate from team content

**Pattern:**
```python
@pytest.mark.asyncio
async def test_list_team_articles_as_non_member_forbidden(
    async_client: AsyncClient,
    other_auth_headers: dict,
    team: dict
):
    """Non-members should NOT be able to list team articles."""
    response = await async_client.get(
        f"/articles?team_id={team['id']}",
        headers=other_auth_headers
    )
    assert response.status_code == 403
```

### 6. Integration Tests: Team Billing

**File:** `backend/tests/integration/test_team_billing.py`

Tests team-level subscription management.

#### Test Classes:

**TestGetTeamSubscription** (4 tests)
- OWNER/ADMIN can view subscription
- MEMBER cannot view (403)
- Shows usage statistics

**TestCreateTeamCheckout** (3 tests)
- OWNER can create checkout
- ADMIN cannot (403)
- Validates subscription tier

**TestTeamWebhookProcessing** (2 tests)
- Webhook updates team subscription
- Webhook handles cancellation

**TestTeamUsageTracking** (3 tests)
- Usage increments on content creation
- Enforces tier limits
- Usage resets on billing cycle

**TestCancelTeamSubscription** (3 tests)
- OWNER can cancel subscription
- ADMIN cannot cancel (403)
- Cannot cancel free tier

**TestTeamBillingIsolation** (2 tests)
- Independent subscriptions per team
- Usage tracked separately per team

**Pattern:**
```python
@pytest.mark.asyncio
async def test_get_team_subscription_as_member_forbidden(
    async_client: AsyncClient,
    team_member_auth: dict,
    team: dict
):
    """MEMBER should NOT be able to view billing information."""
    response = await async_client.get(
        f"/teams/{team['id']}/subscription",
        headers=team_member_auth
    )
    assert response.status_code == 403
```

## Common Test Patterns

### 1. Permission Testing Pattern

```python
@pytest.mark.asyncio
async def test_action_as_role(
    async_client: AsyncClient,
    role_auth_headers: dict,
    team: dict
):
    """ROLE should/should not be able to perform action."""
    response = await async_client.method(
        f"/teams/{team['id']}/endpoint",
        headers=role_auth_headers
    )
    assert response.status_code == expected_code
```

### 2. Authorization Testing Pattern

```python
@pytest.mark.asyncio
async def test_non_member_denied(
    async_client: AsyncClient,
    other_auth_headers: dict,
    team: dict
):
    """Non-members should be denied access."""
    response = await async_client.get(
        f"/teams/{team['id']}",
        headers=other_auth_headers
    )
    assert response.status_code == 403
```

### 3. Data Isolation Pattern

```python
@pytest.mark.asyncio
async def test_team_isolation(
    async_client: AsyncClient,
    auth_headers: dict,
    other_auth_headers: dict
):
    """Users should only see their own teams."""
    # User 1 creates team
    team1 = await create_team(auth_headers)

    # User 2 creates team
    team2 = await create_team(other_auth_headers)

    # User 1 cannot see User 2's team
    list_response = await async_client.get("/teams", headers=auth_headers)
    team_ids = [t["id"] for t in list_response.json()["items"]]
    assert team2["id"] not in team_ids
```

## Error Codes Reference

| Status Code | Meaning | Common Scenarios |
|-------------|---------|------------------|
| 200 | OK | Successful GET/PUT/POST |
| 201 | Created | Team/member created |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Invalid input, business logic error |
| 401 | Unauthorized | Missing/invalid authentication |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Team/member doesn't exist |
| 409 | Conflict | Duplicate member, already accepted |
| 410 | Gone | Expired invitation |
| 422 | Unprocessable | Validation error |

## Database Models Reference

### Team
```python
class Team:
    id: UUID
    name: str
    description: str (optional)
    slug: str (unique)
    created_by: UUID (User FK)
    created_at: datetime
    updated_at: datetime
```

### TeamMember
```python
class TeamMember:
    id: UUID
    team_id: UUID (FK)
    user_id: UUID (FK)
    role: TeamRole (owner/admin/member/viewer)
    joined_at: datetime
```

### TeamInvitation
```python
class TeamInvitation:
    id: UUID
    team_id: UUID (FK)
    email: str
    role: TeamRole
    token: str (unique, urlsafe)
    invited_by: UUID (FK)
    status: str (pending/accepted/revoked)
    expires_at: datetime (default: +7 days)
    created_at: datetime
```

## Best Practices

### 1. Use Appropriate Fixtures
- Use `team` for basic team tests
- Use role-specific fixtures (`team_admin`, `team_member`, `team_viewer`) for permission tests
- Use `other_auth_headers` for testing isolation and access denial

### 2. Test Both Success and Failure Cases
```python
# Good: Test both allowed and forbidden
async def test_owner_can_delete():
    # Test OWNER can delete
    pass

async def test_admin_cannot_delete():
    # Test ADMIN cannot delete
    pass
```

### 3. Verify Database State Changes
```python
# Delete member
await async_client.delete(f"/teams/{team_id}/members/{member_id}")

# Verify member is gone
members_response = await async_client.get(f"/teams/{team_id}/members")
assert member_id not in [m["id"] for m in members_response.json()["items"]]
```

### 4. Test Cascade Effects
```python
# Delete team
await async_client.delete(f"/teams/{team_id}")

# Verify content is also deleted
get_response = await async_client.get(f"/articles/{article_id}")
assert get_response.status_code == 404
```

### 5. Use Clear Test Names
```python
# Good
async def test_member_can_create_content():
    ...

async def test_viewer_cannot_create_content():
    ...

# Bad
async def test_content():
    ...
```

## Troubleshooting

### Tests Skipped: "Team models not yet implemented"

All team tests use `pytest.importorskip` to gracefully skip when the team feature hasn't been implemented yet.

**Solution:** Implement the team models, routes, and schemas, then tests will automatically activate.

### Fixture Dependency Errors

If you see errors like "fixture 'team' not found":

**Solution:** Ensure `backend/tests/conftest.py` is being loaded. Run from project root:
```bash
cd D:\A-Stats-Online
pytest backend/tests/integration/test_teams.py -v
```

### Authentication Errors (401)

If tests fail with 401 errors:

**Solution:** Check that `auth_headers` fixture is being passed correctly:
```python
async def test_example(async_client, auth_headers: dict):  # ✅ Correct
    response = await async_client.get("/teams", headers=auth_headers)
```

### Permission Errors (403)

If tests fail with unexpected 403:

**Solution:** Verify you're using the correct role fixture:
- `auth_headers` = OWNER (test_user)
- `team_admin_auth` = ADMIN
- `team_member_auth` = MEMBER
- `team_viewer_auth` = VIEWER

## Implementation Checklist

When implementing Phase 10 Multi-tenancy, use this test-driven approach:

- [ ] 1. Create database models (Team, TeamMember, TeamInvitation)
- [ ] 2. Create migrations
- [ ] 3. Run unit tests - should pass immediately
- [ ] 4. Create API schemas
- [ ] 5. Implement Teams API routes
- [ ] 6. Run `test_teams.py` - should pass
- [ ] 7. Implement Team Members API routes
- [ ] 8. Run `test_team_members.py` - should pass
- [ ] 9. Implement Invitations API routes
- [ ] 10. Run `test_team_invitations.py` - should pass
- [ ] 11. Add team_id to content models
- [ ] 12. Update content routes with team checks
- [ ] 13. Run `test_team_content.py` - should pass
- [ ] 14. Add team subscription to Team model
- [ ] 15. Implement team billing routes
- [ ] 16. Run `test_team_billing.py` - should pass
- [ ] 17. Run all tests together - all should pass

## Test Metrics

- **Total Tests:** ~158
- **Unit Tests:** 53
- **Integration Tests:** 105
- **Fixtures:** 13
- **Test Files:** 6
- **Expected Coverage:** >90% of team-related code

## Related Documentation

- Main test README: `backend/tests/README.md`
- Test fixtures: `backend/tests/conftest.py`
- Existing test patterns: `backend/tests/integration/test_auth.py`
