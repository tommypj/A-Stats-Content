"""
Example usage of the image storage adapters.

This file demonstrates how to integrate the storage adapters
with image generation workflows (e.g., Replicate).
"""

import asyncio

from adapters.storage import download_image, storage_adapter


async def save_generated_image_from_url(image_url: str, filename: str | None = None) -> str:
    """
    Download and save an image from a URL (e.g., Replicate output).

    Args:
        image_url: URL of the generated image
        filename: Optional custom filename

    Returns:
        Public URL to access the saved image
    """
    # Download the image
    print(f"Downloading image from {image_url}...")
    image_data = await download_image(image_url)
    print(f"Downloaded {len(image_data)} bytes")

    # Generate filename if not provided
    if not filename:
        filename = f"generated_{asyncio.get_event_loop().time()}.png"

    # Save to storage (local or S3 based on settings)
    print(f"Saving to storage as {filename}...")
    storage_path = await storage_adapter.save_image(image_data, filename)
    print(f"Saved to: {storage_path}")

    # Get public URL
    public_url = await storage_adapter.get_image_url(storage_path)
    print(f"Public URL: {public_url}")

    return public_url


async def save_image_bytes(image_data: bytes, filename: str) -> tuple[str, str]:
    """
    Save raw image bytes to storage.

    Args:
        image_data: Raw image bytes
        filename: Desired filename

    Returns:
        Tuple of (storage_path, public_url)
    """
    # Save to storage
    storage_path = await storage_adapter.save_image(image_data, filename)

    # Get public URL
    public_url = await storage_adapter.get_image_url(storage_path)

    return storage_path, public_url


async def cleanup_old_image(image_path_or_url: str) -> bool:
    """
    Delete an old image from storage.

    Args:
        image_path_or_url: Path or URL to the image

    Returns:
        True if deleted successfully
    """
    result = await storage_adapter.delete_image(image_path_or_url)
    if result:
        print(f"Successfully deleted: {image_path_or_url}")
    else:
        print(f"Failed to delete: {image_path_or_url}")
    return result


# Example integration with a use case
class ImageGenerationUseCase:
    """
    Example use case showing how to integrate storage adapter
    with image generation workflow.
    """

    def __init__(self):
        self.storage = storage_adapter

    async def generate_and_save(
        self, prompt: str, user_id: int, project_id: int | None = None
    ) -> dict:
        """
        Generate an image and save it to storage.

        This is a mock example - in real implementation,
        you would call Replicate or another image generation API.

        Args:
            prompt: Image generation prompt
            user_id: User ID for organization
            project_id: Optional project ID

        Returns:
            Dictionary with image metadata
        """
        # Mock: In reality, this would call Replicate
        # output = await replicate_client.run(model, input={"prompt": prompt})
        # image_url = output[0]

        # For this example, we'll use a placeholder
        print(f"[Mock] Generating image for prompt: {prompt}")

        # Download generated image
        # image_data = await download_image(image_url)

        # For this example, create a mock image
        image_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00"

        # Create organized filename
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_prompt = prompt[:30].replace(" ", "_").replace("/", "_")
        filename = f"user_{user_id}_{safe_prompt}_{timestamp}.png"

        # Save to storage
        storage_path = await self.storage.save_image(image_data, filename)

        # Get public URL
        public_url = await self.storage.get_image_url(storage_path)

        return {
            "prompt": prompt,
            "user_id": user_id,
            "project_id": project_id,
            "storage_path": storage_path,
            "public_url": public_url,
            "file_size": len(image_data),
            "generated_at": datetime.now().isoformat(),
        }


# Example usage in a route handler
async def example_route_handler():
    """
    Example of how this might be used in a FastAPI route.
    """
    from infrastructure.config.settings import settings

    print(f"Using storage type: {settings.storage_type}")
    print(f"Storage path: {settings.storage_local_path}")
    print()

    # Example 1: Save from URL
    print("=== Example 1: Save from URL ===")
    # In reality, this would be a Replicate output URL
    mock_url = "https://example.com/generated-image.png"
    # public_url = await save_generated_image_from_url(mock_url, "example.png")
    print(f"Would save from: {mock_url}")
    print()

    # Example 2: Save raw bytes
    print("=== Example 2: Save raw bytes ===")
    mock_image = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00"
    storage_path, public_url = await save_image_bytes(mock_image, "test_image.png")
    print(f"Storage path: {storage_path}")
    print(f"Public URL: {public_url}")
    print()

    # Example 3: Use case integration
    print("=== Example 3: Use Case Integration ===")
    use_case = ImageGenerationUseCase()
    result = await use_case.generate_and_save(
        prompt="A serene mountain landscape at sunset", user_id=123, project_id=456
    )
    print("Generation result:", result)
    print()

    # Example 4: Cleanup
    print("=== Example 4: Cleanup ===")
    await cleanup_old_image(storage_path)


if __name__ == "__main__":
    # Run the example
    asyncio.run(example_route_handler())
