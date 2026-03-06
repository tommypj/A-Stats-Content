"""
Anthropic Claude adapter for AI content generation.
"""

import asyncio
import json
import logging
import random
import re
from dataclasses import dataclass
from typing import Any

import anthropic

from infrastructure.config.settings import settings
from prompts.loader import prompt_loader

logger = logging.getLogger(__name__)


class AIGenerationError(Exception):
    """Raised when the AI model returns an unusable response."""


async def _retry_with_backoff(coro_factory, max_retries=3, base_delay=1.0):
    """Retry an async operation with exponential backoff + jitter."""
    for attempt in range(max_retries + 1):
        try:
            return await coro_factory()
        except Exception as e:
            error_str = str(e).lower()
            is_transient = any(
                k in error_str
                for k in [
                    "rate_limit",
                    "429",
                    "500",
                    "502",
                    "503",
                    "504",
                    "overloaded",
                    "connection",
                    "timeout",
                ]
            )
            if not is_transient or attempt == max_retries:
                raise
            delay = base_delay * (2**attempt) + random.uniform(0, 1)
            logger.warning(
                "Transient API error (attempt %d/%d), retrying in %.1fs: %s",
                attempt + 1,
                max_retries,
                delay,
                str(e),
            )
            await asyncio.sleep(delay)


@dataclass
class OutlineSection:
    """Outline section structure."""

    heading: str
    subheadings: list[str]
    notes: str
    word_count_target: int


@dataclass
class GeneratedOutline:
    """Generated outline result."""

    title: str
    sections: list[OutlineSection]
    meta_description: str
    estimated_word_count: int
    estimated_read_time: int


@dataclass
class GeneratedArticle:
    """Generated article result."""

    title: str
    content: str
    meta_description: str
    word_count: int
    url_slug: str = ""


