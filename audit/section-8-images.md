# Audit Section 8 — Images
**Date**: 2026-02-27
**Status**: Complete

---

## Scope
- AI image generation via Replicate API
- Image storage (local + S3 adapters)
- Image gallery CRUD, bulk operations, download
- Image serving via static files middleware
- Frontend gallery, image picker, admin images panel

---

## Files Audited
- `backend/api/routes/images.py`
- `backend/adapters/storage/image_storage.py`
- `backend/adapters/ai/image_ai_service.py`
- `backend/infrastructure/database/models/` (image models)
- `backend/main.py` (static file serving)
- `frontend/app/[locale]/(dashboard)/images/page.tsx`
- `frontend/app/[locale]/(admin)/admin/content/images/page.tsx`
- `frontend/lib/api.ts` (image methods + getImageUrl)

---

## Findings

### CRITICAL

#### IMG-01 — No file size limit on image downloaded from Replicate — disk exhaustion
- **Severity**: CRITICAL
- **File**: `backend/api/routes/images.py:118-131`
- **Description**: After AI generation, `download_image(generated.url)` fetches the result from Replicate and writes it to disk with no size check. The returned URL's content could be extremely large (e.g., if Replicate ever returns an unusually large file or the URL is manipulated). No Content-Length validation is performed before `response.read()`. An adversary who can influence generation parameters or intercept the HTTP response could cause disk exhaustion.
- **Fix**: Add a maximum size guard in `download_image()`:
  ```python
  MAX_IMAGE_SIZE = 20 * 1024 * 1024  # 20MB
  data = await response.read()
  if len(data) > MAX_IMAGE_SIZE:
      raise ValueError(f"Downloaded image exceeds max size ({MAX_IMAGE_SIZE} bytes)")
  ```

#### IMG-02 — SSRF: Replicate URL downloaded without scheme/domain validation
- **Severity**: CRITICAL
- **File**: `backend/api/routes/images.py:104-131`
- **Description**: The URL returned by the Replicate API is passed directly to `download_image()` without validating the scheme or domain. If Replicate's response is tampered with (e.g., MITM on an unencrypted connection, or a bug in the Replicate SDK returning an attacker-controlled URL), the backend could be tricked into fetching arbitrary URLs including internal metadata services (`http://169.254.169.254/`), filesystem paths (`file:///etc/passwd`), or attacker-controlled servers.
- **Fix**: Whitelist the allowed Replicate CDN domains before downloading:
  ```python
  ALLOWED_IMAGE_DOMAINS = {"replicate.delivery", "cdn.replicate.com", "pbxt.replicate.delivery"}
  parsed = urlparse(generated.url)
  if parsed.scheme != "https" or not any(parsed.netloc.endswith(d) for d in ALLOWED_IMAGE_DOMAINS):
      raise ValueError(f"Image URL from AI service failed domain validation: {parsed.netloc}")
  ```

#### IMG-03 — Orphaned files when DB commit fails after storage write
- **Severity**: CRITICAL
- **File**: `backend/api/routes/images.py:118-127`
- **Description**: The processing sequence is: (1) save file to storage, (2) update `image.local_path`, (3) `await db.commit()`. If step 3 fails (DB connection lost, constraint violation), the file is permanently on disk with no database record. There is no cleanup path. Over time this produces silent storage leaks with no way to identify orphaned files.
- **Fix**: Add cleanup on commit failure:
  ```python
  local_path = await storage_adapter.save_image(image_data, filename)
  try:
      image.local_path = local_path
      await db.commit()
  except Exception:
      await storage_adapter.delete_image(local_path)
      raise
  ```

---

### HIGH

#### IMG-04 — Rate limiting is per-IP only — no per-user/project AI cost guard
- **Severity**: HIGH
- **File**: `backend/api/routes/images.py:199`
- **Description**: `@limiter.limit("10/minute")` on the generate endpoint is per-IP, not per-user. A single authenticated user behind a rate limiter (or using different IPs) can generate images without bound. Each Replicate generation call costs real money. There is no daily/monthly quota check for image generation separate from the article generation limits.
- **Fix**: Add a per-user daily quota check using the existing `GenerationTracker` or a dedicated `image_generation_count` counter. Reject with 429 if the user's daily limit is reached.

#### IMG-05 — File deletion failure is silently swallowed — DB record deleted, file stays on disk
- **Severity**: HIGH
- **File**: `backend/api/routes/images.py:423-427`
- **Description**: The delete endpoint wraps `storage_adapter.delete_image()` in a try-except that only logs a warning on failure and then proceeds to delete the DB record. The caller receives 204 No Content but the file remains on disk. The DB and filesystem are permanently out of sync.
- **Fix**: Fail the HTTP request if file deletion fails — do not delete the DB record until the file is confirmed deleted:
  ```python
  if image.local_path:
      deleted = await storage_adapter.delete_image(image.local_path)
      if not deleted:
          raise HTTPException(500, "Failed to delete image from storage")
  await db.delete(image)
  await db.commit()
  ```

