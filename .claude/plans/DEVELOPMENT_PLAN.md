# A-Stats Content SaaS - Master Development Plan

> **Project:** A-Stats Engine - AI-Powered Content Generation & SEO Platform
> **Version:** 2.0 (Clean Rebuild)
> **Created:** 2026-02-20
> **Overseer:** Claude Opus 4.5

---

## Executive Summary

A-Stats is a therapeutic content SaaS platform that helps wellness practitioners generate SEO-optimized articles, social media content, and manage their digital presence. The platform integrates AI content generation, image creation, WordPress publishing, and Google Search Console analytics.

### Core Value Proposition
- AI-generated articles with therapeutic persona alignment
- Social media repurposing (Instagram carousels, Facebook posts)
- SEO keyword analysis via Google Search Console
- One-click WordPress publishing
- Knowledge vault with RAG context injection

---

## Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Frontend** | Next.js 14 (App Router) | Server components, streaming, TypeScript |
| **Styling** | Tailwind CSS | Utility-first, therapeutic color palette |
| **State** | Zustand + React Query | Simple state + server cache |
| **Backend** | FastAPI | Async, Pydantic, OpenAPI auto-docs |
| **Database** | PostgreSQL + Alembic | Relational data + migrations |
| **Vector DB** | ChromaDB | Knowledge vault embeddings |
| **AI Content** | Anthropic Claude API | Article generation, persona alignment |
| **AI Images** | Replicate (FLUX 1.1 Pro) | Featured image generation |
| **Email** | Resend | Transactional emails, weekly summaries |
| **Payments** | Stripe | Subscriptions, credit packs |
| **Auth** | JWT + OAuth2 | Google OAuth for GSC |
| **Storage** | S3-compatible | Image storage, exports |
| **Hosting** | Vercel (FE) + Railway/Fly.io (BE) | Scalable, cost-effective |
| **Version Control** | GitHub | Monorepo with CI/CD |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (Next.js 14)                          │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │Dashboard│ │Content  │ │Social   │ │Analytics│ │Settings │           │
│  │         │ │Lab      │ │Echo     │ │& ROI    │ │& Billing│           │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘           │
│       └───────────┴───────────┴───────────┴───────────┘                 │
│                               │ API Client                               │
└───────────────────────────────┼─────────────────────────────────────────┘
                                │ HTTPS / WebSocket
┌───────────────────────────────┼─────────────────────────────────────────┐
│                           BACKEND (FastAPI)                              │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                         API LAYER (Routes)                        │   │
│  │  /auth  /content  /social  /images  /gsc  /wordpress  /billing   │   │
│  └──────────────────────────────┬───────────────────────────────────┘   │
│                                 │                                        │
│  ┌──────────────────────────────┴───────────────────────────────────┐   │
│  │                      USE CASES (Business Logic)                   │   │
│  │  GenerateArticle │ CreateSocialEcho │ AnalyzeKeywords │ ...       │   │
│  └──────────────────────────────┬───────────────────────────────────┘   │
│                                 │                                        │
│  ┌──────────────────────────────┴───────────────────────────────────┐   │
│  │                         DOMAIN (Entities)                         │   │
│  │  User │ Outline │ Article │ SocialPost │ Keyword │ Subscription   │   │
│  └──────────────────────────────┬───────────────────────────────────┘   │
│                                 │                                        │
│  ┌──────────────────────────────┴───────────────────────────────────┐   │
│  │                    ADAPTERS (External Services)                   │   │
│  │  AnthropicAdapter │ ReplicateAdapter │ StripeAdapter │ ...        │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                    │              │              │
           ┌────────┴───┐   ┌──────┴──────┐   ┌──┴───────┐
           │ PostgreSQL │   │  ChromaDB   │   │ External │
           │  (Data)    │   │  (Vectors)  │   │  APIs    │
           └────────────┘   └─────────────┘   └──────────┘
