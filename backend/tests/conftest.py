"""
Pytest configuration and shared fixtures for backend tests.
"""

import asyncio
import sys
from pathlib import Path

# Add backend directory to path for imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import pytest
from datetime import datetime, timedelta
from typing import AsyncGenerator
from uuid import uuid4

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Import after path is set
from infrastructure.database.models import Base, User
from infrastructure.database.connection import get_db
from core.security import PasswordHasher, TokenService
from infrastructure.config import get_settings

# Initialize security services
password_hasher = PasswordHasher()
settings = get_settings()
token_service = TokenService(secret_key=settings.jwt_secret_key)


# Database URL for testing (in-memory SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session = sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        id=str(uuid4()),
        email="test@example.com",
        password_hash=password_hasher.hash("testpassword123"),
        name="Test User",
        status="active",
        email_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    """Generate authentication headers for test user."""
    access_token = token_service.create_access_token(user_id=test_user.id)
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing."""
    # Import app here to avoid circular imports
    from main import app

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Reset rate limiter state between tests to prevent cross-test 429s
    if hasattr(app.state, "limiter"):
        try:
            app.state.limiter.reset()
        except Exception:
            pass

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


# ============================================================================
# Billing Test Fixtures
# ============================================================================

@pytest.fixture
async def free_user(db_session: AsyncSession) -> User:
    """
    Create a test user with free tier and no subscription.

    Used for testing:
    - Free tier feature limits
    - Upgrade flows
    - Checkout session creation
    """
    user = User(
        id=str(uuid4()),
        email="free@example.com",
        password_hash=password_hasher.hash("testpassword123"),
        name="Free User",
        subscription_tier="free",
        subscription_status="active",
        lemonsqueezy_customer_id=None,
        lemonsqueezy_subscription_id=None,
        lemonsqueezy_variant_id=None,
        status="active",
        email_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def subscribed_user(db_session: AsyncSession) -> User:
    """
    Create a test user with professional tier and active subscription.

    Used for testing:
    - Subscription management
    - Portal access
    - Cancellation flows
    - Webhook processing
    """
    user = User(
        id=str(uuid4()),
        email="subscribed@example.com",
        password_hash=password_hasher.hash("testpassword123"),
        name="Subscribed User",
        subscription_tier="professional",
        subscription_status="active",
        lemonsqueezy_customer_id="12345",
        lemonsqueezy_subscription_id="67890",
        lemonsqueezy_variant_id="1",
        subscription_expires=datetime.utcnow() + timedelta(days=30),
        status="active",
        email_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def valid_webhook_payload() -> dict:
    """
    Sample subscription_created webhook payload from LemonSqueezy.

    Structure matches actual LemonSqueezy webhook format with:
    - meta.event_name: Event type
    - meta.custom_data: Optional custom data (e.g., user_id)
    - data: Event data (subscription, order, etc.)
    """
    return {
        "meta": {
            "event_name": "subscription_created",
            "custom_data": {
                "user_id": str(uuid4()),
            },
        },
        "data": {
            "type": "subscriptions",
            "id": "1",
            "attributes": {
                "store_id": 12345,
                "customer_id": 1,
                "order_id": 1,
                "product_id": 1,
                "variant_id": 1,
                "product_name": "Professional Plan",
                "variant_name": "Monthly",
                "status": "active",
                "status_formatted": "Active",
                "card_brand": "visa",
                "card_last_four": "4242",
                "pause": None,
                "cancelled": False,
                "trial_ends_at": None,
                "billing_anchor": 1,
                "urls": {
                    "update_payment_method": "https://example.lemonsqueezy.com/update",
                    "customer_portal": "https://example.lemonsqueezy.com/portal",
                },
                "renews_at": "2024-02-01T00:00:00.000000Z",
                "ends_at": None,
                "created_at": "2024-01-01T00:00:00.000000Z",
                "updated_at": "2024-01-01T00:00:00.000000Z",
            },
        },
    }


@pytest.fixture
def valid_webhook_signature(valid_webhook_payload: dict) -> str:
    """
    Generate valid HMAC-SHA256 signature for webhook payload.

    LemonSqueezy uses HMAC-SHA256 to sign webhook payloads:
    1. Convert payload to JSON string
    2. Create HMAC using webhook secret
    3. Return hexadecimal digest

    This signature is passed in the X-Signature header.
    """
    import hmac
    import hashlib
    import json

    webhook_secret = "test_webhook_secret"
    payload_bytes = json.dumps(valid_webhook_payload).encode()
    signature = hmac.new(
        webhook_secret.encode(),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()
    return signature


@pytest.fixture
def mock_lemonsqueezy_api():
    """
    Mock httpx client for LemonSqueezy API calls.

    Usage:
        with mock_lemonsqueezy_api() as mock_client:
            mock_client.get.return_value = mock_response
            # Test code here

    Useful for testing adapter methods without real API calls.
    """
    from unittest.mock import AsyncMock, patch

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance
        yield mock_instance


# ============================================================================
# Knowledge Vault Test Fixtures
# ============================================================================

@pytest.fixture
def sample_pdf():
    """
    Create a simple PDF for testing document upload.

    Returns minimal valid PDF with magic bytes and basic structure.
    Used for testing PDF upload and processing.
    """
    from io import BytesIO

    # Minimal valid PDF structure
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
>>
>>
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test PDF content) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000317 00000 n
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
410
%%EOF
"""
    return BytesIO(pdf_content)


