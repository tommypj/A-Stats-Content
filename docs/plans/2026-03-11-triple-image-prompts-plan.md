# Triple Image Prompts Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Generate 3 distinct image prompt variations per article so users can choose which to generate, giving visual variety without wasting credits.

**Architecture:** Pipeline Step 7 calls Claude Sonnet once returning 3 prompts as JSON. Stored as a JSON array on `Article.image_prompts`. Frontend image generation page shows 3 editable prompt cards when an article is selected, each with its own generate button and "Set as Featured" action.

**Tech Stack:** FastAPI, SQLAlchemy (JSON column), Alembic, Next.js, React Query, Tailwind

---

### Task 1: Database Migration — `image_prompt` → `image_prompts`

**Files:**
- Create: `backend/infrastructure/database/migrations/versions/059_article_image_prompts_json.py`
- Modify: `backend/infrastructure/database/models/content.py:220`

**Step 1: Create migration file**

```python
"""Convert Article.image_prompt (Text) to image_prompts (JSON array)

Revision ID: 059
Revises: 058
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

revision = "059"
down_revision = "058"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new JSON column
    op.add_column("articles", sa.Column("image_prompts", JSON, nullable=True))

    # Migrate existing single prompts into 1-element arrays
    op.execute("""
        UPDATE articles
        SET image_prompts = json_build_array(image_prompt)
        WHERE image_prompt IS NOT NULL AND image_prompt != ''
    """)

    # Drop old column
    op.drop_column("articles", "image_prompt")


def downgrade() -> None:
    op.add_column("articles", sa.Column("image_prompt", sa.Text, nullable=True))

    # Take first element back
    op.execute("""
        UPDATE articles
        SET image_prompt = image_prompts->>0
        WHERE image_prompts IS NOT NULL
    """)

    op.drop_column("articles", "image_prompts")
```

**Step 2: Update Article model**

In `backend/infrastructure/database/models/content.py:220`, replace:

```python
image_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
```

With:

```python
image_prompts: Mapped[list | None] = mapped_column(JSON, nullable=True)
```

Add import at top if not present: `from sqlalchemy.dialects.postgresql import JSON` (or use `sqlalchemy.JSON`).

**Step 3: Run migration locally to verify**

Run: `cd backend && alembic upgrade head`
Expected: Migration applies successfully

**Step 4: Commit**

```bash
git add backend/infrastructure/database/migrations/versions/059_article_image_prompts_json.py backend/infrastructure/database/models/content.py
git commit -m "feat: migrate Article.image_prompt to image_prompts JSON array"
```

---

### Task 2: Update Backend Schemas and API Responses

**Files:**
- Modify: `backend/api/schemas/content.py:222,255`
- Modify: `backend/api/routes/articles.py` (any reference to `image_prompt`)
- Modify: `frontend/lib/api.ts` (Article type)

**Step 1: Update Pydantic schemas**

In `backend/api/schemas/content.py`, find both occurrences of:

```python
image_prompt: str | None = None
```

Replace with:

```python
image_prompts: list[str] | None = None
```

**Step 2: Update article routes**

Search `backend/api/routes/articles.py` for any reference to `image_prompt` and update to `image_prompts`. The pipeline result assignment (where `PipelineResult.image_prompt` is set on the article) needs updating — this happens in `content_pipeline.py` and will be addressed in Task 3.

Run: `grep -n "image_prompt" backend/api/routes/articles.py`

Update each occurrence to `image_prompts`.

**Step 3: Update frontend API type**

In `frontend/lib/api.ts`, find:

```typescript
image_prompt?: string;
```

Replace with:

```typescript
image_prompts?: string[] | null;
```

Also find the pipeline response type (around line 1320) and update:

```typescript
image_prompt?: string
```

to:

```typescript
image_prompts?: string[]
```

**Step 4: Commit**

