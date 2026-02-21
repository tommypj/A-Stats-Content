# Phase 10: Multi-Tenancy Team Context Implementation

## Overview
This document describes the frontend implementation for Phase 10 Multi-tenancy support, specifically focusing on team context integration for content pages.

## Status: PARTIAL IMPLEMENTATION

### Completed Components

#### 1. Team Context (frontend/contexts/TeamContext.tsx)
**Status:** Created with integration points for backend API

**Features:**
- Team state management with React Context
- Team switching between personal and team workspaces
- Permission helpers (canCreate, canEdit, canDelete, isViewer)
- Usage limit tracking (isApproachingLimit, isAtLimit)
- LocalStorage persistence for workspace selection
- Ready for backend team API integration

**Permissions Logic:**
- Personal workspace: Full permissions
- Team OWNER/ADMIN: canCreate, canEdit, canDelete
- Team MEMBER: canCreate, canEdit
- Team VIEWER: Read-only access

#### 2. Content Ownership Badge (frontend/components/team/content-ownership-badge.tsx)
**Status:** Complete and ready to use

**Features:**
- Three variants: compact, default, detailed
- Personal workspace badge (blue theme)
- Team workspace badge (purple theme)
- Team logo support with fallback
- Responsive design

**Usage:**
```tsx
<ContentOwnershipBadge
  teamId={content.team_id}
  teamName={currentTeam?.name}
  isPersonal={!content.team_id}
  variant="compact"
/>
```

#### 3. Usage Limit Warning Components (frontend/components/team/usage-limit-warning.tsx)
**Status:** Complete with two variants

**Components:**
- **UsageLimitWarning:** Detailed warning card for settings/detail pages
- **UsageLimitBanner:** Compact banner for list pages

**Features:**
- Progressive warnings (80%+ yellow, 100% red)
- Progress bar visualization
- Upgrade/manage subscription CTAs
- Team-specific messaging
- Resource-specific limits (articles, outlines, images, storage)

#### 4. API Client Updates (frontend/lib/api.ts)
**Status:** Complete for all content types

**Updated Endpoints:**
- `api.articles.list()` - Added `team_id` parameter
- `api.outlines.list()` - Added `team_id` parameter
- `api.images.list()` - Added `team_id` parameter
- `api.knowledge.sources()` - Added `team_id` parameter
- `api.knowledge.upload()` - Added `teamId` parameter
- `api.social.posts()` - Added `team_id` parameter

**Updated Type Definitions:**
- `Outline` - Added `team_id?: string`
- `Article` - Added `team_id?: string`
- `GeneratedImage` - Added `team_id?: string`
- `KnowledgeSource` - Added `team_id?: string`
- `SocialPost` - Added `team_id?: string`
- All creation inputs updated with `team_id`

#### 5. Articles Page (frontend/app/(dashboard)/articles/page.tsx)
**Status:** Complete with full team context support

**Features:**
- Team context integration via `useTeam()` hook
- Content filter: All | Personal | Team (in team context)
- Usage limit banner for team workspace
- Ownership badges on each article
- Permission-based UI:
  - Create button disabled for viewers
  - Create button disabled when at limit
  - Edit/Delete actions hidden for viewers
  - "View-only mode" banner for viewers
- Dynamic page title based on workspace
- Team-aware data loading with `team_id` parameter

### Pending Implementation

#### Pages to Update (Same Pattern as Articles)

1. **Outlines Page** (frontend/app/(dashboard)/outlines/page.tsx)
   - Add team context integration
   - Add content filter (All | Personal | Team)
   - Add ownership badges
   - Add usage limit checking
   - Update permission logic

2. **Images Page** (frontend/app/(dashboard)/images/page.tsx)
   - Add team context integration
   - Add content filter
   - Add ownership badges
   - Add usage limit checking
   - Update permission logic

3. **Knowledge Page** (frontend/app/(dashboard)/knowledge/page.tsx)
   - Add team context integration
   - Add source ownership badges
   - Add upload permission checks
   - Add usage limit warnings

