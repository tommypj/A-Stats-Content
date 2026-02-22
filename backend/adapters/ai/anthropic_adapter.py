"""
Anthropic Claude adapter for AI content generation.
"""

import json
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

import anthropic

from infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


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

    def _get_system_prompt(self, writing_style: str = "balanced", voice: str = "second_person", list_usage: str = "balanced") -> str:
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

        return f"""You are an expert SEO content writer who produces high-quality, human-sounding articles.

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
8. When citing research or studies, be specific — name the institution, year, or researcher when possible. Do not say "studies show" without attribution."""

    async def generate_outline(
        self,
        keyword: str,
        target_audience: Optional[str] = None,
        tone: str = "professional",
        word_count_target: int = 1500,
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

        audience_context = f"Target audience: {target_audience}" if target_audience else ""

        prompt = f"""Create a comprehensive article outline for the following:

Keyword: {keyword}
{audience_context}
Tone: {tone}
Target word count: {word_count_target} words

Generate a detailed outline with:
1. A compelling, SEO-optimized title
2. 5-7 main sections with H2 headings
3. 2-4 subheadings (H3) per section
4. Brief notes for each section describing the content
5. Estimated word count per section
6. A meta description (150-160 characters)

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

        message = await self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=self._get_system_prompt(writing_style="balanced", voice="second_person", list_usage="balanced"),
            messages=[{"role": "user", "content": prompt}],
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

        audience_context = f"Target audience: {target_audience}" if target_audience else ""
        custom_context = f"\nAdditional instructions from the user:\n{custom_instructions}" if custom_instructions else ""

        # Format sections for the prompt
        sections_text = "\n".join([
            f"## {s['heading']}\n" +
            "\n".join([f"### {sub}" for sub in s.get('subheadings', [])]) +
            f"\nNotes: {s.get('notes', '')}\nTarget: {s.get('word_count_target', 200)} words"
            for s in sections
        ])

        # Calculate max_tokens based on word count target
        # ~1.4 tokens per word on average, plus buffer for meta description
        estimated_tokens = int(word_count_target * 1.5) + 200
        max_tokens = min(max(estimated_tokens, 1500), 8000)

        # Define word count tolerance range
        word_min = int(word_count_target * 0.85)
        word_max = int(word_count_target * 1.15)

        prompt = f"""Write a complete, SEO-optimized article based on this outline:

Title: {title}
Keyword: {keyword}
{audience_context}
Tone: {tone}

**TARGET WORD COUNT: approximately {word_count_target} words (between {word_min} and {word_max} words). This is a strict requirement — do NOT exceed {word_max} words.**

Outline:
{sections_text}

IMPORTANT WRITING GUIDELINES:
1. **WORD COUNT IS CRITICAL**: The article MUST be approximately {word_count_target} words. Distribute the word budget across sections proportionally to the per-section targets shown above. Do NOT write more than {word_max} words total.
2. Follow the outline structure exactly — use the provided H2 and H3 headings
3. Write rich, flowing paragraphs as the PRIMARY content format
4. Open with a compelling introduction (2-3 paragraphs) that hooks the reader without using lists
5. Under each heading, write at least 2-3 substantive paragraphs BEFORE considering any list
6. When you do use a list, introduce it with a paragraph and follow it with analysis or a connecting paragraph
7. End with a conclusion that synthesizes key insights and includes a call-to-action
8. Vary your paragraph openings — do not start consecutive paragraphs the same way
9. Include specific examples, case studies, or scenarios to illustrate points
10. Use transitional phrases to connect sections naturally
{custom_context}

Write the article in markdown format.

At the very end, after the article, add:
---
META_DESCRIPTION: [A compelling 150-160 character meta description]"""

        message = await self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=self._get_system_prompt(writing_style=writing_style, voice=voice, list_usage=list_usage),
            messages=[{"role": "user", "content": prompt}],
        )

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
        }

        prompt = f"""{improvement_instructions.get(improvement_type, improvement_instructions['seo'])}

Original content:
{content}

Provide the improved version in markdown format."""

        message = await self._client.messages.create(
            model=self._model,
            max_tokens=8000,
            system=self._get_system_prompt(writing_style="balanced", voice="second_person", list_usage="balanced"),
            messages=[{"role": "user", "content": prompt}],
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

        message = await self._client.messages.create(
            model=self._model,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
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

        message = await self._client.messages.create(
            model=self._model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
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

        message = await self._client.messages.create(
            model=self._model,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )

        return message.content[0].text.strip()

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
            message = await self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = message.content[0].text
            logger.debug(f"Generated text response ({len(response_text)} chars)")
            return response_text

        except Exception as e:
            logger.error(f"Failed to generate text: {e}")
            raise


# Singleton instance
content_ai_service = AnthropicContentService()