@pytest.fixture
def sample_txt():
    """
    Simple text content for testing.

    Returns plain text with therapeutic content suitable for
    knowledge base testing.
    """
    from io import BytesIO

    content = b"""Cognitive Behavioral Therapy (CBT) Techniques

CBT is a form of psychotherapy that treats problems and boosts happiness
by modifying dysfunctional emotions, behaviors, and thoughts.

Key Techniques:
1. Cognitive restructuring - Identifying and challenging negative thought patterns
2. Behavioral activation - Scheduling positive activities
3. Exposure therapy - Gradual exposure to feared situations
4. Mindfulness - Present moment awareness
5. Relaxation techniques - Deep breathing and progressive muscle relaxation

These evidence-based techniques have been shown to be effective for
anxiety, depression, and stress management.
"""
    return BytesIO(content)


@pytest.fixture
async def test_source(db_session: AsyncSession, test_user: User):
    """
    Create a KnowledgeSource record for testing.

    Used for testing source retrieval, updates, and deletion.
    """
    from infrastructure.database.models.knowledge import KnowledgeSource, SourceStatus

    source = KnowledgeSource(
        id=str(uuid4()),
        user_id=test_user.id,
        title="Test Document",
        filename="test_document.pdf",
        file_type="pdf",
        file_size=1024,
        file_url="uploads/test_document.pdf",
        status=SourceStatus.PENDING.value,
        chunk_count=0,
    )
    db_session.add(source)
    await db_session.commit()
    await db_session.refresh(source)
    return source


@pytest.fixture
async def processed_source(db_session: AsyncSession, test_user: User):
    """
    Create a completed KnowledgeSource with processed chunks.

    Used for testing query operations that require indexed content.
    """
    from infrastructure.database.models.knowledge import KnowledgeSource, SourceStatus

    source = KnowledgeSource(
        id=str(uuid4()),
        user_id=test_user.id,
        title="Therapy Guide",
        filename="therapy_guide.pdf",
        file_type="pdf",
        file_size=5120,
        file_url="uploads/therapy_guide.pdf",
        status=SourceStatus.COMPLETED.value,
        chunk_count=25,
    )
    db_session.add(source)
    await db_session.commit()
    await db_session.refresh(source)
    return source


@pytest.fixture
async def pending_source(db_session: AsyncSession, test_user: User):
    """
    Create a KnowledgeSource in pending status.

    Used for testing processing status checks.
    """
    from infrastructure.database.models.knowledge import KnowledgeSource, SourceStatus

    source = KnowledgeSource(
        id=str(uuid4()),
        user_id=test_user.id,
        title="Processing Document",
        filename="processing.pdf",
        file_type="pdf",
        file_size=2048,
        file_url="uploads/processing.pdf",
        status=SourceStatus.PENDING.value,
        chunk_count=0,
    )
    db_session.add(source)
    await db_session.commit()
    await db_session.refresh(source)
    return source


