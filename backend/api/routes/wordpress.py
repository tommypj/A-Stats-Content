"""
WordPress integration API routes.
"""

import base64
import io
import ipaddress
import json
import logging
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import urlparse

import httpx
from PIL import Image as PILImage
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.wordpress import (
    WordPressConnectRequest,
    WordPressConnectionResponse,
    WordPressPublishRequest,
    WordPressPublishResponse,
    WordPressCategoryResponse,
    WordPressTagResponse,
    WordPressDisconnectResponse,
    WordPressMediaUploadRequest,
    WordPressMediaUploadResponse,
)
from api.routes.auth import get_current_user
from infrastructure.database.connection import get_db
from infrastructure.database.models import User, Article, GeneratedImage
from infrastructure.database.models.project import Project
from infrastructure.config.settings import settings
from core.security.encryption import encrypt_credential, decrypt_credential

router = APIRouter(prefix="/wordpress", tags=["WordPress"])

logger = logging.getLogger(__name__)

WP_USER_AGENT = "A-Stats-Content/1.0 (WordPress Integration)"


def _validate_wp_url(url: str) -> str:
    """Validate WordPress URL is not targeting internal/private networks."""
    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(400, "Invalid WordPress URL")

    # Block private/internal hostnames
    blocked = ["localhost", "127.0.0.1", "0.0.0.0", "::1"]
    if hostname in blocked:
        raise HTTPException(400, "WordPress URL cannot point to localhost")

    # Check for private IP ranges
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise HTTPException(400, "WordPress URL cannot point to a private network")
    except ValueError:
        pass  # hostname is not an IP, that's fine

    return url


def _wp_client(timeout: float = 15.0) -> httpx.AsyncClient:
    """Create an httpx client configured for WordPress API calls."""
    return httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": WP_USER_AGENT},
    )


def get_wp_credentials(project: Project) -> Optional[dict]:
    """
    Extract and decrypt WordPress credentials from project.

    Args:
        project: Project model instance

    Returns:
        Dictionary with site_url, username, and app_password or None
    """
    if not project.wordpress_credentials:
        return None

    try:
        creds = project.wordpress_credentials
        return {
            "site_url": creds.get("site_url", ""),
            "username": creds.get("username", ""),
            "app_password": decrypt_credential(
                creds.get("app_password_encrypted", ""),
                settings.secret_key,
            ),
        }
    except Exception:
        return None


def create_wp_auth_header(username: str, app_password: str) -> str:
    """
    Create Basic Auth header for WordPress API.

    Args:
        username: WordPress username
        app_password: WordPress application password

    Returns:
        Basic auth header value
    """
    credentials = f"{username}:{app_password}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded}"


