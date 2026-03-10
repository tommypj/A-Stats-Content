---
name: check-deploy
description: Run pre-deploy validation checks for Railway (backend) and Vercel (frontend). Catches common deploy-breaking issues before pushing. Use when user says "ready to deploy?", "pre-deploy check", "check deploy", "will this deploy?", or "deploy check".
disable-model-invocation: true
---

# Pre-Deploy Validation

Run all checks that catch known deploy-breaking issues for this project. Report results as a checklist.

## Check 1: Frontend TypeScript Compilation

```bash
cd D:/A-Stats-Online/frontend && npx tsc --noEmit --pretty 2>&1 | tail -30
```

**Pass:** No errors. **Fail:** Fix type errors before deploying.

## Check 2: Frontend ESLint

```bash
cd D:/A-Stats-Online/frontend && npx next lint 2>&1 | tail -20
```

**Pass:** No errors (warnings OK). **Fail:** Fix lint errors.

## Check 3: Frontend Build

```bash
cd D:/A-Stats-Online/frontend && npm run build 2>&1 | tail -30
```

**Pass:** Build succeeds. **Fail:** Fix build errors — Vercel will reject this.

## Check 4: Alembic Migration Chain Integrity

```bash
cd D:/A-Stats-Online/backend && grep -h "^down_revision\|^revision" infrastructure/database/migrations/versions/*.py | paste - - | sort -t'"' -k2 -n | tail -15
```

**Verify:** Each `down_revision` matches the previous migration's `revision`. No gaps, no forks. Migration 009 is an intentional placeholder — skip it.

## Check 5: Railway-Breaking Patterns

### 5a. FK columns must use UUID, not VARCHAR

```bash
cd D:/A-Stats-Online/backend && grep -rn "VARCHAR.*ForeignKey\|String.*ForeignKey" infrastructure/database/models/ --include="*.py"
```

**Pass:** No results. **Fail:** Change `VARCHAR`/`String` FK columns to `UUID(as_uuid=True)`.

### 5b. Pydantic v2 ClassVar annotations

```bash
cd D:/A-Stats-Online/backend && grep -rn "Set\[str\]" schemas/ --include="*.py" | grep -v "ClassVar"
```

**Pass:** No results (all `Set[str]` class variables use `ClassVar`). **Fail:** Add `ClassVar` annotation.

### 5c. Idempotent migrations (new migrations only)

Check that any recent migrations use `DO $$ BEGIN IF NOT EXISTS` pattern:

```bash
cd D:/A-Stats-Online/backend && for f in $(ls infrastructure/database/migrations/versions/*.py | sort -t_ -k1 -n | tail -3); do echo "=== $f ==="; grep -c "IF NOT EXISTS\|IF EXISTS\|DO \$\$" "$f"; done
```

**Pass:** Each migration has at least one idempotent guard. **Fail:** Wrap DDL in `DO $$ BEGIN IF NOT EXISTS ... END $$;`.

## Check 6: Environment Variables

Compare `.env.example` against what's expected:

```bash
cd D:/A-Stats-Online && grep -oP '^[A-Z_]+=' .env.example | sort
```

Remind user to verify these are set in Railway and Vercel environments. Known issues:
- **Sentry DSN** may be truncated/malformed in Railway — verify manually
- **`google-auth>=2.27.0`** is required for Google OAuth verification

## Check 7: Backend Import Check

Quick smoke test that the backend app can import without errors:

```bash
cd D:/A-Stats-Online/backend && python -c "from api.main import app; print('Backend imports OK')" 2>&1
```

**Pass:** Prints "Backend imports OK". **Fail:** Fix import errors.

## Results Report

Present results as a checklist:

```
## Deploy Readiness Report

- [x] Frontend TypeScript — no errors
- [x] Frontend ESLint — clean
- [x] Frontend Build — success
- [x] Migration Chain — valid
- [x] FK Column Types — all UUID
- [x] Pydantic ClassVar — annotated
- [x] Migration Idempotency — guarded
- [ ] Env Vars — VERIFY MANUALLY (Sentry DSN, Google Auth)
- [x] Backend Imports — OK

**Verdict:** Ready to deploy / NOT ready — fix N issues above
```

## Deploy Commands (for reference, do NOT run automatically)

- **Frontend (Vercel):** Pushes to `master` auto-deploy
- **Backend (Railway):** Pushes to `master` auto-deploy; migrations run automatically
- **Manual Railway redeploy:** `railway redeploy --yes` (NOT `railway up` — broken on Windows)
- **Manual migration:** `railway run alembic upgrade head`