```bash
git add backend/api/schemas/content.py backend/api/routes/articles.py frontend/lib/api.ts
git commit -m "feat: update schemas and types for image_prompts array"
```

---

### Task 3: New Prompt Template and AI Service Method

**Files:**
- Create: `backend/prompts/user/image_prompts.v1.0.txt`
- Modify: `backend/prompts/manifest.json`
- Modify: `backend/adapters/ai/anthropic_adapter.py:733-764`

**Step 1: Create new prompt template**

Create `backend/prompts/user/image_prompts.v1.0.txt`:

```
Based on this article, generate exactly 3 distinct image prompts for AI image generation. Each prompt should describe a completely different visual concept for a featured image.

Title: {title}
Keyword: {keyword}
Content excerpt:
{content_excerpt}

Requirements for EACH prompt:
- Describe a specific visual scene, not abstract concepts
- Include details about composition, lighting, colors, and mood
- Do NOT include any text or words in the image description
- Keep each prompt under 200 words
- Optimize for photographic or editorial style

Make the 3 prompts meaningfully different:
- Prompt 1: A close-up or portrait-style composition focusing on a person or detail
- Prompt 2: A wider establishing shot showing environment or context
- Prompt 3: A creative or conceptual approach with dramatic lighting or unique perspective

Respond with ONLY a JSON array of exactly 3 strings. Example format:
["prompt one text here", "prompt two text here", "prompt three text here"]
```

**Step 2: Register in manifest**

In `backend/prompts/manifest.json`, add after the `image_prompt` entry:

```json
"image_prompts": { "version": "1.0", "path": "user/image_prompts.v1.0.txt" },
```

**Step 3: Add `generate_image_prompts` method to anthropic adapter**

In `backend/adapters/ai/anthropic_adapter.py`, after the existing `generate_image_prompt` method (line 764), add:

```python
async def generate_image_prompts(
    self,
    title: str,
    content: str,
    keyword: str,
) -> list[str]:
    """
    Generate 3 distinct image prompts optimized for AI image generation.

    Returns:
        A list of 3 image prompt strings.
    """
    if not self._client:
        return [f"A visually striking image representing {keyword}, related to {title}"]

    prompt = prompt_loader.format(
        "image_prompts",
        title=title,
        keyword=keyword,
        content_excerpt=content[:1500],
    )

    message = await _retry_with_backoff(
        lambda: self._client.messages.create(
            model=self._model,
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
    )

    raw = message.content[0].text.strip()

    # Parse JSON array response
    import json
    try:
        prompts = json.loads(raw)
        if isinstance(prompts, list) and len(prompts) >= 1:
            # Ensure we have strings and cap at 3
            result = [str(p).strip() for p in prompts[:3] if str(p).strip()]
            if result:
                return result
    except (json.JSONDecodeError, TypeError):
        pass

    # Fallback: treat entire response as a single prompt
    return [raw] if raw else [f"A visually striking image representing {keyword}, related to {title}"]
```

**Step 4: Commit**

```bash
git add backend/prompts/user/image_prompts.v1.0.txt backend/prompts/manifest.json backend/adapters/ai/anthropic_adapter.py
git commit -m "feat: add generate_image_prompts method returning 3 prompt variations"
```

---

### Task 4: Update Content Pipeline Step 7

**Files:**
- Modify: `backend/services/content_pipeline.py:91,461-477,606`

**Step 1: Update PipelineResult dataclass**

At line 91, change:

```python
image_prompt: str | None = None
```

To:

```python
image_prompts: list[str] | None = None
```

**Step 2: Update the `_image_prompt` async helper**

At lines 461-473, replace the entire function:

```python
async def _image_prompts() -> list[str] | None:
    try:
        return await asyncio.wait_for(
            content_ai_service.generate_image_prompts(
                title=title or outline.title,
                content=article.content,
                keyword=keyword,
            ),
            timeout=45.0,
        )
    except Exception as e:
        logger.warning("Image prompts generation failed: %s", e)
        return None
```