async def test_wp_connection(site_url: str, username: str, app_password: str) -> dict:
    """
    Test WordPress connection by calling the REST API.

    Args:
        site_url: WordPress site URL
        username: WordPress username
        app_password: WordPress application password

    Returns:
        Dictionary with success status and optional error message
    """
    # Normalize site URL
    site_url = site_url.rstrip("/")
    if not site_url.startswith("http"):
        site_url = f"https://{site_url}"

    _validate_wp_url(site_url)

    test_url = f"{site_url}/wp-json/wp/v2/users/me"
    auth_header = create_wp_auth_header(username, app_password)

    try:
        async with _wp_client() as client:
            response = await client.get(
                test_url,
                headers={"Authorization": auth_header},
            )

            if response.status_code == 200:
                return {"success": True, "error": None}
            else:
                return {
                    "success": False,
                    "error": f"WordPress API returned status {response.status_code}",
                }
    except httpx.TimeoutException:
        return {"success": False, "error": "Connection timeout"}
    except httpx.RequestError as e:
        return {"success": False, "error": f"Connection error: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


@router.post("/connect", response_model=WordPressConnectionResponse)
async def connect_wordpress(
    request: WordPressConnectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Store WordPress credentials for the current project.
    """
    # Load current project
    if not current_user.current_project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active project selected. Please select a project first.",
        )
    project_result = await db.execute(
        select(Project).where(Project.id == current_user.current_project_id)
    )
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Current project not found",
        )

    # Validate URL before making any HTTP requests
    _validate_wp_url(request.site_url)

    # Test the connection first
    test_result = await test_wp_connection(
        request.site_url,
        request.username,
        request.app_password,
    )

    if not test_result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"WordPress connection failed: {test_result['error']}",
        )

    # Encrypt the app password
    encrypted_password = encrypt_credential(request.app_password, settings.secret_key)

    # Normalize site URL
    site_url = request.site_url.rstrip("/")
    if not site_url.startswith("http"):
        site_url = f"https://{site_url}"

    # Store credentials in project model
    project.wordpress_credentials = {
        "site_url": site_url,
        "username": request.username,
        "app_password_encrypted": encrypted_password,
        "connected_at": datetime.now(timezone.utc).isoformat(),
        "last_tested_at": datetime.now(timezone.utc).isoformat(),
    }

    await db.commit()
    await db.refresh(project)

    return WordPressConnectionResponse(
        site_url=site_url,
        username=request.username,
        is_connected=True,
        connected_at=datetime.now(timezone.utc),
        last_tested_at=datetime.now(timezone.utc),
        connection_valid=True,
    )


@router.post("/disconnect", response_model=WordPressDisconnectResponse)
async def disconnect_wordpress(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Remove WordPress credentials from the current project.
    """
    if not current_user.current_project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active project selected.",
        )
    project_result = await db.execute(
        select(Project).where(Project.id == current_user.current_project_id)
    )
    project = project_result.scalar_one_or_none()
    if not project or not project.wordpress_credentials:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No WordPress connection found",
        )

    project.wordpress_credentials = None
    await db.commit()

    return WordPressDisconnectResponse(
        disconnected_at=datetime.now(timezone.utc),
    )


@router.get("/status", response_model=WordPressConnectionResponse)
async def get_wordpress_status(
    test_connection: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Check WordPress connection status for the current project.

    Args:
        test_connection: If True, test the actual connection to WordPress
    """
    if not current_user.current_project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active project selected.",
        )
    project_result = await db.execute(
        select(Project).where(Project.id == current_user.current_project_id)
    )
    project = project_result.scalar_one_or_none()
    if not project or not project.wordpress_credentials:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No WordPress connection configured",
        )

    creds = project.wordpress_credentials
    site_url = creds.get("site_url", "")
    username = creds.get("username", "")

    # Parse dates
    connected_at = None
    last_tested_at = None
    if creds.get("connected_at"):
        connected_at = datetime.fromisoformat(creds["connected_at"])
    if creds.get("last_tested_at"):
        last_tested_at = datetime.fromisoformat(creds["last_tested_at"])

    # Optionally test the connection
    connection_valid = True
    error_message = None

    if test_connection:
        wp_creds = get_wp_credentials(project)
        if wp_creds:
            test_result = await test_wp_connection(
                wp_creds["site_url"],
                wp_creds["username"],
                wp_creds["app_password"],
            )
            connection_valid = test_result["success"]
            error_message = test_result["error"]
            last_tested_at = datetime.now(timezone.utc)

    return WordPressConnectionResponse(
        site_url=site_url,
        username=username,
        is_connected=True,
        connected_at=connected_at,
        last_tested_at=last_tested_at,
        connection_valid=connection_valid,
        error_message=error_message,
    )


@router.get("/categories", response_model=List[WordPressCategoryResponse])
async def get_wordpress_categories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch categories from connected WordPress site.
    """
    if not current_user.current_project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active project selected.",
        )
    project_result = await db.execute(
        select(Project).where(Project.id == current_user.current_project_id)
    )
    project = project_result.scalar_one_or_none()
    wp_creds = get_wp_credentials(project) if project else None
    if not wp_creds:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No WordPress connection configured",
        )

    categories_url = f"{wp_creds['site_url']}/wp-json/wp/v2/categories"
    auth_header = create_wp_auth_header(wp_creds["username"], wp_creds["app_password"])

    try:
        async with _wp_client() as client:
            response = await client.get(
                categories_url,
                headers={"Authorization": auth_header},
                params={"per_page": 100},  # Fetch up to 100 categories
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"WordPress API error: {response.status_code}",
                )

            categories = response.json()
            return [
                WordPressCategoryResponse(
                    id=cat["id"],
                    name=cat["name"],
                    slug=cat["slug"],
                    count=cat.get("count"),
                    parent=cat.get("parent", 0) if cat.get("parent", 0) > 0 else None,
                )
                for cat in categories
            ]
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch categories: {str(e)}",
        )


