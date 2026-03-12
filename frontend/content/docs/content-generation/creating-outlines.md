## What Is an Outline?

An outline is the structural blueprint for an article. Before any AI-generated content is written, A-Stats builds a plan: the target keyword, the sections that will be covered, the intended word count, and any contextual settings you have configured. Generating the article itself is a separate step that happens after the outline is ready.

This two-step approach gives you a chance to review and adjust the structure before committing AI generation credits. A well-shaped outline leads to a sharper, more focused article.

---

## Creating a New Outline

Navigate to **Content → Outlines** in the sidebar, then click **New Outline**.

### Step 1 — Target Keyword

Enter the primary keyword you want the article to rank for. This keyword drives the entire generation: it appears in the AI prompt, is used by the SEO scoring engine, and is checked against the finished article's title, headings, and body density.

> **Tip:** Use the keyword exactly as a searcher would type it. Avoid stuffing variants here — the AI will naturally include related terms throughout the body.

### Step 2 — Article Title (Optional)

You can supply a suggested title. If you leave it blank, the AI will propose one when the outline is generated. You can override the suggested title before or after article generation.

### Step 3 — Target Word Count

Set an approximate word count. The AI treats this as a target, not a strict ceiling. Common ranges:

| Use Case | Suggested Range |
|---|---|
| News / quick answer | 600 – 900 words |
| Standard blog post | 1,000 – 1,500 words |
| In-depth guide | 2,000 – 3,500 words |
| Pillar / cornerstone content | 4,000 – 6,000 words |

### Step 4 — Sections

Sections define the H2 headings that will appear in the article. You can:

- **Let the AI suggest sections** — click **Generate Outline** with the keyword and word count filled in, and the AI will propose a set of sections based on search intent and topic coverage.
- **Add sections manually** — click **Add Section** to type each heading yourself. Drag the handles to reorder them.
- **Mix both** — generate first, then edit, add, or remove sections as needed.

Each section can also carry an optional **description** — a brief note to the AI about what that section should cover. These are especially useful for product-specific sections where the AI would not otherwise know your angle.

> **Tip:** Aim for 4–8 sections for a standard article. Fewer than 4 sections tends to produce shallow coverage; more than 10 can make the article feel disjointed unless the word count target is also high.

---

## AI-Generated vs Manual Outlines

### AI-Generated

Click **Generate Outline** on the creation form. The AI reads the keyword, word count, and any active [AI Settings](/docs/content-generation/ai-settings) (writing style, voice, custom instructions, Knowledge Vault context) to produce a set of sections that match the likely search intent.

Generation takes a few seconds. Once complete, the outline is saved as a draft and you are taken directly to the outline detail view to review the suggested sections.

### Manual

If you prefer full control, skip the **Generate Outline** button and add sections yourself using the **Add Section** form. This is useful when you are following an existing content brief or duplicating a structure from a previous article.

---

## Editing Sections Before Generation

On the outline detail page you can:

- **Edit** any section heading by clicking its text.
- **Add** a description to guide the AI for that section.
- **Reorder** sections by dragging the handle on the left.
- **Delete** a section with the trash icon.

Changes are saved automatically. You do not need to click a Save button.

> **Tip:** If you are using Knowledge Vault sources, add a section description like "Draw on our product documentation for this section" to guide the AI toward your uploaded reference material.

---

## Outline Statuses

| Status | Meaning |
|---|---|
| **Draft** | The outline exists but no article has been generated from it yet. |
| **Generating** | An article generation job is currently running for this outline. |
| **Completed** | At least one article has been generated from this outline. |
| **Failed** | Generation was attempted but encountered an error. The outline itself is intact and you can retry. |

An outline with **Completed** status can still be edited. Editing the outline after generation does not alter the existing article — it only affects future generation runs.
