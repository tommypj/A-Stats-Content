"""
Mixed AI Content Generation Pipeline.

Orchestrates a 10-step self-correcting multi-model pipeline:
  1. SERP Analysis     → Gemini Flash 2.5 (Google Search grounding)
  2. Research          → Gemini Flash 2.5 (Google Search grounding)
     Steps 1+2 run in parallel, cached in Redis (24h TTL)
  3. Outline           → GPT-4o mini (Structured Outputs, fallback: Claude)
     Quality tier assigned (A/B/C). SERP gap coverage validated.
  4. Article           → Claude Sonnet 4.6 (publication-quality prose)
  5. SEO vs SERP check → Gemini Flash (lightweight)
  6. Fact-check        → Claude Haiku 4.5 (lightweight)
  7. Image prompt      → Claude Sonnet 4.6 (lightweight)
     Steps 5-7 run in parallel
  8. SEO repair loop   → Claude Sonnet 4.6 (section-level regeneration)
  9. Fact-check repair → Claude Haiku 4.5 (auto-fix flagged claims)
  10. Schema generation → Pure code (Article + FAQPage JSON-LD)

Graceful degradation: if Gemini or OpenAI keys are absent, the pipeline
falls back to the all-Claude path transparently.

Run metadata (per-step latency, cache hits, quality tier, prompt versions)
is recorded on every pipeline run for debugging and optimization.
"""

import asyncio
import dataclasses
import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field

from adapters.ai.anthropic_adapter import GeneratedArticle, GeneratedOutline, content_ai_service
from adapters.ai.gemini_adapter import ResearchData, SERPAnalysis, gemini_service
from adapters.ai.openai_adapter import openai_outline_service
from infrastructure.config.settings import settings
from prompts.loader import prompt_loader
from services.schema_generator import generate_schemas

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class StepMetrics:
    """Metrics for a single pipeline step."""

    model: str = ""
    latency_ms: int = 0
    cached: bool = False


@dataclass
class PipelineRunMetadata:
    """Operational metadata for a full pipeline run."""

    steps: dict[str, StepMetrics] = field(default_factory=dict)
    total_latency_ms: int = 0
    cache_hits: int = 0
    fact_check_flags: int = 0
    seo_alignment_score: int | None = None
    quality_tier: str = "A"  # A=full, B=claude-outline-fallback, C=full-claude
    prompt_versions: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "steps": {k: dataclasses.asdict(v) for k, v in self.steps.items()},
            "total_latency_ms": self.total_latency_ms,
            "cache_hits": self.cache_hits,
            "fact_check_flags": self.fact_check_flags,
            "seo_alignment_score": self.seo_alignment_score,
            "quality_tier": self.quality_tier,
            "prompt_versions": self.prompt_versions,
        }


@dataclass
class PipelineResult:
    """Full result from running the content generation pipeline."""

    outline: GeneratedOutline
    article: GeneratedArticle
    serp_analysis: SERPAnalysis | None = None
    research_data: ResearchData | None = None
    image_prompt: str | None = None
    flagged_stats: list[str] = field(default_factory=list)
    serp_seo: dict = field(default_factory=dict)
    models_used: dict[str, str] = field(default_factory=dict)
    url_slug: str | None = None
    schemas: dict = field(default_factory=dict)
    run_metadata: PipelineRunMetadata = field(default_factory=PipelineRunMetadata)


# ---------------------------------------------------------------------------
# SERP/Research Redis cache helpers (24h TTL)
# ---------------------------------------------------------------------------

_SERP_CACHE_TTL = 86400  # 24 hours

from infrastructure.redis import get_redis_text


async def _get_redis_pool():
    """Return the shared Redis text connection pool."""
    return await get_redis_text()


def _serp_cache_key(prefix: str, keyword: str, language: str) -> str:
    h = hashlib.sha256(f"{keyword.lower().strip()}:{language}".encode()).hexdigest()[:16]
    return f"serp_cache:{prefix}:{h}"


async def _cache_get(key: str) -> dict | None:
    try:
        r = await _get_redis_pool()
        if r is None:
            return None
        raw = await r.get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return None


async def _cache_set(key: str, data: dict) -> None:
    try:
        r = await _get_redis_pool()
        if r is None:
            return
        await r.setex(key, _SERP_CACHE_TTL, json.dumps(data))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Shared helper (moved here from admin_blog.py to avoid duplication)
# ---------------------------------------------------------------------------


