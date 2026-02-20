# A-Stats Engine

> AI-Powered Content Generation & SEO Platform for Wellness Practitioners

[![CI](https://github.com/your-org/a-stats-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/a-stats-engine/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

A-Stats Engine is a therapeutic content SaaS platform that helps wellness practitioners generate SEO-optimized articles, social media content, and manage their digital presence with AI-powered tools.

### Key Features

- **AI Content Generation** - Create articles with therapeutic persona alignment using Claude
- **Social Echo** - Transform articles into Instagram carousels and Facebook posts
- **Image Generation** - AI-powered featured images with FLUX 1.1 Pro
- **Google Search Console** - Keyword analysis and opportunity detection
- **WordPress Integration** - One-click publishing and archive sync
- **Knowledge Vault** - RAG-powered context injection from your methodology
- **Analytics Dashboard** - Therapeutic ROI metrics and journey phase tracking

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, Tailwind CSS, Zustand |
| Backend | FastAPI, SQLAlchemy, Pydantic |
| Database | PostgreSQL, ChromaDB |
| AI | Anthropic Claude, Replicate |
| Email | Resend |
| Payments | Stripe |

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- PostgreSQL 16 (or use Docker)

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/a-stats-engine.git
   cd a-stats-engine
   ```

2. **Start infrastructure with Docker**
   ```bash
   docker-compose up -d postgres redis chromadb
   ```

3. **Setup backend**
   ```bash
   cd backend
   cp ../.env.example .env
   # Edit .env with your API keys

   # Create virtual environment
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows

   # Install dependencies
   pip install -e ".[dev]"

   # Run migrations
   alembic upgrade head

   # Start server
   uvicorn main:app --reload
   ```

4. **Setup frontend**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

5. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Project Structure

```
a-stats-engine/
├── backend/                 # FastAPI backend
│   ├── core/               # Domain logic
│   │   ├── domain/         # Entities
│   │   ├── use_cases/      # Business logic
│   │   └── interfaces/     # Abstract contracts
│   ├── adapters/           # External service integrations
│   │   ├── ai/             # Anthropic, Replicate
│   │   ├── email/          # Resend
│   │   ├── payments/       # Stripe
│   │   ├── search/         # Google Search Console
│   │   └── cms/            # WordPress
│   ├── api/                # FastAPI routes
│   └── infrastructure/     # Database, config
├── frontend/               # Next.js frontend
│   ├── app/               # App Router pages
│   ├── components/        # React components
│   └── lib/               # Utilities
├── docs/                   # Documentation
└── docker-compose.yml      # Local development
```

## API Documentation

When running in development mode, API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing

```bash
# Backend tests
cd backend
pytest --cov=. -v

# Frontend tests
cd frontend
npm test
```

## Deployment

See [docs/deployment.md](docs/deployment.md) for deployment instructions.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- Documentation: [docs/](docs/)
- Issues: [GitHub Issues](https://github.com/your-org/a-stats-engine/issues)
