# Critical Fix Guide - Model Import Error

**SEVERITY:** CRITICAL BLOCKER
**TIME REQUIRED:** 1 hour
**IMPACT:** Blocks all 600+ tests from running

---

## The Problem

The file `backend/infrastructure/database/models/__init__.py` tries to import classes that don't exist in `social.py`:

```python
# Line 10-18 in __init__.py (BROKEN)
from .social import (
    SocialAccount,
    ScheduledPost,
    PostTarget,
    PostAnalytics,  # ❌ DOES NOT EXIST
    SocialPlatform,  # ❌ Should be "Platform"
    PostStatus,
    PostTargetStatus,  # ❌ Should be "PostStatus" or doesn't exist
)
```

---

## What Actually Exists in social.py

```python
# backend/infrastructure/database/models/social.py
class Platform(str, Enum):  # NOT "SocialPlatform"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"

class PostStatus(str, Enum):  # This exists
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    CANCELLED = "cancelled"

class SocialAccount(Base, TimestampMixin):
    # ...

class ScheduledPost(Base, TimestampMixin):
    # ...

class PostTarget(Base, TimestampMixin):
    # ...

# ❌ PostAnalytics - DOES NOT EXIST
# ❌ SocialPlatform - Should be "Platform"
# ❌ PostTargetStatus - DOES NOT EXIST
```

---

## The Fix

### Option 1: Fix Imports (RECOMMENDED)

Edit `backend/infrastructure/database/models/__init__.py`:

```python
# BEFORE (BROKEN):
from .social import (
    SocialAccount,
    ScheduledPost,
    PostTarget,
    PostAnalytics,  # ❌ Remove this
    SocialPlatform,  # ❌ Change to Platform
    PostStatus,
    PostTargetStatus,  # ❌ Remove this
)

# AFTER (FIXED):
from .social import (
    SocialAccount,
    ScheduledPost,
    PostTarget,
    Platform,  # ✅ Correct name
    PostStatus,
)
```

Also update the `__all__` export list:

```python
# BEFORE (BROKEN):
__all__ = [
    # ... other exports ...
    "SocialAccount",
    "ScheduledPost",
    "PostTarget",
    "PostAnalytics",  # ❌ Remove
    "SocialPlatform",  # ❌ Change to Platform
    "PostStatus",
    "PostTargetStatus",  # ❌ Remove
]

# AFTER (FIXED):
__all__ = [
    # ... other exports ...
    "SocialAccount",
    "ScheduledPost",
    "PostTarget",
    "Platform",  # ✅ Correct name
    "PostStatus",
]
```

---

### Option 2: Add Missing Models (IF NEEDED BY FRONTEND)

If `PostAnalytics` is expected by the frontend or other code, create it in `social.py`:

```python
# Add to backend/infrastructure/database/models/social.py

class PostAnalytics(Base, TimestampMixin):
    """
    Analytics data for social media posts.

    Tracks engagement metrics for published posts.
    """

    __tablename__ = "post_analytics"

    # Primary key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Reference to post target
    post_target_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("post_targets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Analytics metrics
    likes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comments: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    shares: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    engagement_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Timestamps
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationship
    post_target: Mapped["PostTarget"] = relationship(
        "PostTarget",
        back_populates="analytics",
    )

    def __repr__(self) -> str:
        return f"<PostAnalytics(post_target_id={self.post_target_id}, likes={self.likes})>"
```

Then also add relationship in `PostTarget`:

```python
# In PostTarget class
analytics: Mapped[List["PostAnalytics"]] = relationship(
    "PostAnalytics",
    back_populates="post_target",
    cascade="all, delete-orphan",
)
```

---

### Option 3: Add Alias (IF COMPATIBILITY NEEDED)

If code expects `SocialPlatform` instead of `Platform`, add an alias:

```python
# Add to backend/infrastructure/database/models/social.py

# Alias for backward compatibility
SocialPlatform = Platform
```

---

## Step-by-Step Fix Process

### 1. Open the file

```bash
# Windows
notepad backend\infrastructure\database\models\__init__.py

# Linux/Mac
nano backend/infrastructure/database/models/__init__.py
```

### 2. Find the broken import (line 10-18)

Look for:
```python
from .social import (
```

### 3. Replace with fixed version

```python
from .social import (
    SocialAccount,
    ScheduledPost,
    PostTarget,
    Platform,  # Changed from SocialPlatform
    PostStatus,
)
```

### 4. Update __all__ list (around line 40-55)