@router.get("/tags", response_model=List[WordPressTagResponse])
async def get_wordpress_tags(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch tags from connected WordPress site.
    """
    if not current_user.current_project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active project selected.",
        )
    project_result = await db.execute(
        select(Project).where(Project.id == current_user.current_project_id)
    )
    project = project_result.scalar_one_or_none()
    wp_creds = get_wp_credentials(project) if project else None
    if not wp_creds:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No WordPress connection configured",
        )

    tags_url = f"{wp_creds['site_url']}/wp-json/wp/v2/tags"
    auth_header = create_wp_auth_header(wp_creds["username"], wp_creds["app_password"])

    try:
        async with _wp_client() as client:
            response = await client.get(
                tags_url,
                headers={"Authorization": auth_header},
                params={"per_page": 100},  # Fetch up to 100 tags
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"WordPress API error: {response.status_code}",
                )

            tags = response.json()
            return [
                WordPressTagResponse(
                    id=tag["id"],
                    name=tag["name"],
                    slug=tag["slug"],
                    count=tag.get("count"),
                )
                for tag in tags
            ]
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch tags: {str(e)}",
        )


@router.post("/publish", response_model=WordPressPublishResponse)
async def publish_to_wordpress(
    request: WordPressPublishRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Publish an article to WordPress.
    """
    # Require an active project — WordPress credentials are project-scoped
    if not current_user.current_project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active project selected. Please select a project first.",
        )

    # Fetch the article, enforcing both ownership and project membership so a
    # user cannot publish an article that belongs to a different project.
    result = await db.execute(
        select(Article).where(
            Article.id == request.article_id,
            Article.user_id == current_user.id,
            Article.project_id == current_user.current_project_id,
        )
    )
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found",
        )

    if not article.content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Article has no content to publish",
        )

    # Get WordPress credentials from the current project (already verified above)
    proj_result = await db.execute(
        select(Project).where(Project.id == current_user.current_project_id)
    )
    article_project = proj_result.scalar_one_or_none()
    wp_creds = get_wp_credentials(article_project) if article_project else None
    if not wp_creds:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No WordPress connection configured",
        )

    auth_header = create_wp_auth_header(wp_creds["username"], wp_creds["app_password"])

    # Attempt to upload the article's featured image to WordPress before creating the post
    featured_media_id: Optional[int] = None
    if article.featured_image_id:
        try:
            img_result = await db.execute(
                select(GeneratedImage).where(GeneratedImage.id == article.featured_image_id)
            )
            featured_image = img_result.scalar_one_or_none()
            if featured_image and featured_image.url:
                async with _wp_client(timeout=60.0) as media_client:
                    upload_result = await _upload_image_to_wp(
                        client=media_client,
                        image=featured_image,
                        wp_creds=wp_creds,
                        auth_header=auth_header,
                    )
                    featured_media_id = upload_result["wordpress_media_id"]
                    logger.info(
                        "Uploaded featured image %s to WordPress media (ID: %s) for article %s",
                        article.featured_image_id,
                        featured_media_id,
                        article.id,
                    )
            else:
                logger.warning(
                    "Featured image %s not found or has no URL for article %s; skipping upload",
                    article.featured_image_id,
                    article.id,
                )
        except Exception as exc:
            logger.warning(
                "Failed to upload featured image for article %s: %s — publishing without featured_media",
                article.id,
                exc,
            )

    # Prepare post data
    post_data = {
        "title": article.title,
        "content": article.content_html or article.content,
        "status": request.status,
        "excerpt": article.meta_description or "",
    }

    if featured_media_id is not None:
        post_data["featured_media"] = featured_media_id

    # Add categories if provided
    if request.categories:
        post_data["categories"] = request.categories

    # Add tags if provided
    if request.tags:
        post_data["tags"] = request.tags

    try:
        async with _wp_client(timeout=30.0) as client:
            # If article was already published and update_existing is True, update it
            if article.wordpress_post_id and request.update_existing:
                # Update existing post
                update_url = f"{wp_creds['site_url']}/wp-json/wp/v2/posts/{article.wordpress_post_id}"
                response = await client.post(
                    update_url,
                    headers={
                        "Authorization": auth_header,
                        "Content-Type": "application/json",
                    },
                    json=post_data,
                )
            else:
                # Create new post
                create_url = f"{wp_creds['site_url']}/wp-json/wp/v2/posts"
                response = await client.post(
                    create_url,
                    headers={
                        "Authorization": auth_header,
                        "Content-Type": "application/json",
                    },
                    json=post_data,
                )

            if response.status_code not in (200, 201):
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"WordPress API error: {response.status_code} - {response.text}",
                )

            wp_post = response.json()

            # Update article with WordPress post info
            article.wordpress_post_id = wp_post["id"]
            article.published_url = wp_post["link"]
            article.published_at = datetime.now(timezone.utc)

            await db.commit()

            return WordPressPublishResponse(
                wordpress_post_id=wp_post["id"],
                wordpress_url=wp_post["link"],
                status=wp_post["status"],
                message="Article published successfully to WordPress",
            )

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to publish to WordPress: {str(e)}",
        )


