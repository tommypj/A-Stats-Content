# Team Billing API - Multi-Tenancy Implementation

Complete team-level billing system for Phase 10 Multi-tenancy.

## Overview

The team billing system allows teams to have their own subscription plans with shared usage limits across all team members. This is separate from individual user subscriptions.

## Key Features

- **Team-Level Subscriptions**: Teams can subscribe to paid plans (Starter, Professional, Enterprise)
- **Shared Usage Limits**: All team members share the team's content generation limits
- **Role-Based Access**: Only OWNER can manage billing; ADMIN+ can view; MEMBER+ can see usage
- **Webhook Support**: LemonSqueezy webhooks handle both user and team subscriptions
- **Usage Tracking**: Monthly usage reset with proper limit enforcement

## Team Limits

| Tier | Articles | Outlines | Images | Members |
|------|----------|----------|--------|---------|
| Free | 10 | 20 | 5 | 3 |
| Starter | 50 | 100 | 25 | 5 |
| Professional | 200 | 400 | 100 | 15 |
| Enterprise | Unlimited | Unlimited | Unlimited | Unlimited |

**Note**: Team limits are higher than individual user limits to support collaborative work.

## API Endpoints

### GET /teams/{team_id}/billing/subscription

Get team subscription status and usage.

**Authorization**: ADMIN or OWNER role required

**Response**:
```json
{
  "team_id": "uuid",
  "team_name": "My Team",
  "subscription_tier": "professional",
  "subscription_status": "active",
  "subscription_expires": "2026-03-20T00:00:00Z",
  "customer_id": "123456",
  "subscription_id": "sub_123",
  "variant_id": "var_123",
  "usage": {
    "articles_used": 45,
    "articles_limit": 200,
    "outlines_used": 89,
    "outlines_limit": 400,
    "images_used": 23,
    "images_limit": 100,
    "members_count": 7,
    "members_limit": 15,
    "usage_reset_date": "2026-03-01T00:00:00Z"
  },
  "limits": {
    "articles_per_month": 200,
    "outlines_per_month": 400,
    "images_per_month": 100,
    "max_members": 15
  },
  "can_manage": true
}
```

### POST /teams/{team_id}/billing/checkout

Create checkout session for team subscription upgrade.

**Authorization**: OWNER role required

**Request**:
```json
{
  "variant_id": "123456"
}
```

**Response**:
```json
{
  "checkout_url": "https://store.lemonsqueezy.com/checkout/buy/123456?checkout[email]=..."
}
```

The checkout URL includes:
- User email (team owner)
- `team_id` in custom data (used by webhook)
- `user_id` in custom data

### GET /teams/{team_id}/billing/portal

Get customer portal URL for managing team subscription.

**Authorization**: OWNER role required

**Response**:
```json
{
  "portal_url": "https://store.lemonsqueezy.com/billing"
}
```

### POST /teams/{team_id}/billing/cancel

Cancel team subscription (remains active until end of period).

**Authorization**: OWNER role required

**Response**:
```json
{
  "success": true,
  "message": "Team subscription will be cancelled at the end of the billing period..."
}
```

### GET /teams/{team_id}/billing/usage

Get detailed team usage statistics with percentages.

**Authorization**: MEMBER role or higher (any team member)

**Response**:
```json
{
  "team_id": "uuid",
  "team_name": "My Team",
  "subscription_tier": "professional",
  "usage": {
    "articles_used": 45,
    "articles_limit": 200,
    "outlines_used": 89,
    "outlines_limit": 400,
    "images_used": 23,
    "images_limit": 100,
    "members_count": 7,
    "members_limit": 15,
    "usage_reset_date": "2026-03-01T00:00:00Z"
  },
  "limits": {
    "articles_per_month": 200,
    "outlines_per_month": 400,
    "images_per_month": 100,
    "max_members": 15
  },
  "articles_usage_percent": 22.5,
  "outlines_usage_percent": 22.25,
  "images_usage_percent": 23.0,
  "members_usage_percent": 46.67
}
```

## Webhook Integration

The main billing webhook (`POST /billing/webhook`) has been updated to handle both user and team subscriptions.

**Team Subscription Detection**:
```python
# Webhook checks for team_id in custom_data
custom_data = meta.get("custom_data", {})
team_id = custom_data.get("team_id")

if team_id:
    # Process as team subscription
    await handle_team_subscription_webhook(...)
else:
    # Process as user subscription (original behavior)
    ...
```

**Supported Webhook Events**:
- `subscription_created` - New team subscription
- `subscription_updated` - Plan or status change
- `subscription_cancelled` - Cancellation (keeps tier until expiry)
- `subscription_expired` - Downgrade to free tier
- `subscription_payment_success` - Update renewal date
- `subscription_payment_failed` - Log failure
- `subscription_paused` / `subscription_unpaused` - Pause/resume
- `subscription_resumed` - Reactivation

## Team Usage Service

The `TeamUsageService` handles usage tracking and limit enforcement.

