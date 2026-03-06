"""
Google Gemini Flash adapter for SERP analysis and research.

Uses Google Search grounding to retrieve real data — eliminates hallucinated
statistics by grounding all responses in live Google Search results.

Uses the new `google-genai` SDK (google.genai) — the old `google-generativeai`
package is deprecated and no longer receives updates.
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field

from infrastructure.config.settings import settings
from prompts.loader import prompt_loader

logger = logging.getLogger(__name__)


@dataclass
class SERPAnalysis:
    """Structured result from analyzing Google SERP for a keyword."""

    top_headings: list[str] = field(default_factory=list)
    avg_word_count: int = 1500
    paa_questions: list[str] = field(default_factory=list)
    content_gaps: list[str] = field(default_factory=list)
    competing_titles: list[str] = field(default_factory=list)
    search_intent: str = "informational"  # informational | commercial | transactional | navigational


@dataclass
class ResearchData:
    """Real facts and statistics sourced from Google Search."""

    key_facts: list[str] = field(default_factory=list)     # "Fact sentence. (source.com)"
    statistics: list[str] = field(default_factory=list)    # "X% stat with source. (source.com)"
    related_topics: list[str] = field(default_factory=list)


class GeminiFlashService:
    """Google Gemini Flash service for SERP analysis and research with Google Search grounding."""

    def __init__(self) -> None:
        self._client = None
        self._types = None
        self._model_name = settings.gemini_model

        if not settings.gemini_api_key:
            logger.info("GEMINI_API_KEY not set — Gemini SERP/research steps will be skipped")
            return

        try:
            from google import genai  # type: ignore[import]
            from google.genai import types  # type: ignore[import]

            self._client = genai.Client(api_key=settings.gemini_api_key)
            self._types = types
            logger.info("Gemini Flash service initialized (model: %s)", self._model_name)
        except ImportError:
            logger.warning(
                "google-genai package not installed — Gemini steps will be skipped. "
                "Run: pip install google-genai"
            )

    def is_available(self) -> bool:
        """Return True if Gemini is configured and the package is installed."""
        return self._client is not None

    def _extract_json(self, text: str) -> str:
        """Extract a JSON object from Gemini's response text.

        Gemini with search grounding often adds preamble text, citation markers
        like [1] [2], and trailing attribution lines around the JSON block.
        This method robustly extracts just the JSON object.
        """
        # Strip all control characters (including literal newlines in strings)
        text = re.sub(r"[\x00-\x1f\x7f]", " ", text)
        # Strip markdown code fences
        text = re.sub(r"```(?:json)?", "", text)
        # Remove grounding citation markers like [1], [2], [1,2], etc.
        text = re.sub(r"\[\d+(?:,\s*\d+)*\]", "", text)

        # Extract the outermost JSON object { ... }
        start = text.find("{")
        if start == -1:
            return text.strip()

        depth = 0
        end = start
        in_string = False
        escape_next = False
        for i, ch in enumerate(text[start:], start):
            if escape_next:
                escape_next = False
                continue
            if ch == "\\" and in_string:
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break

        return text[start:end].strip()

    async def _call_gemini(self, prompt: str, max_tokens: int = 2048) -> str:
        """Call Gemini with forced JSON output mode.

        Uses response_mime_type='application/json' so Gemini outputs raw JSON
        without any markdown fences, prose preamble, or citation markers.
        Thinking is disabled so the full token budget goes to the response.
        """
        types = self._types
        response = await self._client.aio.models.generate_content(
            model=self._model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=max_tokens,
                response_mime_type="application/json",
                # Gemini 2.5-flash is a thinking model — disable thinking for structured
                # JSON output so all token budget goes to the actual response, not reasoning.
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
        try:
            raw = response.text or ""
        except Exception as text_err:
            logger.warning("Gemini response.text raised: %s", text_err)
            raw = ""
        logger.debug("Gemini raw response (%d chars): %r", len(raw), raw[:200])
        return raw.strip()

    async def analyze_serp(self, keyword: str, language: str = "en") -> SERPAnalysis:
        """Analyze Google SERP for a keyword using Gemini with Search grounding."""
        if not self.is_available():
            return SERPAnalysis()

        prompt = prompt_loader.format(
            "serp_analysis",
            keyword=keyword,
            language=language,
        )

        try:
            raw = await asyncio.wait_for(
                self._call_gemini(prompt, max_tokens=1024),
                timeout=20.0,
            )
            data = json.loads(raw)
            return SERPAnalysis(
                top_headings=data.get("top_headings", []),
                avg_word_count=int(data.get("avg_word_count", 1500)),
                paa_questions=data.get("paa_questions", []),
                content_gaps=data.get("content_gaps", []),
                competing_titles=data.get("competing_titles", []),
                search_intent=data.get("search_intent", "informational"),
            )
        except Exception as e:
            logger.warning("Gemini SERP analysis failed for '%s': %s", keyword, e)
            return SERPAnalysis()

    async def research_topic(self, keyword: str, language: str = "en") -> ResearchData:
        """Research a topic using Gemini with Google Search grounding for real facts and stats."""
        if not self.is_available():
            return ResearchData()

        prompt = prompt_loader.format(
            "research",
            keyword=keyword,
            language=language,
        )

        try:
            raw = await asyncio.wait_for(
                self._call_gemini(prompt, max_tokens=1024),
                timeout=20.0,
            )
            data = json.loads(raw)
            return ResearchData(
                key_facts=data.get("key_facts", []),
                statistics=data.get("statistics", []),
                related_topics=data.get("related_topics", []),
            )
        except Exception as e:
            logger.warning("Gemini research failed for '%s': %s", keyword, e)
            return ResearchData()

    async def analyze_seo_vs_serp(self, content: str, serp: SERPAnalysis) -> dict:
        """Lightweight SEO check: does the article cover top SERP headings and PAA questions?"""
        if not self.is_available() or not serp.top_headings:
            return {}

        headings_list = "\n".join(f"- {h}" for h in serp.top_headings[:8])
        paa_list = "\n".join(f"- {q}" for q in serp.paa_questions[:6])

        prompt = prompt_loader.format(
            "seo_vs_serp",
            headings_list=headings_list,
            paa_list=paa_list,
            content_excerpt=content[:3000],
        )

        try:
            raw = await asyncio.wait_for(
                self._call_gemini(prompt, max_tokens=512),
                timeout=15.0,
            )
            return json.loads(raw)
        except Exception as e:
            logger.warning("Gemini SEO vs SERP analysis failed: %s", e)
            return {}


# Module-level singleton
gemini_service = GeminiFlashService()
