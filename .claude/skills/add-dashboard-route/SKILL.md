---
name: add-dashboard-route
description: Add a new dashboard page with all required wiring — page component, middleware exclusion, breadcrumb label, sidebar entry. Use when user says "add page", "new dashboard page", "new section", "add route", or "dashboard page for".
disable-model-invocation: true
---

# Add Dashboard Route

Wire up a new dashboard page with all 4 required touchpoints.

Ask the user for:
- **Route slug** (e.g., `campaigns`, `audit-logs`)
- **Display name** (e.g., "Campaigns", "Audit Logs")
- **Icon** (Lucide icon name, e.g., `Target`, `ScrollText`)
- **Tier gating** (free / starter / professional / agency — default: free)
- **Nav placement** (top-level or submenu under Content/SEO/Analytics/Agency)

## Step 1: Create Page Component

Create `frontend/app/(dashboard)/<route-slug>/page.tsx`:

```tsx
"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
// If tier-gated:
// import { TierGate } from "@/components/ui/tier-gate";

export default function <PageName>Page() {
  // If tier-gated, wrap the entire return in:
  // <TierGate requiredTier="starter">...</TierGate>

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-text-primary">
          <Display Name>
        </h1>
        <p className="mt-1 text-sm text-text-muted">
          <Description>
        </p>
      </div>

      {/* Content card */}
      <div className="rounded-2xl border border-surface-tertiary bg-surface p-6 shadow-soft">
        {/* Page content */}
      </div>
    </div>
  );
}
```

### Design Token Rules (MANDATORY)

| Use | Token | NEVER Use |
|-----|-------|-----------|
| Page background | `bg-surface` | `bg-white` |
| Card background | `bg-surface` or `bg-surface-secondary` | `bg-white`, `bg-gray-*` |
| Primary text | `text-text-primary` | `text-gray-900` |
| Secondary text | `text-text-secondary` | `text-gray-700` |
| Muted text | `text-text-muted` | `text-gray-500` |
| Borders | `border-surface-tertiary` | `border-gray-*` |
| Cards | `rounded-2xl shadow-soft` | `rounded-lg shadow` |
| Error toasts | `toast.error(parseApiError(err).message)` | `toast.error("Something went wrong")` |

## Step 2: Update Middleware Exclusion

**File:** `frontend/middleware.ts` (~line 19)

Add the route slug to the negative lookahead regex. The regex is a single long string — append the new slug with a `|` separator:

```
Before: ...templates|reports|tags).*)"
After:  ...templates|reports|tags|<route-slug>).*)"
```

**If you forget this:** The route will be intercepted by `next-intl` middleware and get a 404 or redirect to a locale-prefixed path.

## Step 3: Add Breadcrumb Label

**File:** `frontend/components/ui/breadcrumb.tsx`

Add to the `PATH_LABELS` map (keep alphabetical within the map):

```typescript
"<route-slug>": "<Display Name>",
```

For multi-segment routes, add each segment:
```typescript
"audit-logs": "Audit Logs",
"detail": "Detail",
```

## Step 4: Add Sidebar Navigation Entry

**File:** `frontend/app/(dashboard)/layout.tsx`

Add to the `navigation` array. Choose placement based on feature category:

### Top-level item:
```typescript
{ name: "<Display Name>", href: "/<route-slug>", icon: <LucideIcon> },
```

### Submenu item (under existing group):
```typescript
// Find the relevant group (Content, SEO, Analytics, Agency) and add:
{ name: "<Display Name>", href: "/<route-slug>", icon: <LucideIcon> },
```

### Tier-gated item:
```typescript
{ name: "<Display Name>", href: "/<route-slug>", icon: <LucideIcon>, minTier: "starter" },
```

**Import the Lucide icon** at the top of the layout file if not already imported:
```typescript
import { <IconName> } from "lucide-react";
```

## Verification Checklist

After creating the route, verify ALL four touchpoints:

- [ ] Page component exists at `frontend/app/(dashboard)/<route-slug>/page.tsx`
- [ ] Middleware regex includes `<route-slug>` in the exclusion list
- [ ] `PATH_LABELS` has entry for `"<route-slug>"`
- [ ] Sidebar navigation has the entry (correct group, icon, tier)
- [ ] Page uses correct design tokens (no `bg-white`, no `gray-*`)
- [ ] If tier-gated: `TierGate` wrapper with correct `requiredTier`

### Quick Smoke Test

```bash
cd D:/A-Stats-Online/frontend && npx tsc --noEmit --pretty 2>&1 | grep -i error | head -5
```

Then tell the user to visit `/<route-slug>` in the browser to verify.