4. **Social Page** (frontend/app/(dashboard)/social/page.tsx)
   - Add team context integration
   - Add post ownership badges
   - Add permission checks for scheduling

5. **Dashboard Page** (frontend/app/(dashboard)/page.tsx)
   - Show team stats when in team context
   - Show personal stats when in personal workspace
   - Team switcher reminder for new users

#### Detail Pages to Update

1. **Article Detail Page** (frontend/app/(dashboard)/articles/[id]/page.tsx)
   - Show ownership badge
   - Disable edit for viewers
   - Show "Team content" indicator
   - Permission-based form disabling

2. **Outline Detail Page** (frontend/app/(dashboard)/outlines/[id]/page.tsx)
   - Same updates as article detail

3. **Knowledge Source Detail** (frontend/app/(dashboard)/knowledge/sources/[id]/page.tsx)
   - Show ownership badge
   - Permission-based actions

#### Creation Forms to Update

1. **New Article Form** (frontend/app/(dashboard)/articles/new/page.tsx)
   - Show "Creating for: [Team Name]" badge
   - Pass `team_id` to creation API
   - Check usage limits before allowing creation

2. **New Outline Form** (frontend/app/(dashboard)/outlines - CreateOutlineModal)
   - Pass `team_id` to creation API
   - Show team context indicator

3. **Image Generator** (frontend/app/(dashboard)/images/generate/page.tsx)
   - Pass `team_id` to generation API
   - Show team context indicator

4. **Knowledge Upload** (frontend/components/knowledge/upload-modal.tsx)
   - Pass `teamId` to upload function
   - Show team context indicator

### Backend Requirements

**CRITICAL:** The following backend implementations are required before this frontend can be fully functional:

1. **Team Models** (backend/infrastructure/database/models/teams.py)
   - Team table
   - TeamMember table
   - TeamInvitation table
   - TeamRole enum (OWNER, ADMIN, MEMBER, VIEWER)

2. **Team Migration** (backend/infrastructure/database/migrations/)
   - Create teams, team_members, team_invitations tables
   - Add team_id foreign keys to content tables:
     - articles.team_id
     - outlines.team_id
     - generated_images.team_id
     - knowledge_sources.team_id
     - scheduled_posts.team_id

3. **Team API Routes** (backend/api/routes/teams.py)
   - GET /teams - List user's teams
   - GET /teams/:id - Get team details
   - POST /teams - Create team
   - PUT /teams/:id - Update team
   - DELETE /teams/:id - Delete team
   - POST /teams/switch - Switch active team
   - GET /teams/current - Get current team context
   - Team member management endpoints
   - Team invitation endpoints
   - Team billing endpoints

4. **Team Schemas** (backend/api/schemas/teams.py)
   - Already defined in frontend/lib/api.ts
   - Backend needs matching Pydantic schemas

5. **Content API Updates**
   - All content endpoints need team_id query parameter support
   - Authorization checks for team membership
   - Usage limit enforcement per team

6. **Team Usage Tracking**
   - Track content creation per team
   - Track storage usage per team
   - Monthly usage reset
   - GET /teams/:id/billing/usage endpoint

## Implementation Guide

### For Other Content Pages

To update other content pages (Outlines, Images, Knowledge, Social), follow this pattern from Articles:

