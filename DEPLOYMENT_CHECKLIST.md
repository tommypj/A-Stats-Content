# A-Stats Engine — Deployment Variables Checklist

## Vercel (Frontend) — 1 variable

| Variable | Value | Status |
|----------|-------|--------|
| `NEXT_PUBLIC_API_URL` | `https://your-railway-backend-url.up.railway.app` | [ ] |

---

## Railway (Backend)

### Auto-provided by Railway plugins (verify they're linked):
- [ ] `DATABASE_URL` — from PostgreSQL plugin
- [ ] `REDIS_URL` — from Redis plugin
- [ ] `PORT` — auto-provided by Railway

### Must set manually — Critical for app to work:
| Variable | Value | Status |
|----------|-------|--------|
| `ENVIRONMENT` | `production` | [ ] |
| `SECRET_KEY` | *(generate: `python -c "import secrets; print(secrets.token_urlsafe(64))"`)* | [ ] |
| `JWT_SECRET_KEY` | *(generate with same command, different value)* | [ ] |
| `CORS_ORIGINS` | `["https://your-vercel-domain.vercel.app"]` | [ ] |
| `FRONTEND_URL` | `https://your-vercel-domain.vercel.app` | [ ] |

### API Keys — Set the ones you have:
| Variable | Service | Needed for | Status |
|----------|---------|------------|--------|
| `ANTHROPIC_API_KEY` | Anthropic | Content generation | [ ] |
| `OPENAI_API_KEY` | OpenAI | Knowledge vault embeddings | [ ] |
| `REPLICATE_API_TOKEN` | Replicate | Image generation | [ ] |
| `RESEND_API_KEY` | Resend | Sending emails | [ ] |
| `RESEND_FROM_EMAIL` | — | Sender address (default: `noreply@astats.app`) | [ ] |

### LemonSqueezy — Payments (set when ready):
| Variable | Status |
|----------|--------|
| `LEMONSQUEEZY_API_KEY` | [ ] |
| `LEMONSQUEEZY_STORE_ID` | [ ] |
| `LEMONSQUEEZY_WEBHOOK_SECRET` | [ ] |
| `LEMONSQUEEZY_VARIANT_STARTER_MONTHLY` | [ ] |
| `LEMONSQUEEZY_VARIANT_STARTER_YEARLY` | [ ] |
| `LEMONSQUEEZY_VARIANT_PROFESSIONAL_MONTHLY` | [ ] |
| `LEMONSQUEEZY_VARIANT_PROFESSIONAL_YEARLY` | [ ] |
| `LEMONSQUEEZY_VARIANT_ENTERPRISE_MONTHLY` | [ ] |
| `LEMONSQUEEZY_VARIANT_ENTERPRISE_YEARLY` | [ ] |

### OAuth — Update redirect URIs to production domain:
| Variable | Redirect URI | Status |
|----------|-------------|--------|
| `GOOGLE_CLIENT_ID` | `GOOGLE_REDIRECT_URI=https://api.yourdomain.com/api/v1/gsc/callback` | [ ] |
| `GOOGLE_CLIENT_SECRET` | | [ ] |
| `TWITTER_CLIENT_ID` | `TWITTER_REDIRECT_URI=https://api.yourdomain.com/api/v1/social/twitter/callback` | [ ] |
| `TWITTER_CLIENT_SECRET` | | [ ] |
| `LINKEDIN_CLIENT_ID` | `LINKEDIN_REDIRECT_URI=https://api.yourdomain.com/api/v1/social/linkedin/callback` | [ ] |
| `LINKEDIN_CLIENT_SECRET` | | [ ] |
| `FACEBOOK_APP_ID` | `FACEBOOK_REDIRECT_URI=https://api.yourdomain.com/api/v1/social/facebook/callback` | [ ] |
| `FACEBOOK_APP_SECRET` | | [ ] |

### Optional — Skip for now:
| Variable | Default | When to set | Status |
|----------|---------|-------------|--------|
| `CHROMA_HOST` | localhost | When you add ChromaDB service | [ ] |
| `CHROMA_PORT` | 8001 | When you add ChromaDB service | [ ] |
| `S3_BUCKET` | — | When switching to S3 storage | [ ] |
| `S3_REGION` | — | When switching to S3 storage | [ ] |
| `S3_ACCESS_KEY` | — | When switching to S3 storage | [ ] |
| `S3_SECRET_KEY` | — | When switching to S3 storage | [ ] |
