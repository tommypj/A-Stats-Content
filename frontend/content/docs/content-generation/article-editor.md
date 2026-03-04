## Opening the Editor

Click any article title from **Content → Articles** to open the full-screen editor. The editor is split into two areas: the writing canvas on the left and the scoring/tools panel on the right.

---

## Rich Text Editing

The writing canvas supports standard rich text formatting. You can work directly in the AI-generated text or rewrite sections entirely.

### Text Formatting

| Action | Keyboard Shortcut |
|---|---|
| Bold | `Ctrl + B` / `Cmd + B` |
| Italic | `Ctrl + I` / `Cmd + I` |
| Underline | `Ctrl + U` / `Cmd + U` |
| Heading 2 | Use the toolbar dropdown |
| Heading 3 | Use the toolbar dropdown |
| Bullet list | `-` + Space at line start |
| Numbered list | `1.` + Space at line start |
| Link | `Ctrl + K` / `Cmd + K` |
| Undo | `Ctrl + Z` / `Cmd + Z` |
| Redo | `Ctrl + Shift + Z` / `Cmd + Shift + Z` |

### Structure Guidelines

For best SEO results:
- Use exactly one H1 (the article title field at the top — do not add an H1 inside the body).
- Use H2 for main section headings and H3 for subsections within those sections.
- Keep paragraphs under 150 words for readability.

> **Tip:** The SEO score panel on the right flags heading issues in real time — use it as a live guide while you edit.

---

## SEO Score Panel

The SEO score panel grades the article on 10 checks, each worth up to 10 points, for a total of 100. Scores update a few seconds after you stop typing.

Key checks include:

- **Keyword in title** — Does the exact target keyword appear in the article title?
- **Keyword in first 100 words** — Is the keyword introduced early in the body?
- **Keyword density** — Is the keyword used 0.5%–3% of the time (not too sparse, not stuffed)?
- **Meta description length** — Is the meta description between 120 and 160 characters?
- **Word count** — Does the article meet a minimum content threshold?
- **H2 headings present** — Are there at least two H2 headings in the body?
- **Internal links** — Does the article contain at least one internal link?
- **Readability** — Are sentences and paragraphs within recommended lengths?

Each failing check shows a short explanation of what to fix. Click the check name to jump to the relevant part of the panel.

> **Tip:** A score of 70 or above is a solid foundation. Aim for 80+ before publishing to a competitive keyword.

---

## AEO Score Panel

The AEO (Answer Engine Optimization) score measures how likely the article is to be cited by AI assistants such as ChatGPT, Gemini, or Claude. It checks for:

- **Direct answers** — Does the article open with a clear, concise answer to the implied question?
- **Structured data signals** — Are lists, tables, and definitions used to present facts?
- **Question-format headings** — Do any H2/H3 headings phrase the topic as a question?
- **Factual density** — Are claims supported with specifics (numbers, dates, named sources)?

The AEO score is displayed separately from the SEO score and does not affect it. Both scores are stored with each article version for tracking over time.

---

## AI Improvement Suggestions

The **Improve with AI** button (in the right panel, below the scores) sends the current article content back to the AI with a brief improvement prompt. You can ask the AI to:

- Strengthen the introduction.
- Improve readability and sentence variety.
- Expand a specific section (paste the heading in the prompt box).
- Sharpen the conclusion with a clearer call to action.

The AI returns a revised version of the full article. A diff view highlights the changes before you apply them. You can accept all changes, reject all, or selectively apply paragraph by paragraph.

> **Tip:** Run the AI improvement pass after you have done your manual editing pass. That way the AI works on content that already reflects your subject-matter edits, not just the raw generated draft.

---

## Autosave

The editor saves your work automatically every 30 seconds and whenever you pause typing for more than 5 seconds. The save status indicator in the top-right corner shows **Saved**, **Saving...**, or **Unsaved changes**.

If you close the browser tab while there are unsaved changes, the platform displays a warning prompt asking you to confirm before leaving.

---

## Downloading and Exporting

Use the **Export** menu in the top-right of the editor to download the article:

| Format | Notes |
|---|---|
| **Markdown** | Clean `.md` file, compatible with most static site generators. |
| **HTML** | Full HTML body fragment, ready to paste into any CMS. |
| **Plain text** | Stripped of all formatting, useful for further processing. |

To push directly to WordPress, use the **Publish to WordPress** button. This requires a WordPress integration configured in **Settings → Integrations**. See the [WordPress publishing guide](/docs/integrations/wordpress) for setup steps.