**Usage**:
```python
from services.team_usage import TeamUsageService

# Check if team can create more content
usage_service = TeamUsageService(db)
can_create = await usage_service.check_team_limit(team_id, "articles")

if not can_create:
    raise HTTPException(status_code=403, detail="Team article limit reached")

# Increment usage after creation
await usage_service.increment_usage(team_id, "articles")

# Get usage stats
usage_stats = await usage_service.get_team_usage(team_id)

# Reset usage (called by background job monthly)
was_reset = await usage_service.reset_team_usage_if_needed(team_id)
```

**Resource Types**:
- `articles` - Article generation
- `outlines` - Outline generation
- `images` - Image generation
- `members` - Team member slots

## Integration with Content Creation

When creating content with a `team_id`:

1. **Check team limit** before creating:
   ```python
   if team_id:
       usage_service = TeamUsageService(db)
       can_create = await usage_service.check_team_limit(team_id, "articles")
       if not can_create:
           raise HTTPException(403, "Team limit reached")
   ```

2. **Increment usage** after successful creation:
   ```python
   if team_id:
       await usage_service.increment_usage(team_id, "articles")
   ```

3. **Use team limits** instead of user limits for validation

## Role-Based Access Control

Team billing endpoints enforce different role requirements:

| Endpoint | Required Role | Notes |
|----------|---------------|-------|
| GET /subscription | ADMIN | View subscription details |
| POST /checkout | OWNER | Create new subscription |
| GET /portal | OWNER | Manage subscription |
| POST /cancel | OWNER | Cancel subscription |
| GET /usage | MEMBER | Any member can view usage |

**Role Hierarchy**:
- OWNER (highest) - Full billing control
- ADMIN - View billing, manage members
- EDITOR - Create content
- VIEWER - Read-only access

## Database Schema

Team billing uses the existing `Team` model with these fields:

```python
class Team(Base):
    # Subscription
    subscription_tier: str  # free, starter, professional, enterprise
    subscription_status: str  # active, cancelled, expired, past_due
    subscription_expires: datetime
    lemonsqueezy_customer_id: str
    lemonsqueezy_subscription_id: str

    # Usage tracking
    articles_generated_this_month: int
    outlines_generated_this_month: int
    images_generated_this_month: int
    usage_reset_date: datetime

    # Settings
    max_members: int
```

## Testing

**Manual Testing Flow**:

1. Create a team (requires team management routes)
2. Add members to team
3. Create checkout session:
   ```bash
   POST /teams/{team_id}/billing/checkout
   {
     "variant_id": "123456"
   }
   ```
4. Complete checkout on LemonSqueezy
5. Webhook updates team subscription tier
6. Create content as team member
7. Check usage:
   ```bash
   GET /teams/{team_id}/billing/usage
   ```
8. Test limit enforcement when limits reached

**Webhook Testing**:
```bash
# Send test webhook with team_id in custom_data
curl -X POST http://localhost:8000/billing/webhook \
  -H "Content-Type: application/json" \
  -H "X-Signature: <signature>" \
  -d '{
    "meta": {
      "event_name": "subscription_created",
      "custom_data": {
        "team_id": "uuid",
        "user_id": "uuid"
      }
    },
    "data": {
      "id": "sub_123",
      "attributes": {
        "customer_id": "123456",
        "variant_id": "var_123",
        "status": "active",
        "renews_at": "2026-03-20T00:00:00Z"
      }
    }
  }'
```

## Configuration

No additional configuration needed beyond existing LemonSqueezy settings:

- `LEMONSQUEEZY_API_KEY`
- `LEMONSQUEEZY_STORE_ID`
- `LEMONSQUEEZY_WEBHOOK_SECRET`
- `LEMONSQUEEZY_VARIANT_*` (for tier detection)

## Error Handling

Common error scenarios:

- **403 Forbidden**: User not member of team or insufficient role
- **404 Not Found**: Team doesn't exist or no active subscription
- **500 Internal Server Error**: LemonSqueezy configuration missing

All endpoints return proper HTTP status codes and error messages.

## Next Steps

1. **Frontend Integration**: Create team billing UI components
2. **Background Jobs**: Monthly usage reset job
3. **Admin Dashboard**: Team subscription analytics
4. **Notifications**: Email alerts for limit warnings
5. **Content Creation**: Integrate team limit checks in article/outline/image routes

## Files Modified

- `backend/infrastructure/database/models/team.py` - Team model (already existed)
- `backend/api/schemas/team_billing.py` - Team billing schemas (new)
- `backend/services/team_usage.py` - Team usage service (new)
- `backend/api/routes/team_billing.py` - Team billing endpoints (new)
- `backend/api/routes/billing.py` - Updated webhook handler
- `backend/api/routes/__init__.py` - Registered team billing router
- `backend/api/schemas/__init__.py` - Exported team billing schemas

## Architecture Notes

- **Clean Architecture**: Service layer (`TeamUsageService`) handles business logic
- **Separation of Concerns**: Team billing separate from user billing
- **Webhook Delegation**: Main webhook routes to team handler when `team_id` present
- **Role Enforcement**: Helper functions (`require_team_role`) centralize authorization
- **Usage Isolation**: Team usage tracked separately from user usage