@pytest.fixture
async def failed_source(db_session: AsyncSession, test_user: User):
    """
    Create a KnowledgeSource in failed status.

    Used for testing error handling and status reporting.
    """
    from infrastructure.database.models.knowledge import KnowledgeSource, SourceStatus

    source = KnowledgeSource(
        id=str(uuid4()),
        user_id=test_user.id,
        title="Corrupted Document",
        filename="corrupted.pdf",
        file_type="pdf",
        file_size=512,
        file_url="uploads/corrupted.pdf",
        status=SourceStatus.FAILED.value,
        error_message="Failed to parse PDF: Invalid format",
        chunk_count=0,
    )
    db_session.add(source)
    await db_session.commit()
    await db_session.refresh(source)
    return source


@pytest.fixture
async def test_sources(db_session: AsyncSession, test_user: User):
    """
    Create multiple KnowledgeSource records with various statuses.

    Used for testing pagination, filtering, and list operations.
    """
    from infrastructure.database.models.knowledge import KnowledgeSource, SourceStatus

    statuses = [
        SourceStatus.COMPLETED,
        SourceStatus.COMPLETED,
        SourceStatus.PENDING,
        SourceStatus.FAILED,
        SourceStatus.COMPLETED,
    ]

    sources = [
        KnowledgeSource(
            id=str(uuid4()),
            user_id=test_user.id,
            title=f"Document {i}",
            filename=f"document_{i}.pdf",
            file_type="pdf",
            file_size=1024 * i,
            file_url=f"uploads/document_{i}.pdf",
            status=status.value,
            chunk_count=10 * i if status == SourceStatus.COMPLETED else 0,
        )
        for i, status in enumerate(statuses, start=1)
    ]

    for source in sources:
        db_session.add(source)

    await db_session.commit()

    for source in sources:
        await db_session.refresh(source)

    return sources


@pytest.fixture
async def processed_sources(db_session: AsyncSession, test_user: User):
    """
    Create multiple completed KnowledgeSource records.

    Used for testing multi-source queries and filtering.
    """
    from infrastructure.database.models.knowledge import KnowledgeSource, SourceStatus

    filenames = [
        "cbt_techniques.pdf",
        "mindfulness_guide.pdf",
        "stress_management.pdf",
    ]

    sources = [
        KnowledgeSource(
            id=str(uuid4()),
            user_id=test_user.id,
            title=filename.replace("_", " ").replace(".pdf", "").title(),
            filename=filename,
            file_type="pdf",
            file_size=2048,
            file_url=f"uploads/{filename}",
            status=SourceStatus.COMPLETED.value,
            chunk_count=15,
        )
        for filename in filenames
    ]

    for source in sources:
        db_session.add(source)

    await db_session.commit()

    for source in sources:
        await db_session.refresh(source)

    return sources


@pytest.fixture
def mock_chroma_client():
    """
    Mock ChromaDB client for testing vector operations.

    Usage:
        def test_example(mock_chroma_client):
            mock_chroma_client.get_collection.return_value = mock_collection
            # Test code here
    """
    from unittest.mock import Mock

    client = Mock()
    collection = Mock()

    # Mock common ChromaDB methods
    collection.add = Mock()
    collection.query = Mock(return_value={
        'ids': [['chunk1', 'chunk2']],
        'documents': [['Document 1', 'Document 2']],
        'distances': [[0.1, 0.2]],
        'metadatas': [[{'source': 'test.pdf'}, {'source': 'test.pdf'}]]
    })
    collection.delete = Mock()
    collection.count = Mock(return_value=0)

    client.get_or_create_collection = Mock(return_value=collection)
    client.get_collection = Mock(return_value=collection)
    client.heartbeat = Mock()

    return client


@pytest.fixture
def mock_embedding_service():
    """
    Mock embedding generation service.

    Returns deterministic embeddings for testing without API calls.
    """
    from unittest.mock import AsyncMock

    service = AsyncMock()

    # Mock embed_text to return deterministic embeddings
    async def mock_embed_text(text: str):
        # Simple hash-based deterministic embedding
        import hashlib
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        # Generate 384-dimensional vector (common embedding size)
        embedding = [(hash_val >> i) % 100 / 100.0 for i in range(384)]
        return embedding

    # Mock embed_texts for batch processing
    async def mock_embed_texts(texts: list):
        return [await mock_embed_text(text) for text in texts]

    service.embed_text = mock_embed_text
    service.embed_texts = mock_embed_texts

    return service