**Step 3: Update the gather call**

At line 475, change:

```python
serp_seo, ai_flags, image_prompt = await asyncio.gather(
    _seo_check(), _fact_check(), _image_prompt()
)
```

To:

```python
serp_seo, ai_flags, image_prompts = await asyncio.gather(
    _seo_check(), _fact_check(), _image_prompts()
)
```

**Step 4: Update PipelineResult construction**

At line 606, change:

```python
image_prompt=image_prompt,
```

To:

```python
image_prompts=image_prompts,
```

**Step 5: Update where pipeline result is saved to article**

Search for where `result.image_prompt` is assigned to the article model and update to `result.image_prompts` → `article.image_prompts`.

Run: `grep -n "image_prompt" backend/services/content_pipeline.py` to find all remaining references.

**Step 6: Commit**

```bash
git add backend/services/content_pipeline.py
git commit -m "feat: pipeline Step 7 generates 3 image prompts via single AI call"
```

---

### Task 5: Update Article Creation Route

**Files:**
- Modify: `backend/api/routes/articles.py` (where pipeline result is saved to article)

**Step 1: Find and update image_prompt assignment**

Run: `grep -n "image_prompt" backend/api/routes/articles.py`

Replace any `article.image_prompt = ...` with `article.image_prompts = ...`

Also update the pipeline response dict that returns `image_prompt` to the frontend — change key to `image_prompts`.

**Step 2: Verify no remaining references**

Run: `grep -rn "image_prompt[^s]" backend/api/routes/articles.py backend/services/content_pipeline.py backend/api/schemas/content.py`

Expected: No matches (all should be `image_prompts` now)

**Step 3: Commit**

```bash
git add backend/api/routes/articles.py
git commit -m "feat: article creation stores image_prompts array from pipeline"
```

---

### Task 6: Frontend — Article Prompt Cards UI

**Files:**
- Modify: `frontend/app/(dashboard)/images/generate/page.tsx`

This is the largest frontend change. When a user selects an article with `image_prompts`, replace the single prompt textarea with 3 prompt cards.

**Step 1: Update state management**

Replace single prompt state with multi-prompt state. At the top of `GenerateImageContent`:

```typescript
// Replace these:
// const [prompt, setPrompt] = useState("");
// const [promptSource, setPromptSource] = useState<"manual" | "article">("manual");

// With:
const [prompt, setPrompt] = useState("");
const [articlePrompts, setArticlePrompts] = useState<string[]>([]);
const [activePromptIndex, setActivePromptIndex] = useState<number | null>(null);
const [promptCardImages, setPromptCardImages] = useState<Record<number, GeneratedImage | null>>({});
const [generatingIndex, setGeneratingIndex] = useState<number | null>(null);
```

**Step 2: Update article selection effect**

Replace the existing `useEffect` that auto-fills prompt (lines 123-136):

```typescript
useEffect(() => {
  if (!articleId) {
    setArticlePrompts([]);
    setPromptCardImages({});
    setActivePromptIndex(null);
    setGeneratingIndex(null);
    return;
  }
  const selected = articles.find((a) => a.id === articleId);
  if (selected?.image_prompts && selected.image_prompts.length > 0) {
    setArticlePrompts([...selected.image_prompts]);
    setPromptCardImages({});
    setActivePromptIndex(null);
    setGeneratingIndex(null);
  } else {
    setArticlePrompts([]);
  }
}, [articleId, articles]);
```

**Step 3: Add prompt card generation handler**

