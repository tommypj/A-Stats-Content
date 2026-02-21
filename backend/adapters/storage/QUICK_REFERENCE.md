# Image Storage Quick Reference

## Installation

```bash
# Dependencies are already in pyproject.toml
uv pip install aiohttp boto3
```

## Configuration (.env)

```env
# Use local storage (default)
STORAGE_TYPE=local
STORAGE_LOCAL_PATH=./data/uploads

# OR use S3
STORAGE_TYPE=s3
S3_BUCKET=my-bucket
S3_REGION=us-east-1
S3_ACCESS_KEY=AKIAXXXXXXXX
S3_SECRET_KEY=xxxxxxxxxxxx
```

## Import

```python
from adapters.storage import storage_adapter, download_image
```

## Common Operations

### Save Image from URL
```python
# Download from Replicate/external source
image_data = await download_image("https://example.com/image.png")

# Save to storage
path = await storage_adapter.save_image(image_data, "my_image.png")
# Returns: "images/2026/02/my_image_20260220_143022_123456.png"
```

### Save Raw Image Bytes
```python
# You already have bytes (e.g., from PIL)
with open("source.png", "rb") as f:
    image_data = f.read()

path = await storage_adapter.save_image(image_data, "uploaded.png")
```

### Get Public URL
```python
url = await storage_adapter.get_image_url(path)
# Local: "http://localhost:8000/uploads/images/2026/02/..."
# S3: "https://bucket.s3.region.amazonaws.com/images/2026/02/..."
```

### Delete Image
```python
success = await storage_adapter.delete_image(path)
# Returns: True if deleted, False if failed
```

## Use Case Pattern

```python
from adapters.storage import StorageAdapter

class MyImageUseCase:
    def __init__(self, storage: StorageAdapter):
        self.storage = storage

    async def process_image(self, url: str) -> str:
        data = await download_image(url)
        path = await self.storage.save_image(data, "result.png")
        return await self.storage.get_image_url(path)
```

## Testing

```bash
# Run all storage tests
pytest tests/unit/test_image_storage.py -v

# Run specific test
pytest tests/unit/test_image_storage.py::TestLocalStorageAdapter::test_save_image_creates_directory -v

# With coverage
pytest tests/unit/test_image_storage.py --cov=adapters.storage
```

## File Organization

### Local
```
./data/uploads/
└── images/
    └── 2026/
        └── 02/
            └── filename_20260220_143022_123456.png
```

### S3
```
s3://your-bucket/
└── images/
    └── 2026/
        └── 02/
            └── filename_20260220_143022_123456.png
```

## Error Handling

```python
try:
    path = await storage_adapter.save_image(data, "image.png")
except RuntimeError as e:
    # Handle storage errors
    logger.error(f"Storage error: {e}")
```

## Switch Between Local and S3

Just change the environment variable:
```bash
# Use local
export STORAGE_TYPE=local

# Use S3
export STORAGE_TYPE=s3
```

No code changes needed!

## Complete Example: Replicate Integration

```python
import replicate
from adapters.storage import storage_adapter, download_image

async def generate_and_save(prompt: str) -> str:
    """Generate image with Replicate and save to storage."""

    # 1. Generate with Replicate
    output = replicate.run(
        "black-forest-labs/flux-1.1-pro",
        input={"prompt": prompt}
    )

    # 2. Download the generated image
    image_url = output[0] if isinstance(output, list) else output
    image_data = await download_image(image_url)

    # 3. Save to storage (local or S3)
    filename = f"{prompt[:30].replace(' ', '_')}.png"
    storage_path = await storage_adapter.save_image(image_data, filename)

    # 4. Get public URL
    public_url = await storage_adapter.get_image_url(storage_path)

    return public_url
```

## FastAPI Route Example

```python
from fastapi import APIRouter
from adapters.storage import storage_adapter, download_image

router = APIRouter()

@router.post("/images/generate")
async def generate_image(prompt: str):
    """Generate and save an image."""
    # Generate with Replicate...
    replicate_url = "https://replicate.delivery/..."

    # Download and save
    image_data = await download_image(replicate_url)
    path = await storage_adapter.save_image(image_data, "generated.png")
    url = await storage_adapter.get_image_url(path)

    return {"url": url, "path": path}
```

## Tips

1. **Filenames**: Always use safe filenames (no special chars)
2. **Extensions**: Include proper extension (.png, .jpg, .webp)
3. **Cleanup**: Delete old images to save space
4. **URLs**: Store the path in DB, generate URL when needed
5. **Testing**: Use LocalStorageAdapter with temp directory for tests

## Troubleshooting

### Import Error
```
ModuleNotFoundError: No module named 'aiohttp'
```
Solution: `pip install aiohttp boto3`

### S3 Credentials Error
```
RuntimeError: AWS credentials not configured
```
Solution: Set S3_ACCESS_KEY and S3_SECRET_KEY in .env

### Permission Error (Local)
```
PermissionError: [Errno 13] Permission denied
```
Solution: Ensure STORAGE_LOCAL_PATH is writable

### Path Not Found (Local)
```
FileNotFoundError: No such file or directory
```
Solution: Directory is created automatically on save, but parent must exist

## Support

- Full documentation: `README.md`
- Implementation details: `IMPLEMENTATION_SUMMARY.md`
- Example code: `example_usage.py`
- Tests: `tests/unit/test_image_storage.py`
