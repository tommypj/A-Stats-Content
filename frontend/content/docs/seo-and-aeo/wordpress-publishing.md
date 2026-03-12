## WordPress Publishing

A-Stats connects directly to your WordPress site, letting you publish finished articles with a single click. Every piece of metadata --- title, excerpt, featured image, SEO fields, categories, and tags --- is pushed alongside the content, so there is no manual re-entry on the WordPress side.

### What Gets Published

When you publish an article from A-Stats to WordPress, the following data is sent in one operation:

| Field | Details |
|---|---|
| **Article Content** | Full HTML body, including heading structure, images, and formatting |
| **Title** | The article title as configured in A-Stats |
| **Excerpt** | Auto-generated or manually written summary for archive pages and feeds |
| **Featured Image** | The selected or AI-generated featured image, uploaded to your WordPress media library |
| **SEO Title** | Optimized page title for search engines (pushed to your SEO plugin) |
| **SEO Description** | Meta description optimized against A-Stats scoring (pushed to your SEO plugin) |
| **Categories** | Mapped to existing WordPress categories or created if new |
| **Tags** | Applied as WordPress tags for taxonomy and internal linking |

All of this is handled in a single request. There is no partial publish, no draft-then-edit workflow, and no copy-pasting between systems.

### How It Fits Into the Content Workflow

WordPress publishing is the final step in the A-Stats content pipeline, not a separate process. A typical workflow looks like this:

1. **Generate or write** an article using the AI pipeline or the manual editor
2. **Optimize** using the real-time SEO and AEO scoring system
3. **Generate images** using the built-in AI image generation tools
4. **Review** the finished article with all metadata in place
5. **Publish to WordPress** with one click

The article arrives on your WordPress site fully formed --- optimized content, metadata, featured image, and taxonomy all applied. Your WordPress site does not need any special plugins beyond a standard SEO plugin to receive the metadata fields.

### Connection Setup

Connecting your WordPress site requires a one-time setup using read-only OAuth credentials. A-Stats communicates with your site through the WordPress REST API, which is available on all modern WordPress installations (version 4.7 and later) without additional plugins.

Once connected, your WordPress site appears as a publishing target on every article in your dashboard.

### Designed for Scale

For teams managing multiple WordPress sites --- whether an agency handling client blogs or a media company running a network of properties --- each site can be connected independently. Articles can be directed to the appropriate site at publish time, making A-Stats a centralized content hub for distributed publishing.

> **Tip:** Pair WordPress publishing with the Content Calendar to schedule articles for future publication. Content is pushed to WordPress at the scheduled time with all metadata intact, enabling hands-off editorial workflows.

### No Lock-In

Content published to WordPress is standard WordPress content. If you ever stop using A-Stats, your articles, images, categories, and tags remain on your WordPress site exactly as they were published. There is no proprietary formatting, no shortcodes, and no dependency on A-Stats for the published content to render correctly.
