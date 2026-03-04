## The Keywords Dashboard

The Keywords dashboard surfaces every search query that has driven at least one click or impression to your site within the selected date range. Data is pulled directly from your connected Google Search Console property, so figures here match what you see in GSC — no sampling, no estimation.

To access it, go to **Analytics → Keywords** from the sidebar.

### Key Metrics Explained

Each row in the keywords table shows four core metrics:

- **Clicks** — The number of times a user clicked your result in Google Search for that query.
- **Impressions** — How many times your result appeared in search, whether or not it was clicked.
- **CTR (Click-Through Rate)** — Clicks divided by impressions, expressed as a percentage. A higher CTR for a given position suggests a compelling title and meta description.
- **Average Position** — Your average ranking position for the query across the date range. Position 1 is the top organic result. Note that this is an average, so a page ranking between 1 and 3 will show a position like 1.8.

> Tip: A query with high impressions but low CTR often signals that your title tag or meta description needs improvement. The content may be ranking but not compelling enough to click.

### Sorting and Filtering

Click any column header to sort by that metric. You can sort ascending or descending.

Use the search box at the top of the table to filter queries by keyword substring. For example, typing "best" will narrow the table to queries containing that word.

The **Date Range** selector at the top of the page applies to all metrics on the dashboard. Options include Last 7 days, Last 28 days, Last 3 months, Last 6 months, and Last 12 months. Custom ranges are also supported.

## Page Performance

Switch to the **Pages** tab within the Keywords dashboard to see performance broken down by URL rather than by query. Each row represents a unique page on your site.

This view answers the question: "Which pages on my site are actually getting search traffic?"

### Reading the Pages Table

Each page entry shows the same four metrics (clicks, impressions, CTR, position) aggregated across all queries that led to that URL. Clicking a page row expands it to show the top queries driving traffic specifically to that URL.

> Tip: Cross-reference your top pages here with your article list in the Content section. Pages with high impressions but low clicks are strong candidates for title and meta description optimization.

## Position Tracking

The **Position Chart** at the top of the Keywords dashboard shows your site's average position over time for the selected date range. Dips in this chart correlate with algorithm updates or competitors outranking you.

For keyword-level position tracking, click any query in the table to open a detail panel. The panel shows a position trend line for that specific keyword over the selected period.

A-Stats flags keywords where your position has declined by 3 or more places over the past 30 days with an amber indicator. These represent opportunities where proactive re-optimization can recover lost rankings before the drop compounds.

## Impressions vs. Clicks — Understanding the Difference

A common point of confusion: impressions count anytime your page appears in a search result, even if it is below the fold and the user never scrolls to it. Clicks only count when someone actually taps or clicks your result.

This means:
- Very high impressions with near-zero clicks usually means you are ranking on page 2 or 3 — users rarely scroll that far.
- High impressions with moderate clicks at position 1–3 is normal healthy performance.
- If clicks drop while impressions stay flat, your CTR is falling — likely a title/meta issue, not a ranking issue.

## Filtering by Date Range

All data on the Keywords and Pages tabs respects the global date range picker. For trend analysis, compare two periods using the **Compare** toggle, which adds a second line to charts showing the prior equivalent period. This quickly reveals whether metrics are improving or declining relative to the same time window in the past.

> Note: GSC data is not available in real time. Expect a 2–3 day lag. Filtering to "Last 7 days" will typically show data through 2–3 days ago, not through yesterday.
