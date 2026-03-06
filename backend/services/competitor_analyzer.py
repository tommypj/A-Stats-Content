"""
Competitor Analyzer — sitemap crawling, page scraping, and algorithmic keyword extraction.

No AI models are used. Keywords are extracted via weighted n-gram scoring
across title, headings, URL slug, meta description, and body TF-IDF.
"""

import asyncio
import logging
import math
import re
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from uuid import uuid4

import httpx
from bs4 import BeautifulSoup
from lxml import etree
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.connection import async_session_maker
from infrastructure.database.models.competitor import CompetitorAnalysis, CompetitorArticle
from infrastructure.database.models.content import Article

logger = logging.getLogger(__name__)

BOT_USER_AGENT = "AStatsBot/1.0 (+https://a-stats.app)"
MAX_URLS = 500
DEFAULT_CRAWL_DELAY = 1.0
MAX_CONCURRENCY = 3
REQUEST_TIMEOUT = 15.0

# ============================================================================
# English stop words (no external dependency needed)
# ============================================================================

STOP_WORDS: frozenset[str] = frozenset({
    "a", "about", "above", "after", "again", "against", "all", "am", "an",
    "and", "any", "are", "aren't", "as", "at", "be", "because", "been",
    "before", "being", "below", "between", "both", "but", "by", "can",
    "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does",
    "doesn't", "doing", "don't", "down", "during", "each", "few", "for",
    "from", "further", "get", "got", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "her", "here", "hers", "herself",
    "him", "himself", "his", "how", "i", "if", "in", "into", "is", "isn't",
    "it", "its", "itself", "just", "let", "let's", "like", "ll", "me",
    "might", "more", "most", "mustn't", "my", "myself", "new", "no", "nor",
    "not", "now", "of", "off", "on", "once", "only", "or", "other", "ought",
    "our", "ours", "ourselves", "out", "over", "own", "re", "s", "same",
    "shall", "shan't", "she", "should", "shouldn't", "so", "some", "such",
    "t", "than", "that", "the", "their", "theirs", "them", "themselves",
    "then", "there", "these", "they", "this", "those", "through", "to",
    "too", "under", "until", "up", "us", "ve", "very", "was", "wasn't",
    "we", "were", "weren't", "what", "when", "where", "which", "while",
    "who", "whom", "why", "will", "with", "won't", "would", "wouldn't",
    "you", "your", "yours", "yourself", "yourselves",
    # Additional common web/blog words to filter
    "blog", "post", "read", "click", "here", "also", "use", "using",
    "used", "one", "two", "first", "best", "top", "way", "ways",
    "make", "made", "know", "need", "want", "go", "going", "see",
    "well", "back", "still", "even", "take", "come", "good", "great",
    "many", "much", "may", "right", "look", "think", "every", "give",
    "day", "find", "long", "say", "help", "thing", "things",
})


# ============================================================================
# URL filtering patterns — skip non-article URLs
# ============================================================================

SKIP_URL_PATTERNS = re.compile(
    r"/(tag|tags|category|categories|author|page|feed|wp-content|wp-admin|"
    r"wp-includes|wp-json|cart|checkout|account|login|register|search|"
    r"privacy|terms|contact|about-us|sitemap)(/|$)",
    re.IGNORECASE,
)
SKIP_EXTENSIONS = re.compile(r"\.(pdf|jpg|jpeg|png|gif|webp|svg|css|js|xml|zip|mp4|mp3)$", re.IGNORECASE)


# ============================================================================
# Sitemap Discovery & Parsing
# ============================================================================

