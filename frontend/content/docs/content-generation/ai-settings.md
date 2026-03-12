## Where AI Settings Live

AI settings are configured at the project level. Go to any project, then open **Project Settings → AI Settings**. Every outline and article generated inside that project inherits these settings automatically. You can also override settings on individual outlines before generating.

---

## Writing Style

Writing style controls the structural and sentence-level character of the output.

| Style | What It Produces |
|---|---|
| **Informational** | Neutral, fact-first prose. Best for how-to guides, explainers, and reference articles. |
| **Conversational** | Approachable, lightly informal tone. Good for blog posts aimed at general audiences. |
| **Persuasive** | Arguments are front-loaded. Useful for opinion pieces, comparison pages, and landing-adjacent articles. |
| **Authoritative** | Dense, expert-facing prose. Best for technical documentation or B2B long-form. |
| **Storytelling** | Narrative arc with anecdotes and examples. Good for case studies and brand journalism. |

> **Tip:** If you are unsure which style fits your audience, start with **Conversational** — it performs well across a wide range of B2B and B2C niches and rarely alienates readers.

---

## Voice and Tone

Voice is a layer on top of writing style. It adjusts how the author "feels" to the reader without changing the structural approach.

- **Professional** — Polished and measured. No slang, no contractions.
- **Friendly** — Warm and encouraging. Contractions are used naturally.
- **Bold** — Confident, direct. Short sentences, strong verbs, no hedging language.
- **Empathetic** — Acknowledges the reader's challenges. Good for health, finance, or career topics.
- **Witty** — Light humour and wordplay. Use sparingly unless your brand genuinely sustains it.

Voice and style settings are independent — you can combine **Authoritative** style with a **Friendly** voice to produce expert content that does not feel cold.

---

## List Usage

Controls how frequently the AI uses bullet and numbered lists.

| Setting | Behaviour |
|---|---|
| **Minimal** | Lists are used only where they are clearly the best format (step-by-step instructions, feature comparisons). Prose is preferred. |
| **Moderate** | Lists appear in most sections where three or more items exist. The default for most content types. |
| **Heavy** | Lists are used aggressively, including for two-item pairs. Best for skimmable reference pages. |

> **Tip:** AEO score improves when key facts are presented in lists or tables. If AEO is a priority, set list usage to **Moderate** or **Heavy**.

---

## Custom Instructions

The custom instructions field is a free-text box where you describe anything that does not fit the structured settings above. The AI reads this field verbatim as part of every generation prompt.

Good uses for custom instructions:

- **Brand-specific language rules** — "Never use the phrase 'cutting-edge'. Avoid superlatives. Always spell the product name as 'A-Stats' (not 'AStats' or 'a-stats')."
- **Content focus** — "Assume the reader is a freelance SEO consultant with 2–5 years of experience. Do not explain basic concepts."
- **Structural preferences** — "Always end the article with a FAQ section containing three questions derived from the topic."
- **Competitor avoidance** — "Do not mention or recommend any competitor products."
- **Regulatory constraints** — "This content is for a regulated financial services audience. Do not make specific return projections. Always include a disclaimer reminder."

Custom instructions are applied on every generation run in the project until you change them. Keep them focused and specific — overly long instruction blocks can dilute the most important rules.

> **Tip:** Test a new custom instruction on a short article first (600–900 word target) before rolling it out across a bulk job. This lets you verify the AI is following the instruction before spending a large number of credits.

---

## Knowledge Vault Context

If your project has sources uploaded to the [Knowledge Vault](/docs/knowledge-vault), the AI can draw on that material when generating content. Relevant information from your sources is automatically found and used when it matches the outline's topic.

What this means in practice:

- The AI can cite your proprietary data, product details, or research without hallucinating them.
- Brand terminology and specific product names in your documentation carry through into the article.
- You do not need to paste context manually into each custom instruction — the retrieval is automatic.

To control which sources are available, manage them in **Project Settings → Knowledge Vault**. Sources can be toggled active or inactive per project.

> **Tip:** Upload your product one-pager, your brand style guide, and any evergreen FAQ documents to the Knowledge Vault. These three documents alone significantly improve factual accuracy and brand consistency across all generated content.

---

## Brand Voice Presets (Coming Soon)

A future update will allow you to save a named "brand voice" preset — a combination of style, tone, list usage, and custom instructions — and apply it across multiple projects with a single click. If consistent brand voice across projects is important to your workflow, vote for this feature in the product roadmap.