def _convert_to_webp(image_bytes: bytes, quality: int = 82) -> tuple[bytes, bool]:
    """
    Convert image bytes to WebP format.

    Skips conversion if the image is already WebP or is a GIF (animated GIFs
    do not convert well). On any PIL error the original bytes are returned
    unchanged so the caller can proceed without interruption.

    Args:
        image_bytes: Raw bytes of the source image.
        quality: WebP quality (0-100). Default 82 is visually lossless with
                 significant size reduction.

    Returns:
        A tuple of (result_bytes, converted). ``converted`` is True only when
        a new WebP payload was produced.
    """
    try:
        img = PILImage.open(io.BytesIO(image_bytes))

        # Skip if already WebP
        if img.format and img.format.upper() == "WEBP":
            return image_bytes, False

        # Skip GIFs — animated frames are not preserved by PIL WebP export
        if img.format and img.format.upper() == "GIF":
            return image_bytes, False

        buf = io.BytesIO()
        if img.mode in ("RGBA", "LA", "PA"):
            img.save(buf, format="WEBP", quality=quality, method=4)
        else:
            img.convert("RGB").save(buf, format="WEBP", quality=quality, method=4)

        return buf.getvalue(), True

    except Exception as exc:  # noqa: BLE001
        logger.warning("WebP conversion skipped due to PIL error: %s", exc)
        return image_bytes, False


