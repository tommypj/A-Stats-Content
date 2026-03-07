---
name: run-migrations
description: Validate and run Alembic migrations — checks chain integrity, previews pending migrations, and runs upgrade. Use when deploying, after creating migrations, or when user says "run migrations", "migrate", or "alembic upgrade".
disable-model-invocation: true
---

# Run Migrations

Validate the Alembic migration chain and run `alembic upgrade head`.

## Steps

### 1. Validate migration chain

```bash
cd D:/A-Stats-Online/backend
ls infrastructure/database/migrations/versions/*.py | sort -t_ -k1 -n | tail -10
```

Check that `down_revision` values form a continuous chain with no gaps or forks:

```bash
cd D:/A-Stats-Online/backend
grep -h "^down_revision\|^revision" infrastructure/database/migrations/versions/*.py | paste - - | sort -t'"' -k2 -n | tail -10
```

### 2. Check current DB state

```bash
cd D:/A-Stats-Online/backend
uv run alembic current
```

### 3. Preview pending migrations

```bash
cd D:/A-Stats-Online/backend
uv run alembic history --indicate-current | head -20
```

### 4. Run upgrade

Only after confirming the chain is valid and showing the user what will run:

```bash
cd D:/A-Stats-Online/backend
uv run alembic upgrade head
```

### 5. Verify

```bash
cd D:/A-Stats-Online/backend
uv run alembic current
```

## Safety Rules

- ALWAYS show pending migrations and ask for confirmation before running upgrade
- If any migration has a broken `down_revision` chain, STOP and report the issue
- If migration 009 appears — it's an intentional placeholder, skip it in validation
- For Railway deploys: remind user to run via `railway run alembic upgrade head`
