/**
 * Client-side SEO scoring — pure, no API calls.
 * All logic is deterministic so results can be memoised / debounced freely.
 */

export interface SEOCheck {
  /** Human-readable label shown in the checklist */
  label: string;
  /** Whether this check passed */
  passed: boolean;
  /** Actionable tip shown when the check fails */
  tip: string;
}

export interface SEOScore {
  /** 0–100, each of the 10 checks is worth 10 points */
  overall: number;
  checks: SEOCheck[];
}

export interface SEOArticleInput {
  title?: string;
  meta_title?: string;
  meta_description?: string;
  content?: string;
  keyword?: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function normalise(text: string): string {
  return text.toLowerCase().trim();
}

/** Count total words in a string (splits on any whitespace). */
function wordCount(text: string): number {
  const trimmed = text.trim();
  if (!trimmed) return 0;
  return trimmed.split(/\s+/).length;
}

/**
 * Count how many times `keyword` appears in `text` (case-insensitive, whole
 * words only so "react" does not match "reactive").
 */
function countKeyword(text: string, keyword: string): number {
  if (!keyword.trim()) return 0;
  const escaped = keyword.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const re = new RegExp(`\\b${escaped}\\b`, "gi");
  return (text.match(re) ?? []).length;
}

// ---------------------------------------------------------------------------
// Main export
// ---------------------------------------------------------------------------

export function calculateSEOScore(article: SEOArticleInput): SEOScore {
  const title = (article.meta_title || article.title || "").trim();
  const metaDesc = (article.meta_description || "").trim();
  const content = (article.content || "").trim();
  const keyword = (article.keyword || "").trim();

  const checks: SEOCheck[] = [];

  // ------------------------------------------------------------------
  // 1. Title length — 30–60 chars
  // ------------------------------------------------------------------
  const titleLen = title.length;
  checks.push({
    label: "Title length (30–60 chars)",
    passed: titleLen >= 30 && titleLen <= 60,
    tip:
      titleLen < 30
        ? `Your title is only ${titleLen} characters. Aim for at least 30 to give Google enough context.`
        : titleLen > 60
        ? `Your title is ${titleLen} characters — Google truncates at ~60. Try to shorten it.`
        : "",
  });

  // ------------------------------------------------------------------
  // 2. Meta description length — 120–160 chars
  // ------------------------------------------------------------------
  const descLen = metaDesc.length;
  checks.push({
    label: "Meta description length (120–160 chars)",
    passed: descLen >= 120 && descLen <= 160,
    tip:
      descLen === 0
        ? "Add a meta description to improve click-through rate from search results."
        : descLen < 120
        ? `Your meta description is ${descLen} characters. Expand it to at least 120 for best results.`
        : descLen > 160
        ? `Your meta description is ${descLen} characters — Google truncates at ~160. Shorten it.`
        : "",
  });

  // ------------------------------------------------------------------
  // 3. Keyword in title
  // ------------------------------------------------------------------
  const keywordInTitle =
    keyword.length > 0 && normalise(title).includes(normalise(keyword));
  checks.push({
    label: "Keyword in title",
    passed: keywordInTitle,
    tip: keyword
      ? `Include your target keyword "${keyword}" in the title to signal relevance to search engines.`
      : "Set a target keyword so this check can evaluate keyword placement.",
  });

  // ------------------------------------------------------------------
  // 4. Keyword in first paragraph (first 200 chars of content)
  // ------------------------------------------------------------------
  const first200 = content.slice(0, 200);
  const keywordInOpening =
    keyword.length > 0 && normalise(first200).includes(normalise(keyword));
  checks.push({
    label: "Keyword in opening paragraph",
    passed: keywordInOpening,
    tip: keyword
      ? `Mention "${keyword}" early in your content (within the first paragraph) to establish relevance.`
      : "Set a target keyword so this check can evaluate keyword placement.",
  });

  // ------------------------------------------------------------------
  // 5. Keyword density — 1–3% of total words
  // ------------------------------------------------------------------
  const totalWords = wordCount(content);
  const kwCount = keyword ? countKeyword(content, keyword) : 0;
  const density = totalWords > 0 ? (kwCount / totalWords) * 100 : 0;
  const densityOk = keyword.length > 0 && density >= 1 && density <= 3;
  checks.push({
    label: "Keyword density (1–3%)",
    passed: densityOk,
    tip:
      !keyword
        ? "Set a target keyword so this check can evaluate keyword density."
        : density < 1
        ? `Keyword density is ${density.toFixed(1)}% — too low. Aim for 1–3% to reinforce relevance without over-optimising.`
        : density > 3
        ? `Keyword density is ${density.toFixed(1)}% — too high. Reduce usage to avoid keyword stuffing penalties.`
        : "",
  });

  // ------------------------------------------------------------------
  // 6. Content length — at least 800 words
  // ------------------------------------------------------------------
  const contentWords = totalWords;
  checks.push({
    label: "Content length (800+ words)",
    passed: contentWords >= 800,
    tip:
      contentWords === 0
        ? "Add content to your article."
        : `Your article has ${contentWords} words. Most top-ranking pages have at least 800 words.`,
  });

  // ------------------------------------------------------------------
  // 7. Has headings — at least one ## or ###
  // ------------------------------------------------------------------
  const hasHeadings = /^#{2,3}\s/m.test(content);
  checks.push({
    label: "Has subheadings (## or ###)",
    passed: hasHeadings,
    tip: "Add H2 or H3 subheadings to structure your content and improve readability and SEO.",
  });

  // ------------------------------------------------------------------
  // 8. Has internal links — at least one markdown link [text](url)
  // ------------------------------------------------------------------
  const hasLinks = /\[.+?\]\(.+?\)/.test(content);
  checks.push({
    label: "Has at least one link",
    passed: hasLinks,
    tip: "Include at least one internal or external link to provide context and improve crawlability.",
  });

  // ------------------------------------------------------------------
  // 9. Meta description contains keyword
  // ------------------------------------------------------------------
  const kwInMeta =
    keyword.length > 0 &&
    normalise(metaDesc).includes(normalise(keyword));
  checks.push({
    label: "Keyword in meta description",
    passed: kwInMeta,
    tip: keyword
      ? `Include "${keyword}" in your meta description to reinforce relevance in search snippets.`
      : "Set a target keyword so this check can evaluate meta description relevance.",
  });

  // ------------------------------------------------------------------
  // 10. Image alt text — if images exist, they all have alt text
  //     Pattern: ![alt text](url) — alt must be non-empty
  // ------------------------------------------------------------------
  const allImages = Array.from(content.matchAll(/!\[(.*?)\]\(.+?\)/g));
  const imagesWithoutAlt = allImages.filter((m) => m[1].trim() === "");
  const imageAltOk =
    allImages.length === 0 || imagesWithoutAlt.length === 0;
  checks.push({
    label: "Images have alt text",
    passed: imageAltOk,
    tip:
      allImages.length === 0
        ? "No images found. Adding images with descriptive alt text improves SEO and accessibility."
        : `${imagesWithoutAlt.length} image(s) are missing alt text. Add descriptions inside the square brackets: ![describe the image](url).`,
  });

  // ------------------------------------------------------------------
  // Overall score
  // ------------------------------------------------------------------
  const passedCount = checks.filter((c) => c.passed).length;
  const overall = passedCount * 10;

  return { overall, checks };
}