@pytest.fixture
async def other_user(db_session: AsyncSession) -> User:
    """
    Create a second test user for permission testing.

    Used for testing that users cannot access each other's resources.
    """
    user = User(
        id=str(uuid4()),
        email="other@example.com",
        password_hash=password_hasher.hash("testpassword123"),
        name="Other User",
        status="active",
        email_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def other_auth_headers(other_user: User) -> dict:
    """
    Generate authentication headers for second test user.

    Used for testing authorization and permission checks.
    """
    access_token = token_service.create_access_token(user_id=other_user.id)
    return {"Authorization": f"Bearer {access_token}"}


# ============================================================================
# Admin Test Fixtures (Phase 9)
# ============================================================================

@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """
    Create a test user with admin role.

    Used for testing admin dashboard access and operations.
    Admin users can manage users, view analytics, and manage content.
    """
    from infrastructure.database.models.user import UserRole, UserStatus

    user = User(
        id=str(uuid4()),
        email="admin@example.com",
        password_hash=password_hasher.hash("adminpassword123"),
        name="Admin User",
        role=UserRole.ADMIN.value,
        status=UserStatus.ACTIVE.value,
        email_verified=True,
        subscription_tier="professional",
        subscription_status="active",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def super_admin_user(db_session: AsyncSession) -> User:
    """
    Create a test user with super_admin role.

    Used for testing super admin exclusive operations.
    Super admins have all admin permissions plus ability to:
    - Delete users
    - Promote users to super_admin
    - Access sensitive system settings
    """
    from infrastructure.database.models.user import UserRole, UserStatus

    user = User(
        id=str(uuid4()),
        email="superadmin@example.com",
        password_hash=password_hasher.hash("superadminpassword123"),
        name="Super Admin User",
        role=UserRole.SUPER_ADMIN.value,
        status=UserStatus.ACTIVE.value,
        email_verified=True,
        subscription_tier="enterprise",
        subscription_status="active",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def admin_token(admin_user: User) -> dict:
    """
    Generate authentication headers for admin user.

    Used for testing admin-protected endpoints.
    """
    access_token = token_service.create_access_token(user_id=admin_user.id)
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def super_admin_token(super_admin_user: User) -> dict:
    """
    Generate authentication headers for super admin user.

    Used for testing super admin-protected endpoints.
    """
    access_token = token_service.create_access_token(user_id=super_admin_user.id)
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
async def suspended_user(db_session: AsyncSession) -> User:
    """
    Create a suspended user for testing access restrictions.

    Used for testing that suspended users cannot access the platform
    even if they have valid tokens.
    """
    from infrastructure.database.models.user import UserRole, UserStatus

    user = User(
        id=str(uuid4()),
        email="suspended@example.com",
        password_hash=password_hasher.hash("testpassword123"),
        name="Suspended User",
        role=UserRole.USER.value,
        status=UserStatus.SUSPENDED.value,
        email_verified=True,
        subscription_tier="free",
        subscription_status="active",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


# ============================================================================
# Team/Multi-tenancy Test Fixtures (Phase 10)
# ============================================================================

@pytest.fixture
async def team(db_session: AsyncSession, test_user: User) -> dict:
    """
    Create a team with test_user as OWNER.

    Used for testing team operations and permissions.
    Returns dict with team data including ID.
    """
    # Skip if Project model not implemented
    try:
        from infrastructure.database.models import Project, ProjectMember
        from infrastructure.database.models.project import ProjectMemberRole as ProjectRole
    except ImportError:
        pytest.skip("Project models not yet implemented")

    team = Project(
        id=str(uuid4()),
        name="Test Team",
        description="Team for testing",
        slug="test-team",
        owner_id=test_user.id,
    )
    db_session.add(team)

    # Add test_user as OWNER
    member = ProjectMember(
        id=str(uuid4()),
        project_id=team.id,
        user_id=test_user.id,
        role=ProjectRole.OWNER.value,
    )
    db_session.add(member)

    await db_session.commit()
    await db_session.refresh(team)

    return {
        "id": team.id,
        "name": team.name,
        "description": team.description,
        "slug": team.slug,
    }


@pytest.fixture
async def team_admin(db_session: AsyncSession, team: dict) -> dict:
    """
    Create a user with ADMIN role in the team.

    Used for testing admin-level permissions.
    Returns dict with user data.
    """
    try:
        from infrastructure.database.models import ProjectMember
        from infrastructure.database.models.project import ProjectMemberRole as ProjectRole
    except ImportError:
        pytest.skip("Project models not yet implemented")

    # Create admin user
    admin_user = User(
        id=str(uuid4()),
        email="teamadmin@example.com",
        password_hash=password_hasher.hash("adminpass123"),
        name="Team Admin",
        status="active",
        email_verified=True,
    )
    db_session.add(admin_user)
    await db_session.flush()

    # Add as ADMIN to team
    member = ProjectMember(
        id=str(uuid4()),
        project_id=team["id"],
        user_id=admin_user.id,
        role=ProjectRole.ADMIN.value,
    )
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(admin_user)

    return {
        "id": str(uuid4()),
        "user_id": admin_user.id,
        "email": admin_user.email,
        "role": "admin",
    }


@pytest.fixture
def team_admin_auth(team_admin: dict) -> dict:
    """
    Generate authentication headers for team admin user.

    Used for testing admin-protected team endpoints.
    """
    access_token = token_service.create_access_token(user_id=team_admin["user_id"])
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
async def team_member(db_session: AsyncSession, team: dict) -> dict:
    """
    Create a user with MEMBER role in the team.

    Used for testing member-level permissions.
    Returns dict with user data.
    """
    try:
        from infrastructure.database.models import ProjectMember
        from infrastructure.database.models.project import ProjectMemberRole as ProjectRole
    except ImportError:
        pytest.skip("Project models not yet implemented")

    # Create member user
    member_user = User(
        id=str(uuid4()),
        email="teammember@example.com",
        password_hash=password_hasher.hash("memberpass123"),
        name="Team Member",
        status="active",
        email_verified=True,
    )
    db_session.add(member_user)
    await db_session.flush()

    # Add as MEMBER to team
    member = ProjectMember(
        id=str(uuid4()),
        project_id=team["id"],
        user_id=member_user.id,
        role=ProjectRole.EDITOR.value,
    )
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(member_user)

    return {
        "id": str(uuid4()),
        "user_id": member_user.id,
        "email": member_user.email,
        "role": "member",
    }


@pytest.fixture
def team_member_auth(team_member: dict) -> dict:
    """
    Generate authentication headers for team member user.

    Used for testing member-protected team endpoints.
    """
    access_token = token_service.create_access_token(user_id=team_member["user_id"])
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
async def team_viewer(db_session: AsyncSession, team: dict) -> dict:
    """
    Create a user with VIEWER role in the team.

    Used for testing read-only viewer permissions.
    Returns dict with user data.
    """
    try:
        from infrastructure.database.models import ProjectMember
        from infrastructure.database.models.project import ProjectMemberRole as ProjectRole
    except ImportError:
        pytest.skip("Project models not yet implemented")

    # Create viewer user
    viewer_user = User(
        id=str(uuid4()),
        email="teamviewer@example.com",
        password_hash=password_hasher.hash("viewerpass123"),
        name="Team Viewer",
        status="active",
        email_verified=True,
    )
    db_session.add(viewer_user)
    await db_session.flush()

    # Add as VIEWER to team
    member = ProjectMember(
        id=str(uuid4()),
        project_id=team["id"],
        user_id=viewer_user.id,
        role=ProjectRole.VIEWER.value,
    )
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(viewer_user)

    return {
        "id": str(uuid4()),
        "user_id": viewer_user.id,
        "email": viewer_user.email,
        "role": "viewer",
    }


@pytest.fixture
def team_viewer_auth(team_viewer: dict) -> dict:
    """
    Generate authentication headers for team viewer user.

    Used for testing viewer-protected team endpoints.
    """
    access_token = token_service.create_access_token(user_id=team_viewer["user_id"])
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
async def team_invitation(db_session: AsyncSession, team: dict, test_user: User) -> dict:
    """
    Create a pending team invitation.

    Used for testing invitation acceptance and management.
    Returns dict with invitation data including token.
    """
    try:
        from infrastructure.database.models import ProjectInvitation
        from infrastructure.database.models.project import ProjectMemberRole as ProjectRole
    except ImportError:
        pytest.skip("Project models not yet implemented")

    import secrets

    invitation = ProjectInvitation(
        id=str(uuid4()),
        project_id=team["id"],
        email="invited@example.com",
        role=ProjectRole.EDITOR.value,
        token=secrets.token_urlsafe(32),
        invited_by=test_user.id,
        expires_at=datetime.utcnow() + timedelta(days=7),
        status="pending",
    )
    db_session.add(invitation)
    await db_session.commit()
    await db_session.refresh(invitation)

    return {
        "id": invitation.id,
        "project_id": invitation.project_id,
        "email": invitation.email,
        "role": invitation.role,
        "token": invitation.token,
        "status": invitation.status,
    }


# ============================================================================
# Social Media Test Fixtures (Phase 8)
# ============================================================================

def _encrypt_token(value: str) -> str:
    """Encrypt a token using the app settings secret key."""
    from infrastructure.config import get_settings
    from core.security.encryption import encrypt_credential
    settings = get_settings()
    return encrypt_credential(value, settings.secret_key)


@pytest.fixture
async def connected_twitter_account(db_session: AsyncSession, test_user: User):
    """
    Create a connected Twitter account for testing.

    Used for testing post creation and publishing to Twitter.
    """
    from infrastructure.database.models.social import SocialAccount

    account = SocialAccount(
        id=str(uuid4()),
        user_id=test_user.id,
        platform="twitter",
        platform_username="testuser",
        platform_user_id="123456",
        access_token_encrypted=_encrypt_token("test_twitter_token"),
        refresh_token_encrypted=_encrypt_token("test_twitter_refresh"),
        token_expires_at=datetime.utcnow() + timedelta(hours=2),
        is_active=True,
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    return account


@pytest.fixture
async def connected_linkedin_account(db_session: AsyncSession, test_user: User):
    """
    Create a connected LinkedIn account for testing.

    Used for testing post creation and publishing to LinkedIn.
    """
    from infrastructure.database.models.social import SocialAccount

    account = SocialAccount(
        id=str(uuid4()),
        user_id=test_user.id,
        platform="linkedin",
        platform_username="Test User",
        platform_user_id="urn:li:person:123456",
        access_token_encrypted=_encrypt_token("test_linkedin_token"),
        token_expires_at=datetime.utcnow() + timedelta(days=60),
        is_active=True,
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    return account


@pytest.fixture
async def connected_facebook_account(db_session: AsyncSession, test_user: User):
    """
    Create a connected Facebook account for testing.

    Used for testing post creation and publishing to Facebook.
    """
    from infrastructure.database.models.social import SocialAccount

    account = SocialAccount(
        id=str(uuid4()),
        user_id=test_user.id,
        platform="facebook",
        platform_username="Test Page",
        platform_user_id="123456789",
        access_token_encrypted=_encrypt_token("test_facebook_token"),
        token_expires_at=datetime.utcnow() + timedelta(days=60),
        is_active=True,
        account_metadata={"page_id": "123456789"},
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    return account


@pytest.fixture
async def connected_accounts(
    db_session: AsyncSession,
    test_user: User,
    connected_twitter_account,
    connected_linkedin_account,
):
    """
    Create multiple connected accounts for testing.

    Used for testing multi-platform posting and account management.
    """
    return [connected_twitter_account, connected_linkedin_account]


@pytest.fixture
async def pending_post(
    db_session: AsyncSession,
    test_user: User,
    connected_twitter_account,
):
    """
    Create a pending scheduled post for testing.

    Used for testing post retrieval, updates, and publishing.
    """
    from infrastructure.database.models.social import ScheduledPost, PostTarget, PostStatus

    post = ScheduledPost(
        id=str(uuid4()),
        user_id=test_user.id,
        content="Test pending post",
        scheduled_at=datetime.utcnow() + timedelta(hours=2),
        status=PostStatus.SCHEDULED,
    )
    db_session.add(post)
    await db_session.flush()

    target = PostTarget(
        id=str(uuid4()),
        scheduled_post_id=post.id,
        social_account_id=connected_twitter_account.id,
        is_published=False,
    )
    db_session.add(target)

    await db_session.commit()
    await db_session.refresh(post)
    return post


@pytest.fixture
async def posted_post(
    db_session: AsyncSession,
    test_user: User,
    connected_twitter_account,
):
    """
    Create a post that has already been published.

    Used for testing operations that should fail on published posts.
    """
    from infrastructure.database.models.social import ScheduledPost, PostTarget, PostStatus

    post = ScheduledPost(
        id=str(uuid4()),
        user_id=test_user.id,
        content="Test published post",
        scheduled_at=datetime.utcnow() - timedelta(hours=1),
        status=PostStatus.PUBLISHED,
        published_at=datetime.utcnow() - timedelta(hours=1),
    )
    db_session.add(post)
    await db_session.flush()

    target = PostTarget(
        id=str(uuid4()),
        scheduled_post_id=post.id,
        social_account_id=connected_twitter_account.id,
        is_published=True,
        platform_post_id="1234567890",
        published_at=datetime.utcnow() - timedelta(hours=1),
    )
    db_session.add(target)

    await db_session.commit()
    await db_session.refresh(post)
    return post


@pytest.fixture
async def failed_post(
    db_session: AsyncSession,
    test_user: User,
    connected_twitter_account,
):
    """
    Create a post that failed to publish.

    Used for testing retry operations and error handling.
    """
    from infrastructure.database.models.social import ScheduledPost, PostTarget, PostStatus

    post = ScheduledPost(
        id=str(uuid4()),
        user_id=test_user.id,
        content="Test failed post",
        scheduled_at=datetime.utcnow() - timedelta(minutes=30),
        status=PostStatus.FAILED,
        publish_error="API Error: Rate limit exceeded",
    )
    db_session.add(post)
    await db_session.flush()

    target = PostTarget(
        id=str(uuid4()),
        scheduled_post_id=post.id,
        social_account_id=connected_twitter_account.id,
        is_published=False,
        publish_error="API Error: Rate limit exceeded",
    )
    db_session.add(target)

    await db_session.commit()
    await db_session.refresh(post)
    return post


@pytest.fixture
async def multiple_scheduled_posts(
    db_session: AsyncSession,
    test_user: User,
    connected_accounts,
):
    """
    Create multiple scheduled posts with various statuses.

    Used for testing pagination, filtering, and calendar views.
    """
    from infrastructure.database.models.social import ScheduledPost, PostTarget, PostStatus

    posts = []

    statuses = [
        PostStatus.SCHEDULED,
        PostStatus.SCHEDULED,
        PostStatus.PUBLISHED,
        PostStatus.FAILED,
        PostStatus.SCHEDULED,
    ]

    for i, post_status in enumerate(statuses):
        scheduled_at = datetime.utcnow() + timedelta(hours=(i + 1))
        if post_status == PostStatus.PUBLISHED:
            scheduled_at = datetime.utcnow() - timedelta(hours=1)

        post = ScheduledPost(
            id=str(uuid4()),
            user_id=test_user.id,
            content=f"Test post {i + 1}",
            scheduled_at=scheduled_at,
            status=post_status,
            published_at=datetime.utcnow() - timedelta(hours=1) if post_status == PostStatus.PUBLISHED else None,
        )
        db_session.add(post)
        await db_session.flush()

        for account in connected_accounts:
            is_published = post_status == PostStatus.PUBLISHED
            target = PostTarget(
                id=str(uuid4()),
                scheduled_post_id=post.id,
                social_account_id=account.id,
                is_published=is_published,
                platform_post_id=f"post_{i}_{account.platform}" if is_published else None,
                published_at=datetime.utcnow() - timedelta(hours=1) if is_published else None,
            )
            db_session.add(target)

        posts.append(post)

    await db_session.commit()

    for post in posts:
        await db_session.refresh(post)

    return posts
