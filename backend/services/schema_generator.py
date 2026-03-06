"""
Generate JSON-LD structured data (Article + FAQPage schemas) from article content.

These schemas improve visibility in search engines via rich snippets.
"""

import json
import re
from datetime import datetime


def generate_article_schema(
    title: str,
    meta_description: str,
    keyword: str,
    word_count: int,
    url: str | None = None,
    author_name: str | None = None,
    date_published: datetime | None = None,
    date_modified: datetime | None = None,
    image_url: str | None = None,
    language: str = "en",
) -> dict:
    """Generate JSON-LD Article schema."""
    schema: dict = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title[:110],  # Google truncates at 110 chars
        "description": meta_description[:160],
        "wordCount": word_count,
        "inLanguage": language,
    }

    if url:
        schema["url"] = url
        schema["mainEntityOfPage"] = {"@type": "WebPage", "@id": url}
    if author_name:
        schema["author"] = {"@type": "Person", "name": author_name}
    if date_published:
        schema["datePublished"] = date_published.isoformat()
    if date_modified:
        schema["dateModified"] = date_modified.isoformat()
    if image_url:
        schema["image"] = image_url
    if keyword:
        schema["keywords"] = keyword

    return schema


def generate_faq_schema(content: str) -> dict | None:
    """Extract FAQ section from markdown and generate FAQPage JSON-LD schema.

    Looks for a ## heading containing 'FAQ' or 'Frequently Asked Questions',
    then parses ### Q/A pairs or bold-question / answer patterns.

    Returns None if no FAQ section is found or fewer than 2 Q&As are parsed.
    """
    # Find FAQ section
    faq_match = re.search(
        r"^## .*(?:frequently asked questions|faq).*?\n(.*?)(?=^## |\Z)",
        content,
        re.MULTILINE | re.IGNORECASE | re.DOTALL,
    )
    if not faq_match:
        return None

    faq_text = faq_match.group(1).strip()
    qa_pairs: list[dict] = []

    # Pattern 1: ### Question\nAnswer
    h3_pairs = re.findall(
        r"^###\s+(.+?)\n(.*?)(?=^###|\Z)",
        faq_text,
        re.MULTILINE | re.DOTALL,
    )
    for question, answer in h3_pairs:
        q = question.strip().rstrip("?") + "?"
        a = answer.strip()
        # Remove markdown bold/italic
        a = re.sub(r"\*\*(.+?)\*\*", r"\1", a)
        a = re.sub(r"\*(.+?)\*", r"\1", a)
        if q and a and len(a) > 10:
            qa_pairs.append({
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {"@type": "Answer", "text": a[:500]},
            })

    # Pattern 2: **Question?**\nAnswer (if no H3 pairs found)
    if not qa_pairs:
        bold_pairs = re.findall(
            r"\*\*(.+?\??)\*\*\s*\n(.*?)(?=\*\*|\Z)",
            faq_text,
            re.DOTALL,
        )
        for question, answer in bold_pairs:
            q = question.strip().rstrip("?") + "?"
            a = answer.strip()
            if q and a and len(a) > 10:
                qa_pairs.append({
                    "@type": "Question",
                    "name": q,
                    "acceptedAnswer": {"@type": "Answer", "text": a[:500]},
                })

    if len(qa_pairs) < 2:
        return None

    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": qa_pairs,
    }


def generate_schemas(
    content: str,
    title: str,
    meta_description: str,
    keyword: str,
    word_count: int,
    url: str | None = None,
    author_name: str | None = None,
    date_published: datetime | None = None,
    date_modified: datetime | None = None,
    image_url: str | None = None,
    language: str = "en",
) -> dict:
    """Generate both Article and FAQPage schemas.

    Returns a dict with 'article_schema' and optionally 'faq_schema'.
    """
    result: dict = {
        "article_schema": generate_article_schema(
            title=title,
            meta_description=meta_description,
            keyword=keyword,
            word_count=word_count,
            url=url,
            author_name=author_name,
            date_published=date_published,
            date_modified=date_modified,
            image_url=image_url,
            language=language,
        ),
    }

    faq = generate_faq_schema(content)
    if faq:
        result["faq_schema"] = faq

    return result


def schemas_to_html(schemas: dict) -> str:
    """Convert schemas dict to embeddable HTML <script> tags."""
    parts = []
    for key in ("article_schema", "faq_schema"):
        schema = schemas.get(key)
        if schema:
            json_str = json.dumps(schema, indent=2, ensure_ascii=False)
            parts.append(f'<script type="application/ld+json">\n{json_str}\n</script>')
    return "\n".join(parts)