#### IMG-06 — Images served via unauthenticated `/uploads` StaticFiles mount — any user can access any image
- **Severity**: HIGH
- **File**: `backend/main.py:217`
- **Description**: `app.mount("/uploads", StaticFiles(directory=uploads_path))` serves all uploaded/generated images without authentication. Any person who knows (or guesses) a file path (e.g., `/uploads/images/2026/02/image_<uuid>.jpg`) can access any image regardless of which user generated it. The path structure is predictable. This violates multi-tenancy — images should only be accessible to their owner/project.
- **Fix**: Remove the StaticFiles mount and replace with an authenticated route: `GET /images/{image_id}/file` that loads the image from DB, verifies ownership, then serves via `FileResponse`. For external Replicate URLs, redirect directly.

#### IMG-07 — Admin image deletion missing project scope check — IDOR
- **Severity**: HIGH
- **File**: `backend/api/routes/admin_content.py:516-550`
- **Description**: The admin delete endpoint queries `SELECT * FROM generated_images WHERE id=?` with no project filter. An admin with limited project scope could delete images belonging to any project in the system.
- **Fix**: If the admin model supports project-scoped roles, add `AND project_id=admin.project_id` to the query for non-super-admins.

#### IMG-08 — No timeout on image generation — generation task hangs indefinitely on Replicate timeout
- **Severity**: HIGH
- **File**: `backend/api/routes/images.py:95-152`
- **Description**: The background task calls `image_ai_service.generate_image()` with no `asyncio.wait_for()` timeout. If the Replicate API hangs (rate limited, service degraded), the background task hangs indefinitely. The image stays in `generating` status forever with no user notification and no retry.
- **Fix**: Wrap the generation call: `await asyncio.wait_for(image_ai_service.generate_image(...), timeout=120.0)`. On `TimeoutError`, set `image.status = "failed"` with `generation_error = "Image generation timed out"`.

#### IMG-09 — Images served via unauthenticated `/uploads` mount also lacks cache headers
- **Severity**: HIGH (subsection of IMG-06, kept separate as a distinct operational issue)
- **File**: `backend/main.py:217`
- **Description**: Beyond the auth issue (IMG-06), the StaticFiles mount has no cache control headers. Every page load re-fetches images from disk even though generated images are immutable (the same UUID always returns the same image). This causes unnecessary bandwidth and latency.
- **Fix**: When implementing the authenticated image endpoint (IMG-06), add `Cache-Control: public, max-age=31536000, immutable` for authenticated responses.

---

### MEDIUM

#### IMG-10 — Admin images page uses `image.url` directly instead of `getImageUrl()`
- **Severity**: MEDIUM
- **File**: `frontend/app/[locale]/(admin)/admin/content/images/page.tsx:224`
- **Description**: The admin gallery renders images with `src={image.url}` (raw DB value). For locally stored images, `url` is a relative path like `/uploads/images/...`. Without `getImageUrl()`, this path doesn't include the API base URL. Images fail to load in the admin panel for any locally-stored image.
- **Fix**: Replace `image.url` with `getImageUrl(image.url)` consistently.

#### IMG-11 — Content-Type detection based on file extension, not magic bytes
- **Severity**: MEDIUM
- **File**: `backend/adapters/storage/image_storage.py:287-294`
- **Description**: When uploading to S3, content type is determined purely by file extension (`if filename.endswith('.jpg')`). An attacker could rename a non-image file with a `.jpg` extension to bypass content type validation. If served with `Content-Type: image/jpeg`, some browsers may interpret the response differently.
- **Fix**: Use `python-magic` to detect MIME type from the first few bytes of the file data before storage, and use that as the S3 content type override.

#### IMG-12 — Image download function provides no user feedback (no loading state, no error toast)
- **Severity**: MEDIUM
- **File**: `frontend/app/[locale]/(dashboard)/images/page.tsx:192`
- **Description**: `handleDownload()` fires a synthetic click with no loading state and no error handling. If the URL is expired or unavailable, the browser silently fails to download with no indication to the user.
- **Fix**: Add `isDownloading` state, disable the download button during download, wrap in try-catch with `toast.error(parseApiError(err).message)` on failure.

#### IMG-13 — Bulk delete uses generic error message — doesn't use `parseApiError()` pattern
- **Severity**: MEDIUM
- **File**: `frontend/app/[locale]/(dashboard)/images/page.tsx:255-273`
- **Description**: The bulk delete catch block shows `toast.error("Failed to delete images. Please try again.")` — a hardcoded generic message. Backend may return specific errors (e.g., "Image is used as featured image for 3 articles"). These details are silently swallowed.
- **Fix**: Replace with `toast.error(parseApiError(error).message)` following the established project pattern.

