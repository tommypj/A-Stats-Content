"""
Google Gemini Flash adapter for SERP analysis and research.

Uses Google Search grounding to retrieve real data — eliminates hallucinated
statistics by grounding all responses in live Google Search results.
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field

from infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class SERPAnalysis:
    """Structured result from analyzing Google SERP for a keyword."""

    top_headings: list[str] = field(default_factory=list)
    avg_word_count: int = 1500
    paa_questions: list[str] = field(default_factory=list)
    content_gaps: list[str] = field(default_factory=list)
    competing_titles: list[str] = field(default_factory=list)


@dataclass
class ResearchData:
    """Real facts and statistics sourced from Google Search."""

    key_facts: list[str] = field(default_factory=list)     # "Fact sentence. (source.com)"
    statistics: list[str] = field(default_factory=list)    # "X% stat with source. (source.com)"
    related_topics: list[str] = field(default_factory=list)


class GeminiFlashService:
    """Google Gemini Flash service for SERP analysis and research with Google Search grounding."""

    def __init__(self) -> None:
        self._genai = None
        self._model_name = settings.gemini_model

        if not settings.gemini_api_key:
            logger.info("GEMINI_API_KEY not set — Gemini SERP/research steps will be skipped")
            return

        try:
            import google.generativeai as genai  # type: ignore[import]

            genai.configure(api_key=settings.gemini_api_key)
            self._genai = genai
            logger.info("Gemini Flash service initialized (model: %s)", self._model_name)
        except ImportError:
            logger.warning(
                "google-generativeai package not installed — Gemini steps will be skipped. "
                "Run: pip install google-generativeai"
            )

    def is_available(self) -> bool:
        """Return True if Gemini is configured and the package is installed."""
        return self._genai is not None

    def _strip_code_fences(self, text: str) -> str:
        """Strip markdown code fences from response text."""
        text = re.sub(r"^```(?:json)?\s*", "", text.strip())
        text = re.sub(r"\s*```$", "", text.strip())
        return text.strip()

    def _call_sync(self, prompt: str, max_tokens: int = 2048) -> str:
        """Synchronous Gemini call with Google Search grounding (run in executor)."""
        genai = self._genai
        model = genai.GenerativeModel(
            model_name=self._model_name,
            tools=["google_search_retrieval"],
        )
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.1,
                max_output_tokens=max_tokens,
            ),
        )
        return response.text

    async def _call_with_grounding(self, prompt: str, max_tokens: int = 2048) -> str:
        """Async wrapper: runs sync Gemini SDK call in a thread pool executor."""
        loop = asyncio.get_running_loop()
        text = await loop.run_in_executor(
            None,
            lambda: self._call_sync(prompt, max_tokens),
        )
        return self._strip_code_fences(text)

    async def analyze_serp(self, keyword: str, language: str = "en") -> SERPAnalysis:
        """Analyze Google SERP for a keyword using Gemini with Search grounding."""
        if not self.is_available():
            return SERPAnalysis()

        prompt = f"""Search Google for: "{keyword}"

Analyze the top 10 search results and return a JSON object with this exact structure:
{{
  "top_headings": ["heading 1", "heading 2"],
  "avg_word_count": 1500,
  "paa_questions": ["question 1", "question 2"],
  "content_gaps": ["gap 1", "gap 2"],
  "competing_titles": ["title 1", "title 2"]
}}

- top_headings: the most common H2/H3 headings used across top results (max 12)
- avg_word_count: estimated average word count of top results
- paa_questions: "People Also Ask" questions from the SERP (max 8)
- content_gaps: topics the top results miss or undercover (max 5)
- competing_titles: actual article titles from top results (max 5)

Return ONLY valid JSON, no markdown fences, no explanation. Language context: {language}"""

        try:
            raw = await asyncio.wait_for(
                self._call_with_grounding(prompt, max_tokens=1024),
                timeout=20.0,
            )
            data = json.loads(raw)
            return SERPAnalysis(
                top_headings=data.get("top_headings", []),
                avg_word_count=int(data.get("avg_word_count", 1500)),
                paa_questions=data.get("paa_questions", []),
                content_gaps=data.get("content_gaps", []),
                competing_titles=data.get("competing_titles", []),
            )
        except Exception as e:
            logger.warning("Gemini SERP analysis failed for '%s': %s", keyword, e)
            return SERPAnalysis()

    async def research_topic(self, keyword: str, language: str = "en") -> ResearchData:
        """Research a topic using Gemini with Google Search grounding for real facts and stats."""
        if not self.is_available():
            return ResearchData()

        prompt = f"""Search Google for real facts and statistics about: "{keyword}"

Return a JSON object with this exact structure:
{{
  "key_facts": ["Fact sentence. (source.com)"],
  "statistics": ["X% of Y according to Z. (source.com)"],
  "related_topics": ["topic 1", "topic 2"]
}}

- key_facts: verified factual statements with source domain in parentheses (max 8)
- statistics: real numerical statistics with source domain in parentheses (max 6)
- related_topics: closely related subtopics worth covering (max 6)

Only include facts/stats you found via Google Search. Include the source domain in parentheses.
Return ONLY valid JSON, no markdown fences, no explanation. Language context: {language}"""

        try:
            raw = await asyncio.wait_for(
                self._call_with_grounding(prompt, max_tokens=1024),
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

        prompt = f"""Analyze this article content against top SERP competitors.

Top competitor headings:
{headings_list}

People Also Ask questions:
{paa_list}

Article content (first 3000 chars):
{content[:3000]}

Return a JSON object:
{{
  "covers_top_headings": true,
  "addresses_paa": true,
  "word_count_adequate": true,
  "missing_topics": ["topic 1"],
  "serp_alignment_score": 85
}}

- covers_top_headings: does the article cover most of the top competitor headings?
- addresses_paa: does the article answer the PAA questions?
- word_count_adequate: is the article length competitive vs avg_word_count?
- missing_topics: key topics the article should add (max 3)
- serp_alignment_score: 0-100 score for SERP alignment

Return ONLY valid JSON, no markdown fences."""

        try:
            raw = await asyncio.wait_for(
                self._call_with_grounding(prompt, max_tokens=512),
                timeout=15.0,
            )
            return json.loads(raw)
        except Exception as e:
            logger.warning("Gemini SEO vs SERP analysis failed: %s", e)
            return {}


# Module-level singleton
gemini_service = GeminiFlashService()
