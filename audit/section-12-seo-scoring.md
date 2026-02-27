# Audit Section 12 — SEO Scoring & Quality
**Date**: 2026-02-27
**Status**: Complete

---

## Scope
- Backend SEO scoring logic (score calculation, keyword analysis, quality checks)
- Frontend SEO scorer (`seo-score.ts`, 10 checks × 10 pts)
- Article quality metrics (readability, headings, link counts, meta fields)
- Divergence between the two scoring systems
- SEO-related validation during article create/edit
- Rate limiting and security on SEO endpoints

---

## Files Audited
- `frontend/lib/seo-score.ts`
- `backend/api/routes/articles.py` (SEO analysis sections)
- `backend/api/schemas/content.py`
- `frontend/app/[locale]/(dashboard)/articles/[id]/page.tsx`
- `backend/infrastructure/database/models/content.py`

---

## Findings

### CRITICAL

#### SEO-01 — Backend keyword density uses substring matching — scores artificially inflated
- **Severity**: CRITICAL
- **File**: `backend/api/routes/articles.py:135`
- **Description**: Backend calculates keyword density using `content_lower.count(keyword_lower)` which is substring matching. The keyword "react" matches "reactive", "reaction", "proactive", etc. Frontend uses whole-word regex matching (`\b${escaped}\b`). This causes backend density scores to be artificially inflated relative to frontend, and the fundamental check is semantically wrong — a substring match is not a keyword occurrence.
- **Fix**: Use whole-word matching: `len(re.findall(r'\b' + re.escape(keyword_lower) + r'\b', content_lower))`.

---

### HIGH

#### SEO-02 — Two completely different SEO scoring systems produce incompatible scores
- **Severity**: HIGH
- **File**: `frontend/lib/seo-score.ts` vs `backend/api/routes/articles.py:125-210`
- **Description**: Backend uses a base-50 system with additive points (50 + up to 50 = 100), minimum score is always 50 even with zero SEO optimization. Frontend uses 10 checks × 10 points = 100, minimum is 0. Score ranges are fundamentally different: a completely unoptimized article scores 50% on the backend but 0% on the frontend. The UI may display both values interchangeably.
- **Fix**: Unify to a single scoring system. Recommended: adopt the frontend 10×10 model in the backend (base 0, each check worth 10 pts), then remove the client-side scorer and make the backend authoritative.

#### SEO-03 — Backend readability score calculated but never displayed in frontend
- **Severity**: HIGH
- **File**: `backend/api/routes/articles.py:28-30`
- **Description**: Backend calculates a readability score as `100 - (avg_sentence_length - 15) * 2` and stores it in `seo_analysis`. Frontend performs 10 independent checks — none of which include readability. The readability score is computed, stored, and silently ignored. Removing it eliminates dead computation; keeping it without surfacing it misleads about the score's meaning.
- **Fix**: Either (a) add readability as an 11th check to the frontend scorer, or (b) remove the readability calculation from the backend to reduce dead code.

#### SEO-04 — Title keyword check uses substring matching — false positives possible
- **Severity**: HIGH
- **File**: `backend/api/routes/articles.py:39, 61, 185, 194`
- **Description**: Backend checks `keyword_lower in title.lower()` (substring match). This gives false positives: keyword "blog" matches "dialogue", keyword "react" matches "reactive". While the frontend also uses includes() (substring), both systems are wrong. Keyword-in-title should confirm the exact keyword phrase appears as a distinct word or phrase, not as a substring of another word.
- **Fix**: Use whole-word matching for title/heading keyword checks: `bool(re.search(r'\b' + re.escape(keyword_lower) + r'\b', title.lower()))`.

#### SEO-05 — Backend image alt text check passes articles with no images
- **Severity**: HIGH
- **File**: `backend/api/routes/articles.py:24-25`
- **Description**: `image_alt_texts = all(alt.strip() for alt in images) if images else True`. If an article has NO images, this returns True — granting full marks for image alt text. SEO best practice requires articles to have at least one image with alt text. Articles with zero images should not pass this check.
- **Fix**: Change to: `image_alt_texts = all(alt.strip() for alt in images) if images else False`. Update the suggestion to also recommend adding at least one image.

---

### MEDIUM

#### SEO-06 — Backend `meta_title` field absent — frontend reads `meta_title` that never arrives from API
- **Severity**: MEDIUM
- **File**: `frontend/lib/seo-score.ts:60` vs `backend/api/routes/articles.py:247-251`
- **Description**: Frontend checks `meta_title || title` (prefers `meta_title`). The database `Article` model has no `meta_title` field — only `title` and `meta_description`. The frontend `ArticleResponse` type either omits `meta_title` or it is always `undefined`. The frontend scorer silently falls back to `title` every time, making the `meta_title` logic dead code.
- **Fix**: Either add `meta_title: Optional[str]` to the Article model and API response, or remove the `meta_title` reference from the frontend scorer and only use `title`.