```typescript
function handleGenerateForPrompt(index: number) {
  const promptText = articlePrompts[index]?.trim();
  if (!promptText || generateMutation.isPending) return;

  setError("");
  setGeneratingIndex(index);
  setPromptCardImages((prev) => ({ ...prev, [index]: null }));

  const selectedSize = IMAGE_SIZES.find((s) => s.value === size);
  generateMutation.mutate(
    {
      prompt: promptText,
      style,
      width: selectedSize?.width,
      height: selectedSize?.height,
      article_id: articleId || undefined,
    },
    {
      onSuccess: (image) => {
        setPromptCardImages((prev) => ({ ...prev, [index]: image }));
        // Start polling for this specific card
        pollPromptCardImage(index, image.id);
      },
      onError: () => {
        setError(`Failed to generate image for prompt ${index + 1}`);
        setGeneratingIndex(null);
      },
    }
  );
}
```

**Step 4: Add polling for prompt card images**

```typescript
function pollPromptCardImage(index: number, imageId: string) {
  const maxAttempts = 90;
  let attempts = 0;

  if (pollRef.current) clearInterval(pollRef.current);
  pollRef.current = setInterval(async () => {
    if (!isMountedRef.current) {
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = null;
      return;
    }
    try {
      attempts++;
      const image = await api.images.get(imageId);
      if (!isMountedRef.current) return;

      if (image.status === "completed") {
        setPromptCardImages((prev) => ({ ...prev, [index]: image }));
        setGeneratingIndex(null);
        queryClient.invalidateQueries({ queryKey: ["images"] });
        if (pollRef.current) clearInterval(pollRef.current);
        pollRef.current = null;
      } else if (image.status === "failed" || attempts >= maxAttempts) {
        setPromptCardImages((prev) => ({ ...prev, [index]: { ...image, status: "failed" } as GeneratedImage }));
        setGeneratingIndex(null);
        if (pollRef.current) clearInterval(pollRef.current);
        pollRef.current = null;
      }
    } catch {
      setGeneratingIndex(null);
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, 2000);
}
```

**Step 5: Add "Set as Featured" handler**

```typescript
const setFeaturedMutation = useMutation({
  mutationFn: (data: { imageId: string; articleId: string }) =>
    api.images.setFeatured(data.imageId, { article_id: data.articleId }),
  onSuccess: () => {
    toast.success("Image set as featured!");
    queryClient.invalidateQueries({ queryKey: ["articles"] });
  },
  onError: (err) => {
    toast.error(parseApiError(err).message || "Failed to set featured image");
  },
});
```

**Step 6: Render prompt cards in the form area**

Inside the form, after the article selector and before the error display, add a conditional block:

