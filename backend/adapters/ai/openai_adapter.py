"""
OpenAI adapter for structured outline generation using GPT-4o mini.

Uses Structured Outputs (response_format=BaseModel) to guarantee valid JSON schema
and produce consistently well-structured article outlines.
"""

import logging
from typing import Any

from pydantic import BaseModel

from adapters.ai.anthropic_adapter import GeneratedOutline, OutlineSection
from infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic schemas for OpenAI Structured Outputs
# ---------------------------------------------------------------------------


class OutlineSectionSchema(BaseModel):
    heading: str
    subheadings: list[str]
    notes: str
    word_count_target: int


class GeneratedOutlineSchema(BaseModel):
    title: str
    sections: list[OutlineSectionSchema]
    meta_description: str
    estimated_word_count: int
    estimated_read_time: int


# ---------------------------------------------------------------------------
# Service class
# ---------------------------------------------------------------------------


class OpenAIOutlineService:
    """OpenAI GPT-4o mini service for structured outline generation."""

    def __init__(self) -> None:
        self._client = None
        self._model = settings.openai_outline_model

        if not settings.openai_api_key:
            logger.info("OPENAI_API_KEY not set — OpenAI outline step will fall back to Claude")
            return

        try:
            from openai import AsyncOpenAI  # type: ignore[import]

            self._client = AsyncOpenAI(api_key=settings.openai_api_key)
            logger.info("OpenAI outline service initialized (model: %s)", self._model)
        except ImportError:
            logger.warning("openai package not installed — outline will fall back to Claude")

    def is_available(self) -> bool:
        """Return True if OpenAI client is configured."""
        return self._client is not None

    async def generate_outline(
        self,
        keyword: str,
        serp_analysis: Any | None = None,
        research_data: Any | None = None,
        tone: str = "professional",
        target_audience: str | None = None,
        word_count_target: int = 1500,
        language: str = "en",
        writing_style: str = "balanced",
        voice: str = "second_person",
        list_usage: str = "balanced",
        custom_instructions: str | None = None,
        secondary_keywords: list[str] | None = None,
        entities: list[str] | None = None,
    ) -> GeneratedOutline:
        """Generate a structured outline using GPT-4o mini with Structured Outputs.

        Raises RuntimeError if OpenAI client is not available (caller should fallback).
        """
        if not self.is_available():
            raise RuntimeError("OpenAI client not available")

        # Build SERP context block
        serp_block = ""
        if serp_analysis and (serp_analysis.top_headings or serp_analysis.paa_questions):
            headings = "\n".join(f"  - {h}" for h in serp_analysis.top_headings[:10])
            paa = "\n".join(f"  - {q}" for q in serp_analysis.paa_questions[:6])
            gaps = "\n".join(f"  - {g}" for g in serp_analysis.content_gaps[:5])
            serp_block = (
                f"\nSERP Intelligence (from live Google Search):\n"
                f"- Search intent: {serp_analysis.search_intent}\n"
                f"- Top competitor headings:\n{headings}\n"
                f"- People Also Ask questions:\n{paa}\n"
                f"- Content gaps to exploit:\n{gaps}\n"
                f"- Target word count based on SERP: ~{serp_analysis.avg_word_count} words\n"
            )

        # Build research context block
        research_block = ""
        if research_data and (research_data.key_facts or research_data.statistics):
            facts = "\n".join(f"  - {f}" for f in research_data.key_facts[:6])
            stats = "\n".join(f"  - {s}" for s in research_data.statistics[:5])
            research_block = (
                f"\nResearch data (from live Google Search):\n"
                f"- Key facts to incorporate:\n{facts}\n"
                f"- Real statistics to use:\n{stats}\n"
            )

        secondary_keywords = secondary_keywords or []
        entities = entities or []

        audience_line = f"Target audience: {target_audience}" if target_audience else ""
        custom_line = (
            f"\nAdditional instructions: {custom_instructions}" if custom_instructions else ""
        )
        secondary_kw_line = (
            f"\nSecondary keywords to cover naturally: {', '.join(secondary_keywords[:10])}"
            if secondary_keywords else ""
        )
        entities_line = (
            f"\nKey entities to integrate naturally: {', '.join(entities[:10])}"
            if entities else ""
        )
        search_intent_line = (
            f"\nDetected search intent: {serp_analysis.search_intent}"
            if serp_analysis and hasattr(serp_analysis, "search_intent") else ""
        )

        system_prompt = (
            f"You are an expert content strategist. Generate a comprehensive, "
            f"SEO-optimized article outline.\n\n"
            f"Keyword: {keyword}\n"
            f"Tone: {tone}\n"
            f"{audience_line}\n"
            f"Writing style: {writing_style}\n"
            f"Voice: {voice}\n"
            f"List usage preference: {list_usage}\n"
            f"Word count target: {word_count_target}\n"
            f"Language: {language}\n"
            f"{serp_block}"
            f"{research_block}"
            f"{secondary_kw_line}"
            f"{entities_line}"
            f"{custom_line}\n\n"
            f"Create an outline that:\n"
            f"1. Covers the keyword comprehensively based on SERP data\n"
            f"2. Addresses People Also Ask questions within relevant sections\n"
            f"3. Exploits content gaps that competitors miss\n"
            f"4. Incorporates the research facts naturally within section notes\n"
            f"5. Has sections with realistic word count targets summing to ~{word_count_target} words\n"
            f"6. Matches the detected search intent{search_intent_line}"
        )

        response = await self._client.beta.chat.completions.parse(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Generate a detailed outline for an article about: {keyword}",
                },
            ],
            response_format=GeneratedOutlineSchema,
            temperature=0.4,
            max_tokens=3000,
        )

        parsed = response.choices[0].message.parsed
        if parsed is None:
            raise ValueError("OpenAI returned no parsed response")

        return GeneratedOutline(
            title=parsed.title,
            sections=[
                OutlineSection(
                    heading=s.heading,
                    subheadings=s.subheadings,
                    notes=s.notes,
                    word_count_target=s.word_count_target,
                )
                for s in parsed.sections
            ],
            meta_description=parsed.meta_description,
            estimated_word_count=parsed.estimated_word_count,
            estimated_read_time=parsed.estimated_read_time,
        )


# Module-level singleton
openai_outline_service = OpenAIOutlineService()