#### SEO-07 — Missing rate limiting on `/analyze-seo` endpoint
- **Severity**: MEDIUM
- **File**: `backend/api/routes/articles.py:1110`
- **Description**: The `POST /articles/{article_id}/analyze-seo` endpoint has no `@limiter.limit()` decorator. It recomputes all SEO metrics on every call. A user or script can call it unlimited times, causing repeated regex processing and DB writes.
- **Fix**: Add `@limiter.limit("10/minute")`.

#### SEO-08 — Word count calculation differs between backend and frontend
- **Severity**: MEDIUM
- **File**: `backend/api/routes/articles.py:131` vs `frontend/app/.../articles/[id]/page.tsx:66`
- **Description**: Backend uses `len(content.split())` (splits on any whitespace, including multiple consecutive spaces, creating empty strings). Frontend uses `text.trim().split(/\s+/).length` (normalizes whitespace). For content with irregular spacing (tabs, double spaces), counts differ.
- **Fix**: Normalize whitespace before splitting: `len(re.split(r'\s+', content.strip()))`.

#### SEO-09 — Headings structure check too strict — valid structures penalized
- **Severity**: MEDIUM
- **File**: `backend/api/routes/articles.py:17`
- **Description**: Backend requires `h2_count >= 3 AND h3_count >= 2` to pass the structure check. A well-structured article with 4 H2s and 0 H3s fails. Frontend only checks for the presence of at least one heading. Backend penalizes perfectly valid flat-heading structures.
- **Fix**: Relax the H3 requirement: pass if `h2_count >= 3` (regardless of H3 count). H3s are supplementary, not mandatory.

#### SEO-10 — Link detection regex can produce false positives on malformed markdown
- **Severity**: MEDIUM
- **File**: `backend/api/routes/articles.py:20-21`
- **Description**: Regex `r"\[.*?\]\(/"` uses non-greedy `.*?` that can match across bracket pairs in malformed markdown such as `[hello]world](/path)`. Valid links and broken links produce the same match.
- **Fix**: Use a stricter regex: `r"\[[^\[\]]+\]\(/[^\)]*\)"` which requires non-bracket content inside `[]` and a `/`-prefixed href.

#### SEO-11 — Backend SEO score minimum is 50 — zero-effort articles score 50%
- **Severity**: MEDIUM
- **File**: `backend/api/routes/articles.py:68`
- **Description**: The base score of 50 means any article, regardless of how poorly optimized, scores at least 50%. A blank article with no keyword, no headings, no meta description, no links gets 50/100. This is misleading to users.
- **Fix**: Remove the base 50. Change to: `score = 0`. Add 10 pts per passing check (aligning with frontend). Minimum score becomes 0.

#### SEO-12 — Special characters in `focus_keyword` can break regex in SEO analysis
- **Severity**: MEDIUM
- **File**: `backend/api/schemas/content.py:118` and keyword usage in scoring
- **Description**: `keyword` field accepts any string up to 255 chars. Keywords with regex metacharacters (e.g., `C++`, `node.js`, `a+b`) passed to `re.findall(r'\b' + keyword + r'\b', ...)` without `re.escape()` will either raise `re.error` or match incorrect patterns.
- **Fix**: Always wrap keyword in `re.escape()` before using in regex patterns. This applies consistently to both density and title/heading checks.

---

### LOW

#### SEO-13 — Sentence counting includes empty elements — readability score inflated
- **Severity**: LOW
- **File**: `backend/api/routes/articles.py:28`
- **Description**: `re.split(r"[.!?]+", content)` creates empty string elements when punctuation occurs at the end of content or consecutively. Empty strings reduce the average sentence length, inflating the readability score.
- **Fix**: Filter empty sentences: `sentences = [s for s in re.split(r"[.!?]+", content) if s.strip()]`.

#### SEO-14 — No staleness detection for stored SEO scores — stale scores after content edit
- **Severity**: LOW
- **File**: `backend/infrastructure/database/models/content.py`
- **Description**: `Article.seo_score` is stored as a column but is not automatically updated when `Article.content` changes. If a user edits article content without calling `/analyze-seo`, the displayed score is stale with no indication.
- **Fix**: Add `seo_analysis_updated_at: Optional[datetime]` timestamp. In the article editor, show a "Score may be outdated" badge when `seo_analysis_updated_at < updated_at`.

