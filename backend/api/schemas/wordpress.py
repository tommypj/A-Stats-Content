"""
WordPress integration API schemas.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, HttpUrl


class WordPressConnectRequest(BaseModel):
    """Request to connect a WordPress site."""

    site_url: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="WordPress site URL (e.g., https://mysite.com)",
    )
    username: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="WordPress username",
    )
    app_password: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="WordPress application password",
    )


class WordPressConnectionResponse(BaseModel):
    """WordPress connection status response."""

    site_url: str
    username: str
    is_connected: bool
    connected_at: Optional[datetime] = None
    last_tested_at: Optional[datetime] = None
    connection_valid: bool = Field(
        default=True,
        description="Whether the connection is currently valid",
    )
    error_message: Optional[str] = Field(
        None,
        description="Error message if connection test failed",
    )


class WordPressPublishRequest(BaseModel):
    """Request to publish an article to WordPress."""

    article_id: str = Field(..., description="UUID of the article to publish")
    status: str = Field(
        default="draft",
        description="WordPress post status: draft or publish",
    )
    categories: Optional[List[int]] = Field(
        None,
        description="Category IDs to assign to the post",
    )
    tags: Optional[List[int]] = Field(
        None,
        description="Tag IDs to assign to the post",
    )
    update_existing: bool = Field(
        default=True,
        description="If article was published before, update the existing post",
    )


class WordPressPublishResponse(BaseModel):
    """Response after publishing to WordPress."""

    wordpress_post_id: int
    wordpress_url: str
    status: str
    message: str = Field(
        default="Article published successfully",
        description="Success or error message",
    )


class WordPressCategoryResponse(BaseModel):
    """WordPress category information."""

    id: int
    name: str
    slug: str
    count: Optional[int] = Field(None, description="Number of posts in this category")
    parent: Optional[int] = Field(None, description="Parent category ID if nested")


class WordPressTagResponse(BaseModel):
    """WordPress tag information."""

    id: int
    name: str
    slug: str
    count: Optional[int] = Field(None, description="Number of posts with this tag")


class WordPressMediaUploadRequest(BaseModel):
    """Request to upload an image to WordPress media library."""

    image_id: str = Field(..., description="UUID of the generated image to upload")
    title: Optional[str] = Field(None, description="Media title (defaults to prompt)")
    alt_text: Optional[str] = Field(None, description="Alt text for the image")


class WordPressMediaUploadResponse(BaseModel):
    """Response after uploading media to WordPress."""

    wordpress_media_id: int
    wordpress_url: str
    source_url: str
    message: str = Field(default="Image uploaded successfully to WordPress")


class WordPressDisconnectResponse(BaseModel):
    """Response after disconnecting WordPress."""

    message: str = "WordPress connection removed successfully"
    disconnected_at: datetime