```tsx
// 1. Import team context and components
import { useTeam } from "@/contexts/TeamContext";
import { ContentOwnershipBadge } from "@/components/team/content-ownership-badge";
import { UsageLimitBanner } from "@/components/team/usage-limit-warning";

// 2. Add team context in component
const {
  currentTeam,
  isPersonalWorkspace,
  canCreate,
  canEdit,
  isViewer,
  usage,
  limits,
  isAtLimit,
} = useTeam();

// 3. Add content filter state
const [contentFilter, setContentFilter] = useState<ContentFilter>("all");

// 4. Update data loading with team_id
async function loadContent() {
  const params: any = { page_size: 50 };

  if (!isPersonalWorkspace && currentTeam) {
    params.team_id = currentTeam.id;
  }

  if (contentFilter === "personal") {
    delete params.team_id;
  } else if (contentFilter === "team" && currentTeam) {
    params.team_id = currentTeam.id;
  }

  const response = await api.content.list(params);
  // ...
}

// 5. Add usage limit banner
{!isPersonalWorkspace && currentTeam && usage && limits && (
  <UsageLimitBanner
    resource="content_type"
    used={usage.content_used}
    limit={limits.content_per_month}
    isTeam={true}
    teamName={currentTeam.name}
  />
)}

// 6. Add content filter UI (in header)
{!isPersonalWorkspace && currentTeam && (
  <div className="flex items-center gap-1 bg-surface-secondary rounded-lg p-1">
    {/* All | Personal | Team buttons */}
  </div>
)}

// 7. Check permissions for create button
const showCreateButton = canCreate && !isAtLimit("content_type");

// 8. Add ownership badge to each item
<ContentOwnershipBadge
  teamId={item.team_id}
  teamName={currentTeam?.name}
  isPersonal={!item.team_id}
  variant="compact"
/>

// 9. Update permission checks for actions
const canModify = canEdit || item.user_id === currentUserId;

// 10. Add viewer banner if needed
{isViewer && (
  <div className="text-xs text-text-muted italic">
    View-only mode: You cannot edit team content
  </div>
)}
```

### For Creation Forms

```tsx
// 1. Get team context
const { currentTeam, isPersonalWorkspace } = useTeam();

// 2. Show creating for indicator
{!isPersonalWorkspace && currentTeam && (
  <div className="mb-4 p-3 bg-purple-50 rounded-lg border border-purple-200">
    <p className="text-sm text-purple-700">
      Creating for: <strong>{currentTeam.name}</strong>
    </p>
  </div>
)}

// 3. Pass team_id when creating
const data = {
  // ... other fields
  team_id: !isPersonalWorkspace && currentTeam ? currentTeam.id : undefined,
};

await api.content.create(data);
```

## Testing Checklist

### Before Backend Integration
- [x] TeamContext compiles without errors
- [x] ContentOwnershipBadge renders correctly (3 variants)
- [x] UsageLimitWarning components render correctly
- [x] API client type definitions are correct
- [x] Articles page compiles and renders

### After Backend Integration
- [ ] Team switching works correctly
- [ ] Content filters work (All | Personal | Team)
- [ ] Ownership badges show correct team/personal state
- [ ] Usage limits are enforced
- [ ] Viewers cannot create/edit content
- [ ] Members can create/edit content
- [ ] Admins/Owners can delete content
- [ ] Team content shows in team context
- [ ] Personal content shows in personal workspace
- [ ] Content creation assigns correct team_id
- [ ] Usage limits are calculated correctly per team

## Migration Notes

### Database Migration Required
Before deploying frontend changes, ensure backend migration is complete:

```sql
-- Add team_id to all content tables
ALTER TABLE articles ADD COLUMN team_id UUID REFERENCES teams(id) ON DELETE CASCADE;
ALTER TABLE outlines ADD COLUMN team_id UUID REFERENCES teams(id) ON DELETE CASCADE;
ALTER TABLE generated_images ADD COLUMN team_id UUID REFERENCES teams(id) ON DELETE CASCADE;
ALTER TABLE knowledge_sources ADD COLUMN team_id UUID REFERENCES teams(id) ON DELETE CASCADE;
ALTER TABLE scheduled_posts ADD COLUMN team_id UUID REFERENCES teams(id) ON DELETE CASCADE;

-- Create indexes for team queries
CREATE INDEX idx_articles_team_id ON articles(team_id);
CREATE INDEX idx_outlines_team_id ON outlines(team_id);
CREATE INDEX idx_generated_images_team_id ON generated_images(team_id);
CREATE INDEX idx_knowledge_sources_team_id ON knowledge_sources(team_id);
CREATE INDEX idx_scheduled_posts_team_id ON scheduled_posts(team_id);
```