#### IMG-14 — Storage adapter `delete_image()` returns `False` on failure instead of raising
- **Severity**: MEDIUM
- **File**: `backend/adapters/storage/image_storage.py` (LocalStorageAdapter vs S3StorageAdapter)
- **Description**: `LocalStorageAdapter.delete_image()` returns `False` on failure; `S3StorageAdapter.delete_image()` raises an exception. Callers must handle two different error contracts. The route code (IMG-05) checks neither the return value nor catches exceptions consistently.
- **Fix**: Standardize: both adapters should raise a `StorageError` exception on failure. Update callers to catch `StorageError`.

#### IMG-15 — Downloaded image data not validated before storage — corrupted images stored silently
- **Severity**: MEDIUM
- **File**: `backend/api/routes/images.py:119-127`
- **Description**: After downloading from Replicate, `image_data` bytes are written to disk without verifying they constitute a valid image. A corrupted or empty response would create a broken file. When the frontend later tries to display it, the image fails to render.
- **Fix**: Validate using Pillow: `from PIL import Image; Image.open(BytesIO(image_data)).verify()`. If verification fails, mark generation as failed.

---

### LOW

#### IMG-16 — No retry logic on transient download failures
- **Severity**: LOW
- **File**: `backend/api/routes/images.py:119`
- **Description**: If the `download_image()` call fails due to a transient network error (Replicate CDN hiccup), the image is immediately marked as failed with no retry. The user must regenerate to get a new attempt.
- **Fix**: Wrap `download_image()` with exponential backoff retry (3 attempts, 1s/2s/4s delays) using the existing retry pattern from `anthropic_adapter.py`.

#### IMG-17 — Alt text for generated images auto-generated from prompt — not user-customizable
- **Severity**: LOW
- **File**: `backend/api/routes/images.py:106`
- **Description**: `image.alt_text` is set to the first 100 characters of the prompt. Users cannot provide custom alt text for accessibility. Screen reader users see the raw prompt text, which is often not a good accessibility description.
- **Fix**: Add an optional `alt_text: Optional[str] = Field(None, max_length=500)` to `ImageGenerateRequest`. Use it if provided, fall back to prompt-derived text.

#### IMG-18 — No structured error logging for image generation failures
- **Severity**: LOW
- **File**: `backend/api/routes/images.py:135-152`
- **Description**: Generation failures write to `image.generation_error` in the DB but don't emit structured log events. Monitoring systems can't alert on elevated generation failure rates.
- **Fix**: Add `logger.error("Image generation failed", extra={"image_id": ..., "error_type": ..., "user_id": ...}, exc_info=True)` in the failure path.

#### IMG-19 — No prompt content validation before sending to Replicate
- **Severity**: LOW
- **File**: `backend/api/schemas/content.py:307`
- **Description**: Image prompts accept any string up to 1000 characters with no keyword filtering. While Replicate has its own safety filters, the absence of backend-level prompt validation means abusive or policy-violating prompts are sent directly to the AI API before being rejected, consuming quota.
- **Fix**: Add a basic blocklist check for terms that violate Replicate's usage policies. Log rejected prompts for abuse monitoring.

#### IMG-20 — WordPress image send failure uses generic error — doesn't surface backend detail
- **Severity**: LOW
- **File**: `frontend/app/[locale]/(dashboard)/images/page.tsx:212`
- **Description**: When sending an image to WordPress fails, the catch block sets a generic error state. The actual WordPress API error (wrong credentials, size limit exceeded, etc.) is not surfaced to the user.
- **Fix**: Use `parseApiError(err).message` in the catch block for the WordPress send action.

---

## What's Working Well
- Background task pattern for generation (non-blocking, returns 202 immediately)
- Image status lifecycle: generating → completed/failed
- `getImageUrl()` helper correctly proxies local vs external URLs (just not used consistently)
- Gallery pagination with configurable page size (1–100)
- Bulk delete correctly uses request body for ID list
- Soft delete not used — hard delete appropriate for images (no versioning needed)
- Image generation uses Replicate's async prediction API (avoids blocking)
- Local storage adapter creates organized directory structure by date

---

## Fix Priority Order
1. IMG-01 — No download size limit (CRITICAL)
2. IMG-02 — SSRF via unvalidated Replicate URL (CRITICAL)
3. IMG-03 — Orphaned files on DB commit failure (CRITICAL)
4. IMG-04 — Rate limiting per-IP only, no per-user quota (HIGH)
5. IMG-05 — File deletion failure swallowed silently (HIGH)
6. IMG-06 — Unauthenticated image serving via StaticFiles (HIGH)
7. IMG-07 — Admin deletion no project scope (HIGH)
8. IMG-08 — No timeout on image generation task (HIGH)
9. IMG-10 — Admin page uses raw URL without getImageUrl() (MEDIUM)
10. IMG-11 — Content-Type from extension, not magic bytes (MEDIUM)
11. IMG-12 — Download button no feedback/error handling (MEDIUM)
12. IMG-13 — Bulk delete generic error, not parseApiError() (MEDIUM)
13. IMG-14 — Storage adapter inconsistent error contract (MEDIUM)
14. IMG-15 — No image validation after download (MEDIUM)
15. IMG-16 through IMG-20 — Low severity items (LOW)