def _extract_flagged_stats(html: str) -> list[str]:
    """Scan generated HTML for statistical claims that need editorial verification."""
    plain = re.sub(r"<[^>]+>", " ", html)
    plain = re.sub(r"\s+", " ", plain).strip()

    flagged: list[str] = []

    # Percentage with parenthetical citation — "X% (Source, Year)"
    for m in re.finditer(r"([^.]*?\d+(?:\.\d+)?%\s*\([^)]{2,60}\)[^.]*\.?)", plain):
        flagged.append(m.group(1).strip())

    # "N in N" or "N out of N" ratio claims near a parenthetical
    for m in re.finditer(
        r"([^.]*?\d+\s+(?:in|out of)\s+\d+[^.]*\([^)]{2,60}\)[^.]*\.?)", plain
    ):
        flagged.append(m.group(1).strip())

    # Anything the AI self-tagged with [VERIFY]
    for m in re.finditer(r"([^.]*?\[VERIFY\][^.]*\.?)", plain):
        flagged.append(m.group(1).strip())

    # Deduplicate preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for item in flagged:
        normalized = re.sub(r"\s+", " ", item).strip()
        if normalized not in seen:
            seen.add(normalized)
            unique.append(normalized)
    return unique


# ---------------------------------------------------------------------------
# Pipeline class
# ---------------------------------------------------------------------------


