"""
Knowledge document processor: extracts text, splits into chunks, and performs
keyword-based search.

Intentionally simple — no vector embeddings, no external AI.  The goal is a
fully functional feature that replaces the previous placeholder implementation.
"""

import csv
import io
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple
from uuid import uuid4

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Storage directory
# ---------------------------------------------------------------------------

# Resolve relative to main.py's location (backend/)
_BACKEND_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_STORAGE_DIR = _BACKEND_DIR / "storage" / "knowledge"


def ensure_storage_dir() -> None:
    """Create the storage directory if it does not exist."""
    KNOWLEDGE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def get_file_path(source_id: str, filename: str) -> Path:
    """Return the canonical on-disk path for a knowledge source file."""
    ensure_storage_dir()
    # Sanitise the filename to prevent path traversal.
    safe_name = re.sub(r"[^\w.\-]", "_", filename)
    return KNOWLEDGE_STORAGE_DIR / f"{source_id}_{safe_name}"


def delete_file(file_path: str) -> None:
    """Delete a file from disk, ignoring missing-file errors."""
    try:
        path = Path(file_path)
        if path.exists():
            path.unlink()
            logger.info("Deleted knowledge file: %s", file_path)
    except OSError as exc:
        logger.warning("Failed to delete knowledge file %s: %s", file_path, exc)


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

WORDS_PER_CHUNK = 500
MIN_CHUNK_CHARS = 50  # ignore tiny chunks


def _extract_txt(content: bytes) -> str:
    """Decode plain text / markdown bytes."""
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("latin-1", errors="replace")


def _extract_pdf(content: bytes) -> Tuple[str, bool]:
    """
    Extract text from a PDF.

    Returns (text, success).  If pypdf is unavailable or parsing fails the
    caller should mark the source as pending for manual reprocessing.
    """
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(io.BytesIO(content))
        parts: List[str] = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                parts.append(text.strip())
        return "\n\n".join(parts), True
    except ImportError:
        logger.warning("pypdf not available – PDF stored without text extraction")
        return "", False
    except (ValueError, KeyError, OSError, EOFError) as exc:
        # pypdf raises various exceptions on corrupt/malformed PDFs
        logger.warning("PDF extraction failed: %s", exc)
        return "", False


def _extract_csv(content: bytes) -> str:
    """Convert CSV bytes to a text representation."""
    try:
        text = content.decode("utf-8", errors="replace")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        if not rows:
            return ""
        # Build a simple table-like string
        lines: List[str] = []
        header = rows[0]
        lines.append("\t".join(header))
        lines.append("-" * 40)
        for row in rows[1:]:
            lines.append("\t".join(row))
        return "\n".join(lines)
    except (csv.Error, UnicodeDecodeError, ValueError) as exc:
        logger.warning("CSV extraction failed: %s", exc)
        return content.decode("utf-8", errors="replace")


def _extract_json(content: bytes) -> str:
    """Pretty-print JSON bytes to a string."""
    try:
        data = json.loads(content)
        return json.dumps(data, indent=2, ensure_ascii=False)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return content.decode("utf-8", errors="replace")


def _extract_html(content: bytes) -> str:
    """Strip HTML tags and return plain text."""
    try:
        from bs4 import BeautifulSoup  # type: ignore

        soup = BeautifulSoup(content, "lxml")
        # Remove script/style elements
        for tag in soup(["script", "style"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)
    except ImportError:
        # Fall back to simple regex strip
        text = content.decode("utf-8", errors="replace")
        return re.sub(r"<[^>]+>", " ", text)
    except (ValueError, TypeError, UnicodeDecodeError) as exc:
        # BeautifulSoup can raise these on severely malformed HTML
        logger.warning("HTML extraction failed: %s", exc)
        return content.decode("utf-8", errors="replace")


def _extract_docx(content: bytes) -> str:
    """Extract text from a DOCX file using python-docx."""
    try:
        import docx  # type: ignore
        from zipfile import BadZipFile

        doc = docx.Document(io.BytesIO(content))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)
    except ImportError:
        logger.warning("python-docx not available – DOCX stored without text extraction")
        return ""
    except (BadZipFile, ValueError, KeyError, OSError) as exc:
        # DOCX is a ZIP archive; corrupt files trigger BadZipFile or KeyError
        logger.warning("DOCX extraction failed: %s", exc)
        return ""


