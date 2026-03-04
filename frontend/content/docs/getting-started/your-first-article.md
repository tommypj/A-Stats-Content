## Overview

This guide walks through the full article creation process in detail — from choosing a keyword to a polished, scored draft ready for publication. If you have already completed the Quick Start, this guide fills in the context behind each step and covers options you may have skipped the first time.

---

## Choosing a Keyword

The keyword you enter becomes the anchor for everything the AI produces: the outline structure, the article title, the section headings, and the SEO scoring checks.

**What makes a good keyword for A-Stats:**

- Specific enough to write a focused article (not just "SEO" — try "on-page SEO checklist for e-commerce sites")
- Reflective of actual search intent — question-style keywords ("how to...") tend to produce better AEO scores because the AI naturally structures the answer
- Realistic for your domain authority — very competitive head terms are harder to rank for regardless of content quality

> **Tip:** You do not need to do formal keyword research before generating in A-Stats, but if you have a target keyword from a tool like Ahrefs or Google Search Console, paste it in exactly. The SEO score checks for exact keyword presence in the title, headings, and body.

---

## Creating the Outline

Navigate to **Outlines** in your project sidebar and click **New Outline**.

### The Outline Form

**Keyword**: Enter your target keyword. This is required.

**Target word count**: This guides how much content the AI generates per section. For a 1,500-word article with five sections, the AI will aim for roughly 300 words per section. Longer articles (2,500+ words) perform better for informational and comparison content; shorter articles (800–1,200 words) work well for quick-answer topics.

**Writing style**: Choose from options like Informative, Conversational, Technical, or Persuasive. This is set at the project level by default (in Project Settings > Brand Voice) but can be overridden per outline.

**Voice**: Controls formality. First-person singular ("I recommend..."), first-person plural ("We recommend..."), or third-person neutral. Match this to how your publication usually writes.

**List usage**: Controls how heavily the AI uses bullet and numbered lists. High list usage produces more scannable content; low list usage produces more flowing prose. For AEO purposes, a mix of prose and structured lists typically performs best.

**Custom instructions**: A free-text field for anything not covered by the other settings. For example: "Include a comparison table in the third section" or "Avoid mentioning competitor brand names." These instructions are injected into the AI prompt for every section.

### Reviewing the Generated Outline

After clicking **Generate Outline**, A-Stats returns a suggested title and a list of sections with short descriptions.

**Editing sections:**

- Click a section heading to rename it
- Click the description text to edit what the AI should cover in that section
- Drag the handle on the left to reorder sections
- Click the plus button between sections to insert a new section
- Click the trash icon to delete a section

> **Tip:** The outline generation is fast — treat it as a starting point, not a final structure. It is faster to delete two sections and add one of your own than to write the whole outline from scratch.

A well-structured outline typically has:

- An introduction section (sets up the topic and reader benefit)
- 3–6 body sections covering distinct subtopics
- A conclusion or call-to-action section

---

## Generating the Article

With the outline saved, click **Generate Article**. A-Stats sends each section to the Claude AI in sequence and streams the result into the editor. You will see sections appear one at a time as they complete.

**What the AI produces:**

- A full paragraph or set of paragraphs for each section
- H2 headings for each section (matching your outline headings)
- H3 subheadings where the AI determines they improve structure
- Bullet or numbered lists where appropriate given your list-usage setting

Generation typically takes 20–60 seconds depending on article length and server load. You do not need to stay on the page — A-Stats saves the draft automatically when generation completes.

> **Tip:** If you navigate away during generation and come back, the article will be in your Outlines list with a status of "Generating" or "Draft". Click it to open the editor.

---

## Using the Editor

The editor is a rich-text interface with a toolbar for common formatting actions.

### Toolbar Actions

- **Bold / Italic / Underline**: Standard text formatting
- **Headings**: H2 and H3 — use H2 for major sections, H3 for subsections
- **Bullet list / Numbered list**: Block-level list formatting
- **Link**: Insert a hyperlink — add internal links to related articles for SEO benefit
- **Image**: Insert an image from your project media library, or generate a new one

### Editing AI Content

The AI output is a starting point. Most articles benefit from:

1. **Reading for accuracy**: The AI can hallucinate specific facts, statistics, or product details. Review every claim you intend to publish.
2. **Adding your perspective**: Insert first-hand examples, opinions, or case studies. This is what distinguishes your article from AI-generated content competitors can replicate.
3. **Adjusting the introduction**: AI introductions are often generic. Rewrite the first paragraph to lead with something specific and compelling.
4. **Checking transitions**: Section transitions can feel abrupt when sections are generated independently. A sentence or two linking sections improves flow.

### The Meta Description Field

The meta description appears in search results below your page title. It is not generated automatically — you need to write it manually in the right panel.

Guidelines for a good meta description:
- 140–160 characters
- Contains your target keyword naturally
- Describes what the reader will get from the article
- Ends with a mild call to action or benefit statement

---

## Understanding the SEO Score

The SEO score panel on the right side of the editor shows your current score (0–100) and a breakdown of the ten checks. Each check is worth up to 10 points.

### The Ten SEO Checks

1. **Keyword in title**: Your target keyword (or a close variation) appears in the H1 title
2. **Keyword in meta description**: The keyword appears in the meta description field
3. **Keyword density**: The keyword appears in the body at a natural frequency (not too sparse, not stuffed)
4. **Title length**: The title is between 50 and 60 characters (optimal for search result display)
5. **Meta description length**: The meta description is between 140 and 160 characters
6. **H2 headings present**: The article has at least one H2 subheading
7. **Content length**: The article meets the minimum word count for your chosen target length
8. **Internal links**: At least one internal link is present in the article body
9. **Readability**: Sentences are not excessively long on average
10. **Keyword in first paragraph**: The keyword appears within the first 100 words

> **Tip:** The score updates in real time as you edit. Make changes and watch the score respond — this is the fastest way to learn what each check actually measures.

---

## Understanding the AEO Score

AEO (Answer Engine Optimization) measures how well your content is positioned to be cited by AI search engines like Google AI Overviews, Perplexity, and ChatGPT.

AI systems prefer content that:

- **Directly answers questions**: Has a clear, concise answer near the top of the article before going into detail
- **Uses structured formats**: Bullet lists, numbered steps, and comparison tables make content easier for AI to extract and cite
- **Signals authority**: Specific facts, cited sources, and first-hand expertise markers
- **Has a clear topic scope**: Tightly focused articles on one topic outperform broad overview articles for AI citation

### Improving Your AEO Score

1. Add a short "What is X?" or "In short, ..." paragraph near the top of your article — this is often the snippet AI cites
2. Convert prose answers to numbered steps where the topic is procedural
3. Add a FAQ section at the bottom of the article addressing common related questions
4. Be specific — replace vague claims ("this can improve performance") with quantified ones ("this typically reduces load time by 30–50%")

---

## Saving and Next Steps

A-Stats auto-saves your article every 30 seconds. A manual save (Ctrl+S or the Save button) is recommended before navigating away.

Once your SEO and AEO scores are satisfactory:

- **Copy HTML**: Use the "Copy HTML" button to paste into your CMS
- **WordPress publish**: If you have connected WordPress in Project Settings > Integrations, click **Publish to WordPress** to push the article directly
- **Schedule social posts**: Use the Social scheduler to draft promotion posts from this article's content
