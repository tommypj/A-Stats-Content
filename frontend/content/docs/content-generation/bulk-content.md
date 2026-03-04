## What Is Bulk Generation?

Bulk generation lets you queue dozens of articles from a list of keywords in a single operation. Instead of creating an outline and generating each article one by one, you supply the keyword list, configure the job settings once, and A-Stats handles the rest in the background.

This is the fastest way to build out a content cluster, populate a programmatic SEO template, or cover an entire topic category without manual repetition.

---

## Creating a Bulk Job

Navigate to **Content → Bulk Generation** and click **New Bulk Job**.

### Step 1 — Job Name

Give the job a descriptive name so you can identify it later (e.g., "Q2 SaaS Comparison Pages" or "Local Landing Pages — May 2025").

### Step 2 — Add Keywords

You have two input methods:

**CSV upload**

Download the CSV template from the creation form. The required column is `keyword`. Optional columns:

| Column | Purpose |
|---|---|
| `keyword` | Required. The target keyword for each article. |
| `title` | Override the AI-suggested title for that article. |
| `word_count` | Override the job-level word count target for that row. |
| `notes` | Passed as a section description hint to the AI. |

Upload your completed CSV and the platform previews the parsed rows before you confirm.

**Manual keyword list**

If your list is short (under 20 keywords), paste them directly into the text area — one keyword per line. The platform converts each line to a row in the job.

> **Tip:** Avoid adding the same keyword twice in one bulk job. Duplicate keywords produce near-identical articles and waste generation credits. Run a deduplication pass on your keyword list before uploading.

### Step 3 — Job Settings

These settings apply to every article in the job unless overridden at the row level in the CSV:

- **Target word count** — Approximate length per article.
- **Writing style and voice** — Defaults to the project's AI Settings. You can override here for this job only.
- **Knowledge Vault** — Uses the project's active sources by default.

### Step 4 — Submit

Click **Start Bulk Job**. The job is queued immediately. Generation runs sequentially in the background — each article is generated one at a time to maintain quality and avoid rate-limit issues with the AI provider.

---

## Monitoring Progress

Open **Content → Bulk Generation** to see all bulk jobs and their current status.

### Job Statuses

| Status | Meaning |
|---|---|
| **Queued** | The job is waiting to start. |
| **Processing** | Articles are being generated. The progress bar shows completed vs total. |
| **Completed** | All items finished (some may have failed — check the item list). |
| **Failed** | The entire job encountered a blocking error (e.g., generation limit hit). |

Click a job name to open the detail view. Each keyword row shows its individual status (**Pending**, **Generating**, **Done**, **Failed**) and links to the generated article when available.

---

## Retrying Failed Items

Individual items within a completed or failed job can be retried without resubmitting the whole job.

1. Open the bulk job detail view.
2. Filter the item list by **Status: Failed**.
3. Click **Retry Failed Items**.

The platform re-queues only the failed rows. A new generation credit is consumed for each retried item.

> **Tip:** Before retrying, check whether the failures share a pattern — for example, all failing items have unusually long keywords or special characters. Fix the underlying data issue first, or the retry will fail again.

If the job itself is still processing (not yet completed), the retry button is disabled. Wait for the current run to finish before retrying.

---

## Usage Limits for Bulk Generation

Bulk jobs draw from the same monthly article generation pool as single-article generation. There is no separate bulk credit — every article generated in a bulk job counts as one credit toward your plan's monthly limit.

| Plan | Monthly Articles (Shared with Single Generation) |
|---|---|
| Free | 3 |
| Starter | 30 |
| Pro | 100 |
| Enterprise | 300 |

If a bulk job is submitted when you have fewer remaining credits than the number of keywords in the job, the job will generate as many articles as your remaining credits allow and then stop. The remaining rows are left in **Pending** status. Upgrade your plan or wait for the monthly reset to continue.

> **Tip:** Before starting a large bulk job, check your remaining credits in **Settings → Billing**. It is easier to plan capacity before a job starts than to piece together partial output afterward.

### Rate Limit

You can submit a maximum of **5 bulk job creation requests per minute**. If you are running automation scripts or integrations that create bulk jobs programmatically, build in a delay between requests to stay within this limit.
