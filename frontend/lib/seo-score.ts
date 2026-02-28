/**
 * Client-side SEO scoring — pure, no API calls.
 * All logic is deterministic so results can be memoised / debounced freely.
 *
 * Updated 2025-2026: checks now reflect GEO/AEO best practices —
 * FAQ sections, external citations, structured lists, and content
 * depth thresholds that align with AI answer engine citation criteria.
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

/** Count H2-level headings (## but not ###). */
function countH2(content: string): number {
  return (content.match(/^## /gm) ?? []).length;
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
  // 1. Keyword in title
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
  // 2. Keyword in opening (first 300 chars — covers HPPP hook + problem)
  // ------------------------------------------------------------------
  const opening = content.slice(0, 300);
  const keywordInOpening =
    keyword.length > 0 && normalise(opening).includes(normalise(keyword));
  checks.push({
    label: "Keyword in opening paragraph",
    passed: keywordInOpening,
    tip: keyword
      ? `Mention "${keyword}" in the first paragraph. AI engines weight early keyword signals heavily.`
      : "Set a target keyword so this check can evaluate keyword placement.",
  });

  // ------------------------------------------------------------------
  // 3. Keyword density — 1–3% of total words
  // ------------------------------------------------------------------
  const totalWords = wordCount(content);
  const kwCount = keyword ? countKeyword(content, keyword) : 0;
  const density = totalWords > 0 ? (kwCount / totalWords) * 100 : 0;
  const densityOk = keyword.length > 0 && density >= 1 && density <= 3;
  checks.push({
    label: "Keyword density (1–3%)",
    passed: densityOk,
    tip: !keyword
      ? "Set a target keyword so this check can evaluate keyword density."
      : density < 1
      ? `Keyword density is ${density.toFixed(1)}% — too low. Aim for 1–3%.`
      : density > 3
      ? `Keyword density is ${density.toFixed(1)}% — too high. Reduce usage to avoid keyword stuffing penalties.`
      : "",
  });

  // ------------------------------------------------------------------
  // 4. Meta description — 120–160 chars and contains keyword
  // ------------------------------------------------------------------
  const descLen = metaDesc.length;
  const kwInMeta =
    keyword.length > 0 && normalise(metaDesc).includes(normalise(keyword));
  const metaOk = descLen >= 120 && descLen <= 160 && kwInMeta;
  checks.push({
    label: "Meta description (120–160 chars, includes keyword)",
    passed: metaOk,
    tip:
      descLen === 0
        ? "Add a meta description containing your keyword — it's both an SEO and AI citation signal."
        : !kwInMeta
        ? `Include "${keyword}" in your meta description to reinforce relevance in search snippets.`
        : descLen < 120
        ? `Meta description is ${descLen} chars — expand to at least 120.`
        : descLen > 160
        ? `Meta description is ${descLen} chars — Google truncates at ~160. Shorten it.`
        : "",
  });

  // ------------------------------------------------------------------
  // 5. Content length — 1500+ words (GEO/AEO threshold)
  //    Research: articles 1500+ words average 5.1 AI citations vs 3.2 for <800
  // ------------------------------------------------------------------
  checks.push({
    label: "Content depth (1500+ words)",
    passed: totalWords >= 1500,
    tip:
      totalWords === 0
        ? "Add content to your article."
        : `Your article has ${totalWords} words. Articles with 1500+ words average significantly more AI citations and top-10 rankings.`,
  });

  // ------------------------------------------------------------------
  // 6. H2 structure — at least 3 H2 headings
  //    Optimal range for AI passage retrieval is 4-8 H2 sections
  // ------------------------------------------------------------------
  const h2Count = countH2(content);
  checks.push({
    label: "Section structure (3+ H2 headings)",
    passed: h2Count >= 3,
    tip:
      h2Count === 0
        ? "Add H2 headings (## Heading) to structure your content. AI engines use headings as extraction anchors."
        : `Your article has ${h2Count} H2 heading${h2Count === 1 ? "" : "s"}. Use at least 3 H2s to give AI engines enough modular sections to cite.`,
  });

  // ------------------------------------------------------------------
  // 7. FAQ section — contains a Frequently Asked Questions H2
  //    FAQPage schema + FAQ content = highest AI citation format
  // ------------------------------------------------------------------
  const hasFaq = /##\s+(frequently asked questions|faq)/i.test(content);
  checks.push({
    label: "FAQ section present",
    passed: hasFaq,
    tip: "Add a '## Frequently Asked Questions' section. FAQs are the #1 format cited by Google AI Overviews and Perplexity — even though FAQ rich results were removed from SERPs.",
  });

  // ------------------------------------------------------------------
  // 8. External citation link — at least one https:// link
  //    3–5 external links per 1000 words to authoritative sources
  //    is the GEO best practice for citation readiness
  // ------------------------------------------------------------------
  const externalLinks = (content.match(/\[.+?\]\(https?:\/\//g) ?? []).length;
  checks.push({
    label: "External citation link (1+)",
    passed: externalLinks >= 1,
    tip: "Add at least one external link to an authoritative source (study, official docs, industry report). AI engines treat outbound citations as a trust signal and citation-readiness marker.",
  });

  // ------------------------------------------------------------------
  // 9. Structured lists — at least one bullet or numbered list
  //    Lists are among the most-cited formats by AI answer engines
  // ------------------------------------------------------------------
  const hasLists = /^(\s*[-*+]|\s*\d+\.)\s/m.test(content);
  checks.push({
    label: "Has structured lists (bullets or numbered)",
    passed: hasLists,
    tip: "Add bullet points or a numbered list. Lists are one of the highest-citation formats for Google AI Overviews, Perplexity, and ChatGPT Search.",
  });

  // ------------------------------------------------------------------
  // 10. TL;DR / Quick Answer block — Answer Capsule at the top
  //     Checks for the > **Quick Answer:** blockquote pattern
  // ------------------------------------------------------------------
  const hasTldr = />\s*\*\*(quick answer|tl;?dr|summary|key takeaway)/i.test(content);
  checks.push({
    label: "Quick Answer / TL;DR block",
    passed: hasTldr,
    tip: "Add a Quick Answer block near the top: > **Quick Answer:** [40-70 word standalone answer]. This is the most-extracted format by AI Overviews and is critical for zero-click visibility.",
  });

  // ------------------------------------------------------------------
  // Overall score
  // ------------------------------------------------------------------
  const passedCount = checks.filter((c) => c.passed).length;
  const overall = passedCount * 10;

  return { overall, checks };
}
