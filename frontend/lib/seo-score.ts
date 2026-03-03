/**
 * Client-side SEO scoring — pure, no API calls.
 *
 * IMPORTANT: checks, weights, and regexes are kept in 1:1 parity with
 * backend/api/routes/articles.py :: analyze_seo() so both sides always
 * produce the same score for the same content.
 *
 * Weights (sum = 100):
 *   Keyword density 1–3%     15 pts
 *   Keyword in title         15 pts
 *   Meta description length  10 pts
 *   H2 headings (3+)         15 pts
 *   FAQ section              15 pts
 *   External citation link   10 pts
 *   Structured lists         10 pts
 *   Quick Answer / TL;DR      5 pts
 *   Image alt texts           5 pts
 */

export interface SEOCheck {
  label: string;
  passed: boolean;
  tip: string;
  /** Maximum points awarded for this check */
  points: number;
}

export interface SEOScore {
  /** 0–100 weighted score, matching the backend algorithm exactly */
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

function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function wordCount(text: string): number {
  const trimmed = text.trim();
  if (!trimmed) return 0;
  return trimmed.split(/\s+/).length;
}

function countKeyword(text: string, keyword: string): number {
  if (!keyword.trim()) return 0;
  const re = new RegExp(`\\b${escapeRegex(keyword)}\\b`, "gi");
  return (text.match(re) ?? []).length;
}

// ---------------------------------------------------------------------------
// Main export
// ---------------------------------------------------------------------------

export function calculateSEOScore(article: SEOArticleInput): SEOScore {
  const title   = (article.meta_title || article.title || "").trim();
  const meta    = (article.meta_description || "").trim();
  const content = (article.content || "").trim();
  const keyword = (article.keyword || "").trim();
  const kw      = keyword.toLowerCase();

  const total   = wordCount(content);
  const kwCount = keyword ? countKeyword(content, kw) : 0;
  const density = total > 0 ? (kwCount / total) * 100 : 0;

  const titleHasKeyword = keyword.length > 0 &&
    new RegExp(`\\b${escapeRegex(kw)}\\b`, "i").test(title);

  const metaLen = meta.length;
  const metaOk  = !!meta && metaLen >= 120 && metaLen <= 160;

  const h2Count = (content.match(/^## /gm) ?? []).length;

  // Same regex as backend: ^## .*(frequently asked questions|faq)
  const hasFaq  = /^## .*(frequently asked questions|faq)/im.test(content);

  const externalLinks = (content.match(/\[.*?\]\(https?:\/\//g) ?? []).length;

  const hasLists = /^(\s*[-*+]|\s*\d+\.)\s/m.test(content);

  // Same regex as backend
  const hasQuickAnswer = />\s*\*\*(quick answer|tl;?dr|summary|key takeaway)/i.test(content);

  // All images must have non-empty alt text (matches backend logic)
  const images = [...content.matchAll(/!\[(.*?)\]\(/g)].map((m) => m[1]);
  const imageAltTexts = images.length > 0 && images.every((alt) => alt.trim().length > 0);

  const checks: SEOCheck[] = [
    {
      label: `Keyword density 1–3% (${density.toFixed(1)}%)`,
      passed: keyword.length > 0 && density >= 1 && density <= 3,
      tip: !keyword
        ? "Set a target keyword so this check can evaluate keyword density."
        : density < 1
        ? `Use "${keyword}" more naturally throughout — currently ${density.toFixed(1)}%.`
        : `Reduce keyword repetition to avoid over-optimisation — currently ${density.toFixed(1)}%.`,
      points: 15,
    },
    {
      label: "Keyword in title",
      passed: titleHasKeyword,
      tip: keyword
        ? `Include "${keyword}" in your article title.`
        : "Set a target keyword so this check can evaluate title placement.",
      points: 15,
    },
    {
      label: "Meta description (120–160 chars)",
      passed: metaOk,
      tip: !meta
        ? "Add a meta description (120–160 characters)."
        : metaLen < 120
        ? `Expand meta description to at least 120 characters (currently ${metaLen}).`
        : `Shorten meta description to under 160 characters (currently ${metaLen}).`,
      points: 10,
    },
    {
      label: `Section structure (3+ H2 headings, ${h2Count} found)`,
      passed: h2Count >= 3,
      tip: "Add more ## headings — aim for at least 3 modular sections.",
      points: 15,
    },
    {
      label: "FAQ section present",
      passed: hasFaq,
      tip: "Add a '## Frequently Asked Questions' section — the highest-citation format for Google AI Overviews and Perplexity.",
      points: 15,
    },
    {
      label: "External citation link",
      passed: externalLinks >= 1,
      tip: "Add at least one external link to an authoritative source (study, official docs, industry report).",
      points: 10,
    },
    {
      label: "Structured lists (bullets or numbered)",
      passed: hasLists,
      tip: "Add bullet points or a numbered list — structured lists are among the most-cited formats by AI answer engines.",
      points: 10,
    },
    {
      label: "Quick Answer / TL;DR block",
      passed: hasQuickAnswer,
      tip: "Add a blockquote near the top: > **Quick Answer:** [40–70 word standalone answer].",
      points: 5,
    },
    {
      label: "Images have alt text",
      passed: images.length === 0 || imageAltTexts,
      tip: "Ensure all images have descriptive alt text.",
      points: 5,
    },
  ];

  const overall = checks.reduce((sum, c) => sum + (c.passed ? c.points : 0), 0);

  return { overall, checks };
}