class ContentPipeline:
    """Orchestrates the multi-model content generation pipeline."""

    async def _get_outline(
        self,
        keyword: str,
        serp_analysis: SERPAnalysis | None,
        research_data: ResearchData | None,
        tone: str,
        target_audience: str | None,
        word_count_target: int,
        language: str,
        writing_style: str,
        voice: str,
        list_usage: str,
        custom_instructions: str | None,
        secondary_keywords: list[str] | None = None,
        entities: list[str] | None = None,
    ) -> tuple[GeneratedOutline, str]:
        """Generate outline via OpenAI (Structured Outputs), falling back to Claude on error.

        Returns (outline, model_name_used).
        """
        if openai_outline_service.is_available():
            try:
                outline = await asyncio.wait_for(
                    openai_outline_service.generate_outline(
                        keyword=keyword,
                        serp_analysis=serp_analysis,
                        research_data=research_data,
                        tone=tone,
                        target_audience=target_audience,
                        word_count_target=word_count_target,
                        language=language,
                        writing_style=writing_style,
                        voice=voice,
                        list_usage=list_usage,
                        custom_instructions=custom_instructions,
                        secondary_keywords=secondary_keywords,
                        entities=entities,
                    ),
                    timeout=60.0,
                )
                logger.info("Outline generated via OpenAI (%s)", settings.openai_outline_model)
                return outline, settings.openai_outline_model
            except Exception as e:
                logger.warning(
                    "OpenAI outline failed (%s), falling back to Claude: %s", type(e).__name__, e
                )

        # Claude fallback
        outline = await content_ai_service.generate_outline(
            keyword=keyword,
            target_audience=target_audience,
            tone=tone,
            word_count_target=word_count_target,
            language=language,
            writing_style=writing_style,
            voice=voice,
            list_usage=list_usage,
            custom_instructions=custom_instructions,
            secondary_keywords=secondary_keywords,
            entities=entities,
        )
        logger.info("Outline generated via Claude (fallback)")
        return outline, settings.anthropic_model

    async def run_full_pipeline(
        self,
        keyword: str,
        title: str,
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
    ) -> PipelineResult:
        """Run the full 6-step multi-model pipeline.

        Steps 1+2 run in parallel (Gemini SERP + research, with Redis cache).
        Step 3: outline via OpenAI (fallback Claude).
        Step 4: article via Claude (enriched with research context).
        Steps 5+6+7 run in parallel (SERP SEO check + AI fact-check + image prompt).
        """
        models_used: dict[str, str] = {}
        run_meta = PipelineRunMetadata()
        pipeline_start = time.monotonic()

        # ----------------------------------------------------------------
        # Steps 1 + 2: SERP analysis + research (parallel, both Gemini)
        # Redis cache (24h TTL) avoids repeat Gemini calls for same keyword.
        # ----------------------------------------------------------------
        serp_analysis: SERPAnalysis | None = None
        research_data: ResearchData | None = None

        serp_start = time.monotonic()
        if gemini_service.is_available() and settings.enable_serp_analysis:
            serp_key = _serp_cache_key("serp", keyword, language)
            research_key = _serp_cache_key("research", keyword, language)

            serp_cached, research_cached = await asyncio.gather(
                _cache_get(serp_key), _cache_get(research_key)
            )

            if serp_cached:
                try:
                    serp_analysis = SERPAnalysis(**serp_cached)
                    logger.info("SERP cache hit for '%s' [%s]", keyword, language)
                    models_used["serp"] = "cache"
                except Exception:
                    serp_cached = None

            if research_cached:
                try:
                    research_data = ResearchData(**research_cached)
                    logger.info("Research cache hit for '%s' [%s]", keyword, language)
                    models_used["research"] = "cache"
                except Exception:
                    research_cached = None

            gemini_tasks: list[tuple[str, object]] = []
            if not serp_cached and settings.enable_serp_analysis:
                gemini_tasks.append(("serp", gemini_service.analyze_serp(keyword, language)))
            if not research_cached and settings.enable_research_step:
                gemini_tasks.append(("research", gemini_service.research_topic(keyword, language)))

            if gemini_tasks:
                results = await asyncio.gather(*[t[1] for t in gemini_tasks], return_exceptions=True)
                for (name, _), result in zip(gemini_tasks, results):
                    if name == "serp" and isinstance(result, SERPAnalysis):
                        serp_analysis = result
                        models_used["serp"] = settings.gemini_model
                        if result.top_headings:
                            await _cache_set(serp_key, dataclasses.asdict(result))
                    elif name == "research" and isinstance(result, ResearchData):
                        research_data = result
                        models_used["research"] = settings.gemini_model
                        if result.key_facts or result.statistics:
                            await _cache_set(research_key, dataclasses.asdict(result))

        serp_ms = int((time.monotonic() - serp_start) * 1000)
        if models_used.get("serp") == "cache":
            run_meta.cache_hits += 1
            run_meta.steps["serp"] = StepMetrics(model="cache", latency_ms=serp_ms, cached=True)
        elif "serp" in models_used:
            run_meta.steps["serp"] = StepMetrics(model=models_used["serp"], latency_ms=serp_ms)
        if models_used.get("research") == "cache":
            run_meta.cache_hits += 1
            run_meta.steps["research"] = StepMetrics(model="cache", latency_ms=serp_ms, cached=True)
        elif "research" in models_used:
            run_meta.steps["research"] = StepMetrics(model=models_used["research"], latency_ms=serp_ms)

        # ----------------------------------------------------------------
        # Step 3: Outline generation
        # ----------------------------------------------------------------
        outline_start = time.monotonic()
        outline, outline_model = await self._get_outline(
            keyword=keyword,
            serp_analysis=serp_analysis,
            research_data=research_data,
            tone=tone,
            target_audience=target_audience,
            word_count_target=word_count_target,
            language=language,
            writing_style=writing_style,
            voice=voice,
            list_usage=list_usage,
            custom_instructions=custom_instructions,
            secondary_keywords=secondary_keywords,
            entities=entities,
        )
        models_used["outline"] = outline_model
        run_meta.steps["outline"] = StepMetrics(
            model=outline_model,
            latency_ms=int((time.monotonic() - outline_start) * 1000),
        )

        # Determine quality tier
        has_gemini = "serp" in models_used and models_used["serp"] != "cache"
        has_openai_outline = outline_model == settings.openai_outline_model
        if has_gemini and has_openai_outline:
            run_meta.quality_tier = "A"  # Full pipeline
        elif has_openai_outline or has_gemini:
            run_meta.quality_tier = "B"  # Partial fallback
        else:
            run_meta.quality_tier = "C"  # Full Claude fallback

        # Validate SERP gap coverage in outline — log warning if gaps are missed
        if serp_analysis and serp_analysis.content_gaps:
            outline_text = " ".join(s.heading.lower() + " " + s.notes.lower() for s in outline.sections)
            covered = sum(
                1 for gap in serp_analysis.content_gaps[:3]
                if any(word in outline_text for word in gap.lower().split() if len(word) > 4)
            )
            if covered == 0:
                logger.warning(
                    "Outline covers 0/%d SERP content gaps — article may miss competitive advantage",
                    min(3, len(serp_analysis.content_gaps)),
                )

        # ----------------------------------------------------------------
        # Step 4: Article generation (Claude) — enriched with research
        # ----------------------------------------------------------------
        enriched_instructions = custom_instructions or ""
        if research_data and (research_data.key_facts or research_data.statistics):
            facts_block = ""
            if research_data.key_facts:
                facts_block += "\n\nVerified facts to incorporate naturally:\n" + "\n".join(
                    f"- {f}" for f in research_data.key_facts[:6]
                )
            if research_data.statistics:
                facts_block += "\n\nReal statistics to cite (include the source):\n" + "\n".join(
                    f"- {s}" for s in research_data.statistics[:5]
                )
            if facts_block:
                enriched_instructions = (
                    (enriched_instructions + "\n\n" if enriched_instructions else "")
                    + "RESEARCH DATA (sourced from Google Search — use these in the article):"
                    + facts_block
                )

        sections = [
            {
                "heading": s.heading,
                "subheadings": s.subheadings,
                "notes": s.notes,
                "word_count_target": s.word_count_target,
            }
            for s in outline.sections
        ]

        article_start = time.monotonic()
        article = await content_ai_service.generate_article(
            title=title or outline.title,
            keyword=keyword,
            sections=sections,
            tone=tone,
            target_audience=target_audience,
            writing_style=writing_style,
            voice=voice,
            list_usage=list_usage,
            custom_instructions=enriched_instructions or None,
            word_count_target=word_count_target,
            language=language,
            secondary_keywords=secondary_keywords,
            entities=entities,
        )
        models_used["article"] = settings.anthropic_model
        run_meta.steps["article"] = StepMetrics(
            model=settings.anthropic_model,
            latency_ms=int((time.monotonic() - article_start) * 1000),
        )

        # ----------------------------------------------------------------
        # Steps 5 + 6 + 7: SEO check, fact-check, image prompt (parallel)
        # ----------------------------------------------------------------
        async def _seo_check() -> dict:
            if serp_analysis:
                try:
                    return await gemini_service.analyze_seo_vs_serp(article.content, serp_analysis)
                except Exception as e:
                    logger.warning("SERP SEO check failed: %s", e)
            return {}

        async def _fact_check() -> list[str]:
            try:
                return await asyncio.wait_for(
                    content_ai_service.fact_check_content(article.content),
                    timeout=30.0,
                )
            except Exception as e:
                logger.warning("AI fact-check failed: %s", e)
                return []

        async def _image_prompt() -> str | None:
            try:
                return await asyncio.wait_for(
                    content_ai_service.generate_image_prompt(
                        title=title or outline.title,
                        content=article.content,
                        keyword=keyword,
                    ),
                    timeout=30.0,
                )
            except Exception as e:
                logger.warning("Image prompt generation failed: %s", e)
                return None

        serp_seo, ai_flags, image_prompt = await asyncio.gather(
            _seo_check(), _fact_check(), _image_prompt()
        )

        # Merge regex + AI flagged stats, deduplicate
        import markdown as _md

        content_html = _md.markdown(article.content, extensions=["extra"])
        regex_flags = _extract_flagged_stats(content_html)

        seen: set[str] = {re.sub(r"\s+", " ", s).strip() for s in regex_flags}
        flagged_stats = list(regex_flags)
        for claim in ai_flags:
            normalized = re.sub(r"\s+", " ", claim).strip()
            if normalized not in seen:
                seen.add(normalized)
                flagged_stats.append(claim)

        if serp_seo:
            models_used["seo_check"] = settings.gemini_model

        # ----------------------------------------------------------------
        # Step 8: SEO repair loop — regenerate sections for missing topics
        # ----------------------------------------------------------------
        missing_topics: list[str] = serp_seo.get("missing_topics", []) if serp_seo else []
        if missing_topics and outline.sections:
            try:
                # Find the best section to regenerate (last body section before FAQ/conclusion)
                body_sections = [
                    s for s in outline.sections
                    if not any(
                        kw in s.heading.lower()
                        for kw in ["faq", "frequently asked", "conclusion"]
                    )
                ]
                target_section = (
                    body_sections[-1]
                    if body_sections
                    else outline.sections[-2] if len(outline.sections) >= 2 else outline.sections[-1]
                )
                reason = f"SEO gap — cover missing topics: {', '.join(missing_topics[:3])}"

                repaired_article = await asyncio.wait_for(
                    content_ai_service.regenerate_section(
                        full_content=article.content,
                        section_heading=target_section.heading,
                        keyword=keyword,
                        tone=tone,
                        section_word_target=target_section.word_count_target,
                        reason=reason,
                        writing_style=writing_style,
                        voice=voice,
                        list_usage=list_usage,
                        language=language,
                    ),
                    timeout=60.0,
                )
                if repaired_article != article.content:
                    article = GeneratedArticle(
                        title=article.title,
                        content=repaired_article,
                        meta_description=article.meta_description,
                        word_count=len(repaired_article.split()),
                        url_slug=article.url_slug,
                    )
                    models_used["seo_repair"] = settings.anthropic_model
                    logger.info(
                        "SEO repair applied — section '%s' regenerated for %d missing topics",
                        target_section.heading,
                        len(missing_topics),
                    )
            except Exception as e:
                logger.warning("SEO repair loop failed, using original: %s", e)

        # ----------------------------------------------------------------
        # Step 9: Fact-check repair pass (auto-fix flagged claims)
        # ----------------------------------------------------------------
        if flagged_stats:
            try:
                repaired_content = await asyncio.wait_for(
                    content_ai_service.repair_flagged_claims(
                        content=article.content,
                        flagged_claims=flagged_stats,
                    ),
                    timeout=60.0,
                )
                if repaired_content != article.content:
                    article = GeneratedArticle(
                        title=article.title,
                        content=repaired_content,
                        meta_description=article.meta_description,
                        word_count=len(repaired_content.split()),
                        url_slug=article.url_slug,
                    )
                    models_used["fact_repair"] = settings.anthropic_haiku_model
                    logger.info(
                        "Fact-check repair applied (%d claims fixed)", len(flagged_stats)
                    )
            except Exception as e:
                logger.warning("Fact-check repair failed, using original: %s", e)

        # ----------------------------------------------------------------
        # Step 10: Generate structured data schemas (Article + FAQPage)
        # ----------------------------------------------------------------
        schemas = generate_schemas(
            content=article.content,
            title=title or outline.title,
            meta_description=article.meta_description,
            keyword=keyword,
            word_count=article.word_count,
            language=language,
        )

        # Finalize run metadata
        run_meta.total_latency_ms = int((time.monotonic() - pipeline_start) * 1000)
        run_meta.fact_check_flags = len(flagged_stats)
        run_meta.seo_alignment_score = serp_seo.get("serp_alignment_score") if serp_seo else None
        run_meta.prompt_versions = {
            name: prompt_loader.get_version(name)
            for name in [
                "article_system", "article_generation", "outline_openai",
                "outline_claude", "fact_check", "serp_analysis", "research",
            ]
            if name in prompt_loader._get_manifest()["prompts"]
        }

        return PipelineResult(
            outline=outline,
            article=article,
            serp_analysis=serp_analysis,
            research_data=research_data,
            image_prompt=image_prompt,
            flagged_stats=flagged_stats,
            serp_seo=serp_seo,
            models_used=models_used,
            url_slug=article.url_slug or None,
            schemas=schemas,
            run_metadata=run_meta,
        )

    async def run_outline_only(
        self,
        keyword: str,
        tone: str = "professional",
        target_audience: str | None = None,
        word_count_target: int = 1500,
        language: str = "en",
        writing_style: str = "balanced",
        voice: str = "second_person",
        list_usage: str = "balanced",
        custom_instructions: str | None = None,
        with_serp: bool = False,
        secondary_keywords: list[str] | None = None,
        entities: list[str] | None = None,
    ) -> GeneratedOutline:
        """Generate an outline only (used by bulk generation).

        with_serp=False (default) skips Gemini steps for speed.
        with_serp=True runs full SERP+research enrichment first.
        """
        serp_analysis: SERPAnalysis | None = None
        research_data: ResearchData | None = None

        if with_serp and gemini_service.is_available() and settings.enable_serp_analysis:
            results = await asyncio.gather(
                gemini_service.analyze_serp(keyword, language),
                gemini_service.research_topic(keyword, language),
                return_exceptions=True,
            )
            if isinstance(results[0], SERPAnalysis):
                serp_analysis = results[0]
            if isinstance(results[1], ResearchData):
                research_data = results[1]

        outline, _ = await self._get_outline(
            keyword=keyword,
            serp_analysis=serp_analysis,
            research_data=research_data,
            tone=tone,
            target_audience=target_audience,
            word_count_target=word_count_target,
            language=language,
            writing_style=writing_style,
            voice=voice,
            list_usage=list_usage,
            custom_instructions=custom_instructions,
            secondary_keywords=secondary_keywords,
            entities=entities,
        )
        return outline

    async def generate_content_cluster(
        self,
        keyword: str,
        target_audience: str | None = None,
        language: str = "en",
    ) -> dict:
        """Generate a topical authority cluster plan for a pillar keyword.

        Returns a dict with 'pillar' and 'supporting_articles' keys.
        Each entry has title, keyword, word_count_target, and description.
        """
        return await content_ai_service.generate_content_cluster(
            keyword=keyword,
            target_audience=target_audience,
            language=language,
        )


# Module-level singleton
content_pipeline = ContentPipeline()