```tsx
{/* Article Prompt Cards */}
{articleId && articlePrompts.length > 0 && (
  <div className="space-y-4">
    <h3 className="text-sm font-medium text-text-secondary">
      AI-Generated Prompts ({articlePrompts.length})
    </h3>
    {articlePrompts.map((p, index) => {
      const cardImage = promptCardImages[index];
      const isGenerating = generatingIndex === index;
      const isCompleted = cardImage?.status === "completed";
      const isFailed = cardImage?.status === "failed";

      return (
        <Card key={index} className="p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-text-muted uppercase tracking-wide">
              Prompt {index + 1}
            </span>
            {isCompleted && (
              <span className="text-xs text-primary-600 flex items-center gap-1">
                <CheckCircle2 className="h-3 w-3" /> Generated
              </span>
            )}
          </div>

          <textarea
            value={p}
            onChange={(e) => {
              const updated = [...articlePrompts];
              updated[index] = e.target.value;
              setArticlePrompts(updated);
            }}
            rows={3}
            disabled={isGenerating || isCompleted}
            className="w-full px-3 py-2 text-sm rounded-lg border border-surface-tertiary focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none transition-all resize-none disabled:opacity-60 disabled:bg-surface-secondary"
          />

          {/* Image preview */}
          {isGenerating && (
            <div className="flex items-center gap-2 text-sm text-primary-600">
              <Loader2 className="h-4 w-4 animate-spin" />
              Generating image...
            </div>
          )}

          {isCompleted && cardImage.url && (
            <div className="relative aspect-video rounded-lg overflow-hidden bg-surface-secondary">
              <Image
                src={getImageUrl(cardImage.url)}
                alt={cardImage.alt_text || `Generated image ${index + 1}`}
                fill
                className="object-cover"
              />
            </div>
          )}

          {isFailed && (
            <p className="text-sm text-red-600">Generation failed. Try editing the prompt.</p>
          )}

          {/* Action buttons */}
          <div className="flex gap-2">
            {!isCompleted && !isGenerating && (
              <Button
                type="button"
                size="sm"
                onClick={() => handleGenerateForPrompt(index)}
                disabled={generateMutation.isPending || !p.trim()}
              >
                <Sparkles className="h-3.5 w-3.5 mr-1.5" />
                Generate
              </Button>
            )}
            {isCompleted && articleId && (
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => setFeaturedMutation.mutate({ imageId: cardImage.id, articleId })}
                disabled={setFeaturedMutation.isPending}
              >
                <ImageIcon className="h-3.5 w-3.5 mr-1.5" />
                Set as Featured
              </Button>
            )}
            {isCompleted && (
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={() => {
                  const link = document.createElement("a");
                  link.href = getImageUrl(cardImage.url!);
                  link.download = `image-${cardImage.id}.png`;
                  document.body.appendChild(link);
                  link.click();
                  document.body.removeChild(link);
                }}
              >
                <Download className="h-3.5 w-3.5 mr-1.5" />
                Download
              </Button>
            )}
          </div>
        </Card>
      );
    })}
  </div>
)}
```

**Step 7: Keep standalone prompt form for non-article usage**

Wrap the existing single-prompt textarea + generate button in a conditional:

```tsx
{(!articleId || articlePrompts.length === 0) && (
  // ... existing single prompt form ...
)}
```

This preserves the current standalone generation flow when no article is selected.

**Step 8: Verify the page works**

Run: `cd frontend && npx next build`
Expected: Build succeeds with no errors

**Step 9: Commit**

```bash
git add frontend/app/\(dashboard\)/images/generate/page.tsx
git commit -m "feat: show 3 editable prompt cards when article selected in image generator"
```

---

### Task 7: Verify `api.images.setFeatured` exists in API client

**Files:**
- Check: `frontend/lib/api.ts`

**Step 1: Verify the method exists**

Run: `grep -n "setFeatured\|set_featured\|set-featured" frontend/lib/api.ts`

If it exists, confirm it calls `POST /api/v1/images/{id}/set-featured` with `{ article_id }`.

If it doesn't exist, add it to the `images` namespace in the API client:

```typescript
setFeatured: (imageId: string, data: { article_id: string }) =>
  apiRequest<GeneratedImage>({
    method: "POST",
    url: `/images/${imageId}/set-featured`,
    data,
  }),
```

**Step 2: Commit if changed**

```bash
git add frontend/lib/api.ts
git commit -m "feat: add images.setFeatured API client method"
```

---

### Task 8: End-to-End Verification

**Step 1: Build frontend**

Run: `cd frontend && npx next build`
Expected: No errors

**Step 2: Verify backend starts**

Run: `cd backend && python -c "from api.routes.articles import router; print('OK')"`
Expected: `OK`

**Step 3: Final commit and push**

```bash
git push origin master
```

---

## Summary

| Task | What | Files |
|------|------|-------|
| 1 | Migration: `image_prompt` → `image_prompts` JSON | migration 059, content model |
| 2 | Update schemas + API types | schemas, api.ts |
| 3 | New prompt template + AI method | prompt file, manifest, anthropic adapter |
| 4 | Pipeline Step 7: 3 prompts | content_pipeline.py |
| 5 | Article creation route updates | articles.py |
| 6 | Frontend: 3 prompt cards UI | generate page |
| 7 | Verify `setFeatured` API method | api.ts |
| 8 | E2E verification + push | build check |
