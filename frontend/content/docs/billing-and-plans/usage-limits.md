## What Counts as a Generation?

Each of the following actions consumes one generation from your monthly limit:

- Generating an AI article from an outline
- Generating an AI content outline
- Regenerating an outline or article (each attempt counts)
- Generating an AI image via Replicate Flux
- Using the "Improve Article" AI feature on an existing article

Viewing, editing, publishing, or scheduling existing content does not consume generations. Querying the Knowledge Vault directly does not consume generations. SEO analysis and AEO scoring do not consume generations.

## Monthly Generation Limits by Plan

| Plan | Monthly Generations |
|------|-------------------|
| Free | 10 |
| Starter | 50 |
| Pro | 150 |
| Enterprise | 300 |

## When the Limit Resets

Your generation count resets on the **first day of each calendar month** at midnight UTC. It does not reset on your billing anniversary date — it resets on the calendar month boundary regardless of when you subscribed.

For example, if you subscribe on March 15, your limit resets on April 1, then May 1, and so on.

> **Tip:** If you are approaching your limit near the end of the month and have urgent content needs, consider spacing generation tasks to the first of the following month when the limit resets, rather than upgrading just to cover a few extra items.

## Checking Your Remaining Limit

Your current usage and remaining generations are visible in two places:

### Settings > Billing
The billing settings page shows:
- Plan name and current limit
- Generations used this month
- Generations remaining this month
- Reset date (first of next month)

### Generation Buttons
When you click any generation button (Generate Article, Generate Outline, Generate Image), the button or surrounding UI shows your current remaining count. If you are at or near the limit, a warning is displayed before you confirm generation.

## What Happens When You Reach the Limit

When your generation count reaches zero:

1. Generation buttons (Generate Article, Generate Outline, Generate Image, Improve Article) are **disabled**.
2. A "Limit Reached" message is shown next to each disabled button.
3. An **Upgrade** link appears inline with the message, taking you directly to the plan upgrade flow.
4. Bulk generation jobs that are queued but not yet started will fail with a limit-exceeded error and mark the affected items as failed.

No existing content is affected. You can continue to read, edit, publish, and schedule content that has already been generated. Only new AI generation is blocked.

## Shared Limit Across a Project

The generation limit is per **user account**, not per project. If you have three projects and one user account, all three projects draw from the same monthly pool of generations.

If multiple team members with Editor or Admin access generate content in your projects, each person's generations are counted against **their own account's limit**, not yours. Inviting editors does not reduce your personal generation allowance.

## Upgrading to Get More Generations

To unblock generation before the monthly reset:

1. Navigate to **Settings > Billing**.
2. Click **Upgrade Plan**.
3. Select a higher plan.
4. The upgrade takes effect immediately, and your new limit (minus what you have already used) becomes available right away.

If you upgrade mid-month, your generation count is **not retroactively reset** — the higher limit simply applies to the remainder of the current month. Your already-consumed generations still count against the new higher limit.

**Example:** You are on Starter (50/month) and have used 48. You upgrade to Pro (150/month). You immediately have 102 remaining generations for the rest of the month (150 - 48 = 102).

## Enterprise Usage Monitoring

Enterprise plan users (300/month) can access detailed usage reports showing:
- Generations by date
- Generations by project
- Generations by content type (article / outline / image)

This helps large teams track where generation capacity is being consumed and forecast whether additional capacity is needed.

## Rollover Policy

Unused generations do **not** roll over to the next month. The limit resets to the full plan amount on the first of each month regardless of how many you used in the previous month.

> **Tip:** If you consistently use only 30–40% of your plan's generations each month, you may be over-provisioned. Consider whether a lower plan tier would meet your actual usage pattern and save on subscription cost.
