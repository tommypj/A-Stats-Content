# Triple Image Prompts per Article

## Goal

Generate 3 distinct image prompt variations during article creation so users can choose which to generate, giving them visual variety without wasting image generation credits.

## Architecture

Single Claude Sonnet call in pipeline Step 7 returns 3 prompts (different compositions/concepts). Prompts are stored on the Article model. Users see all 3 when they navigate to the image section, can edit each prompt, and generate images one at a time. Each generated image has a "Set as Featured" button.

## Data Model

### Migration: `Article.image_prompt` (Text) → `Article.image_prompts` (JSON)

- New column: `image_prompts` — JSON array of up to 3 strings
- Migration copies existing `image_prompt` values into `["existing prompt"]`
- Articles with no prompt get `image_prompts: null`
- Drop `image_prompt` column after migration

### No changes to `GeneratedImage` model

Existing `article_id` FK and `prompt` field already support multiple images per article. The frontend matches generated images to prompt slots by comparing `GeneratedImage.prompt` against the `image_prompts` array entries.

## Backend Changes

### Content Pipeline (Step 7)

**File:** `backend/services/content_pipeline.py`

Current: `content_ai_service.generate_image_prompt()` → returns 1 string

New: `content_ai_service.generate_image_prompts()` → returns list of 3 strings

- Single Claude Sonnet call with instruction to return 3 distinct visual concepts
- Each prompt describes a different composition (e.g., close-up portrait, wide establishing shot, abstract conceptual)
- Timeout: 45s (slightly longer for 3 prompts)
- Fallback: if parsing fails, wrap whatever is returned in a 1-element list
- Store result in `Article.image_prompts` (JSON array)

### Content AI Service

**File:** `backend/services/content_ai_service.py`

New method `generate_image_prompts(title, content, keyword)`:
- System prompt instructs: "Generate exactly 3 distinct image prompts for this article. Each should describe a different visual concept. Return as a JSON array of 3 strings."
- Parse response as JSON array
- Validate: must be list of 3 non-empty strings
- If validation fails, fall back to single prompt in a list

### Article Serialization

**File:** `backend/api/schemas/content.py`

- `ArticleResponse.image_prompt` → `image_prompts: list[str] | None`
- Backward compatible: old clients receiving `null` or `["single"]` still work

### No changes to image generation endpoint

`POST /api/v1/images/generate` already accepts `prompt` + `article_id`. Frontend sends one prompt at a time.

## Frontend Changes

### Image Generation Page (article selected)

**File:** `frontend/app/(dashboard)/images/generate/page.tsx`

When user selects an article with `image_prompts`:

- Show 3 prompt cards (or fewer if article has < 3)
- Each card contains:
  - Editable textarea with the prompt text
  - "Generate" button
  - After generation: image preview with "Set as Featured" button
- User can edit the prompt before generating (one shot — no regenerate)
- Generation uses existing polling mechanism (POST → poll status)
- "Set as Featured" calls existing `POST /images/{id}/set-featured`

### Image matching logic

To show which prompts already have images generated:
- Fetch `GeneratedImage` records where `article_id` matches
- Match each image's `prompt` field against `image_prompts` entries (fuzzy — user may have edited)
- Unmatched images show in a separate "Other images" section

## Usage & Billing

- Each image generation = 1 credit against monthly quota (no change)
- Generating all 3 = 3 credits
- Prompt generation (text) is part of article pipeline cost (1 extra Claude call, negligible)

## Edge Cases

| Case | Behavior |
|------|----------|
| Old article with 1 prompt | Shows 1 prompt card. No retroactive generation. |
| Article with no prompts | Shows empty state with link to standalone generator |
| Pipeline prompt generation fails | `image_prompts: null` — same as today |
| User edits prompt then generates | Edited prompt sent to image API. Image stores the edited version. |
| User generates image, then wants different result | Must use standalone image generator (one shot per prompt slot) |

## Not In Scope

- Retroactive 3-prompt generation for existing articles
- Regenerate button per prompt slot
- Auto-generation of images during pipeline (user-triggered only)
- Changes to admin blog post creation flow (already uses `featured_image_id`)
