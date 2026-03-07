"""
Site Audit Service — crawls a user's website and detects SEO issues.

BFS crawler with concurrency control, robots.txt compliance, and
comprehensive on-page SEO analysis. Runs as a background task with
its own DB session via async_session_maker.
"""

import asyncio
import ipaddress
import logging
import re
import socket
import time
from collections import defaultdict, deque
from datetime import UTC, datetime
from urllib.parse import urljoin, urlparse, urlunparse
from uuid import uuid4

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.connection import async_session_maker
from infrastructure.database.models.site_audit import AuditIssue, AuditPage, SiteAudit

logger = logging.getLogger(__name__)

BOT_USER_AGENT = "A-Stats-SiteAudit/1.0 (+https://a-stats.app/bot)"
MAX_CONCURRENCY = 5
REQUEST_TIMEOUT = 10.0
MAX_CRAWL_TIME = 1800  # 30 minutes
CRAWL_DELAY = 0.5  # seconds between requests per slot

# Tier-based limits
PAGE_CAPS = {"free": 0, "starter": 10, "professional": 100, "enterprise": 500}
AUDITS_PER_MONTH = {"free": 0, "starter": 5, "professional": 15, "enterprise": 50}


# ============================================================================
# SSRF Protection
# ============================================================================

def _is_safe_url(url: str) -> bool:
    """
    Block requests to private/internal IPs and hostnames.
    Returns True only for valid public domains.
    """
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return False

        # Block hostnames without a dot (e.g. "localhost", "internal")
        if "." not in hostname and hostname != "localhost":
            return False
        if hostname == "localhost":
            return False

        # Resolve hostname and check all IPs
        try:
            addrinfos = socket.getaddrinfo(hostname, None)
        except socket.gaierror:
            return False

        for family, _type, _proto, _canonname, sockaddr in addrinfos:
            ip_str = sockaddr[0]
            try:
                ip = ipaddress.ip_address(ip_str)
            except ValueError:
                return False
            if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local:
                return False

        return True
    except Exception:
        return False


# ============================================================================
# URL Normalization
# ============================================================================

def _normalize_url(url: str, base_url: str) -> str | None:
    """
    Resolve relative URLs, strip fragments and trailing slashes,
    lowercase scheme and host. Returns None for non-HTTP URLs.
    """
    # Skip non-HTTP schemes early
    lower = url.strip().lower()
    if any(lower.startswith(s) for s in ("mailto:", "tel:", "javascript:", "data:", "ftp:")):
        return None

    # Resolve relative URLs
    resolved = urljoin(base_url, url.strip())

    parsed = urlparse(resolved)

    # Only http(s)
    if parsed.scheme not in ("http", "https"):
        return None

    # Lowercase scheme and host
    scheme = parsed.scheme.lower()
    host = parsed.hostname.lower() if parsed.hostname else ""
    port = f":{parsed.port}" if parsed.port and parsed.port not in (80, 443) else ""

    # Strip fragment
    path = parsed.path

    # Strip trailing slash (except for root /)
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    normalized = urlunparse((scheme, f"{host}{port}", path, parsed.params, parsed.query, ""))
    return normalized


# ============================================================================
# Robots.txt
# ============================================================================