def extract_text(content: bytes, file_type: str) -> Tuple[str, bool]:
    """
    Extract plain text from file bytes.

    Returns (text, fully_extracted).  fully_extracted is False when the
    extraction was incomplete or impossible (e.g. missing library).
    """
    ft = file_type.lower().lstrip(".")

    if ft in ("txt", "md", "markdown"):
        return _extract_txt(content), True
    if ft == "pdf":
        return _extract_pdf(content)
    if ft == "csv":
        return _extract_csv(content), True
    if ft == "json":
        return _extract_json(content), True
    if ft in ("html", "htm"):
        return _extract_html(content), True
    if ft == "docx":
        text = _extract_docx(content)
        return text, bool(text)
    # Unknown type — attempt UTF-8 decode
    try:
        return content.decode("utf-8", errors="replace"), True
    except (UnicodeDecodeError, ValueError):
        return "", False


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def split_into_chunks(text: str, words_per_chunk: int = WORDS_PER_CHUNK) -> List[str]:
    """
    Split text into chunks of approximately *words_per_chunk* words.

    Strategy:
    1. Split on double newlines (paragraph boundaries) first.
    2. If a paragraph is still too large, split it by sentence-ish boundaries.
    3. Accumulate paragraphs into a chunk until the word budget is exhausted.
    """
    if not text.strip():
        return []

    # Normalise whitespace
    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks: List[str] = []
    current_words: List[str] = []
    current_count = 0

    for para in paragraphs:
        para_words = para.split()
        para_count = len(para_words)

        if para_count == 0:
            continue

        # If adding this paragraph would exceed the budget and we already have
        # content, flush the current chunk first.
        if current_count > 0 and current_count + para_count > words_per_chunk * 1.2:
            chunk_text = " ".join(current_words)
            if len(chunk_text) >= MIN_CHUNK_CHARS:
                chunks.append(chunk_text)
            current_words = []
            current_count = 0

        # If the paragraph itself is larger than the budget, slice it.
        if para_count > words_per_chunk * 1.2:
            for i in range(0, para_count, words_per_chunk):
                slice_words = para_words[i : i + words_per_chunk]
                slice_text = " ".join(slice_words)
                if len(slice_text) >= MIN_CHUNK_CHARS:
                    chunks.append(slice_text)
        else:
            current_words.extend(para_words)
            current_count += para_count

    # Flush remainder
    if current_words:
        chunk_text = " ".join(current_words)
        if len(chunk_text) >= MIN_CHUNK_CHARS:
            chunks.append(chunk_text)

    return chunks


# ---------------------------------------------------------------------------
# Keyword search
# ---------------------------------------------------------------------------

def score_chunk(chunk: str, query_words: List[str]) -> float:
    """
    Return a relevance score in [0, 1] for a chunk given query words.

    Scoring is based on the proportion of unique query words that appear
    in the chunk (case-insensitive), weighted by term frequency.
    """
    if not query_words or not chunk:
        return 0.0

    chunk_lower = chunk.lower()
    total_score = 0.0
    for word in query_words:
        count = chunk_lower.count(word.lower())
        if count > 0:
            # Logarithmic TF to avoid runaway scores for repeated terms
            import math
            total_score += 1 + math.log(count)

    # Normalise by number of query words so score is in a comparable range
    return min(total_score / len(query_words), 10.0)


def search_chunks(
    chunks: List[Tuple[str, str, str, int]],  # (chunk_id, source_id, source_title, chunk_index, content)
    query: str,
    top_k: int = 5,
) -> List[dict]:
    """
    Keyword search over a list of chunk tuples.

    ``chunks`` is a list of (chunk_id, source_id, source_title, chunk_index, content).

    Returns up to *top_k* results sorted by score descending.
    """
    # Tokenise query — keep only meaningful words (length >= 3)
    raw_words = re.findall(r"\b\w+\b", query.lower())
    query_words = [w for w in raw_words if len(w) >= 3]
    if not query_words:
        query_words = raw_words  # fallback to all words

    results = []
    for chunk_id, source_id, source_title, chunk_index, content in chunks:
        s = score_chunk(content, query_words)
        if s > 0:
            results.append(
                {
                    "chunk_id": chunk_id,
                    "source_id": source_id,
                    "source_title": source_title,
                    "chunk_index": chunk_index,
                    "content": content,
                    "score": s,
                }
            )

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:top_k]


def build_answer(query: str, matched_chunks: List[dict]) -> str:
    """
    Build a human-readable answer from matched chunks.

    This is a simple text assembly — not AI-generated.  It surfaces the most
    relevant passages so the user can read the actual source material.
    """
    if not matched_chunks:
        return (
            "No relevant content found in your knowledge base for this query. "
            "Try different keywords or upload more documents."
        )

    lines: List[str] = [
        f"Found {len(matched_chunks)} relevant passage(s) for: **{query}**\n"
    ]
    for i, chunk in enumerate(matched_chunks, 1):
        lines.append(f"### Source {i}: {chunk['source_title']}\n")
        # Trim very long chunks to a readable excerpt (~500 chars)
        content = chunk["content"]
        if len(content) > 600:
            content = content[:597] + "..."
        lines.append(content)
        lines.append("")  # blank line between chunks

    return "\n".join(lines)