async def _upload_image_to_wp(
    client: httpx.AsyncClient,
    image: GeneratedImage,
    wp_creds: dict,
    auth_header: str,
    title: Optional[str] = None,
    alt_text: Optional[str] = None,
) -> dict:
    """
    Download an image from its source URL and upload it to the WordPress media library.

    Args:
        client: An active httpx.AsyncClient instance.
        image: The GeneratedImage model instance to upload.
        wp_creds: Decrypted WordPress credentials dict with site_url.
        auth_header: Prebuilt Basic Auth header value.
        title: Optional title override for the media item.
        alt_text: Optional alt text override for the media item.

    Returns:
        A dict with ``wordpress_media_id`` (int) and ``source_url`` (str).

    Raises:
        httpx.RequestError: On network-level failures.
        HTTPException: If the download or upload returns a non-success status.
    """
    # Download the image from its source URL
    img_response = await client.get(image.url)
    if img_response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to download image from source: {img_response.status_code}",
        )

    image_data = img_response.content
    content_type = img_response.headers.get("content-type", "image/png")

    # Convert to WebP before uploading (graceful fallback on any error)
    webp_data, converted = _convert_to_webp(image_data)
    if converted:
        original_kb = len(image_data) / 1024
        webp_kb = len(webp_data) / 1024
        reduction_pct = (1 - webp_kb / original_kb) * 100 if original_kb else 0
        logger.info(
            "Converted image to WebP: %.0fKB -> %.0fKB (%.0f%% reduction)",
            original_kb,
            webp_kb,
            reduction_pct,
        )
        image_data = webp_data
        content_type = "image/webp"

    # Determine file extension from content type
    ext_map = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }
    ext = ext_map.get(content_type, ".png")
    filename = f"ai-image-{image.id[:8]}{ext}"

    # Resolve title and alt text
    resolved_title = title or image.alt_text or image.prompt[:100]
    resolved_alt = alt_text or image.alt_text or f"AI-generated image: {image.prompt[:100]}"

    # Upload to WordPress media library
    upload_url = f"{wp_creds['site_url']}/wp-json/wp/v2/media"
    response = await client.post(
        upload_url,
        headers={
            "Authorization": auth_header,
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": content_type,
        },
        content=image_data,
    )

    if response.status_code not in (200, 201):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"WordPress media upload failed: {response.status_code} - {response.text}",
        )

    wp_media = response.json()
    media_id = wp_media["id"]

    # Set title and alt text on the uploaded media item
    update_url = f"{wp_creds['site_url']}/wp-json/wp/v2/media/{media_id}"
    await client.post(
        update_url,
        headers={
            "Authorization": auth_header,
            "Content-Type": "application/json",
        },
        json={
            "title": resolved_title,
            "alt_text": resolved_alt,
        },
    )

    source_url = wp_media.get(
        "source_url", wp_media.get("guid", {}).get("rendered", "")
    )
    return {"wordpress_media_id": media_id, "source_url": source_url}


@router.post("/upload-media", response_model=WordPressMediaUploadResponse)
async def upload_media_to_wordpress(
    request: WordPressMediaUploadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a generated image to the WordPress media library.
    Downloads the image from its URL and uploads it to WordPress.
    """
    # Get WordPress credentials from the current project
    if not current_user.current_project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active project selected.",
        )
    proj_result = await db.execute(
        select(Project).where(Project.id == current_user.current_project_id)
    )
    current_project = proj_result.scalar_one_or_none()
    wp_creds = get_wp_credentials(current_project) if current_project else None
    if not wp_creds:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No WordPress connection configured",
        )

    # Get the image, also verifying it belongs to the current project so a user
    # cannot upload images from a different project's context.
    result = await db.execute(
        select(GeneratedImage).where(
            GeneratedImage.id == request.image_id,
            GeneratedImage.user_id == current_user.id,
            GeneratedImage.project_id == current_user.current_project_id,
        )
    )
    image = result.scalar_one_or_none()

    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    if not image.url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image has no URL",
        )

    auth_header = create_wp_auth_header(wp_creds["username"], wp_creds["app_password"])

    try:
        async with _wp_client(timeout=60.0) as client:
            result_data = await _upload_image_to_wp(
                client=client,
                image=image,
                wp_creds=wp_creds,
                auth_header=auth_header,
                title=request.title,
                alt_text=request.alt_text,
            )

            return WordPressMediaUploadResponse(
                wordpress_media_id=result_data["wordpress_media_id"],
                wordpress_url="",
                source_url=result_data["source_url"],
                message="Image uploaded successfully to WordPress media library",
            )

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to upload media to WordPress: {str(e)}",
        )
