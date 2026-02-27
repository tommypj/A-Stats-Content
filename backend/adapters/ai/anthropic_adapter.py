"""
Anthropic Claude adapter for AI content generation.
"""

import asyncio
import json
import logging
import random
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

import anthropic

from infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


async def _retry_with_backoff(coro_factory, max_retries=3, base_delay=1.0):
    """Retry an async operation with exponential backoff + jitter."""
    for attempt in range(max_retries + 1):
        try:
            return await coro_factory()
        except Exception as e:
            error_str = str(e).lower()
            is_transient = any(k in error_str for k in ["rate_limit", "429", "500", "502", "503", "504", "overloaded", "connection", "timeout"])
            if not is_transient or attempt == max_retries:
                raise
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            logger.warning("Transient API error (attempt %d/%d), retrying in %.1fs: %s", attempt + 1, max_retries, delay, str(e))
            await asyncio.sleep(delay)


@dataclass
class OutlineSection:
    """Outline section structure."""

    heading: str
    subheadings: List[str]
    notes: str
    word_count_target: int


@dataclass
class GeneratedOutline:
    """Generated outline result."""

    title: str
    sections: List[OutlineSection]
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


class AnthropicContentService:
    """AI content generation service using Anthropic Claude."""

    def __init__(self):
        if settings.anthropic_api_key:
            self._client = anthropic.AsyncAnthropic(
                api_key=settings.anthropic_api_key,
                timeout=300.0,
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

    def _get_system_prompt(self, writing_style: str = "balanced", voice: str = "second_person", list_usage: str = "balanced", language: str = "en") -> str:
        """Get the system prompt for content generation."""

        style_instructions = {
            "editorial": "Write in an editorial, opinion-driven style. Take clear positions, use rhetorical questions, and build persuasive arguments. Each section should read like a magazine feature — compelling, authoritative, and narrative-driven.",
            "narrative": "Write in a storytelling, narrative style. Use anecdotes, scenarios, and vivid descriptions. Guide the reader through a journey rather than presenting information in a structured list format. Paint pictures with words.",
            "listicle": "Write in a structured listicle style. Use numbered items or bullet points as the primary format. Each point should have a bold heading followed by a brief explanation. Keep it scannable and punchy.",
            "balanced": "Write in a balanced editorial style that combines flowing prose paragraphs with occasional lists. The majority of content should be written as engaging paragraphs. Use bullet points or numbered lists sparingly — only when presenting 4+ parallel items that genuinely benefit from list format (like ingredients, steps in a process, or tool recommendations). Never use a list when a well-written paragraph would be more engaging.",
        }

        voice_instructions = {
            "first_person": "Write in first person (I/we). Share personal insights and experiences as if you are an expert sharing your own journey and knowledge.",
            "second_person": "Write in second person (you/your). Address the reader directly, making the content feel personal and actionable.",
            "third_person": "Write in third person (one/they/people). Maintain an objective, authoritative distance suitable for academic or professional contexts.",
        }

        list_instructions = {
            "minimal": "Avoid bullet points and numbered lists almost entirely. Express all information through well-crafted prose paragraphs. If you must use a list, limit it to one per 500 words maximum.",
            "balanced": "Use lists sparingly and strategically. For every list you include, ensure there are at least 3-4 substantial prose paragraphs surrounding it. Lists should be the exception, not the rule.",
            "heavy": "Feel free to use bullet points and numbered lists frequently to make content highly scannable. But still include introductory and transitional paragraphs between lists.",
        }

        language_name = self._get_language_name(language)
        language_instruction = ""
        if language != "en":
            language_instruction = f"""
LANGUAGE — THIS IS CRITICAL:
You MUST write the ENTIRE article in {language_name}. Every word, heading, subheading, paragraph, and meta description must be in {language_name}.
Use native-level grammar, correct gender agreements, proper declensions, and natural idiomatic expressions.
Do NOT mix languages. Do NOT use English words unless they are commonly used loanwords in {language_name}.
Write as a native {language_name} speaker would — with correct syntax, word order, and cultural context.
Before finalizing each paragraph, mentally verify grammar: correct gender agreements, proper case declensions, accurate verb conjugations, and natural word order for {language_name}.
"""
        else:
            language_instruction = "\nLANGUAGE: Write in English.\n"

        return f"""You are an expert SEO content writer who produces high-quality, human-sounding articles.
{language_instruction}
WRITING APPROACH:
{style_instructions.get(writing_style, style_instructions['balanced'])}

VOICE:
{voice_instructions.get(voice, voice_instructions['second_person'])}

LIST USAGE:
{list_instructions.get(list_usage, list_instructions['balanced'])}

CRITICAL RULES:
1. Write like a skilled human journalist, not an AI. Vary sentence length. Use transitional phrases between ideas.
2. Each paragraph should be 3-5 sentences that develop a single idea with depth.
3. Use the target keyword naturally — never bold it repeatedly or force it into every section.
4. Subheadings (H2, H3) should be followed by at least 2-3 prose paragraphs before any list appears.
5. Include specific examples, analogies, and scenarios rather than generic advice.
6. Do NOT start multiple consecutive paragraphs with the same word or structure.
7. Avoid filler phrases like "In conclusion", "It's important to note that", "As mentioned above".
8. When citing research or studies, be specific — name the institution, year, or researcher when possible. Do not say "studies show" without attribution.
9. GRAMMAR AND LANGUAGE QUALITY: Use impeccable grammar throughout. Ensure subject-verb agreement, correct tense consistency, proper use of articles (a/an/the), correct prepositions, and natural sentence flow. Every sentence must be grammatically correct and publication-ready."""

    @staticmethod
    def _sanitize_prompt_input(text: Optional[str], max_length: int) -> str:
        """Strip control characters and limit length to prevent prompt injection."""
        if not text:
            return ""
        import re as _re
        text = _re.sub(r'[\r\n\t\x00-\x1f\x7f]', ' ', text)
        text = _re.sub(r' +', ' ', text).strip()
        return text[:max_length]

    async def generate_outline(
        self,
        keyword: str,
        target_audience: Optional[str] = None,
        tone: str = "professional",
        word_count_target: int = 1500,
        language: str = "en",
        writing_style: str = "balanced",
        voice: str = "second_person",
        list_usage: str = "balanced",
        custom_instructions: Optional[str] = None,
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
        keyword = self._sanitize_prompt_input(keyword, 200)
        tone = self._sanitize_prompt_input(tone, 50)
        target_audience = self._sanitize_prompt_input(target_audience, 500) if target_audience else None
        custom_instructions = self._sanitize_prompt_input(custom_instructions, 1000) if custom_instructions else None

        audience_context = f"Target audience: {target_audience}" if target_audience else ""
        custom_context = f"\nAdditional instructions: {custom_instructions}" if custom_instructions else ""
        language_name = self._get_language_name(language)
        language_context = f"\nLanguage: Write ALL content (title, headings, notes, meta description) in {language_name}." if language != "en" else ""

        prompt = f"""Create a comprehensive article outline for the following:

Keyword: {keyword}
{audience_context}
Tone: {tone}
Target word count: {word_count_target} words{language_context}{custom_context}

Generate a detailed outline with:
1. A compelling, SEO-optimized title that is 30-60 characters long and includes the keyword "{keyword}"{f' (in {language_name})' if language != 'en' else ''}
2. 5-7 main sections with H2 headings{f' (in {language_name})' if language != 'en' else ''}
3. 2-4 subheadings (H3) per section
4. Brief notes for each section describing the content
5. Estimated word count per section
6. A meta description (150-160 characters) that includes the keyword "{keyword}"{f' (in {language_name})' if language != 'en' else ''}

Respond in JSON format:
{{
    "title": "Article Title",
    "meta_description": "SEO meta description...",
    "sections": [
        {{
            "heading": "Section H2 Heading",
            "subheadings": ["H3 Subheading 1", "H3 Subheading 2"],
            "notes": "Brief description of what to cover",
            "word_count_target": 200
        }}
    ],
    "estimated_word_count": 1500,
    "estimated_read_time": 7
}}"""

        message = await _retry_with_backoff(lambda: self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=self._get_system_prompt(writing_style=writing_style, voice=voice, list_usage=list_usage, language=language),
            messages=[{"role": "user", "content": prompt}],
        ))

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
        sections: List[Dict[str, Any]],
        tone: str = "professional",
        target_audience: Optional[str] = None,
        writing_style: str = "balanced",
        voice: str = "second_person",
        list_usage: str = "balanced",
        custom_instructions: Optional[str] = None,
        word_count_target: int = 1500,
        language: str = "en",
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
        keyword = self._sanitize_prompt_input(keyword, 200)
        tone = self._sanitize_prompt_input(tone, 50)
        target_audience = self._sanitize_prompt_input(target_audience, 500) if target_audience else None
        custom_instructions = self._sanitize_prompt_input(custom_instructions, 1000) if custom_instructions else None
        title = self._sanitize_prompt_input(title, 300)

        audience_context = f"Target audience: {target_audience}" if target_audience else ""
        custom_context = f"\nAdditional instructions from the user:\n{custom_instructions}" if custom_instructions else ""
        language_name = self._get_language_name(language)
        language_context = f"\n**LANGUAGE: Write the ENTIRE article in {language_name}. All headings, paragraphs, and meta description must be in {language_name} with correct grammar, gender agreements, and natural phrasing.**" if language != "en" else ""

        # Format sections for the prompt
        sections_text = "\n".join([
            f"## {s['heading']}\n" +
            "\n".join([f"### {sub}" for sub in s.get('subheadings', [])]) +
            f"\nNotes: {s.get('notes', '')}\nTarget: {s.get('word_count_target', 200)} words"
            for s in sections
        ])

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
        if list_usage == "heavy" or writing_style == "listicle":
            format_guidelines = """4. Structure content for maximum scannability — use bullet points and numbered lists as a primary format alongside paragraphs
5. Open with a brief introduction (1-2 paragraphs) that hooks the reader, then dive into structured content
6. Under each heading, use a mix of short paragraphs and lists. Lead with a brief context paragraph, then use a list to present key points
7. When you use a list, each item should have a bold lead-in followed by a 1-2 sentence explanation"""
        elif list_usage == "minimal":
            format_guidelines = """4. Write rich, flowing paragraphs as the ONLY content format — avoid bullet points and numbered lists almost entirely
5. Open with a compelling introduction (2-3 paragraphs) that hooks the reader through narrative prose
6. Under each heading, write 3-4 substantive paragraphs. Do NOT use lists unless absolutely necessary (e.g., a sequence of 5+ steps)
7. If you must use a single list, limit it to one in the entire article, and surround it with explanatory paragraphs"""
        else:
            format_guidelines = """4. Write rich, flowing paragraphs as the PRIMARY content format, with occasional lists where they genuinely help
5. Open with a compelling introduction (2-3 paragraphs) that hooks the reader without using lists
6. Under each heading, write at least 2-3 substantive paragraphs BEFORE considering any list
7. When you do use a list, introduce it with a paragraph and follow it with analysis or a connecting paragraph"""

        prompt = f"""Write a complete, SEO-optimized article based on this outline:

Title: {title}
Keyword: {keyword}
{audience_context}
Tone: {tone}{language_context}

**TARGET WORD COUNT: approximately {word_count_target} words (between {word_min} and {word_max} words). This is a strict requirement — do NOT exceed {word_max} words.**

Outline:
{sections_text}

IMPORTANT WRITING GUIDELINES:
1. **WORD COUNT IS CRITICAL**: The article MUST be approximately {word_count_target} words. Distribute the word budget across sections proportionally to the per-section targets shown above. Do NOT write more than {word_max} words total.
2. **COMPLETE ALL SECTIONS**: You MUST write content for EVERY section in the outline. Do not stop early. All {len(sections)} sections must be covered.
3. Follow the outline structure exactly — use the provided H2 and H3 headings
{format_guidelines}
8. End with a conclusion that synthesizes key insights and includes a call-to-action
9. Vary your paragraph openings — do not start consecutive paragraphs the same way
10. Include specific examples, case studies, or scenarios to illustrate points
11. Use transitional phrases to connect sections naturally

SEO REQUIREMENTS (these are critical for ranking):
12. **Keyword in introduction**: Naturally mention "{keyword}" within the first 1-2 sentences of the article
13. **Internal/external links**: Include 2-3 contextual markdown links throughout the article — use descriptive anchor text. Examples: [relevant anchor text](https://example.com/relevant-page). Place them naturally within paragraphs where a source, tool, or related concept is mentioned
14. **Keyword density**: Use "{keyword}" naturally throughout the article, aiming for roughly 1-2% density. Do NOT force it — only place it where it reads naturally
{custom_context}

Write the article in markdown format. Start directly with the introduction — do NOT repeat the title as an H1.

At the very end, after the article, add:
---
META_DESCRIPTION: [A compelling 150-160 character meta description that MUST include the keyword "{keyword}"]"""

        # Generate with retry on truncation
        max_attempts = 2
        for attempt in range(max_attempts):
            _max_tokens_capture = max_tokens
            message = await _retry_with_backoff(lambda: self._client.messages.create(
                model=self._model,
                max_tokens=_max_tokens_capture,
                system=self._get_system_prompt(writing_style=writing_style, voice=voice, list_usage=list_usage, language=language),
                messages=[{"role": "user", "content": prompt}],
            ))

            if message.stop_reason == "max_tokens" and attempt < max_attempts - 1:
                # Response was truncated — retry with 50% more tokens
                logger.warning(
                    "Article generation truncated (stop_reason=max_tokens, "
                    "max_tokens=%d, word_target=%d, language=%s). Retrying with more tokens.",
                    max_tokens, word_count_target, language,
                )
                max_tokens = min(int(max_tokens * 1.5), 16000)
                continue

            if message.stop_reason == "max_tokens":
                logger.error(
                    "Article generation still truncated after retry "
                    "(max_tokens=%d, word_target=%d, language=%s)",
                    max_tokens, word_count_target, language,
                )
            break

        if not message.content:
            raise AIGenerationError("AI returned empty response")
        response_text = message.content[0].text

        # Extract meta description
        meta_description = ""
        content = response_text
        if "META_DESCRIPTION:" in response_text:
            parts = response_text.split("META_DESCRIPTION:")
            content = parts[0].strip().rstrip("-").strip()
            meta_description = parts[1].strip()[:160]

        # Calculate word count
        word_count = len(content.split())

        return GeneratedArticle(
            title=title,
            content=content,
            meta_description=meta_description,
            word_count=word_count,
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

        prompt = f"""Proofread the following article and fix ALL grammar mistakes.

RULES:
1. Fix grammar errors: subject-verb agreement, tense consistency, articles, prepositions, punctuation, and sentence fragments.
2. Do NOT change the meaning, tone, or structure of the content.
3. Do NOT add or remove sections, headings, or paragraphs.
4. Do NOT change markdown formatting (##, ###, **, [], etc.).
5. Do NOT rephrase sentences that are already grammatically correct.
6. Do NOT change the word count significantly (stay within 2% of original).
7. Language: {language_name}

Return ONLY the corrected article in markdown format. No explanations or notes.

ARTICLE:
{content}"""

        _proofread_max_tokens = max(len(content.split()) * 3, 4000)
        message = await _retry_with_backoff(lambda: self._client.messages.create(
            model=self._model,
            max_tokens=_proofread_max_tokens,
            messages=[{"role": "user", "content": prompt}],
        ))

        return message.content[0].text

    async def improve_content(
        self,
        content: str,
        improvement_type: str = "seo",
        keyword: Optional[str] = None,
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

        improvement_instructions = {
            "seo": f"Optimize this content for SEO, naturally incorporating the keyword '{keyword}' where appropriate. Improve headings, meta tags, and keyword placement.",
            "readability": "Improve the readability of this content. Use shorter sentences, clearer language, and better paragraph structure.",
            "engagement": "Make this content more engaging. Add hooks, rhetorical questions, and emotional appeals while maintaining professionalism.",
            "grammar": "Proofread and fix all grammar mistakes in this content. Fix subject-verb agreement, tense consistency, articles, prepositions, punctuation, and sentence fragments. Do NOT change the meaning, structure, or tone. Do NOT add or remove sections.",
        }

        prompt = f"""{improvement_instructions.get(improvement_type, improvement_instructions['seo'])}

Original content:
{content}

Provide the improved version in markdown format."""

        message = await _retry_with_backoff(lambda: self._client.messages.create(
            model=self._model,
            max_tokens=8000,
            system=self._get_system_prompt(writing_style="balanced", voice="second_person", list_usage="balanced"),
            messages=[{"role": "user", "content": prompt}],
        ))

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

        prompt = f"""Generate an SEO-optimized meta description for this article:

Title: {title}
Keyword: {keyword}
Content summary: {content[:500]}...

Requirements:
- 150-160 characters
- Include the keyword naturally
- Compelling and action-oriented
- Encourage clicks from search results

Respond with ONLY the meta description, nothing else."""

        message = await _retry_with_backoff(lambda: self._client.messages.create(
            model=self._model,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        ))

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
        self, title: str, keyword: str, sections: List[Dict[str, Any]]
    ) -> GeneratedArticle:
        """Generate mock article for development."""
        content_parts = [f"# {title}\n"]

        for section in sections:
            content_parts.append(f"\n## {section['heading']}\n")
            content_parts.append(f"This section covers {section.get('notes', keyword)}.\n")
            for sub in section.get('subheadings', []):
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
        keywords: Optional[List[str]] = None,
    ) -> Dict[str, str]:
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

        prompt = f"""Generate social media posts for the following article. Each post should promote the article and include the URL.

Article Title: {article_title}
Article Summary: {article_summary}
Article URL: {article_url}
Keywords: {keywords_text}

Generate a post for each platform with these constraints:

1. **Twitter/X** (max 280 characters total including URL): Concise hook, include the URL, add 2-3 relevant hashtags. Must be punchy and engaging.

2. **LinkedIn** (max 3000 characters): Professional tone, include 2-3 key takeaways as bullet points, include the URL, add 3-5 professional hashtags. Start with a compelling hook.

3. **Facebook** (max 500 characters): Conversational tone, start with an engaging question or hook, include the URL, add 2-3 hashtags. Encourage engagement.

4. **Instagram** (caption style): Write an engaging caption with emojis, include 5-10 relevant hashtags at the end, mention "link in bio" instead of the URL. Make it visually descriptive.

Respond in JSON format:
{{
    "twitter": "tweet text here",
    "linkedin": "linkedin post here",
    "facebook": "facebook post here",
    "instagram": "instagram caption here"
}}"""

        message = await _retry_with_backoff(lambda: self._client.messages.create(
            model=self._model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        ))

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

        # Use only the first ~1500 chars of content to keep cost low
        content_excerpt = content[:1500]

        prompt = f"""Based on this article, write a concise image generation prompt (1-3 sentences) that an AI image model like Ideogram or DALL-E could use to create a compelling featured image.

Title: {title}
Keyword: {keyword}
Content excerpt:
{content_excerpt}

Requirements:
- Describe a specific visual scene, not abstract concepts
- Include details about composition, lighting, colors, and mood
- Do NOT include any text or words in the image description
- Keep it under 200 words
- Optimize for photographic or editorial style

Respond with ONLY the image prompt, nothing else."""

        message = await _retry_with_backoff(lambda: self._client.messages.create(
            model=self._model,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        ))

        return message.content[0].text.strip()

    async def generate_content_suggestions(
        self,
        keywords: List[Dict[str, Any]],
        existing_articles: List[str],
        language: str = "en",
    ) -> List[Dict[str, Any]]:
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
        language_instruction = f"\nGenerate all titles and content angles in {language_name}." if language != "en" else ""

        keywords_text = "\n".join([
            f"- \"{kw['keyword']}\" — {kw.get('impressions', 0)} impressions, "
            f"{kw.get('clicks', 0)} clicks, CTR: {kw.get('ctr', 0):.2%}, "
            f"Avg Position: {kw.get('position', 0):.1f}"
            for kw in keywords
        ])

        existing_text = "\n".join([f"- {title}" for title in existing_articles]) if existing_articles else "None"

        prompt = f"""Analyze these keyword opportunities from Google Search Console and suggest article topics.

KEYWORD DATA:
{keywords_text}

EXISTING ARTICLES (avoid duplicating these):
{existing_text}
{language_instruction}

For each suggestion provide:
1. A compelling, SEO-optimized article title
2. The primary target keyword
3. A content angle (1-2 sentences describing the unique approach)
4. Rationale for why this content would perform well (based on the data)
5. Estimated difficulty (easy/medium/hard based on keyword competition implied by position)
6. Recommended word count (1000-3000)

Group related keywords into single article suggestions where appropriate.
Suggest 5-{min(len(keywords), 10)} articles.

Respond in JSON format:
{{
    "suggestions": [
        {{
            "suggested_title": "Article Title",
            "target_keyword": "primary keyword",
            "content_angle": "Unique approach description",
            "rationale": "Why this will perform well",
            "estimated_difficulty": "easy|medium|hard",
            "estimated_word_count": 1500
        }}
    ]
}}"""

        try:
            message = await _retry_with_backoff(lambda: self._client.messages.create(
                model=self._model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            ))

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
            message = await _retry_with_backoff(lambda: self._client.messages.create(
                model=self._model,
                max_tokens=_gt_max_tokens,
                temperature=_gt_temperature,
                messages=[{"role": "user", "content": _gt_prompt}],
            ))

            response_text = message.content[0].text
            logger.debug(f"Generated text response ({len(response_text)} chars)")
            return response_text

        except Exception as e:
            logger.error(f"Failed to generate text: {e}")
            raise


# Singleton instance
content_ai_service = AnthropicContentService()