#### SEO-15 — Empty content on article creation causes no initial SEO analysis
- **Severity**: LOW
- **File**: `backend/api/routes/articles.py:246-254`
- **Description**: When an article is created without content (or with empty content), SEO analysis is skipped. On first content edit via PUT, the analysis runs. But if the PUT only updates a non-content field (e.g., title), the content is not re-analyzed and the score stays unset.
- **Fix**: Ensure SEO analysis always runs whenever `content` is non-empty and has changed (compare with previous version before deciding whether to re-score).

#### SEO-16 — Suggestion text is inconsistent between backend and frontend
- **Severity**: LOW
- **File**: `backend/api/routes/articles.py:35, 45, 50, 53, 56` vs `frontend/lib/seo-score.ts`
- **Description**: Backend generates suggestion strings in Python; frontend generates separate suggestion strings in TypeScript. The same issue (e.g., keyword density) may produce different guidance text in the backend API response vs. the frontend editor panel.
- **Fix**: Derive suggestions from a shared definition file (or make the backend the authoritative source and remove frontend duplicates).

#### SEO-17 — Confusing feedback when no keyword is set
- **Severity**: LOW
- **File**: `backend/api/routes/articles.py:136, 158`
- **Description**: If keyword is an empty string, density calculation produces 0 and the suggestion says "Increase keyword usage" even though no keyword was set. The message is misleading — the real problem is that no keyword has been defined.
- **Fix**: Check `if not keyword.strip()` before generating density suggestions. Return a specific suggestion: "Set a focus keyword to enable keyword analysis."

#### SEO-18 — `readability_score` in `seo_analysis` JSON is dead storage
- **Severity**: LOW
- **File**: `backend/api/routes/articles.py:78`
- **Description**: Backend calculates and stores `readability_score` in the `seo_analysis` JSON column. No frontend component reads or displays this field. It consumes storage and adds confusion.
- **Fix**: Remove from `seo_analysis` if SEO-03 is resolved by dropping readability (option b). If kept, surface it in the UI.

#### SEO-19 — Title length check in frontend but absent from backend scoring
- **Severity**: LOW
- **File**: `frontend/lib/seo-score.ts:73` vs `backend/api/routes/articles.py:183-190`
- **Description**: Frontend has a dedicated check for title length (30–60 chars). Backend only checks keyword presence in title — title length is not part of the backend score. This contributes to score divergence.
- **Fix**: Add title length check to backend: `score += 10 if 30 <= len(title) <= 60 else 0`.

#### SEO-20 — Meta description max length schema allows 320 chars but SEO recommends 160
- **Severity**: LOW
- **File**: `backend/api/schemas/content.py:120, 130` vs `backend/infrastructure/database/models/content.py:167`
- **Description**: Schema limits `meta_description` to `max_length=320` but SEO analysis only recommends 120–160 chars. Users who submit 200-char meta descriptions will pass validation but fail the SEO check, with no clear explanation why.
- **Fix**: Align the schema max to 160 chars to prevent submission of values that will immediately fail the SEO check. Or adjust the recommendation message to reflect the 320-char field.

---

## What's Working Well
- Frontend `seo-score.ts` checks are well-structured and clearly named
- Backend calculates and stores `seo_analysis` alongside the article — no extra call needed on read
- Heading detection via regex is correct (H1/H2/H3 separate counts)
- Internal link detection checks for relative URLs specifically (not external)
- `re.escape()` is correctly used in some (but not all) keyword regex calls
- Meta description length recommendation (120–160 chars) is aligned with SEO best practice
- Frontend score is recalculated live in the editor on every keystroke

---

## Fix Priority Order
1. SEO-01 — Keyword density substring matching (CRITICAL)
2. SEO-02 — Two incompatible scoring systems (HIGH)
3. SEO-03 — Readability computed but unused (HIGH)
4. SEO-04 — Title keyword check substring false positives (HIGH)
5. SEO-05 — Alt text check passes articles with no images (HIGH)
6. SEO-06 — meta_title field absent from API (MEDIUM)
7. SEO-07 — No rate limiting on analyze-seo endpoint (MEDIUM)
8. SEO-08 — Word count calculation divergence (MEDIUM)
9. SEO-09 — Heading structure check too strict (MEDIUM)
10. SEO-10 — Link detection regex false positives (MEDIUM)
11. SEO-11 — Backend base score of 50 misleads users (MEDIUM)
12. SEO-12 — Missing re.escape() on keyword — regex injection (MEDIUM)
13. SEO-13 through SEO-20 — Low severity (LOW)
