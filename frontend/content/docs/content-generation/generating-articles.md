## From Outline to Article

Once an outline is ready and its sections look right, you can generate the full article. Open the outline detail page and click **Generate Article**. A-Stats sends the outline — keyword, title, sections, word count target, and any active AI settings — to the AI, which writes each section in sequence and assembles a complete draft.

Generation typically takes 30–90 seconds depending on the target word count and server load. You do not need to stay on the page; the job runs in the background and the article status updates automatically.

---

## What Happens During Generation

1. **Credit check** — A-Stats confirms you have remaining generation credits for your plan. If you are at your limit, you will see an upgrade prompt.
2. **Knowledge applied** — If your project has [Knowledge Vault](/docs/knowledge-vault) sources, the AI draws on relevant information from those documents while writing.
3. **Article written** — The AI writes each section according to its heading and description, following the writing style, voice, and custom instructions set in [AI Settings](/docs/content-generation/ai-settings).
4. **Draft ready** — The finished article is saved to your project as a **Draft**, and one generation credit is deducted.

> **Tip:** Generation credits reset at the start of each billing cycle. You can check your current usage in **Settings → Billing**.

---

## Article Statuses

| Status | Meaning |
|---|---|
| **Draft** | The article has been generated but not yet published. You can edit it freely. |
| **Published** | The article has been pushed to WordPress or manually marked as published. |
| **Archived** | The article has been archived. It remains visible in filtered views. |

Status transitions are intentional — moving an article back from Published to Draft is allowed, but the platform logs each transition so you have a change history.

---

## Generation Limits by Plan

Each plan includes a monthly article generation allowance. Limits apply per user, not per project.

| Plan | Monthly Articles |
|---|---|
| Free | 3 |
| Starter | 30 |
| Pro | 100 |
| Enterprise | 300 |

When the limit is reached, the **Generate Article** button is disabled and a banner explains the restriction. Bulk generation jobs also draw from this same pool.

> **Tip:** If you need more capacity mid-cycle, upgrading your plan resets the counter to your new plan's limit immediately.

---

## Regenerating an Article

You can generate a new article from the same outline at any time. Open the outline, click **Generate Article** again, and a new article is created alongside the previous one. Both articles are retained — the older version is not overwritten.

This is useful when you want to:

- Try a different tone or writing style (adjust AI Settings first, then regenerate).
- Compare two AI drafts and keep the better one.
- Start fresh after heavily editing an outline's sections.

Each regeneration consumes one generation credit.

---

## If Generation Fails

If the AI job encounters an error (timeout, content policy rejection, or an unexpected platform issue), the article is created with a **Failed** status and the outline reverts to **Failed**. No credit is deducted for a failed generation.

To retry:

1. Go to **Content → Outlines** and open the outline.
2. Review the error note shown on the article row.
3. Click **Generate Article** to submit a new job.

If an outline consistently fails, check that it has at least one valid section with a non-empty heading. The platform requires at least one section to proceed.
