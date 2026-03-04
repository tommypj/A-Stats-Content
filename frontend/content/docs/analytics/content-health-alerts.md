## What Is Content Decay

Content decay describes the gradual loss of search visibility that affects most published articles over time. A page that ranked in position 4 for a key term may slip to position 9 six months later — not because anything broke, but because competitors published fresher content, search intent shifted, or Google updated its quality signals.

Left unaddressed, decaying content loses clicks steadily while continuing to consume crawl budget and internal link equity. A-Stats monitors your connected GSC data continuously and raises alerts when a page's performance drops past configurable thresholds, so you can act before a slip becomes a freefall.

> Content decay detection requires a connected Google Search Console account. See the Connecting Google Search Console guide if you have not set that up yet.

## How Alerts Work

A-Stats evaluates each indexed page in your GSC property on a rolling basis. The evaluation compares the most recent 28-day window against the prior 28-day window for three signals:

- **Position decline** — Average ranking position has dropped.
- **Click decline** — Absolute clicks have fallen.
- **Impression decline** — Search impressions have declined, suggesting reduced indexing coverage or topic relevance.

When a page crosses a threshold on one or more signals, an alert is created and appears in **Analytics → Content Health**.

Alerts are generated automatically — you do not need to manually run scans. The system checks for decay on a daily schedule.

## Alert Severity Levels

Each alert is assigned a severity based on how much performance has dropped:

- **Critical** — Position dropped 10+ places, or clicks declined more than 50% period-over-period. Immediate attention recommended.
- **High** — Position dropped 5–9 places, or clicks declined 25–50%. Prioritize these within the week.
- **Medium** — Position dropped 3–4 places, or clicks declined 10–24%. Worth investigating during your next content review cycle.
- **Low** — Minor dip, possibly normal variance. Monitor rather than act immediately.

> Tip: Focus on Critical and High alerts first. Low severity alerts often resolve on their own within 2–4 weeks as Google re-evaluates freshness signals.

## Viewing Alerts

Navigate to **Analytics → Content Health** from the sidebar. The page shows:

- A health score for your overall content library (percentage of pages without active alerts).
- Summary cards for total alerts, alerts by severity, and resolved alerts.
- A filterable, paginated table of all active alerts.

You can filter alerts by type (position, clicks, impressions), severity, and resolution status. Clicking an alert row expands it to show the full metric comparison: the before and after values for the affected page alongside an AI-generated recovery suggestion.

## Responding to Decay Alerts

### Review the Page

Before making changes, open the affected article in your content editor and read it critically. Ask:

- Is the information still accurate and up to date?
- Does it fully cover the search intent behind its target keyword?
- Is it shorter or thinner than top-ranking competitors?
- Are internal links pointing to this page still relevant?

### Use AI Recovery Suggestions

Each alert includes an **AI Recovery Suggestion** panel. Click **Suggest Fix** on any alert to generate a tailored recommendation based on the page's content and the keywords it was ranking for. Suggestions typically include specific sections to expand, angle adjustments, or structural changes.

> Tip: AI suggestions are a starting point, not a prescription. Use them alongside a manual review of the top 3–5 pages currently outranking yours for the target query.

### Re-optimizing the Content

Common recovery actions based on decay type:

- **Position decline**: Expand thin sections, add an FAQ block targeting long-tail variants, refresh statistics and examples, strengthen internal linking.
- **Click decline with stable position**: Rewrite the title tag and meta description to improve CTR without changing the URL or heading structure.
- **Impression decline**: The page may have fallen out of Google's index or had its topic authority reduced. Consider merging it with a related stronger article or adding significantly more depth.

## Resolving Alerts

After you have taken action on a page, mark the alert as **Resolved** using the button in the alert row. Resolved alerts are archived and tracked so you can review what was done and when.

A-Stats will continue monitoring resolved pages. If performance drops again after resolution, a new alert will be raised automatically.

## Alert Retention

Alerts older than 90 days are automatically removed from the system. If a page is still underperforming after 90 days, a fresh alert will be generated at the next evaluation cycle.
