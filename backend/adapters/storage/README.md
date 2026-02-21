# Image Storage Adapters

This module provides storage adapters for saving generated images locally or to AWS S3.

## Architecture

Following Clean Architecture principles:
- **Abstract Base Class**: `StorageAdapter` defines the interface
- **Concrete Implementations**: `LocalStorageAdapter` and `S3StorageAdapter`
- **Factory Pattern**: `get_storage_adapter()` returns the appropriate adapter based on settings

## Configuration

Configure storage in `.env` or `settings.py`:

```env
# Storage Type (local or s3)
STORAGE_TYPE=local

# Local Storage
STORAGE_LOCAL_PATH=./data/uploads

# S3 Storage (if STORAGE_TYPE=s3)
S3_BUCKET=my-bucket-name
S3_REGION=us-east-1
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
```

## Usage

### Basic Usage

```python
from adapters.storage import storage_adapter, download_image

# Download an image from a URL (e.g., from Replicate)
image_data = await download_image("https://replicate.delivery/pbxt/...")

# Save to storage (local or S3 based on settings)
image_path = await storage_adapter.save_image(image_data, "generated_image.png")

# Get public URL
public_url = await storage_adapter.get_image_url(image_path)

# Delete image
await storage_adapter.delete_image(image_path)
```

### Using Specific Adapters

```python
from adapters.storage import LocalStorageAdapter, S3StorageAdapter

# Force local storage
local_adapter = LocalStorageAdapter(base_path="./custom/path")
path = await local_adapter.save_image(image_data, "test.png")

# Force S3 storage
s3_adapter = S3StorageAdapter(
    bucket="my-bucket",
    region="us-east-1",
    access_key="key",
    secret_key="secret"
)
url = await s3_adapter.save_image(image_data, "test.png")
```

### Integration with Image Generation

```python
from adapters.storage import storage_adapter, download_image
import replicate

async def generate_and_save_image(prompt: str) -> str:
    """Generate an image with Replicate and save it to storage."""

    # Generate image with Replicate
    output = replicate.run(
        "black-forest-labs/flux-1.1-pro",
        input={"prompt": prompt}
    )

    # Download the generated image
    image_url = output[0] if isinstance(output, list) else output
    image_data = await download_image(image_url)

    # Save to storage (local or S3)
    filename = f"{prompt[:30].replace(' ', '_')}.png"
    storage_path = await storage_adapter.save_image(image_data, filename)

    # Get public URL
    public_url = await storage_adapter.get_image_url(storage_path)

    return public_url
```

## File Organization

### Local Storage Structure
```
./data/uploads/
└── images/
    └── 2026/
        └── 02/
            ├── hero_image_20260220_143022_123456.png
            ├── logo_20260220_143055_789012.jpg
            └── banner_20260220_143112_345678.webp
```

### S3 Storage Structure
```
s3://your-bucket/
└── images/
    └── 2026/
        └── 02/
            ├── hero_image_20260220_143022_123456.png
            ├── logo_20260220_143055_789012.jpg
            └── banner_20260220_143112_345678.webp
```

## Features

### LocalStorageAdapter

- **Date-based organization**: Files organized by year and month
- **Automatic directory creation**: Creates directories as needed
- **Filename sanitization**: Prevents directory traversal attacks
- **Collision prevention**: Adds timestamps to prevent filename collisions
- **Local URL generation**: Returns URLs suitable for serving via backend API

### S3StorageAdapter

- **Public access**: Uploads with `public-read` ACL for direct access
- **Content-Type detection**: Automatically sets correct MIME types
- **Date-based organization**: Same structure as local storage
- **Graceful error handling**: Handles missing credentials and S3 errors
- **URL generation**: Returns public S3 URLs

### Helper Functions

#### `download_image(url: str) -> bytes`
- Downloads images from URLs (e.g., Replicate output)
- 30-second timeout
- Proper error handling for network issues

#### `get_storage_adapter() -> StorageAdapter`
- Factory function that returns the correct adapter
- Based on `settings.storage_type`
- Supports 'local' and 's3'

## Testing

Run the test suite:

```bash
# From backend directory
pytest tests/unit/test_image_storage.py -v

# With coverage
pytest tests/unit/test_image_storage.py --cov=adapters.storage --cov-report=term-missing
```

## Dependency Injection

For use cases that need storage, inject the adapter:

```python
from core.use_cases.base import UseCase
from adapters.storage import StorageAdapter

class GenerateImageUseCase(UseCase):
    def __init__(self, storage: StorageAdapter):
        self.storage = storage

    async def execute(self, prompt: str) -> str:
        # Generate image...
        image_data = await self._generate(prompt)

        # Save to storage
        path = await self.storage.save_image(image_data, "image.png")
        return await self.storage.get_image_url(path)
```

## Error Handling

All methods raise `RuntimeError` on failure:

```python
try:
    path = await storage_adapter.save_image(image_data, "test.png")
except RuntimeError as e:
    logger.error(f"Failed to save image: {e}")
    # Handle error appropriately
```

## Security Considerations

1. **Filename Sanitization**: All filenames are sanitized to prevent directory traversal
2. **S3 ACLs**: Files are uploaded with public-read ACL - ensure bucket policies are configured correctly
3. **Credentials**: S3 credentials should be stored in environment variables, never in code
4. **Download Validation**: The `download_image` function validates HTTP status codes
5. **Path Validation**: Local storage validates paths to prevent writing outside upload directory
