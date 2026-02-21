# WordPress REST API Adapter

A comprehensive adapter for publishing articles to WordPress sites using the WordPress REST API v2 and Application Password authentication.

## Features

- WordPress Application Password authentication (Basic Auth)
- Test WordPress connection and credentials
- Fetch available categories and tags
- Upload images to WordPress media library
- Create, update, and retrieve posts
- Support for featured images, categories, tags
- SEO meta description support (Yoast SEO compatible)
- Comprehensive error handling with custom exceptions
- Async/await support with httpx
- Context manager for automatic connection cleanup

## Installation

The adapter uses `httpx` for async HTTP requests. Make sure it's installed:

```bash
uv add httpx
```

## WordPress Setup

### 1. Enable Application Passwords

Application Passwords are available in WordPress 5.6+. To create one:

1. Go to **WordPress Admin > Users > Profile**
2. Scroll to **Application Passwords** section
3. Enter a name (e.g., "A-Stats Content API")
4. Click **Add New Application Password**
5. Copy the generated password (format: `xxxx xxxx xxxx xxxx xxxx xxxx`)

**Important:** Save this password securely - it's only shown once!

### 2. Enable REST API

The REST API is enabled by default in WordPress. If you have security plugins, make sure they don't block REST API access.

### 3. Get Category and Tag IDs

You can fetch these programmatically using the adapter:

```python
categories = await adapter.get_categories()
tags = await adapter.get_tags()
```

Or find them in WordPress Admin:
- Categories: Posts > Categories (hover over category name to see ID in URL)
- Tags: Posts > Tags (hover over tag name to see ID in URL)

## Basic Usage

```python
from adapters.cms import WordPressAdapter

async def publish_article():
    # Initialize adapter
    adapter = WordPressAdapter(
        site_url="https://your-site.com",
        username="your-username",
        app_password="xxxx xxxx xxxx xxxx xxxx xxxx",
    )

    # Test connection
    await adapter.test_connection()

    # Create a post
    post = await adapter.create_post(
        title="My Article Title",
        content="<p>Article content in HTML</p>",
        status="draft",
        categories=[1, 2],
        tags=[5, 6],
    )

    print(f"Published: {post['link']}")

    # Clean up
    await adapter.close()
```

## Using Context Manager (Recommended)

```python
async with WordPressAdapter(
    site_url="https://your-site.com",
    username="your-username",
    app_password="xxxx xxxx xxxx xxxx xxxx xxxx",
) as wp:
    # Connection is automatically managed
    await wp.test_connection()

    post = await wp.create_post(
        title="My Article",
        content="<p>Content</p>",
    )

    print(f"Published: {post['link']}")
# Connection is automatically closed
```

## Complete Workflow Example

```python
from adapters.cms import WordPressAdapter

async def publish_with_image():
    async with WordPressAdapter(
        site_url="https://your-site.com",
        username="username",
        app_password="app-password",
    ) as wp:
        # 1. Test connection
        await wp.test_connection()

        # 2. Upload featured image
        media = await wp.upload_media(
            image_url="https://example.com/image.jpg",
            filename="featured-image.jpg",
            alt_text="Article featured image",
        )

        # 3. Create post with featured image
        post = await wp.create_post(
            title="Complete Guide to Mindfulness",
            content="<p>Your article content...</p>",
            status="publish",
            categories=[5],
            tags=[10, 11, 12],
            featured_media_id=media["id"],
            meta_description="Learn mindfulness techniques...",
            excerpt="A comprehensive guide...",
        )

        return post
```

## API Reference

### WordPressAdapter

#### Constructor

```python
WordPressAdapter(
    site_url: str,
    username: str,
    app_password: str,
    timeout: int = 30,
)
```

#### Methods

##### test_connection()
Test WordPress connection and validate credentials.

```python
is_connected = await adapter.test_connection()
```

##### get_categories()
Fetch all available categories.