async def _fetch_robots_txt(
    client: httpx.AsyncClient, domain: str
) -> tuple[list[str], float]:
    """
    Fetch /robots.txt and parse Disallow rules + Crawl-delay.
    Returns (disallowed_paths, crawl_delay).
    """
    disallowed: list[str] = []
    crawl_delay = 0.0
    url = f"https://{domain}/robots.txt"

    try:
        resp = await client.get(url, follow_redirects=True, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return disallowed, crawl_delay

        current_agent: str | None = None
        applies_to_us = False

        for raw_line in resp.text.splitlines():
            line = raw_line.split("#", 1)[0].strip()
            if not line:
                continue

            lower = line.lower()
            if lower.startswith("user-agent:"):
                agent = line.split(":", 1)[1].strip().lower()
                current_agent = agent
                applies_to_us = agent == "*" or "a-stats" in agent
            elif applies_to_us:
                if lower.startswith("disallow:"):
                    path = line.split(":", 1)[1].strip()
                    if path:
                        disallowed.append(path)
                elif lower.startswith("crawl-delay:"):
                    try:
                        crawl_delay = max(crawl_delay, float(line.split(":", 1)[1].strip()))
                    except ValueError:
                        pass

    except Exception as exc:
        logger.debug("Failed to fetch robots.txt for %s: %s", domain, exc)

    return disallowed, crawl_delay


def _is_path_allowed(path: str, disallowed: list[str]) -> bool:
    """Check if path is allowed by robots.txt Disallow rules."""
    for rule in disallowed:
        if rule.endswith("*"):
            if path.startswith(rule[:-1]):
                return False
        elif path.startswith(rule):
            return False
    return True


# ============================================================================
# Page Analysis — single page
# ============================================================================

def _analyze_page(
    url: str,
    status_code: int,
    response_time_ms: int,
    html_body: str,
    headers: dict,
    page_size: int,
    redirect_chain: list[str],
) -> tuple[dict, list[dict]]:
    """
    Analyze a single crawled page for SEO issues.
    Returns (page_data_dict, issues_list).
    """
    issues: list[dict] = []
    soup = BeautifulSoup(html_body, "html.parser")
    is_https = url.startswith("https://")

    # --- Title tag ---
    title_tag = soup.find("title")
    title_text = title_tag.get_text(strip=True) if title_tag else ""
    if not title_text:
        issues.append({
            "issue_type": "missing_title",
            "severity": "critical",
            "message": "Missing title tag",
        })
    else:
        tlen = len(title_text)
        if tlen < 30:
            issues.append({
                "issue_type": "title_too_short",
                "severity": "warning",
                "message": f"Title too short ({tlen} chars, recommended 30-60)",
            })
        elif tlen > 60:
            issues.append({
                "issue_type": "title_too_long",
                "severity": "warning",
                "message": f"Title too long ({tlen} chars, recommended 30-60)",
            })

    # --- Meta description ---
    meta_tag = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
    meta_desc = meta_tag.get("content", "").strip() if meta_tag else ""
    if not meta_desc:
        issues.append({
            "issue_type": "missing_meta_description",
            "severity": "warning",
            "message": "Missing meta description",
        })
    else:
        mlen = len(meta_desc)
        if mlen < 70:
            issues.append({
                "issue_type": "meta_description_too_short",
                "severity": "info",
                "message": f"Meta description too short ({mlen} chars, recommended 70-160)",
            })
        elif mlen > 160:
            issues.append({
                "issue_type": "meta_description_too_long",
                "severity": "warning",
                "message": f"Meta description too long ({mlen} chars, recommended 70-160)",
            })

    # --- Headings ---
    h1s = soup.find_all("h1")
    h1_count = len(h1s)
    if h1_count == 0:
        issues.append({
            "issue_type": "missing_h1",
            "severity": "critical",
            "message": "Missing H1 heading",
        })
    elif h1_count > 1:
        issues.append({
            "issue_type": "multiple_h1",
            "severity": "warning",
            "message": f"Multiple H1 headings found ({h1_count})",
        })

    # --- Images without alt ---
    images = soup.find_all("img")
    total_images = len(images)
    missing_alt_srcs: list[str] = []
    for img in images:
        alt = img.get("alt", None)
        if alt is None or alt.strip() == "":
            src = img.get("src", "")
            missing_alt_srcs.append(src)
    if missing_alt_srcs:
        issues.append({
            "issue_type": "images_missing_alt",
            "severity": "warning",
            "message": f"Found {len(missing_alt_srcs)} images without alt text out of {total_images}",
            "details": {
                "total_images": total_images,
                "missing_alt": len(missing_alt_srcs),
                "sample_srcs": missing_alt_srcs[:10],
            },
        })

    # --- Canonical ---
    canonical_tag = soup.find("link", attrs={"rel": "canonical"})
    has_canonical = canonical_tag is not None
    if not has_canonical:
        issues.append({
            "issue_type": "missing_canonical",
            "severity": "warning",
            "message": "Missing canonical tag",
        })
    elif canonical_tag:
        canonical_href = canonical_tag.get("href", "").strip()
        if canonical_href and canonical_href != url:
            issues.append({
                "issue_type": "canonical_mismatch",
                "severity": "info",
                "message": "Canonical URL differs from page URL",
                "details": {"canonical": canonical_href, "page_url": url},
            })

    # --- Content / word count ---
    # Remove script, style, nav, footer for body text extraction
    for tag in soup.find_all(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
        tag.decompose()

    body_el = soup.find("body")
    body_text = body_el.get_text(separator=" ", strip=True) if body_el else ""
    words = body_text.split()
    word_count = len(words)

    if word_count < 300:
        issues.append({
            "issue_type": "thin_content",
            "severity": "warning",
            "message": f"Thin content ({word_count} words, recommended 300+)",
        })

    # Page size check
    size_mb = round(page_size / (1024 * 1024), 2)
    if page_size > 3 * 1024 * 1024:
        issues.append({
            "issue_type": "large_page",
            "severity": "warning",
            "message": f"Large page size ({size_mb}MB)",
        })

    # --- Open Graph ---
    og_title = soup.find("meta", attrs={"property": "og:title"})
    og_desc = soup.find("meta", attrs={"property": "og:description"})
    og_image = soup.find("meta", attrs={"property": "og:image"})
    missing_og: list[str] = []
    if not og_title:
        missing_og.append("og:title")
    if not og_desc:
        missing_og.append("og:description")
    if not og_image:
        missing_og.append("og:image")
    has_og_tags = len(missing_og) == 0
    if missing_og:
        issues.append({
            "issue_type": "missing_og_tags",
            "severity": "info",
            "message": f"Missing Open Graph tags: {', '.join(missing_og)}",
        })

    # --- Structured Data ---
    ld_json_scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
    has_structured_data = len(ld_json_scripts) > 0
    if not has_structured_data:
        issues.append({
            "issue_type": "no_structured_data",
            "severity": "info",
            "message": "No structured data (JSON-LD) found",
        })

    # --- Performance ---
    if response_time_ms > 3000:
        issues.append({
            "issue_type": "slow_response",
            "severity": "warning",
            "message": f"Slow page response ({response_time_ms}ms)",
        })

    # --- Mixed content ---
    if is_https:
        mixed_count = 0
        for tag_name, attr in [("img", "src"), ("script", "src"), ("link", "href")]:
            if tag_name == "link":
                # Only check stylesheets
                elements = soup.find_all(tag_name, attrs={"rel": "stylesheet"})
            else:
                elements = soup.find_all(tag_name)
            for el in elements:
                val = el.get(attr, "")
                if val.startswith("http://"):
                    mixed_count += 1
        if mixed_count:
            issues.append({
                "issue_type": "mixed_content",
                "severity": "warning",
                "message": f"Mixed content: {mixed_count} HTTP resources on HTTPS page",
            })

    # --- Robots meta ---
    robots_meta = soup.find("meta", attrs={"name": re.compile(r"^robots$", re.I)})
    has_robots_meta = robots_meta is not None
    if robots_meta:
        content = (robots_meta.get("content", "") or "").lower()
        if "noindex" in content:
            issues.append({
                "issue_type": "noindex",
                "severity": "info",
                "message": "Page has noindex directive",
            })

    # --- Redirect chain ---
    if len(redirect_chain) >= 3:
        issues.append({
            "issue_type": "redirect_chain",
            "severity": "warning",
            "message": f"Redirect chain detected ({len(redirect_chain)} hops)",
            "details": {"chain": redirect_chain[:10]},
        })

    # --- Hreflang ---
    lang_attr = soup.find("html", attrs={"lang": True})
    hreflang_links = soup.find_all("link", attrs={"hreflang": True})
    if lang_attr and not hreflang_links:
        issues.append({
            "issue_type": "missing_hreflang",
            "severity": "info",
            "message": "Missing hreflang tags on multilingual page",
        })

    # --- Favicon ---
    favicon = soup.find("link", attrs={"rel": re.compile(r"icon", re.I)})
    if not favicon:
        issues.append({
            "issue_type": "missing_favicon",
            "severity": "info",
            "message": "Missing favicon declaration",
        })

    # Build page data dict
    content_type = headers.get("content-type", "")
    issues_summary = [{"type": i["issue_type"], "severity": i["severity"]} for i in issues]

    page_data = {
        "url": url,
        "status_code": status_code,
        "response_time_ms": response_time_ms,
        "content_type": content_type,
        "word_count": word_count,
        "title": title_text or None,
        "meta_description": meta_desc or None,
        "h1_count": h1_count,
        "has_canonical": has_canonical,
        "has_og_tags": has_og_tags,
        "has_structured_data": has_structured_data,
        "has_robots_meta": has_robots_meta,
        "page_size_bytes": page_size,
        "redirect_chain": redirect_chain,
        "issues": issues_summary,
    }

    return page_data, issues


# ============================================================================
# Cross-page (site-wide) analysis
# ============================================================================

def _analyze_site_wide(pages_data: list[dict]) -> list[dict]:
    """
    Detect site-wide issues across all crawled pages.
    Returns list of issue dicts (audit-level, no page_id).
    """
    issues: list[dict] = []

    # --- Duplicate titles ---
    title_map: dict[str, list[str]] = defaultdict(list)
    for p in pages_data:
        t = p.get("title")
        if t:
            title_map[t.strip().lower()].append(p["url"])
    for title, urls in title_map.items():
        if len(urls) >= 2:
            issues.append({
                "issue_type": "duplicate_title",
                "severity": "warning",
                "message": f"Duplicate title found on {len(urls)} pages",
                "details": {"title": title, "urls": urls[:20]},
            })

    # --- Duplicate meta descriptions ---
    desc_map: dict[str, list[str]] = defaultdict(list)
    for p in pages_data:
        d = p.get("meta_description")
        if d:
            desc_map[d.strip().lower()].append(p["url"])
    for desc, urls in desc_map.items():
        if len(urls) >= 2:
            issues.append({
                "issue_type": "duplicate_meta_description",
                "severity": "warning",
                "message": f"Duplicate meta description found on {len(urls)} pages",
                "details": {"description": desc[:200], "urls": urls[:20]},
            })

    # --- Orphan pages ---
    # A page is orphan if no other crawled page links to it
    all_urls = {p["url"] for p in pages_data}
    linked_urls: set[str] = set()
    for p in pages_data:
        for link in p.get("internal_links", []):
            linked_urls.add(link)

    # The root URL is never orphan
    root_urls: set[str] = set()
    for u in all_urls:
        parsed = urlparse(u)
        if parsed.path in ("", "/"):
            root_urls.add(u)

    orphans = all_urls - linked_urls - root_urls
    if orphans:
        issues.append({
            "issue_type": "orphan_pages",
            "severity": "info",
            "message": f"Found {len(orphans)} orphan pages (not linked from other crawled pages)",
            "details": {"urls": sorted(orphans)[:50]},
        })

    return issues


# ============================================================================
# Sitemap & robots essentials check
# ============================================================================

async def _check_site_essentials(
    client: httpx.AsyncClient, domain: str
) -> list[dict]:
    """Check for sitemap.xml and robots.txt presence."""
    issues: list[dict] = []
    base = f"https://{domain}"

    # Sitemap
    try:
        resp = await client.get(
            f"{base}/sitemap.xml", follow_redirects=True, timeout=REQUEST_TIMEOUT
        )
        if resp.status_code != 200:
            issues.append({
                "issue_type": "missing_sitemap",
                "severity": "warning",
                "message": "Missing sitemap.xml",
            })
    except Exception:
        issues.append({
            "issue_type": "missing_sitemap",
            "severity": "warning",
            "message": "Missing sitemap.xml",
        })

    # Robots.txt
    try:
        resp = await client.get(
            f"{base}/robots.txt", follow_redirects=True, timeout=REQUEST_TIMEOUT
        )
        if resp.status_code != 200:
            issues.append({
                "issue_type": "missing_robots_txt",
                "severity": "info",
                "message": "Missing robots.txt",
            })
    except Exception:
        issues.append({
            "issue_type": "missing_robots_txt",
            "severity": "info",
            "message": "Missing robots.txt",
        })

    return issues


# ============================================================================
# BFS Crawl Loop
# ============================================================================

async def _crawl_site(
    audit_id: str,
    domain: str,
    max_pages: int,
    disallowed_paths: list[str],
    crawl_delay: float,
    client: httpx.AsyncClient,
) -> tuple[list[dict], dict[str, set[str]]]:
    """
    BFS crawl starting from domain root. Returns:
    - list of raw page result dicts (url, status_code, response_time_ms, html, headers, size, redirect_chain)
    - internal_links_map: {source_url: set of linked urls}
    """
    start_url = f"https://{domain}"
    queue: deque[str] = deque([start_url])
    visited: set[str] = set()
    results: list[dict] = []
    internal_links_map: dict[str, set[str]] = defaultdict(set)
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    crawl_start = time.monotonic()
    pages_discovered = 1  # root is already discovered

    async def fetch_page(page_url: str) -> dict | None:
        """Fetch a single page, respecting concurrency and SSRF."""
        async with semaphore:
            # SSRF check
            if not _is_safe_url(page_url):
                logger.debug("Blocked unsafe URL: %s", page_url)
                return None

            # Robots check
            parsed_path = urlparse(page_url).path or "/"
            if not _is_path_allowed(parsed_path, disallowed_paths):
                logger.debug("Robots.txt disallows: %s", page_url)
                return None

            try:
                t0 = time.monotonic()
                resp = await client.get(
                    page_url,
                    follow_redirects=True,
                    timeout=REQUEST_TIMEOUT,
                )
                elapsed_ms = int((time.monotonic() - t0) * 1000)

                # Build redirect chain from history
                chain: list[str] = [str(r.url) for r in resp.history]
                if chain:
                    chain.append(str(resp.url))

                html_body = ""
                ct = resp.headers.get("content-type", "")
                if "text/html" in ct:
                    html_body = resp.text

                return {
                    "url": page_url,
                    "final_url": str(resp.url),
                    "status_code": resp.status_code,
                    "response_time_ms": elapsed_ms,
                    "html": html_body,
                    "headers": dict(resp.headers),
                    "page_size": len(resp.content),
                    "redirect_chain": chain,
                    "content_type": ct,
                }
            except Exception as exc:
                logger.debug("Crawl error for %s: %s", page_url, exc)
                return None
            finally:
                await asyncio.sleep(crawl_delay)

    batch_counter = 0

    while queue and len(results) < max_pages:
        # Time limit
        if time.monotonic() - crawl_start > MAX_CRAWL_TIME:
            logger.warning("Crawl time limit reached for audit %s", audit_id)
            break

        # Drain up to MAX_CONCURRENCY URLs from queue
        batch: list[str] = []
        while queue and len(batch) < MAX_CONCURRENCY:
            candidate = queue.popleft()
            if candidate not in visited:
                visited.add(candidate)
                batch.append(candidate)

        if not batch:
            break

        # Fetch batch concurrently
        fetch_results = await asyncio.gather(*[fetch_page(u) for u in batch])

        for result in fetch_results:
            if result is None:
                continue
            results.append(result)

            # Extract internal links from HTML pages
            if result["html"] and "text/html" in result.get("content_type", ""):
                try:
                    link_soup = BeautifulSoup(result["html"], "html.parser")
                    for a_tag in link_soup.find_all("a", href=True):
                        href = a_tag["href"]
                        normalized = _normalize_url(href, result["final_url"])
                        if normalized is None:
                            continue
                        link_parsed = urlparse(normalized)
                        link_domain = link_parsed.hostname or ""
                        if link_domain != domain:
                            continue
                        # Skip static assets
                        if re.search(
                            r"\.(pdf|jpg|jpeg|png|gif|webp|svg|css|js|xml|zip|mp4|mp3)$",
                            link_parsed.path,
                            re.IGNORECASE,
                        ):
                            continue

                        internal_links_map[result["url"]].add(normalized)

                        if normalized not in visited and len(visited) + len(queue) < max_pages * 3:
                            queue.append(normalized)
                            pages_discovered += 1
                except Exception as exc:
                    logger.debug("Link extraction error on %s: %s", result["url"], exc)

        batch_counter += len(batch)

        # Update progress every 5 pages
        if batch_counter % 5 < MAX_CONCURRENCY:
            try:
                async with async_session_maker() as progress_db:
                    audit = await progress_db.get(SiteAudit, audit_id)
                    if audit:
                        audit.pages_crawled = len(results)
                        audit.pages_discovered = pages_discovered
                        await progress_db.commit()
            except Exception:
                pass  # Non-critical progress update

    return results, internal_links_map


# ============================================================================
# Main Pipeline Orchestrator
# ============================================================================

async def run_site_audit(audit_id: str) -> None:
    """
    Background task that orchestrates the full site audit pipeline.
    Uses its own DB session (not the request session).
    """
    start_time = time.monotonic()

    try:
        async with async_session_maker() as db:
            # ----- Step 1: Load audit, set status to crawling -----
            audit = await db.get(SiteAudit, audit_id)
            if not audit:
                logger.error("Site audit %s not found", audit_id)
                return

            domain = audit.domain
            user_id = audit.user_id
            logger.info("Starting site audit for %s (id: %s)", domain, audit_id)

            audit.status = "crawling"
            audit.started_at = datetime.now(UTC)
            await db.commit()

            # ----- Step 2: Determine user tier → page cap -----
            from infrastructure.database.models.user import User

            user = await db.get(User, user_id)
            if not user:
                audit.status = "failed"
                audit.error_message = "User not found"
                await db.commit()
                return

            tier = user.subscription_tier or "free"
            max_pages = PAGE_CAPS.get(tier, PAGE_CAPS["free"])

            if max_pages <= 0:
                audit.status = "failed"
                audit.error_message = "Site audits are not available on the free plan. Please upgrade."
                await db.commit()
                return

            # ----- Step 3: Robots.txt -----
            async with httpx.AsyncClient(
                headers={"User-Agent": BOT_USER_AGENT},
                follow_redirects=True,
                timeout=REQUEST_TIMEOUT,
            ) as client:
                disallowed_paths, robots_delay = await _fetch_robots_txt(client, domain)
                crawl_delay = max(CRAWL_DELAY, robots_delay)

                # ----- Step 4: BFS Crawl -----
                raw_results, internal_links_map = await _crawl_site(
                    audit_id=audit_id,
                    domain=domain,
                    max_pages=max_pages,
                    disallowed_paths=disallowed_paths,
                    crawl_delay=crawl_delay,
                    client=client,
                )

                if not raw_results:
                    await db.refresh(audit)
                    audit.status = "failed"
                    audit.error_message = (
                        f"Could not crawl any pages on {domain}. "
                        "The site may be unreachable or blocking automated access."
                    )
                    await db.commit()
                    return

                # ----- Step 5: Analyzing -----
                await db.refresh(audit)
                audit.status = "analyzing"
                audit.pages_crawled = len(raw_results)
                await db.commit()

                # ----- Step 6: Analyze each page -----
                all_page_data: list[dict] = []
                all_page_issues: list[tuple[int, list[dict]]] = []  # (page_index, issues)

                for idx, raw in enumerate(raw_results):
                    if raw["html"] and "text/html" in raw.get("content_type", ""):
                        page_data, page_issues = _analyze_page(
                            url=raw["url"],
                            status_code=raw["status_code"],
                            response_time_ms=raw["response_time_ms"],
                            html_body=raw["html"],
                            headers=raw["headers"],
                            page_size=raw["page_size"],
                            redirect_chain=raw["redirect_chain"],
                        )
                    else:
                        # Non-HTML page — store minimal data
                        page_data = {
                            "url": raw["url"],
                            "status_code": raw["status_code"],
                            "response_time_ms": raw["response_time_ms"],
                            "content_type": raw.get("content_type", ""),
                            "word_count": 0,
                            "title": None,
                            "meta_description": None,
                            "h1_count": 0,
                            "has_canonical": False,
                            "has_og_tags": False,
                            "has_structured_data": False,
                            "has_robots_meta": False,
                            "page_size_bytes": raw["page_size"],
                            "redirect_chain": raw["redirect_chain"],
                            "issues": [],
                        }
                        page_issues = []

                    # Attach internal links for orphan detection
                    page_data["internal_links"] = list(internal_links_map.get(raw["url"], set()))
                    all_page_data.append(page_data)
                    all_page_issues.append((idx, page_issues))

                # ----- Step 7: Site-wide cross-page analysis -----
                site_wide_issues = _analyze_site_wide(all_page_data)

                # ----- Step 8: Site essentials (sitemap, robots) -----
                essentials_issues = await _check_site_essentials(client, domain)

            # ----- Step 8b: PageSpeed Insights on top pages -----
            try:
                from services.pagespeed import fetch_pagespeed

                # Pick homepage + top 4 most-linked pages for PageSpeed analysis
                # internal_links_map is {source_url: set_of_urls_it_links_to}
                # We want pages that are linked TO the most (most inbound links)
                inbound_counts: dict[str, int] = {}
                for _source_url, targets in internal_links_map.items():
                    for target in targets:
                        inbound_counts[target] = inbound_counts.get(target, 0) + 1

                # Start with homepage, add top linked pages
                homepage = f"https://{domain}"
                pagespeed_urls = [homepage]
                sorted_by_inbound = sorted(
                    ((url, count) for url, count in inbound_counts.items() if url != homepage),
                    key=lambda x: x[1],
                    reverse=True,
                )
                for ps_url, _ in sorted_by_inbound[:4]:
                    pagespeed_urls.append(ps_url)

                logger.info("Running PageSpeed Insights on %d pages", len(pagespeed_urls))

                for ps_url in pagespeed_urls:
                    ps_result = await fetch_pagespeed(ps_url)
                    if ps_result:
                        # Find the matching page data and update it
                        for pdata in all_page_data:
                            if pdata["url"] == ps_url:
                                pdata["performance_score"] = ps_result["performance_score"]
                                pdata["pagespeed_data"] = ps_result
                                break
                        logger.info(
                            "PageSpeed for %s: score=%s",
                            ps_url, ps_result["performance_score"],
                        )
                    await asyncio.sleep(1)  # Rate limit PageSpeed API calls

            except Exception as ps_err:
                logger.warning("PageSpeed analysis failed: %s", ps_err)

            # ----- Step 9: Compute score -----
            critical_count = 0
            warning_count = 0
            info_count = 0

            # Count page-level issues
            for _idx, page_issues in all_page_issues:
                for iss in page_issues:
                    sev = iss.get("severity", "info")
                    if sev == "critical":
                        critical_count += 1
                    elif sev == "warning":
                        warning_count += 1
                    else:
                        info_count += 1

            # Count site-wide + essentials issues
            for iss in site_wide_issues + essentials_issues:
                sev = iss.get("severity", "info")
                if sev == "critical":
                    critical_count += 1
                elif sev == "warning":
                    warning_count += 1
                else:
                    info_count += 1

            total_issues = critical_count + warning_count + info_count
            score = max(0, round(100 - critical_count * 3 - warning_count * 1 - info_count * 0.2))

            # ----- Step 10: Bulk create AuditPage rows -----
            page_id_map: dict[int, str] = {}  # index -> page row ID

            for idx, pdata in enumerate(all_page_data):
                page_row_id = str(uuid4())
                page_id_map[idx] = page_row_id
                audit_page = AuditPage(
                    id=page_row_id,
                    audit_id=audit_id,
                    url=pdata["url"],
                    status_code=pdata["status_code"],
                    response_time_ms=pdata["response_time_ms"],
                    content_type=pdata.get("content_type", ""),
                    word_count=pdata.get("word_count", 0),
                    title=pdata.get("title"),
                    meta_description=pdata.get("meta_description"),
                    h1_count=pdata.get("h1_count", 0),
                    has_canonical=pdata.get("has_canonical", False),
                    has_og_tags=pdata.get("has_og_tags", False),
                    has_structured_data=pdata.get("has_structured_data", False),
                    has_robots_meta=pdata.get("has_robots_meta", False),
                    page_size_bytes=pdata.get("page_size_bytes"),
                    redirect_chain=pdata.get("redirect_chain") or None,
                    performance_score=pdata.get("performance_score"),
                    pagespeed_data=pdata.get("pagespeed_data"),
                    issues_json=pdata.get("issues"),
                )
                db.add(audit_page)

            # ----- Step 11: Bulk create AuditIssue rows -----
            # Page-level issues
            for idx, page_issues in all_page_issues:
                page_row_id = page_id_map.get(idx)
                for iss in page_issues:
                    db.add(AuditIssue(
                        id=str(uuid4()),
                        audit_id=audit_id,
                        page_id=page_row_id,
                        issue_type=iss["issue_type"],
                        severity=iss["severity"],
                        message=iss["message"],
                        details=iss.get("details"),
                    ))

            # Site-wide issues (no page_id)
            for iss in site_wide_issues + essentials_issues:
                db.add(AuditIssue(
                    id=str(uuid4()),
                    audit_id=audit_id,
                    page_id=None,
                    issue_type=iss["issue_type"],
                    severity=iss["severity"],
                    message=iss["message"],
                    details=iss.get("details"),
                ))

            # ----- Step 12: Finalize audit -----
            await db.refresh(audit)
            audit.total_issues = total_issues
            audit.critical_issues = critical_count
            audit.warning_issues = warning_count
            audit.info_issues = info_count
            audit.score = score
            audit.pages_crawled = len(raw_results)
            audit.pages_discovered = len(all_page_data)
            audit.status = "completed"
            audit.completed_at = datetime.now(UTC)
            await db.commit()

            elapsed = time.monotonic() - start_time
            logger.info(
                "Site audit completed for %s: %d pages, %d issues (C:%d W:%d I:%d), score=%d in %.1fs",
                domain,
                len(raw_results),
                total_issues,
                critical_count,
                warning_count,
                info_count,
                score,
                elapsed,
            )

    except Exception as exc:
        logger.exception("Site audit failed for audit %s: %s", audit_id, exc)
        try:
            async with async_session_maker() as db:
                audit = await db.get(SiteAudit, audit_id)
                if audit:
                    audit.status = "failed"
                    audit.error_message = f"Audit failed: {str(exc)[:500]}"
                    await db.commit()
        except Exception:
            logger.exception("Failed to mark audit %s as failed", audit_id)