async def _fetch_text(client: httpx.AsyncClient, url: str) -> str | None:
    """Fetch URL text content, return None on failure."""
    try:
        resp = await client.get(url, follow_redirects=True, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            return resp.text
    except Exception as exc:
        logger.debug("Failed to fetch %s: %s", url, exc)
    return None


def _parse_robots_txt(robots_text: str) -> tuple[list[str], float]:
    """
    Parse robots.txt for Sitemap directives and Crawl-delay.
    Returns (sitemap_urls, crawl_delay).
    """
    sitemaps: list[str] = []
    crawl_delay = DEFAULT_CRAWL_DELAY
    for line in robots_text.splitlines():
        line = line.strip()
        if line.lower().startswith("sitemap:"):
            url = line.split(":", 1)[1].strip()
            if url:
                sitemaps.append(url)
        elif line.lower().startswith("crawl-delay:"):
            try:
                delay = float(line.split(":", 1)[1].strip())
                crawl_delay = max(delay, DEFAULT_CRAWL_DELAY)
            except ValueError:
                pass
    return sitemaps, crawl_delay


def _extract_urls_from_sitemap_xml(xml_text: str) -> tuple[list[str], list[str]]:
    """
    Parse a sitemap XML. Returns (page_urls, child_sitemap_urls).
    Handles both regular sitemaps and sitemap indexes.
    """
    page_urls: list[str] = []
    child_sitemaps: list[str] = []
    try:
        root = etree.fromstring(xml_text.encode("utf-8"))
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        # Check for sitemap index
        for sitemap_el in root.findall(".//sm:sitemap/sm:loc", ns):
            if sitemap_el.text:
                child_sitemaps.append(sitemap_el.text.strip())

        # Check for regular URLs
        for url_el in root.findall(".//sm:url/sm:loc", ns):
            if url_el.text:
                page_urls.append(url_el.text.strip())

    except Exception as exc:
        logger.warning("Failed to parse sitemap XML: %s", exc)

    return page_urls, child_sitemaps


def _is_article_url(url: str) -> bool:
    """Filter out non-article URLs (tags, categories, author pages, static assets, etc.)."""
    path = urlparse(url).path
    if SKIP_EXTENSIONS.search(path):
        return False
    if SKIP_URL_PATTERNS.search(path):
        return False
    # Must have a meaningful path (not just the homepage)
    segments = [s for s in path.strip("/").split("/") if s]
    return len(segments) >= 1


async def discover_urls(client: httpx.AsyncClient, domain: str) -> tuple[list[str], float]:
    """
    Discover article URLs from a competitor's sitemaps.
    Returns (urls, crawl_delay).
    """
    base_url = f"https://{domain}"
    crawl_delay = DEFAULT_CRAWL_DELAY
    all_urls: set[str] = set()

    # Step 1: Check robots.txt
    robots_text = await _fetch_text(client, f"{base_url}/robots.txt")
    sitemap_candidates: list[str] = []
    if robots_text:
        robot_sitemaps, crawl_delay = _parse_robots_txt(robots_text)
        sitemap_candidates.extend(robot_sitemaps)

    # Step 2: Add standard sitemap locations as fallbacks
    sitemap_candidates.extend([
        f"{base_url}/sitemap.xml",
        f"{base_url}/sitemap_index.xml",
        f"{base_url}/post-sitemap.xml",
        f"{base_url}/page-sitemap.xml",
    ])
    # Deduplicate while preserving order
    seen = set()
    unique_candidates = []
    for s in sitemap_candidates:
        if s not in seen:
            seen.add(s)
            unique_candidates.append(s)

    # Step 3: Fetch and parse sitemaps (up to 2 levels deep)
    visited_sitemaps: set[str] = set()

    async def process_sitemap(sitemap_url: str, depth: int = 0):
        if depth > 2 or sitemap_url in visited_sitemaps:
            return
        visited_sitemaps.add(sitemap_url)

        xml_text = await _fetch_text(client, sitemap_url)
        if not xml_text:
            return

        page_urls, child_sitemaps = _extract_urls_from_sitemap_xml(xml_text)
        for u in page_urls:
            if _is_article_url(u):
                all_urls.add(u)

        for child in child_sitemaps:
            if len(all_urls) >= MAX_URLS:
                break
            await process_sitemap(child, depth + 1)

    for candidate in unique_candidates:
        if len(all_urls) >= MAX_URLS:
            break
        await process_sitemap(candidate)

    # Cap at MAX_URLS
    url_list = sorted(all_urls)[:MAX_URLS]
    logger.info("Discovered %d article URLs for %s (from %d total)", len(url_list), domain, len(all_urls))
    return url_list, crawl_delay


# ============================================================================
# Page Scraping
# ============================================================================

def _extract_page_data(html: str, url: str) -> dict:
    """
    Extract SEO-relevant data from an HTML page.
    Returns dict with title, meta_description, headings, url_slug, word_count, body_text.
    """
    soup = BeautifulSoup(html, "lxml")

    # Remove non-content elements
    for tag in soup.find_all(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
        tag.decompose()

    # Title
    title = None
    title_tag = soup.find("title")
    if title_tag and title_tag.string:
        title = title_tag.string.strip()
        # Strip common suffixes like " | Site Name" or " - Brand"
        for sep in [" | ", " - ", " – ", " — ", " :: "]:
            if sep in title:
                title = title.split(sep)[0].strip()

    # Meta description
    meta_desc = None
    meta_tag = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
    if meta_tag and meta_tag.get("content"):
        meta_desc = meta_tag["content"].strip()

    # Headings
    headings = []
    for level in range(1, 4):
        for h in soup.find_all(f"h{level}"):
            text = h.get_text(strip=True)
            if text and len(text) > 1:
                headings.append({"level": level, "text": text})

    # URL slug
    path = urlparse(url).path.rstrip("/")
    url_slug = path.split("/")[-1] if path else None

    # Body text
    body = soup.find("body")
    body_text = body.get_text(separator=" ", strip=True) if body else ""
    word_count = len(body_text.split()) if body_text else 0

    return {
        "title": title,
        "meta_description": meta_desc,
        "headings": headings,
        "url_slug": url_slug,
        "word_count": word_count,
        "body_text": body_text,
    }


async def scrape_pages(
    client: httpx.AsyncClient,
    urls: list[str],
    crawl_delay: float,
    analysis_id: str,
) -> list[dict]:
    """
    Scrape a list of URLs with rate limiting and concurrency control.
    Updates analysis.scraped_urls in the DB as pages are processed.
    """
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    results: list[dict] = []
    scraped_count = 0

    async def scrape_one(url: str) -> dict | None:
        nonlocal scraped_count
        async with semaphore:
            try:
                resp = await client.get(url, follow_redirects=True, timeout=REQUEST_TIMEOUT)
                if resp.status_code != 200:
                    logger.debug("Non-200 for %s: %d", url, resp.status_code)
                    return None
                # Only process HTML responses
                ct = resp.headers.get("content-type", "")
                if "text/html" not in ct:
                    return None
                data = _extract_page_data(resp.text, url)
                data["url"] = url
                scraped_count += 1
                return data
            except Exception as exc:
                logger.debug("Failed to scrape %s: %s", url, exc)
                return None
            finally:
                await asyncio.sleep(crawl_delay)

    # Process in batches for DB progress updates
    batch_size = 10
    for i in range(0, len(urls), batch_size):
        batch = urls[i : i + batch_size]
        batch_results = await asyncio.gather(*[scrape_one(u) for u in batch])
        for r in batch_results:
            if r is not None:
                results.append(r)

        # Update progress in DB
        try:
            async with async_session_maker() as session:
                analysis = await session.get(CompetitorAnalysis, analysis_id)
                if analysis:
                    analysis.scraped_urls = scraped_count
                    await session.commit()
        except Exception:
            pass  # Non-critical progress update

    logger.info("Scraped %d pages out of %d URLs for analysis %s", len(results), len(urls), analysis_id)
    return results


# ============================================================================
# Keyword Extraction Algorithm
# ============================================================================

def _tokenize(text: str) -> list[str]:
    """Lowercase, strip punctuation, split into word tokens."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return [w for w in text.split() if len(w) > 1 and w not in STOP_WORDS]


def _generate_ngrams(tokens: list[str], max_n: int = 4) -> list[str]:
    """Generate n-grams (1 to max_n) from a token list."""
    ngrams = []
    for n in range(1, min(max_n + 1, len(tokens) + 1)):
        for i in range(len(tokens) - n + 1):
            gram = " ".join(tokens[i : i + n])
            # Skip if any component is a stop word (for n > 1)
            if n > 1 and any(t in STOP_WORDS for t in tokens[i : i + n]):
                continue
            # Skip if it's just numbers
            if re.match(r"^[\d\s-]+$", gram):
                continue
            ngrams.append(gram)
    return ngrams


def _extract_keyword_for_article(page_data: dict) -> tuple[str | None, float]:
    """
    Extract the most likely target keyword for a single article.
    Uses weighted scoring across title, H1, URL slug, meta description, and H2s.

    Returns (keyword, confidence_score).
    """
    scores: Counter = Counter()

    # Weight configuration
    weights = {
        "title": 3.0,
        "h1": 2.5,
        "slug": 2.0,
        "meta": 1.5,
        "h2": 1.0,
    }

    # Title
    if page_data.get("title"):
        tokens = _tokenize(page_data["title"])
        for gram in _generate_ngrams(tokens, max_n=4):
            scores[gram] += weights["title"]

    # H1 headings
    for h in (page_data.get("headings") or []):
        if h["level"] == 1:
            tokens = _tokenize(h["text"])
            for gram in _generate_ngrams(tokens, max_n=4):
                scores[gram] += weights["h1"]

    # URL slug
    if page_data.get("url_slug"):
        slug_text = page_data["url_slug"].replace("-", " ").replace("_", " ")
        tokens = _tokenize(slug_text)
        for gram in _generate_ngrams(tokens, max_n=4):
            scores[gram] += weights["slug"]

    # Meta description
    if page_data.get("meta_description"):
        tokens = _tokenize(page_data["meta_description"])
        for gram in _generate_ngrams(tokens, max_n=4):
            scores[gram] += weights["meta"]

    # H2 headings
    for h in (page_data.get("headings") or []):
        if h["level"] == 2:
            tokens = _tokenize(h["text"])
            for gram in _generate_ngrams(tokens, max_n=4):
                scores[gram] += weights["h2"]

    if not scores:
        return None, 0.0

    # Apply length bonus: 2-3 word phrases are most realistic as keywords
    adjusted_scores: Counter = Counter()
    for gram, score in scores.items():
        word_count = len(gram.split())
        if word_count in (2, 3):
            adjusted_scores[gram] = score * 1.3
        elif word_count == 4:
            adjusted_scores[gram] = score * 1.1
        else:
            adjusted_scores[gram] = score

    # Get top candidate
    top_keyword, top_score = adjusted_scores.most_common(1)[0]

    # Normalize confidence to 0-1 range
    max_possible = sum(weights.values()) * 1.3  # All sources match, with length bonus
    confidence = min(top_score / max_possible, 1.0)

    return top_keyword, round(confidence, 3)


def extract_keywords_with_tfidf(pages_data: list[dict]) -> list[tuple[str | None, float]]:
    """
    Extract keywords for all articles, with a TF-IDF body text boost.

    First pass: positional scoring (title, H1, slug, meta, H2).
    Second pass: compute IDF across all docs, add body TF-IDF signal.

    Returns list of (keyword, confidence) tuples, one per page.
    """
    # First pass: get positional keywords
    positional_results = [_extract_keyword_for_article(p) for p in pages_data]

    # Compute document frequencies for body n-grams
    num_docs = len(pages_data)
    if num_docs < 3:
        # Too few documents for meaningful IDF; return positional results
        return positional_results

    doc_freq: Counter = Counter()
    doc_ngrams: list[Counter] = []

    for page in pages_data:
        body = page.get("body_text", "")
        tokens = _tokenize(body)
        # Only consider 1-3 grams for body TF
        grams = _generate_ngrams(tokens[:500], max_n=3)  # Cap at 500 tokens for performance
        gram_counts = Counter(grams)
        doc_ngrams.append(gram_counts)
        for gram in set(gram_counts.keys()):
            doc_freq[gram] += 1

    # Second pass: boost positional scores with body TF-IDF
    final_results: list[tuple[str | None, float]] = []
    body_weight = 0.5

    for i, page in enumerate(pages_data):
        keyword, confidence = positional_results[i]
        if keyword is None:
            final_results.append((None, 0.0))
            continue

        # Check if the positional keyword appears in body
        tf = doc_ngrams[i].get(keyword, 0)
        df = doc_freq.get(keyword, 1)
        idf = math.log(num_docs / df) if df > 0 else 0

        if tf > 0 and idf > 0:
            # Boost confidence if the keyword also appears significantly in the body
            tfidf_score = (tf * idf) / 100  # Normalize
            boosted_confidence = min(confidence + (tfidf_score * body_weight), 1.0)
            final_results.append((keyword, round(boosted_confidence, 3)))
        else:
            final_results.append((keyword, confidence))

    return final_results


# ============================================================================
# Gap Analysis
# ============================================================================

async def compute_keyword_gaps(
    db: AsyncSession,
    analysis_id: str,
    user_id: str,
    project_id: str | None = None,
) -> dict:
    """
    Compare competitor keywords against the user's own articles.
    Returns dict with gaps, total counts.
    """
    # Get competitor keywords with article counts
    comp_result = await db.execute(
        select(
            CompetitorArticle.extracted_keyword,
            func.count(CompetitorArticle.id).label("cnt"),
            func.array_agg(CompetitorArticle.url).label("urls"),
        )
        .where(
            CompetitorArticle.analysis_id == analysis_id,
            CompetitorArticle.extracted_keyword.isnot(None),
        )
        .group_by(CompetitorArticle.extracted_keyword)
    )
    competitor_keywords: dict[str, dict] = {}
    for row in comp_result:
        kw = row.extracted_keyword.lower().strip()
        competitor_keywords[kw] = {
            "count": row.cnt,
            "urls": row.urls or [],
        }

    # Get user's keywords
    user_query = select(func.lower(Article.keyword)).where(
        Article.user_id == user_id,
        Article.keyword.isnot(None),
    )
    if project_id:
        user_query = user_query.where(Article.project_id == project_id)

    user_result = await db.execute(user_query)
    user_keywords: set[str] = {row[0].strip() for row in user_result if row[0]}

    # Compute gaps
    gaps = []
    for kw, data in sorted(competitor_keywords.items(), key=lambda x: x[1]["count"], reverse=True):
        if kw not in user_keywords:
            gaps.append({
                "keyword": kw,
                "competitor_articles": data["count"],
                "competitor_urls": data["urls"][:10],  # Cap URLs for response size
            })

    return {
        "gaps": gaps,
        "total_competitor_keywords": len(competitor_keywords),
        "total_your_keywords": len(user_keywords),
        "total_gaps": len(gaps),
    }


# ============================================================================
# Main Pipeline Orchestrator (runs as background task)
# ============================================================================

async def run_competitor_analysis(analysis_id: str) -> None:
    """
    Background task that orchestrates the full competitor analysis pipeline.
    Uses its own DB session (not the request session).
    """
    start_time = time.monotonic()

    try:
        async with async_session_maker() as db:
            analysis = await db.get(CompetitorAnalysis, analysis_id)
            if not analysis:
                logger.error("Analysis %s not found", analysis_id)
                return

            domain = analysis.domain
            logger.info("Starting competitor analysis for %s (id: %s)", domain, analysis_id)

            # Step 1: Discover URLs
            analysis.status = "crawling"
            await db.commit()

            async with httpx.AsyncClient(
                headers={"User-Agent": BOT_USER_AGENT},
                follow_redirects=True,
                timeout=REQUEST_TIMEOUT,
            ) as client:
                urls, crawl_delay = await discover_urls(client, domain)

                if not urls:
                    analysis.status = "failed"
                    analysis.error_message = (
                        f"No article URLs found for {domain}. "
                        "The site may not have a public sitemap, or all URLs were filtered out."
                    )
                    await db.commit()
                    return

                analysis.total_urls = len(urls)
                analysis.status = "scraping"
                await db.commit()

                # Step 2: Scrape pages
                pages_data = await scrape_pages(client, urls, crawl_delay, analysis_id)

            if not pages_data:
                analysis.status = "failed"
                analysis.error_message = "All page scrapes failed. The site may block automated access."
                await db.commit()
                return

            # Step 3: Extract keywords
            # Re-fetch analysis since scrape_pages used separate sessions for progress
            await db.refresh(analysis)
            analysis.status = "extracting"
            await db.commit()

            keyword_results = extract_keywords_with_tfidf(pages_data)

            # Step 4: Save competitor articles
            for page_data, (keyword, confidence) in zip(pages_data, keyword_results):
                article = CompetitorArticle(
                    id=str(uuid4()),
                    analysis_id=analysis_id,
                    url=page_data["url"],
                    title=page_data.get("title"),
                    meta_description=page_data.get("meta_description"),
                    headings=page_data.get("headings"),
                    url_slug=page_data.get("url_slug"),
                    word_count=page_data.get("word_count"),
                    extracted_keyword=keyword,
                    keyword_confidence=confidence,
                    scraped_at=datetime.now(timezone.utc),
                )
                db.add(article)

            # Step 5: Finalize
            distinct_keywords = len({
                kw for kw, _ in keyword_results if kw is not None
            })
            analysis.total_keywords = distinct_keywords
            analysis.scraped_urls = len(pages_data)
            analysis.status = "completed"
            analysis.completed_at = datetime.now(timezone.utc)
            await db.commit()

            elapsed = time.monotonic() - start_time
            logger.info(
                "Competitor analysis completed for %s: %d URLs, %d scraped, %d keywords in %.1fs",
                domain,
                len(urls),
                len(pages_data),
                distinct_keywords,
                elapsed,
            )

    except Exception as exc:
        logger.exception("Competitor analysis failed for analysis %s: %s", analysis_id, exc)
        try:
            async with async_session_maker() as db:
                analysis = await db.get(CompetitorAnalysis, analysis_id)
                if analysis:
                    analysis.status = "failed"
                    analysis.error_message = f"Analysis failed: {str(exc)[:500]}"
                    await db.commit()
        except Exception:
            logger.exception("Failed to mark analysis %s as failed", analysis_id)