class AnthropicContentService:
    """AI content generation service using Anthropic Claude."""

    def __init__(self):
        if settings.anthropic_api_key:
            self._client = anthropic.AsyncAnthropic(
                api_key=settings.anthropic_api_key,
                timeout=float(settings.anthropic_timeout),
            )
        else:
            self._client = None
        self._model = settings.anthropic_model
        self._max_tokens = settings.anthropic_max_tokens

    # Language name mapping for clear AI instructions
    LANGUAGE_NAMES = {
        "en": "English",
        "ro": "Romanian (limba română)",
        "es": "Spanish (español)",
        "de": "German (Deutsch)",
        "fr": "French (français)",
        "it": "Italian (italiano)",
        "pt": "Portuguese (português)",
        "nl": "Dutch (Nederlands)",
        "pl": "Polish (polski)",
        "ru": "Russian (русский)",
        "ja": "Japanese (日本語)",
        "ko": "Korean (한국어)",
        "zh": "Chinese (中文)",
        "ar": "Arabic (العربية)",
        "tr": "Turkish (Türkçe)",
        "sv": "Swedish (svenska)",
        "da": "Danish (dansk)",
        "no": "Norwegian (norsk)",
        "fi": "Finnish (suomi)",
        "hu": "Hungarian (magyar)",
        "cs": "Czech (čeština)",
        "bg": "Bulgarian (български)",
    }

    def _get_language_name(self, language_code: str) -> str:
        """Get the full language name from a language code."""
        return self.LANGUAGE_NAMES.get(language_code, language_code)

    def _get_system_prompt(
        self,
        writing_style: str = "balanced",
        voice: str = "second_person",
        list_usage: str = "balanced",
        language: str = "en",
    ) -> str:
        """Get the system prompt for content generation from versioned template."""
        style_instructions = prompt_loader.get_config("writing_styles")
        voice_instructions = prompt_loader.get_config("voice_options")
        list_instructions = prompt_loader.get_config("list_usage")

        language_name = self._get_language_name(language)
        if language != "en":
            language_instruction = (
                f"\nLANGUAGE — THIS IS CRITICAL:\n"
                f"You MUST write the ENTIRE article in {language_name}. Every heading, paragraph, sentence, and meta description must be in {language_name}.\n"
                f"Use native-level grammar, correct gender agreements, proper declensions, and natural idiomatic expressions.\n"
                f"Do NOT mix languages. Do NOT use English words unless they are commonly used loanwords in {language_name}.\n"
                f"Write as a native {language_name} speaker would — with correct syntax, word order, and cultural context.\n"
                f"Before finalizing each paragraph, mentally verify grammar: correct gender agreements, proper case declensions, accurate verb conjugations, and natural word order for {language_name}.\n"
            )
        else:
            language_instruction = "\nLANGUAGE: Write in English.\n"

        return prompt_loader.format(
            "article_system",
            language_instruction=language_instruction,
            style_instruction=style_instructions.get(writing_style, style_instructions["balanced"]),
            voice_instruction=voice_instructions.get(voice, voice_instructions["second_person"]),
            list_instruction=list_instructions.get(list_usage, list_instructions["balanced"]),
        )

    @staticmethod
    def _sanitize_prompt_input(text: str | None, max_length: int) -> str:
        """Strip control characters and limit length to prevent prompt injection."""
        if not text:
            return ""
        import re as _re

        text = _re.sub(r"[\r\n\t\x00-\x1f\x7f]", " ", text)
        text = _re.sub(r" +", " ", text).strip()
        return text[:max_length]

    async def generate_outline(
        self,
        keyword: str,
        target_audience: str | None = None,
        tone: str = "professional",
        word_count_target: int = 1500,
        language: str = "en",
        writing_style: str = "balanced",
        voice: str = "second_person",
        list_usage: str = "balanced",
        custom_instructions: str | None = None,
        secondary_keywords: list[str] | None = None,
        entities: list[str] | None = None,
    ) -> GeneratedOutline:
        """
        Generate an article outline based on keyword and parameters.

        Args:
            keyword: Target SEO keyword
            target_audience: Description of target audience
            tone: Content tone (professional, friendly, empathetic, etc.)
            word_count_target: Target word count for the final article

        Returns:
            GeneratedOutline with structured sections
        """
        if not self._client:
            # Return mock data for development
            return self._mock_outline(keyword, word_count_target)

        # GEN-02: Sanitize all user-supplied inputs before interpolation
        # GEN-34: Cap keyword at 100 chars to prevent oversized prompt interpolation
        keyword = self._sanitize_prompt_input(keyword, 100)
        tone = self._sanitize_prompt_input(tone, 50)
        target_audience = (
            self._sanitize_prompt_input(target_audience, 500) if target_audience else None
        )
        custom_instructions = (
            self._sanitize_prompt_input(custom_instructions, 1000) if custom_instructions else None
        )

        secondary_keywords = [
            self._sanitize_prompt_input(kw, 100) for kw in (secondary_keywords or [])[:10] if kw
        ]
        entities = [
            self._sanitize_prompt_input(e, 100) for e in (entities or [])[:10] if e
        ]

        audience_context = f"Target audience: {target_audience}" if target_audience else ""
        secondary_kw_context = (
            f"\nSecondary keywords to include: {', '.join(secondary_keywords)}" if secondary_keywords else ""
        )
        entities_context = (
            f"\nEntities to mention: {', '.join(entities)}" if entities else ""
        )
        custom_context = (
            f"\nAdditional instructions: {custom_instructions}" if custom_instructions else ""
        )
        language_name = self._get_language_name(language)
        language_context = (
            f"\nLanguage: Write ALL content (title, headings, notes, meta description) in {language_name}."
            if language != "en"
            else ""
        )

        language_name = self._get_language_name(language)
        language_title_hint = f' (in {language_name})' if language != "en" else ""
        language_heading_hint = f' (in {language_name})' if language != "en" else ""
        language_meta_hint = f' (in {language_name})' if language != "en" else ""

        prompt = prompt_loader.format(
            "outline_claude",
            keyword=keyword,
            audience_context=audience_context,
            tone=tone,
            word_count_target=word_count_target,
            language_context=language_context,
            secondary_kw_context=secondary_kw_context,
            entities_context=entities_context,
            custom_context=custom_context,
            language_title_hint=language_title_hint,
            language_heading_hint=language_heading_hint,
            language_meta_hint=language_meta_hint,
        )

        message = await _retry_with_backoff(
            lambda: self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                temperature=0.4,
                system=self._get_system_prompt(
                    writing_style=writing_style,
                    voice=voice,
                    list_usage=list_usage,
                    language=language,
                ),
                messages=[{"role": "user", "content": prompt}],
            )
        )

        # Parse the response
        response_text = message.content[0].text

        # Extract JSON from response (handle markdown code blocks)
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        data = json.loads(response_text.strip())

        sections = [
            OutlineSection(
                heading=s["heading"],
                subheadings=s.get("subheadings", []),
                notes=s.get("notes", ""),
                word_count_target=s.get("word_count_target", 200),
            )
            for s in data.get("sections", [])
        ]

        # GEN-33: cap sections to prevent AI returning excessive counts
        if len(sections) > 20:
            sections = sections[:20]

        return GeneratedOutline(
            title=data.get("title", f"Article about {keyword}"),
            sections=sections,
            meta_description=data.get("meta_description", ""),
            estimated_word_count=data.get("estimated_word_count", word_count_target),
            estimated_read_time=data.get("estimated_read_time", word_count_target // 200),
        )

    async def generate_article(
        self,
        title: str,
        keyword: str,
        sections: list[dict[str, Any]],
        tone: str = "professional",
        target_audience: str | None = None,
        writing_style: str = "balanced",
        voice: str = "second_person",
        list_usage: str = "balanced",
        custom_instructions: str | None = None,
        word_count_target: int = 1500,
        language: str = "en",
        secondary_keywords: list[str] | None = None,
        entities: list[str] | None = None,
    ) -> GeneratedArticle:
        """
        Generate a full article based on an outline.

        Args:
            title: Article title
            keyword: Target SEO keyword
            sections: List of outline sections
            tone: Content tone
            target_audience: Description of target audience

        Returns:
            GeneratedArticle with full content
        """
        if not self._client:
            # Return mock data for development
            return self._mock_article(title, keyword, sections)

        # GEN-02: Sanitize all user-supplied inputs before interpolation
        # GEN-34: Cap keyword at 100 chars to prevent oversized prompt interpolation
        keyword = self._sanitize_prompt_input(keyword, 100)
        tone = self._sanitize_prompt_input(tone, 50)
        target_audience = (
            self._sanitize_prompt_input(target_audience, 500) if target_audience else None
        )
        custom_instructions = (
            self._sanitize_prompt_input(custom_instructions, 1000) if custom_instructions else None
        )
        title = self._sanitize_prompt_input(title, 300)

        secondary_keywords = [
            self._sanitize_prompt_input(kw, 100) for kw in (secondary_keywords or [])[:10] if kw
        ]
        entities = [
            self._sanitize_prompt_input(e, 100) for e in (entities or [])[:10] if e
        ]

        audience_context = f"Target audience: {target_audience}" if target_audience else ""
        secondary_kw_context = (
            f"\nSECONDARY KEYWORDS: {', '.join(secondary_keywords)}" if secondary_keywords else ""
        )
        entities_context = (
            f"\nENTITIES (integrate naturally): {', '.join(entities)}" if entities else ""
        )
        custom_context = (
            f"\nAdditional instructions from the user:\n{custom_instructions}"
            if custom_instructions
            else ""
        )
        language_name = self._get_language_name(language)
        language_context = (
            f"\n**LANGUAGE: Write the ENTIRE article in {language_name}. All headings, paragraphs, and meta description must be in {language_name} with correct grammar, gender agreements, and natural phrasing.**"
            if language != "en"
            else ""
        )

        # Format sections for the prompt
        sections_text = "\n".join(
            [
                f"## {s['heading']}\n"
                + "\n".join([f"### {sub}" for sub in s.get("subheadings", [])])
                + f"\nNotes: {s.get('notes', '')}\nTarget: {s.get('word_count_target', 200)} words"
                for s in sections
            ]
        )

        # Calculate max_tokens based on word count target
        # Non-English languages (Romanian, German, etc.) use significantly more tokens
        # per word due to tokenization. Be generous — you only pay for tokens generated.
        if language != "en":
            tokens_per_word = 4.0
        else:
            tokens_per_word = 2.5
        estimated_tokens = int(word_count_target * tokens_per_word) + 1000
        max_tokens = min(max(estimated_tokens, 4000), 16000)

        # Define word count tolerance range
        word_min = int(word_count_target * 0.85)
        word_max = int(word_count_target * 1.15)

        # Build content format guidelines that respect list_usage and writing_style
        fmt_config = prompt_loader.get_config("format_guidelines")
        if list_usage == "heavy" or writing_style == "listicle":
            format_guidelines = fmt_config["heavy"]
        elif list_usage == "minimal":
            format_guidelines = fmt_config["minimal"]
        else:
            format_guidelines = fmt_config["default"]

        prompt = prompt_loader.format(
            "article_generation",
            title=title,
            keyword=keyword,
            audience_context=audience_context,
            secondary_kw_context=secondary_kw_context,
            entities_context=entities_context,
            tone=tone,
            language_context=language_context,
            word_count_target=word_count_target,
            word_min=word_min,
            word_max=word_max,
            sections_text=sections_text,
            format_guidelines=format_guidelines,
            section_count=len(sections),
            custom_context=custom_context,
        )

        # Generate with retry on truncation
        max_attempts = 2
        for attempt in range(max_attempts):
            _max_tokens_capture = max_tokens
            message = await _retry_with_backoff(
                lambda: self._client.messages.create(
                    model=self._model,
                    max_tokens=_max_tokens_capture,  # noqa: B023
                    temperature=0.3,
                    system=self._get_system_prompt(
                        writing_style=writing_style,
                        voice=voice,
                        list_usage=list_usage,
                        language=language,
                    ),
                    messages=[{"role": "user", "content": prompt}],
                )
            )

            if message.stop_reason == "max_tokens" and attempt < max_attempts - 1:
                # Response was truncated — retry with 50% more tokens
                logger.warning(
                    "Article generation truncated (stop_reason=max_tokens, "
                    "max_tokens=%d, word_target=%d, language=%s). Retrying with more tokens.",
                    max_tokens,
                    word_count_target,
                    language,
                )
                max_tokens = min(int(max_tokens * 1.5), 16000)
                continue

            if message.stop_reason == "max_tokens":
                logger.error(
                    "Article generation still truncated after retry "
                    "(max_tokens=%d, word_target=%d, language=%s)",
                    max_tokens,
                    word_count_target,
                    language,
                )
            break

        if not message.content:
            raise AIGenerationError("AI returned empty response")
        response_text = message.content[0].text

        # Extract meta description and url slug
        meta_description = ""
        url_slug = ""
        content = response_text
        if "META_DESCRIPTION:" in response_text:
            parts = response_text.split("META_DESCRIPTION:", 1)
            content = parts[0].strip().rstrip("-").strip()
            after_meta = parts[1]
            if "URL_SLUG:" in after_meta:
                meta_parts = after_meta.split("URL_SLUG:", 1)
                meta_description = meta_parts[0].strip()[:160]
                url_slug = meta_parts[1].split("\n")[0].strip()[:100]
            else:
                meta_description = after_meta.strip()[:160]

        # Calculate word count
        word_count = len(content.split())

        return GeneratedArticle(
            title=title,
            content=content,
            meta_description=meta_description,
            word_count=word_count,
            url_slug=url_slug,
        )

    async def proofread_grammar(
        self,
        content: str,
        language: str = "en",
    ) -> str:
        """
        Proofread and fix grammar issues in generated content.
        Preserves markdown structure, headings, and meaning.

        Args:
            content: Article content in markdown format
            language: Language code

        Returns:
            Grammar-corrected content
        """
        if not self._client:
            return content

        language_name = self._get_language_name(language)

        prompt = prompt_loader.format(
            "proofread",
            language_name=language_name,
            content=content,
        )

        _proofread_max_tokens = max(len(content.split()) * 3, 4000)
        message = await _retry_with_backoff(
            lambda: self._client.messages.create(
                model=self._model,
                max_tokens=_proofread_max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
        )

        return message.content[0].text

    async def improve_content(
        self,
        content: str,
        improvement_type: str = "seo",
        keyword: str | None = None,
    ) -> str:
        """
        Improve existing content.

        Args:
            content: Original content to improve
            improvement_type: Type of improvement (seo, readability, engagement)
            keyword: Target keyword for SEO improvements

        Returns:
            Improved content
        """
        if not self._client:
            return content

        improvement_instructions = prompt_loader.get_config("improvement_types")
        instruction = improvement_instructions.get(improvement_type, improvement_instructions["seo"])
        if improvement_type == "seo" and keyword:
            instruction = instruction.replace("{keyword}", keyword)

        prompt = prompt_loader.format(
            "improve_content",
            improvement_instruction=instruction,
            content=content,
        )

        message = await _retry_with_backoff(
            lambda: self._client.messages.create(
                model=self._model,
                max_tokens=8000,
                system=self._get_system_prompt(
                    writing_style="balanced", voice="second_person", list_usage="balanced"
                ),
                messages=[{"role": "user", "content": prompt}],
            )
        )

        return message.content[0].text

    async def generate_meta_description(
        self,
        title: str,
        content: str,
        keyword: str,
    ) -> str:
        """Generate an SEO meta description."""
        if not self._client:
            return f"Learn about {keyword}. {title[:100]}"

        prompt = prompt_loader.format(
            "meta_description",
            title=title,
            keyword=keyword,
            content_summary=content[:500],
        )

        message = await _retry_with_backoff(
            lambda: self._client.messages.create(
                model=self._model,
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}],
            )
        )

        return message.content[0].text.strip()[:160]

    def _mock_outline(self, keyword: str, word_count_target: int) -> GeneratedOutline:
        """Generate mock outline for development."""
        return GeneratedOutline(
            title=f"Complete Guide to {keyword.title()}: Everything You Need to Know",
            sections=[
                OutlineSection(
                    heading=f"What is {keyword.title()}?",
                    subheadings=["Definition and Overview", "Why It Matters"],
                    notes="Introduction to the topic with clear definitions",
                    word_count_target=200,
                ),
                OutlineSection(
                    heading=f"Benefits of {keyword.title()}",
                    subheadings=["Physical Benefits", "Mental Benefits", "Long-term Advantages"],
                    notes="Detailed exploration of key benefits",
                    word_count_target=300,
                ),
                OutlineSection(
                    heading="How to Get Started",
                    subheadings=["Step-by-Step Guide", "Common Mistakes to Avoid"],
                    notes="Practical implementation guide",
                    word_count_target=350,
                ),
                OutlineSection(
                    heading="Best Practices and Tips",
                    subheadings=["Expert Recommendations", "Tools and Resources"],
                    notes="Advanced tips for better results",
                    word_count_target=300,
                ),
                OutlineSection(
                    heading="Conclusion",
                    subheadings=[],
                    notes="Summary and call to action",
                    word_count_target=150,
                ),
            ],
            meta_description=f"Discover everything about {keyword}. Learn the benefits, best practices, and how to get started with our comprehensive guide.",
            estimated_word_count=word_count_target,
            estimated_read_time=word_count_target // 200,
        )

    def _mock_article(
        self, title: str, keyword: str, sections: list[dict[str, Any]]
    ) -> GeneratedArticle:
        """Generate mock article for development."""
        content_parts = [f"# {title}\n"]

        for section in sections:
            content_parts.append(f"\n## {section['heading']}\n")
            content_parts.append(f"This section covers {section.get('notes', keyword)}.\n")
            for sub in section.get("subheadings", []):
                content_parts.append(f"\n### {sub}\n")
                content_parts.append(f"Detailed content about {sub.lower()}.\n")

        content = "\n".join(content_parts)

        return GeneratedArticle(
            title=title,
            content=content,
            meta_description=f"Learn about {keyword} in this comprehensive guide.",
            word_count=len(content.split()),
        )

    async def generate_social_posts(
        self,
        article_title: str,
        article_summary: str,
        article_url: str,
        keywords: list[str] | None = None,
    ) -> dict[str, str]:
        """
        Generate platform-specific social media posts for an article.

        Returns:
            Dict with keys: twitter, linkedin, facebook, instagram
        """
        if not self._client:
            return {
                "twitter": f"Check out our latest article: {article_title} {article_url} #content #seo",
                "linkedin": f"I just published a new article: {article_title}\n\nKey takeaways from this piece:\n\nRead more: {article_url}\n\n#ContentMarketing #SEO",
                "facebook": f"Have you ever wondered about {article_title.lower()}? We just published a deep dive into this topic. Check it out!\n\n{article_url}",
                "instagram": f"{article_title}\n\nWe break down everything you need to know in our latest article. Link in bio!\n\n#content #seo #digitalmarketing #blogging #contentcreation",
            }

        keywords_text = ", ".join(keywords) if keywords else "content marketing"

        prompt = prompt_loader.format(
            "social_posts",
            article_title=article_title,
            article_summary=article_summary,
            article_url=article_url,
            keywords_text=keywords_text,
        )

        message = await _retry_with_backoff(
            lambda: self._client.messages.create(
                model=self._model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
        )

        response_text = message.content[0].text

        # Extract JSON from response
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        data = json.loads(response_text.strip())

        return {
            "twitter": data.get("twitter", ""),
            "linkedin": data.get("linkedin", ""),
            "facebook": data.get("facebook", ""),
            "instagram": data.get("instagram", ""),
        }

    async def generate_image_prompt(
        self,
        title: str,
        content: str,
        keyword: str,
    ) -> str:
        """
        Generate a concise image prompt optimized for AI image generation,
        based on the article's title, content, and keyword.

        Returns:
            A 1-3 sentence visual image prompt.
        """
        if not self._client:
            return f"A visually striking image representing {keyword}, related to {title}"

        prompt = prompt_loader.format(
            "image_prompt",
            title=title,
            keyword=keyword,
            content_excerpt=content[:1500],
        )

        message = await _retry_with_backoff(
            lambda: self._client.messages.create(
                model=self._model,
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}],
            )
        )

        return message.content[0].text.strip()

    async def fact_check_content(self, content: str) -> list[str]:
        """
        Self-review pass: ask the AI to list any specific statistics,
        data points, or cited claims in the content that it is not
        highly confident are accurate.

        Returns a list of potentially unreliable claim strings.
        Uses temperature=0.0 for deterministic output and haiku-class
        model to keep cost low.
        """
        if not self._client:
            return []

        # Limit input to keep cost low — first 6000 chars covers most articles
        excerpt = content[:6000]

        prompt = prompt_loader.format(
            "fact_check",
            excerpt=excerpt,
        )

        message = await _retry_with_backoff(
            lambda: self._client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=512,
                temperature=0.0,
                messages=[{"role": "user", "content": prompt}],
            )
        )

        response = message.content[0].text.strip()
        if not response or response.upper() == "NONE":
            return []

        claims: list[str] = []
        for line in response.splitlines():
            line = line.strip().lstrip("- ").strip()
            if line and len(line) > 10:
                claims.append(line)
        return claims

    async def regenerate_section(
        self,
        full_content: str,
        section_heading: str,
        keyword: str,
        tone: str = "professional",
        section_word_target: int = 200,
        reason: str | None = None,
        writing_style: str = "balanced",
        voice: str = "second_person",
        list_usage: str = "balanced",
        language: str = "en",
    ) -> str:
        """Regenerate a single H2 section within an article.

        Splits the article at the target H2, regenerates just that section,
        and returns the full article with the section replaced.
        """
        if not self._client:
            return full_content

        # Split article into sections by H2 headings
        h2_pattern = re.compile(r"^(## .+)$", re.MULTILINE)
        parts = h2_pattern.split(full_content)

        # Find the target section
        target_idx = None
        for i, part in enumerate(parts):
            if part.strip().startswith("## ") and section_heading.lower() in part.lower():
                target_idx = i
                break

        if target_idx is None:
            logger.warning("Section '%s' not found in article", section_heading)
            return full_content

        # Build context: content before and after the target section
        context_before = "".join(parts[max(0, target_idx - 2) : target_idx]).strip()[-500:]
        # Section content is at target_idx (heading) + target_idx+1 (body)
        next_section_idx = target_idx + 2
        context_after = "".join(parts[next_section_idx : next_section_idx + 2]).strip()[:500]

        reason_context = f"Reason for regeneration: {reason}" if reason else ""

        prompt = prompt_loader.format(
            "section_regeneration",
            keyword=keyword,
            tone=tone,
            section_heading=section_heading.lstrip("# ").strip(),
            section_word_target=section_word_target,
            reason_context=reason_context,
            context_before=context_before or "(beginning of article)",
            context_after=context_after or "(end of article)",
        )

        message = await _retry_with_backoff(
            lambda: self._client.messages.create(
                model=self._model,
                max_tokens=2000,
                temperature=0.3,
                system=self._get_system_prompt(
                    writing_style=writing_style,
                    voice=voice,
                    list_usage=list_usage,
                    language=language,
                ),
                messages=[{"role": "user", "content": prompt}],
            )
        )

        new_section = message.content[0].text.strip()

        # Replace the old section with the new one
        before = "".join(parts[:target_idx])
        after = "".join(parts[next_section_idx:])
        return before + new_section + "\n\n" + after

    async def repair_flagged_claims(
        self,
        content: str,
        flagged_claims: list[str],
    ) -> str:
        """Repair flagged statistical claims by replacing them with qualitative language.

        Uses Haiku for cost efficiency. Returns the repaired article content.
        If no claims are flagged or client is unavailable, returns content unchanged.
        """
        if not self._client or not flagged_claims:
            return content

        claims_text = "\n".join(f"- {claim}" for claim in flagged_claims)

        prompt = prompt_loader.format(
            "fact_check_repair",
            flagged_claims=claims_text,
            content=content,
        )

        _repair_max_tokens = max(len(content.split()) * 3, 4000)
        message = await _retry_with_backoff(
            lambda: self._client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=_repair_max_tokens,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}],
            )
        )

        repaired = message.content[0].text.strip()
        if not repaired or len(repaired) < len(content) * 0.5:
            logger.warning("Fact-check repair returned suspiciously short content, using original")
            return content
        return repaired

    async def generate_content_suggestions(
        self,
        keywords: list[dict[str, Any]],
        existing_articles: list[str],
        language: str = "en",
    ) -> list[dict[str, Any]]:
        """
        Generate content suggestions based on keyword opportunity data.

        Args:
            keywords: List of dicts with keyword, impressions, clicks, ctr, position
            existing_articles: List of existing article titles to avoid duplication
            language: Target language code

        Returns:
            List of suggestion dicts with title, keyword, angle, rationale, difficulty, word_count
        """
        if not self._client:
            return [
                {
                    "suggested_title": f"Complete Guide to {kw['keyword'].title()}",
                    "target_keyword": kw["keyword"],
                    "content_angle": "Comprehensive guide covering all aspects",
                    "rationale": f"Keyword has {kw.get('impressions', 0)} impressions with room for improvement",
                    "estimated_difficulty": "medium",
                    "estimated_word_count": 1500,
                }
                for kw in keywords[:5]
            ]

        language_name = self._get_language_name(language)
        language_instruction = (
            f"\nGenerate all titles and content angles in {language_name}."
            if language != "en"
            else ""
        )

        keywords_text = "\n".join(
            [
                f'- "{kw["keyword"]}" — {kw.get("impressions", 0)} impressions, '
                f"{kw.get('clicks', 0)} clicks, CTR: {kw.get('ctr', 0):.2%}, "
                f"Avg Position: {kw.get('position', 0):.1f}"
                for kw in keywords
            ]
        )

        existing_text = (
            "\n".join([f"- {title}" for title in existing_articles])
            if existing_articles
            else "None"
        )

        prompt = prompt_loader.format(
            "content_suggestions",
            keywords_text=keywords_text,
            existing_text=existing_text,
            language_instruction=language_instruction,
            max_suggestions=min(len(keywords), 10),
        )

        try:
            message = await _retry_with_backoff(
                lambda: self._client.messages.create(
                    model=self._model,
                    max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}],
                )
            )

            response_text = message.content[0].text

            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]

            data = json.loads(response_text.strip())
            return data.get("suggestions", [])

        except Exception as e:
            logger.error(f"Failed to generate content suggestions: {e}")
            raise

    async def generate_content_cluster(
        self,
        keyword: str,
        target_audience: str | None = None,
        language: str = "en",
    ) -> dict:
        """Generate a topical authority cluster plan: pillar + supporting articles.

        Returns a dict with 'pillar' and 'supporting_articles' keys.
        """
        if not self._client:
            return {
                "pillar": {
                    "title": f"Complete Guide to {keyword.title()}",
                    "keyword": keyword,
                    "word_count_target": 3000,
                    "description": f"Comprehensive guide covering all aspects of {keyword}",
                },
                "supporting_articles": [],
            }

        keyword = self._sanitize_prompt_input(keyword, 100)
        audience_context = (
            f"Target audience: {self._sanitize_prompt_input(target_audience, 500)}"
            if target_audience
            else ""
        )

        prompt = prompt_loader.format(
            "cluster_generation",
            keyword=keyword,
            language=language,
            audience_context=audience_context,
        )

        message = await _retry_with_backoff(
            lambda: self._client.messages.create(
                model=self._model,
                max_tokens=3000,
                temperature=0.4,
                messages=[{"role": "user", "content": prompt}],
            )
        )

        response_text = message.content[0].text
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        return json.loads(response_text.strip())

    async def generate_text(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        """
        Generate simple text response from a prompt.

        Used for RAG question answering and general text generation.

        Args:
            prompt: User prompt
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation (0.0-1.0)

        Returns:
            Generated text response
        """
        if not self._client:
            # Return mock response for development
            return "This is a mock response for development. Configure ANTHROPIC_API_KEY to use real AI."

        try:
            _gt_max_tokens = max_tokens
            _gt_temperature = temperature
            _gt_prompt = prompt
            message = await _retry_with_backoff(
                lambda: self._client.messages.create(
                    model=self._model,
                    max_tokens=_gt_max_tokens,
                    temperature=_gt_temperature,
                    messages=[{"role": "user", "content": _gt_prompt}],
                )
            )

            response_text = message.content[0].text
            logger.debug(f"Generated text response ({len(response_text)} chars)")
            return response_text

        except Exception as e:
            logger.error(f"Failed to generate text: {e}")
            raise


# Singleton instance
content_ai_service = AnthropicContentService()