```python
categories = await adapter.get_categories()
# Returns: [{"id": 1, "name": "Category Name", "slug": "category-slug", ...}, ...]
```

##### get_tags()
Fetch all available tags.

```python
tags = await adapter.get_tags()
# Returns: [{"id": 1, "name": "Tag Name", "slug": "tag-slug", ...}, ...]
```

##### upload_media()
Upload an image to WordPress media library.

```python
media = await adapter.upload_media(
    image_url="https://example.com/image.jpg",
    filename="my-image.jpg",
    alt_text="Image description",
)
# Returns: {"id": 123, "source_url": "https://...", ...}
```

##### create_post()
Create a new WordPress post.

```python
post = await adapter.create_post(
    title="Post Title",
    content="<p>HTML content</p>",
    status="draft",  # draft, publish, pending, private
    categories=[1, 2],
    tags=[3, 4],
    featured_media_id=123,
    meta_description="SEO description",
    excerpt="Post excerpt",
)
# Returns: {"id": 456, "link": "https://...", "status": "draft", ...}
```

##### update_post()
Update an existing post.

```python
updated = await adapter.update_post(
    post_id=456,
    title="Updated Title",
    status="publish",
)
```

##### get_post()
Retrieve a post by ID.

```python
post = await adapter.get_post(post_id=456)
```

##### close()
Close the HTTP client connection.

```python
await adapter.close()
```

## Error Handling

The adapter provides three custom exceptions:

- **WordPressConnectionError**: Network connection issues
- **WordPressAuthError**: Authentication failures (401, 403)
- **WordPressAPIError**: API errors (4xx, 5xx responses)

```python
from adapters.cms import (
    WordPressAdapter,
    WordPressConnectionError,
    WordPressAuthError,
    WordPressAPIError,
)

try:
    async with WordPressAdapter(...) as wp:
        await wp.test_connection()
        post = await wp.create_post(...)

except WordPressConnectionError as e:
    print(f"Connection error: {e}")
except WordPressAuthError as e:
    print(f"Authentication error: {e}")
except WordPressAPIError as e:
    print(f"API error: {e}")
```

## Post Status Options

- `draft` - Save as draft (default)
- `publish` - Publish immediately
- `pending` - Mark as pending review
- `private` - Private post (only visible to admins)

## SEO Meta Description

The adapter supports Yoast SEO meta descriptions. If you have Yoast SEO installed:

```python
post = await adapter.create_post(
    title="...",
    content="...",
    meta_description="Your SEO meta description (150-160 characters)",
)
```

This sets the `_yoast_wpseo_metadesc` meta field. If Yoast SEO is not installed, the field is safely ignored.

## Testing

Run the test suite:

```bash
pytest backend/tests/unit/test_wordpress_adapter.py -v
```

## Example Files

- `example_usage.py` - Comprehensive usage examples
- `test_wordpress_adapter.py` - Full test suite

## Architecture Notes

This adapter follows Clean Architecture principles:

- **Location**: `backend/adapters/cms/` (Adapter layer)
- **Dependencies**: Only infrastructure (httpx, logging)
- **No domain coupling**: Can be used independently
- **Async-first**: All operations are async for better performance
- **Error handling**: Custom exceptions for proper error propagation

## Troubleshooting

### "Authentication failed"
- Verify the application password is correct
- Ensure username matches WordPress user
- Check if REST API is accessible

### "Connection timeout"
- Verify the site URL is correct
- Check network connectivity
- Increase timeout parameter if needed

### "Authorization failed"
- User must have `publish_posts` capability
- Check user role (should be Author, Editor, or Administrator)

### "Post not found"
- Verify the post ID exists
- Check if post was deleted
- Ensure user has permission to view the post

## Related Documentation

- [WordPress REST API Handbook](https://developer.wordpress.org/rest-api/)
- [Application Passwords Documentation](https://make.wordpress.org/core/2020/11/05/application-passwords-integration-guide/)
- [WordPress REST API Reference](https://developer.wordpress.org/rest-api/reference/)
