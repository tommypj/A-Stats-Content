---
name: railway-logs
description: Check Railway deployment status and recent logs for the backend. Use when user says "check railway", "backend logs", "why did deploy fail", "railway status", "deploy logs", or "backend down".
disable-model-invocation: true
---

# Railway Logs & Debug

Quick Railway deployment diagnostics for the A-Stats backend.

## Step 1: Check Deployment Status

```bash
railway deployment list 2>&1 | head -15
```

Look for: latest deployment status (SUCCESS, FAILED, DEPLOYING, CRASHED).

## Step 2: View Recent Logs

```bash
railway logs --latest 2>&1 | tail -60
```

Scan for:
- **Import errors** — missing dependency or wrong module path
- **Migration errors** — broken chain, syntax error, FK type mismatch
- **Startup errors** — port binding, env var missing, DB connection failure
- **Runtime errors** — unhandled exceptions, timeouts

## Step 3: Common Railway Failure Patterns

| Error Pattern | Cause | Fix |
|---------------|-------|-----|
| `ForeignKey ... VARCHAR` | FK column uses String instead of UUID | Change to `UUID(as_uuid=True)` |
| `ClassVar` / unannotated | Pydantic v2 class variable | Add `ClassVar[Set[str]]` annotation |
| `alembic.util.exc.CommandError` | Broken migration chain | Fix `down_revision` in latest migration |
| `asyncpg.InvalidCatalogNameError` | Wrong DATABASE_URL | Check Railway env vars |
| `ModuleNotFoundError` | Missing dependency | Add to `pyproject.toml` dependencies |
| `os error 1` from `railway up` | Windows incompatibility | Use `railway redeploy --yes` instead |
| Port bind failure | PORT env var not set | Railway sets PORT automatically — don't hardcode |
| `google.auth` error | `google-auth<2.27.0` | Ensure `google-auth>=2.27.0` in deps |

## Step 4: Health Check

```bash
curl -s https://a-stats-content-production.up.railway.app/api/v1/health | python -m json.tool 2>/dev/null || echo "Backend unreachable"
```

```bash
curl -s https://a-stats-content-production.up.railway.app/api/v1/health/db | python -m json.tool 2>/dev/null || echo "DB health check failed"
```

## Step 5: If Deploy Failed — Redeploy

**Do NOT use `railway up`** — it fails on Windows with `os error 1`.

Instead:
```bash
railway redeploy --yes
```

Or push to `master` — Railway auto-deploys on push.

## Step 6: Migration Issues

If the error is migration-related:

```bash
railway run alembic current
railway run alembic history --indicate-current | head -20
```

To run pending migrations manually:
```bash
railway run alembic upgrade head
```

## Report Format

```
## Railway Status

**Deployment:** SUCCESS / FAILED / CRASHED
**Last deploy:** <timestamp>
**Health:** OK / DEGRADED / DOWN
**DB:** Connected / Error

### Issues Found
- <issue description + fix>

### Recommended Action
- <what to do next>
```