```

---

## Modular Architecture

The system is designed for extensibility with plugin-style modules:

```
backend/
├── core/
│   ├── domain/           # Entities (pure, no dependencies)
│   ├── use_cases/        # Business logic
│   └── interfaces/       # Abstract contracts
├── adapters/
│   ├── ai/               # Anthropic, Replicate
│   ├── email/            # Resend
│   ├── payments/         # Stripe
│   ├── search/           # Google Search Console
│   ├── cms/              # WordPress
│   └── storage/          # S3, local
├── api/
│   └── routes/           # FastAPI endpoints
├── modules/              # FUTURE EXPANSION
│   ├── website_crawler/  # Crawl & analyze sites
│   ├── article_fetcher/  # Import external articles
│   ├── seo_auditor/      # Full SEO analysis
│   └── competitor_spy/   # Competitor tracking
└── infrastructure/
    ├── database/         # SQLAlchemy models
    ├── migrations/       # Alembic
    └── config/           # Settings
```

### Future Module Hooks
Each module follows a standard interface:
```python
class ModuleInterface(ABC):
    @abstractmethod
    async def execute(self, context: ModuleContext) -> ModuleResult: ...
    @abstractmethod
    def get_routes(self) -> list[APIRouter]: ...
    @abstractmethod
    def get_background_tasks(self) -> list[BackgroundTask]: ...