### Deployment Steps
1. Deploy backend team models and API
2. Run database migration
3. Test team API endpoints
4. Deploy frontend team context
5. Update remaining content pages
6. Test end-to-end team workflows

## File Structure

```
frontend/
├── contexts/
│   └── TeamContext.tsx                     # ✅ Created
├── components/
│   └── team/
│       ├── content-ownership-badge.tsx     # ✅ Created
│       └── usage-limit-warning.tsx         # ✅ Created
├── lib/
│   └── api.ts                              # ✅ Updated with team_id support
└── app/(dashboard)/
    ├── articles/
    │   ├── page.tsx                        # ✅ Updated with team support
    │   ├── [id]/page.tsx                   # ⏳ Needs update
    │   └── new/page.tsx                    # ⏳ Needs update
    ├── outlines/
    │   ├── page.tsx                        # ⏳ Needs update
    │   └── [id]/page.tsx                   # ⏳ Needs update
    ├── images/
    │   ├── page.tsx                        # ⏳ Needs update
    │   └── generate/page.tsx               # ⏳ Needs update
    ├── knowledge/
    │   ├── page.tsx                        # ⏳ Needs update
    │   └── sources/
    │       ├── page.tsx                    # ⏳ Needs update
    │       └── [id]/page.tsx               # ⏳ Needs update
    ├── social/
    │   ├── page.tsx                        # ⏳ Needs update
    │   └── compose/page.tsx                # ⏳ Needs update
    └── page.tsx                            # ⏳ Needs update (dashboard)
```

Legend:
- ✅ Created/Completed
- ⏳ Pending implementation

## Next Steps

1. **Immediate:**
   - Create or verify backend team models exist
   - Create or verify backend team API routes exist
   - Test team API integration with TeamContext

2. **Short-term:**
   - Update Outlines page (same pattern as Articles)
   - Update Images page (same pattern as Articles)
   - Update Knowledge page
   - Update Social page

3. **Medium-term:**
   - Update all detail pages with permission checks
   - Update all creation forms with team_id support
   - Update Dashboard page with team stats

4. **Testing:**
   - End-to-end testing of team workflows
   - Permission testing (OWNER, ADMIN, MEMBER, VIEWER)
   - Usage limit enforcement testing

## Architecture Decisions

### Why Context API?
- Centralized team state management
- Avoids prop drilling through many components
- Easy access to team data and permissions anywhere
- Persists workspace selection in localStorage

### Why Separate Personal/Team Workspaces?
- Clear mental model for users
- Prevents accidental team content creation
- Allows users to maintain personal content
- Enables easy switching between contexts

### Why Usage Limits at Team Level?
- Team subscription determines limits
- Prevents individual team members from exceeding quota
- Centralizes billing and usage tracking
- Matches typical SaaS multi-tenancy patterns

### Why Permission-Based UI vs Error Messages?
- Better UX (prevent actions vs show errors)
- Clear indication of capabilities
- Reduces support requests
- Matches user expectations for team tools

## Additional Components Needed

### Team Switcher Component
**Location:** `frontend/components/team/team-switcher.tsx`

**Purpose:** Dropdown in header to switch between personal workspace and teams

**Features:**
- Personal workspace option
- List of user's teams
- Current team indicator
- Quick switch without page reload
- Search for teams (if many teams)

### Team Creation Modal
**Location:** `frontend/components/team/create-team-modal.tsx`

**Purpose:** Modal for creating new teams

**Features:**
- Team name input
- Team slug (auto-generated from name)
- Subscription tier selection
- Member invitation (optional)

### Team Settings Page
**Location:** `frontend/app/(dashboard)/teams/[id]/settings/page.tsx`

**Purpose:** Team configuration and management

**Features:**
- Team details editing
- Member management
- Invitation management
- Billing management
- Usage statistics
- Team deletion

## Resources

- TeamContext API: See `frontend/contexts/TeamContext.tsx`
- Component Examples: See `frontend/app/(dashboard)/articles/page.tsx`
- Backend Team Types: Already defined in `frontend/lib/api.ts` (lines 1333-1420)
