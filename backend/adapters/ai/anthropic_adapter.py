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
                timeout=120.0,
            )
        else:
            self._client = None
        self._model = settings.anthropic_model
        self._max_tokens = settings.anthropic_max_tokens

    def _get_system_prompt(self) -> str:
        """Get the system prompt for content generation."""
        return """You are an expert SEO content writer specializing in therapeutic and wellness content.
Your writing style is:
- Empathetic and understanding
- Clear and accessible
- Evidence-based when appropriate
- Engaging and actionable
- Optimized for search engines while remaining natural

You understand therapeutic language, healing modalities, and how to communicate with audiences seeking wellness information.
Always maintain a professional yet warm tone that builds trust with readers.

When generating content:
1. Use the target keyword naturally throughout the content
2. Include relevant subheadings (H2, H3) for better structure
3. Write in a way that's easy to read (short paragraphs, bullet points where appropriate)
4. Include a compelling introduction and conclusion
5. Provide actionable insights and practical advice"""

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
            system=self._get_system_prompt(),
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

        # Format sections for the prompt
        sections_text = "\n".join([
            f"## {s['heading']}\n" +
            "\n".join([f"### {sub}" for sub in s.get('subheadings', [])]) +
            f"\nNotes: {s.get('notes', '')}\nTarget: {s.get('word_count_target', 200)} words"
            for s in sections
        ])

        prompt = f"""Write a complete, SEO-optimized article based on this outline:

Title: {title}
Keyword: {keyword}
{audience_context}
Tone: {tone}

Outline:
{sections_text}

Requirements:
1. Write naturally flowing content that incorporates the keyword organically
2. Use the provided headings and subheadings exactly as specified
3. Include an engaging introduction that hooks the reader
4. Provide practical, actionable advice in each section
5. End with a compelling conclusion with a call-to-action
6. Use bullet points and numbered lists where appropriate
7. Write in markdown format

Also provide a meta description (150-160 characters) at the end.

Format your response as:
[Article content in markdown]

---
META_DESCRIPTION: [Your meta description here]"""

        message = await self._client.messages.create(
            model=self._model,
            max_tokens=8000,
            system=self._get_system_prompt(),
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
            system=self._get_system_prompt(),
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