Remove these from the list:
- `"PostAnalytics"`
- `"SocialPlatform"`
- `"PostTargetStatus"`

Add this:
- `"Platform"`

### 5. Save the file

### 6. Verify the fix

```bash
cd backend
python -c "from infrastructure.database.models import *; print('✅ Import successful')"
```

Expected output:
```
✅ Import successful
```

If you see an error, the fix didn't work.

---

## After Fixing - Run Tests

```bash
cd backend

# Run all tests
pytest tests/ -v

# Or run just import tests first
pytest tests/conftest.py -v
```

Expected:
- All imports should work
- Test collection should succeed
- Tests may still fail (that's OK for now), but they should at least RUN

---

## Verification Checklist

- [ ] Opened `backend/infrastructure/database/models/__init__.py`
- [ ] Changed `PostAnalytics` → Removed (or created model if needed)
- [ ] Changed `SocialPlatform` → `Platform`
- [ ] Removed `PostTargetStatus` (or added to social.py if needed)
- [ ] Updated `__all__` export list
- [ ] Saved file
- [ ] Ran `python -c "from infrastructure.database.models import *"`
- [ ] Import succeeded without errors
- [ ] Ran `pytest tests/ --collect-only`
- [ ] Test collection succeeded
- [ ] Committed fix to git

---

## If You Still Get Errors

### Error: "cannot import name 'PostAnalytics'"

**Solution:** Remove `PostAnalytics` from `__all__` list too (not just the import)

### Error: "cannot import name 'Platform'"

**Solution:** Check that `social.py` actually exports `Platform` class. If not, you may need to add it.

### Error: "circular import"

**Solution:** Check that you didn't accidentally create a circular dependency. The import order should be:
1. base.py (no imports)
2. user.py (imports base)
3. team.py (imports base, user)
4. Other models (import base, user, team as needed)

---

## Frontend Impact

If the frontend TypeScript types expect these names, update `frontend/lib/api.ts`:

```typescript
// If you see these type references:
export type SocialPlatform = "twitter" | "linkedin" | "facebook" | "instagram";

// They should match the backend. If you renamed to Platform, consider:
export type Platform = "twitter" | "linkedin" | "facebook" | "instagram";

// Or keep SocialPlatform on frontend (frontend doesn't need to match backend exactly)
```

---

## Quick Fix (Copy-Paste Ready)

```python
# backend/infrastructure/database/models/__init__.py

"""
SQLAlchemy database models.
"""

from .base import Base, TimestampMixin
from .user import User, UserRole, UserStatus, SubscriptionTier
from .content import Outline, Article, GeneratedImage, ContentStatus, ContentTone
from .analytics import GSCConnection, KeywordRanking, PagePerformance, DailyAnalytics
from .knowledge import KnowledgeSource, KnowledgeQuery, SourceStatus
from .social import (
    SocialAccount,
    ScheduledPost,
    PostTarget,
    Platform,  # ✅ Fixed: was SocialPlatform
    PostStatus,
)
from .admin import AdminAuditLog, AuditAction, AuditTargetType
from .team import Team, TeamMember, TeamInvitation, TeamMemberRole, InvitationStatus

__all__ = [
    "Base",
    "TimestampMixin",
    "User",
    "UserRole",
    "UserStatus",
    "SubscriptionTier",
    "Outline",
    "Article",
    "GeneratedImage",
    "ContentStatus",
    "ContentTone",
    "GSCConnection",
    "KeywordRanking",
    "PagePerformance",
    "DailyAnalytics",
    "KnowledgeSource",
    "KnowledgeQuery",
    "SourceStatus",
    "SocialAccount",
    "ScheduledPost",
    "PostTarget",
    "Platform",  # ✅ Fixed: was SocialPlatform
    "PostStatus",
    "AdminAuditLog",
    "AuditAction",
    "AuditTargetType",
    "Team",
    "TeamMember",
    "TeamInvitation",
    "TeamMemberRole",
    "InvitationStatus",
]
```

---

## After This Fix

You'll be able to:
1. ✅ Run the test suite
2. ✅ Start the application
3. ✅ Import models without errors
4. ✅ Continue development

This unblocks ~600 tests and enables CI/CD verification!

---

**Next Steps After Fix:**
1. Run `pytest tests/ -v` to see which tests actually fail
2. Fix any remaining test failures
3. Move on to the next critical issue: Social OAuth implementation

---

**Need Help?** Check the full audit report: `INTEGRATION_AUDIT_REPORT.md`