```

---

## Development Phases

### Phase 0: Foundation & Infrastructure
**Duration:** 3-4 sessions
**Agent:** Operator + Builder

| Task | Description | Priority |
|------|-------------|----------|
| GitHub Repository | Create monorepo with branch protection | Critical |
| Project Structure | Scaffold backend + frontend directories | Critical |
| Database Setup | PostgreSQL + Alembic migrations | Critical |
| Environment Config | .env management, secrets | Critical |
| Docker Compose | Local development environment | High |
| CI/CD Pipeline | GitHub Actions for lint, test, deploy | High |
| Documentation | README, CONTRIBUTING, API docs | Medium |

**Deliverables:**
- [ ] GitHub repo with monorepo structure
- [ ] Docker Compose for local dev (Postgres, Redis, ChromaDB)
- [ ] Base FastAPI app with health check
- [ ] Base Next.js app with Tailwind configured
- [ ] Alembic migrations setup
- [ ] GitHub Actions workflow

---

### Phase 1: Authentication & User Management
**Duration:** 2-3 sessions
**Agent:** Gatekeeper + Builder

| Task | Description | Priority |
|------|-------------|----------|
| User Entity | SQLAlchemy model with Pydantic schemas | Critical |
| JWT Auth | Access + refresh token flow | Critical |
| Registration | Email/password signup | Critical |
| Login | Email/password + token issuance | Critical |
| Google OAuth | OAuth2 flow for GSC connection | Critical |
| Email Verification | Resend integration for verify emails | High |
| Password Reset | Forgot password flow | High |
| Session Management | Token refresh, logout | High |

**Deliverables:**
- [ ] /auth routes (register, login, refresh, logout)
- [ ] JWT middleware with user injection
- [ ] Google OAuth2 flow
- [ ] Resend email adapter
- [ ] Frontend auth pages (login, register, verify)

---

### Phase 2: Core Content Engine
**Duration:** 4-5 sessions
**Agent:** Builder + Librarian

| Task | Description | Priority |
|------|-------------|----------|
| Outline Entity | Content outline with keyword, status | Critical |
| Article Entity | Generated content with sections | Critical |
| Anthropic Adapter | Claude API integration | Critical |
| Content Generation | Full article from outline | Critical |
| Async Generation | Background job with progress | Critical |
| WebSocket Progress | Real-time progress updates | High |
| Persona System | Therapeutic Guide voice profiles | High |
| Brief Injection | Custom AI direction | Medium |
| Credit Tracking | Usage metering per action | High |

**Deliverables:**
- [ ] /content routes (create, generate, status)
- [ ] Anthropic adapter with streaming
- [ ] Background task system (Celery or ARQ)
- [ ] WebSocket endpoint for progress
- [ ] Persona intensity configuration

---

### Phase 3: Image Generation
**Duration:** 2 sessions
**Agent:** Builder + Visualizer

| Task | Description | Priority |
|------|-------------|----------|
| Replicate Adapter | FLUX 1.1 Pro integration | Critical |
| Generate Image | Create featured image from prompt | Critical |
| Image Status | Poll generation progress | High |
| Image Upload | Custom image upload + WebP conversion | High |
| Alt Text Generation | Claude Vision for SEO alt text | Medium |
| Image Optimization | Compression, format conversion | Medium |

**Deliverables:**
- [ ] /images routes (generate, upload, optimize)
- [ ] Replicate adapter
- [ ] Image storage (S3 or local)
- [ ] WebP conversion utility
- [ ] Claude Vision alt text generator

---

### Phase 4: Social Echo Module
**Duration:** 2-3 sessions
**Agent:** Builder + Empath

| Task | Description | Priority |
|------|-------------|----------|
| Social Post Entity | Instagram + Facebook content | Critical |
| Generate Social Echo | Transform article to social posts | Critical |
| Instagram Carousel | 5-slide format (Hook, Problem, Solution, Insight, CTA) | Critical |
| Facebook Post | Long-form companion post | High |
| Edit Slides | Modify individual carousel slides | High |
| Regenerate | Refresh social content | Medium |

**Deliverables:**
- [ ] /social routes (generate, edit, export)
- [ ] Social Echo use case with Claude
- [ ] Carousel data structure
- [ ] Frontend preview components

---

### Phase 5: Google Search Console Integration
**Duration:** 2-3 sessions
**Agent:** Gatekeeper + Librarian

| Task | Description | Priority |
|------|-------------|----------|
| GSC OAuth | Authorization flow for Search Console | Critical |
| Token Management | Encrypted storage, auto-refresh | Critical |
| Fetch Analytics | Query performance data | Critical |
| Journey Phase Mapping | Discovery/Validation/Action classification | High |
| Keyword Opportunities | Identify content gaps | High |
| Filters | Impressions, position, date range | Medium |

**Deliverables:**
- [ ] /gsc routes (auth, properties, analytics)
- [ ] GSC adapter with token encryption
- [ ] Journey phase classifier
- [ ] Opportunity detection algorithm

---

### Phase 6: WordPress Integration
**Duration:** 2 sessions
**Agent:** Builder + Operator

| Task | Description | Priority |
|------|-------------|----------|
| WP Connection | REST API authentication | Critical |
| Sync Articles | Import existing posts | High |
| Push Content | Publish articles to WP | Critical |
| Push Social | Create draft from carousel | High |
| Media Sync | Image library integration | Medium |
| Journey Tags | Apply SEO stage tags | Medium |

**Deliverables:**
- [ ] /wordpress routes (connect, sync, push)
- [ ] WordPress REST adapter
- [ ] Article sync with metadata
- [ ] Featured image upload

---

### Phase 7: Knowledge Vault (RAG)
**Duration:** 2 sessions
**Agent:** Librarian

| Task | Description | Priority |
|------|-------------|----------|
| ChromaDB Setup | Vector database configuration | Critical |
| Document Upload | PDF/text ingestion | Critical |
| Chunking | Smart text splitting | High |
| Embedding | OpenAI or local embeddings | High |
| Semantic Search | Query knowledge base | Critical |
| Context Injection | RAG for content generation | High |

**Deliverables:**
- [ ] /knowledge routes (upload, query, delete)
- [ ] ChromaDB adapter
- [ ] Document processor
- [ ] RAG integration in content generation

---

### Phase 8: Analytics & ROI
**Duration:** 2 sessions
**Agent:** Librarian + Strategist

| Task | Description | Priority |
|------|-------------|----------|
| Therapeutic ROI | Custom ROI metrics | High |
| Journey Heatmap | Stage distribution visualization | High |
| Growth Velocity | Month-over-month trends | Medium |
| Executive View | Quick health summary | High |
| Weekly Performance | Automated performance cards | Medium |

**Deliverables:**
- [ ] /analytics routes
- [ ] ROI calculation engine
- [ ] Heatmap data aggregation
- [ ] Frontend dashboard charts (Recharts)

---

### Phase 9: Billing & Subscriptions
**Duration:** 2-3 sessions
**Agent:** Gatekeeper + Builder

| Task | Description | Priority |
|------|-------------|----------|
| Stripe Integration | Customer, subscription, webhook | Critical |
| Tier System | Free/Pro/Elite plans | Critical |
| Credit Packs | One-time purchases | High |
| Usage Tracking | Metered billing support | High |
| Billing Portal | Manage subscription | High |
| Webhook Security | Signature verification | Critical |

**Deliverables:**
- [ ] /billing routes
- [ ] Stripe adapter with webhooks
- [ ] Subscription tier enforcement
- [ ] Usage tracking middleware

---

### Phase 10: Email System
**Duration:** 1-2 sessions
**Agent:** Builder + Empath

| Task | Description | Priority |
|------|-------------|----------|
| Resend Integration | Email sending adapter | Critical |
| Welcome Email | Registration confirmation | High |
| Verification Email | Email verification flow | Critical |
| Weekly Summary | Automated performance digest | Medium |
| Notification Hub | Centralized notification routing | Medium |

**Deliverables:**
- [ ] Resend adapter
- [ ] Email templates (React Email)
- [ ] Scheduled summary job
- [ ] Notification preferences

---

### Phase 11: Frontend - Dashboard & Core UI
**Duration:** 3-4 sessions
**Agent:** Visualizer

| Task | Description | Priority |
|------|-------------|----------|
| Design System | Therapeutic color palette, components | Critical |
| Layout | Sidebar, header, responsive shell | Critical |
| Dashboard | Stats, recent activity, quick actions | Critical |
| Content Lab | Outline list, editor, preview | Critical |
| Settings | User preferences, integrations | High |
| Billing Page | Plans, usage, portal link | High |

**Deliverables:**
- [ ] Tailwind config with therapeutic theme
- [ ] Reusable component library
- [ ] Dashboard page
- [ ] Content management pages
- [ ] Settings pages

---

### Phase 12: Frontend - Advanced Features
**Duration:** 2-3 sessions
**Agent:** Visualizer

| Task | Description | Priority |
|------|-------------|----------|
| Social Echo Workspace | Carousel preview, editor | High |
| Analytics Dashboard | Charts, heatmaps | High |
| Knowledge Vault UI | Document management | Medium |
| WebSocket Integration | Real-time progress bars | High |
| Mobile Responsiveness | S23 Ultra optimization | High |

**Deliverables:**
- [ ] Social Echo page with phone mockup
- [ ] Analytics page with Recharts
- [ ] Knowledge vault page
- [ ] Global progress bar component

---

### Phase 13: Admin Panel
**Duration:** 1-2 sessions
**Agent:** Gatekeeper + Builder

| Task | Description | Priority |
|------|-------------|----------|
| Admin Routes | User management, system control | High |
| User List | View, edit, delete users | High |
| System Health | Database stats, job queues | Medium |
| Cleanup Scripts | Stale data purge | Medium |
| Admin UI | Protected admin pages | High |

**Deliverables:**
- [ ] /admin routes with superuser check
- [ ] Admin dashboard
- [ ] User management UI
- [ ] System health indicators

---

### Phase 14: Testing & Quality
**Duration:** 2 sessions
**Agent:** Builder + Strategist

| Task | Description | Priority |
|------|-------------|----------|
| Unit Tests | Domain logic, use cases | Critical |
| Integration Tests | API endpoints | Critical |
| E2E Tests | Critical user flows | High |
| Load Testing | Performance benchmarks | Medium |
| Security Audit | OWASP top 10 review | High |

**Deliverables:**
- [ ] pytest suite with 80%+ coverage
- [ ] Playwright E2E tests
- [ ] Security checklist completion
- [ ] Performance baseline

---

### Phase 15: Deployment & Launch
**Duration:** 2 sessions
**Agent:** Operator

| Task | Description | Priority |
|------|-------------|----------|
| Production Build | Optimized Docker images | Critical |
| Database Migration | Production Postgres setup | Critical |
| Environment Secrets | Secure secret management | Critical |
| Domain & SSL | DNS, certificates | Critical |
| Monitoring | Logging, error tracking | High |
| Backup Strategy | Database backup automation | High |

**Deliverables:**
- [ ] Production deployment on Vercel + Railway/Fly
- [ ] Monitoring with Sentry
- [ ] Automated backups
- [ ] Launch checklist completion

---

## Agent Assignments Summary

| Phase | Primary Agent | Support Agent | Focus Area |
|-------|---------------|---------------|------------|
| 0 | Operator | Builder | Infrastructure |
| 1 | Gatekeeper | Builder | Security, Auth |
| 2 | Builder | Librarian | Core Engine |
| 3 | Builder | Visualizer | Images |
| 4 | Builder | Empath | Social Content |
| 5 | Gatekeeper | Librarian | GSC Security |
| 6 | Builder | Operator | WordPress |
| 7 | Librarian | - | RAG System |
| 8 | Librarian | Strategist | Analytics |
| 9 | Gatekeeper | Builder | Payments |
| 10 | Builder | Empath | Email |
| 11 | Visualizer | - | Frontend Core |
| 12 | Visualizer | - | Frontend Advanced |
| 13 | Gatekeeper | Builder | Admin |
| 14 | Builder | Strategist | Testing |
| 15 | Operator | - | Deployment |

---

## GitHub Repository Structure

```
a-stats-engine/
├── .github/
│   └── workflows/
│       ├── ci.yml           # Lint, test on PR
│       ├── deploy-be.yml    # Backend deployment
│       └── deploy-fe.yml    # Frontend deployment
├── backend/
│   ├── core/
│   ├── adapters/
│   ├── api/
│   ├── infrastructure/
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── types/
│   ├── package.json
│   └── Dockerfile
├── docs/
│   ├── api/
│   ├── architecture/
│   └── deployment/
├── docker-compose.yml
├── .env.example
└── README.md
```

### Branch Strategy
- `main` - Production-ready code
- `develop` - Integration branch
- `feature/*` - Feature branches
- `fix/*` - Bug fixes
- `release/*` - Release preparation

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| API Response Time | < 200ms (p95) | Monitoring |
| Article Generation | < 60s | Timer |
| Test Coverage | > 80% | pytest-cov |
| Lighthouse Score | > 90 | Lighthouse CI |
| Uptime | 99.9% | Monitoring |
| Error Rate | < 0.1% | Sentry |

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| API rate limits | High | Implement queuing, caching |
| Token expiration | Medium | Auto-refresh, graceful degradation |
| Stripe webhook failures | High | Idempotency, retry logic |
| Database overload | High | Connection pooling, query optimization |
| AI content quality | Medium | Shadow review, persona calibration |

---

## Future Expansion Modules

These modules are designed to be added after MVP launch:

### Module: Website Crawler
- Crawl and analyze any website
- Extract content structure
- Identify SEO issues

### Module: Article Fetcher
- Import articles from URLs
- Parse and structure content
- Competitor content analysis

### Module: SEO Auditor
- Full technical SEO audit
- Page speed analysis
- Mobile-friendliness check
- Schema markup validation

### Module: Competitor Intelligence
- Track competitor rankings
- Content gap analysis
- Backlink monitoring

---

## Next Steps

1. **Approve this plan** - Review and confirm scope
2. **Create GitHub repository** - Initialize monorepo
3. **Begin Phase 0** - Infrastructure setup
4. **Daily standups** - Track progress via AGENT_LOG.md

---

*Plan created by The Overseer*
*A-Stats Engine v2.0*
