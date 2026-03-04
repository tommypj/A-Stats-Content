## What Is Revenue Attribution

Revenue attribution answers a question that most content teams struggle to answer: which articles actually produce customers and revenue, not just traffic?

A page might attract 10,000 monthly visitors without generating a single conversion. Another page with 500 visitors might close 20 sales because it targets buyers at the bottom of the funnel. Without attribution, you cannot tell the difference — and you risk investing time in content that looks successful by traffic metrics but contributes nothing to business outcomes.

A-Stats revenue attribution connects each piece of content to the conversions and revenue it influenced by tracking which pages users visited before completing a defined goal.

## Setting Up Conversion Goals

Before attribution data can appear, you must define what a "conversion" means for your business.

### Navigate to Attribution Settings

Go to **Analytics → Revenue Attribution** and click **Manage Goals**. If this is your first visit, the goals list will be empty.

### Create a Goal

Click **Add Goal** and fill in the following fields:

- **Goal name** — A descriptive label (e.g., "Free trial signup", "Enterprise contact form", "Checkout complete").
- **Goal URL** — The URL a user lands on after completing the conversion (a thank-you page, success page, or confirmation URL). Attribution is triggered when a session that passed through tracked content pages reaches this URL.
- **Revenue value** — Optional. Assign a monetary value per conversion to calculate attributed revenue. If your conversions have variable value (e-commerce orders), leave this field blank and enter values manually or via integration.

> Tip: Thank-you pages and confirmation pages work best as goal URLs because they are only reachable after a genuine conversion. Avoid using checkout page URLs, which users may visit without completing a purchase.

### Goal Matching

A-Stats matches goals using exact URL matching by default. Query parameters and trailing slashes are normalized automatically, so `https://example.com/thank-you/` and `https://example.com/thank-you` are treated as the same goal URL.

## How Attribution Is Calculated

A-Stats uses a **last-touch attribution model** for the default report view. Under this model, the content page a user visited most recently before converting receives full credit for the conversion.

The attribution window is 30 days by default. A conversion is attributed to content if the user visited a tracked article within the 30 days prior to completing the goal.

> The attribution model reflects user journeys through your content, not ad clicks or referral sources. It is designed specifically for content teams measuring organic content impact.

## Connecting Content to Revenue

### The Attribution Report

Navigate to **Analytics → Revenue Attribution** to view the main report. The report table lists every article and page that received attribution credit during the selected period, with columns for:

- **Attributed conversions** — Number of goals completed by users who visited this page.
- **Attributed revenue** — Total monetary value from those conversions (if goal values are set).
- **Unique converting visitors** — Number of distinct users who both visited this page and later converted.
- **Conversion rate** — Attributed conversions divided by total unique visitors to the page.

Sort by attributed revenue to immediately see which content is most valuable to your business.

### Comparing Content Value vs. Traffic

The report intentionally surfaces the gap between traffic and value. Filter the table to show only pages with more than 100 monthly visitors, then sort by conversion rate. Pages with high traffic but near-zero conversions are worth re-examining for intent alignment. Pages with modest traffic but strong conversions deserve more internal linking and promotion to send more users to them.

## Viewing Attribution Reports

### Date Range

Use the date range picker at the top of the attribution page to examine different periods. Monthly views are most useful for identifying sustained content-revenue relationships. Shorter windows (7–14 days) can be used to evaluate the impact of a specific content update.

### Filtering by Goal

If you have multiple conversion goals defined, use the **Goal** filter to isolate attribution for a specific goal type. For example, filter to "Enterprise contact form" to see which articles drive enterprise leads specifically, separate from self-serve signups.

### Individual Article Breakdown

Clicking any row in the attribution report opens a detail panel showing the individual conversions attributed to that page: timestamps, goal names, and revenue values. This is useful for reporting to stakeholders and for validating that attribution is firing correctly for a specific article.

## Troubleshooting Attribution

**No data appearing after setup**
Attribution data accumulates over time as users complete goals. If goals were just configured, allow at least 7 days before expecting meaningful data to appear.

**Goal URL not matching**
Double-check that the goal URL you entered exactly matches the URL users land on after converting. Use your browser's address bar on the confirmation page to copy the exact URL, including any path segments.

**Lower conversion numbers than expected**
Attribution only counts sessions where users passed through a tracked content page before converting. Direct visits to your checkout or signup page without prior content engagement will not appear in the content attribution report.
