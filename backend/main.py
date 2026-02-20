"""A-Stats Engine - Main FastAPI Application."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from rich.console import Console

from infrastructure.config import get_settings
from infrastructure.database import init_db, close_db
from api.routes import api_router

console = Console()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    console.print(f"[bold green]Starting {settings.app_name} v{settings.app_version}[/bold green]")
    console.print(f"Environment: {settings.environment}")

    if settings.is_development:
        console.print("[yellow]Development mode - initializing database...[/yellow]")
        await init_db()

    console.print("[green]Application started successfully![/green]")

    yield

    # Shutdown
    console.print("[yellow]Shutting down...[/yellow]")
    await close_db()
    console.print("[red]Application stopped.[/red]")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="AI-Powered Content Generation & SEO Platform",
    version=settings.app_version,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs" if settings.is_development else "disabled",
        "health": "/api/v1/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_development,
        workers=settings.workers if not settings.is_development else 1,
    )
