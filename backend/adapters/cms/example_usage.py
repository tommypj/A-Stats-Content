"""
Example usage of the WordPress adapter.

This file demonstrates how to use the WordPress REST API adapter
to publish articles to a WordPress site.
"""

import asyncio
from adapters.cms.wordpress_adapter import (
    WordPressAdapter,
    WordPressConnectionError,
    WordPressAuthError,
    WordPressAPIError,
)


async def main():
    """Example workflow for publishing to WordPress."""

    # Initialize the adapter
    adapter = WordPressAdapter(
        site_url="https://your-wordpress-site.com",
        username="your-username",
        app_password="xxxx xxxx xxxx xxxx xxxx xxxx",  # From WordPress > Users > Application Passwords
    )

    try:
        # Step 1: Test the connection
        print("Testing WordPress connection...")
        is_connected = await adapter.test_connection()
        if is_connected:
            print("✓ Connection successful!")
        else:
            print("✗ Connection failed")
            return

        # Step 2: Get available categories and tags
        print("\nFetching categories...")
        categories = await adapter.get_categories()
        print(f"Found {len(categories)} categories:")
        for cat in categories[:5]:  # Show first 5
            print(f"  - {cat['name']} (ID: {cat['id']})")

        print("\nFetching tags...")
        tags = await adapter.get_tags()
        print(f"Found {len(tags)} tags:")
        for tag in tags[:5]:  # Show first 5
            print(f"  - {tag['name']} (ID: {tag['id']})")

        # Step 3: Upload a featured image (optional)
        # print("\nUploading featured image...")
        # media = await adapter.upload_media(
        #     image_url="https://example.com/path/to/image.jpg",
        #     filename="article-featured-image.jpg",
        #     alt_text="Article featured image",
        # )
        # print(f"✓ Image uploaded! Media ID: {media['id']}")
        # featured_media_id = media['id']

        # Step 4: Create a new post
        print("\nCreating a new post...")
        post = await adapter.create_post(
            title="My First Article from API",
            content="""
                <h2>Introduction</h2>
                <p>This is a test article created via the WordPress REST API.</p>

                <h2>Main Content</h2>
                <p>This article demonstrates the WordPress adapter functionality.</p>

                <h3>Features</h3>
                <ul>
                    <li>Automatic authentication</li>
                    <li>Category and tag support</li>
                    <li>Media upload</li>
                    <li>SEO meta description</li>
                </ul>

                <h2>Conclusion</h2>
                <p>The WordPress adapter makes it easy to publish content programmatically.</p>
            """,
            status="draft",  # Can be: draft, publish, pending, private
            categories=[1],  # Replace with actual category IDs
            tags=[],  # Replace with actual tag IDs
            # featured_media_id=featured_media_id,  # If you uploaded an image
            meta_description="Learn how to use the WordPress REST API adapter to publish articles programmatically.",
            excerpt="A demonstration of the WordPress adapter for automated content publishing.",
        )

        print(f"✓ Post created successfully!")
        print(f"  Post ID: {post['id']}")
        print(f"  Post URL: {post['link']}")
        print(f"  Status: {post['status']}")

        # Step 5: Update the post (optional)
        # print("\nUpdating the post...")
        # updated_post = await adapter.update_post(
        #     post_id=post['id'],
        #     status="publish",  # Change from draft to published
        # )
        # print(f"✓ Post updated! New status: {updated_post['status']}")

        # Step 6: Retrieve the post
        print("\nRetrieving the post...")
        retrieved_post = await adapter.get_post(post_id=post['id'])
        print(f"✓ Retrieved post: {retrieved_post['title']['rendered']}")

    except WordPressConnectionError as e:
        print(f"✗ Connection error: {e}")
    except WordPressAuthError as e:
        print(f"✗ Authentication error: {e}")
    except WordPressAPIError as e:
        print(f"✗ API error: {e}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
    finally:
        # Always close the connection
        await adapter.close()
        print("\n✓ Connection closed")


async def example_with_context_manager():
    """Example using async context manager for automatic cleanup."""

    # Using context manager automatically closes the connection
    async with WordPressAdapter(
        site_url="https://your-wordpress-site.com",
        username="your-username",
        app_password="xxxx xxxx xxxx xxxx xxxx xxxx",
    ) as adapter:
        # Test connection
        await adapter.test_connection()

        # Create a post
        post = await adapter.create_post(
            title="Test Post",
            content="<p>This is a test post.</p>",
        )

        print(f"Post created: {post['link']}")

    # Connection is automatically closed when exiting the context


async def example_article_workflow():
    """
    Example workflow that matches the A-Stats Content SaaS use case:
    Generate article -> Upload images -> Publish to WordPress
    """

    async with WordPressAdapter(
        site_url="https://your-wordpress-site.com",
        username="your-username",
        app_password="xxxx xxxx xxxx xxxx xxxx xxxx",
    ) as wp:
        # 1. Test connection
        await wp.test_connection()

        # 2. Upload featured image (from Replicate/AI generation)
        featured_image = await wp.upload_media(
            image_url="https://replicate.delivery/pbxt/xxxx/image.png",
            filename="featured-image.png",
            alt_text="AI-generated featured image for the article",
        )

        # 3. Create the article
        article_data = {
            "title": "10 Benefits of Mindfulness Meditation",
            "content": """<p>Article content here...</p>""",
            "status": "draft",  # Start as draft for review
            "categories": [5],  # Wellness category
            "tags": [12, 15, 18],  # mindfulness, meditation, wellness
            "featured_media_id": featured_image["id"],
            "meta_description": "Discover the top 10 science-backed benefits of mindfulness meditation for mental and physical health.",
        }

        post = await wp.create_post(**article_data)

        print(f"Article published: {post['link']}")
        print(f"Status: {post['status']}")

        return post


if __name__ == "__main__":
    # Run the main example
    asyncio.run(main())

    # Or run with context manager
    # asyncio.run(example_with_context_manager())

    # Or run the article workflow
    # asyncio.run(example_article_workflow())
