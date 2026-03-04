## Why Connect Google Search Console

Google Search Console (GSC) is the most accurate source of search performance data for your website. Connecting your GSC account unlocks keyword tracking, page-level click and impression data, position trends, and the content decay detection system that automatically alerts you when a page starts losing search visibility.

Without a GSC connection, analytics features in A-Stats are limited to content scoring and AI-generated insights. With it, every article you publish can be tracked against real search data from Google.

## What You Need Before Starting

- A Google account that has been granted access to your property in GSC. You must be listed as an **Owner** or **Full User** — Restricted Users cannot grant OAuth access.
- Your website must already be verified in Google Search Console. A-Stats does not verify properties; it reads from properties you have already set up.
- Pop-ups must be allowed for the A-Stats domain in your browser, since the OAuth flow opens a Google authorization window.

## Connecting Your Account

### Step 1 — Open the Integrations Panel

Navigate to **Settings → Integrations** from the main dashboard sidebar. You will see a Google Search Console card showing a "Not connected" status.

### Step 2 — Start the OAuth Flow

Click **Connect Google Search Console**. A-Stats will redirect you to Google's authorization page. Sign in with the Google account that has access to your GSC property.

### Step 3 — Review and Approve Permissions

Google will show you a permissions screen. A-Stats requests the following scopes:

- `https://www.googleapis.com/auth/webmasters.readonly` — Read-only access to your GSC search analytics data.

A-Stats does not request write access and cannot modify your GSC settings or data. Click **Allow** to continue.

### Step 4 — Select Your Property

After authorizing, you will be returned to A-Stats and prompted to choose which GSC property to connect. Select the property that matches your website. If you manage multiple properties, you can connect one per A-Stats project.

> Tip: If your site exists as both `https://example.com` and `https://www.example.com`, choose whichever variant has the most data in GSC — usually the canonical version.

### Step 5 — Confirm the Connection

Once a property is selected, the integration card will update to show a green "Connected" badge along with your property URL. Initial data sync begins immediately and typically completes within a few minutes for sites with moderate search history.

## What Data Becomes Available

After connecting, the following features are enabled or enhanced:

- **Keywords dashboard** — Top queries driving traffic, with clicks, impressions, CTR, and average position.
- **Page performance** — Per-URL breakdown of all search analytics metrics.
- **Position tracking** — Historical position charts for individual keywords and pages.
- **Content decay alerts** — Automated monitoring that flags pages whose position or clicks have dropped significantly week-over-week or month-over-month.
- **Article performance tab** — Each article in your content library gains a real-data performance panel drawn from GSC.

> Note: GSC data has a 2–3 day lag built into the API. Data for the most recent 2 days may be incomplete or absent. This is a Google-side limitation and not an A-Stats issue.

## Troubleshooting Auth Issues

**"No properties found after connecting"**
Your Google account may not have access to any verified GSC properties. Log into [search.google.com/search-console](https://search.google.com/search-console) and confirm properties appear there first.

**"Authorization failed" or redirect error**
Clear your browser cookies for both Google and A-Stats, then retry. If you are using a browser extension that blocks third-party cookies, temporarily disable it for the OAuth flow.

**Data stopped syncing**
OAuth tokens expire or get revoked if you change your Google account password or revoke app access. Go to **Settings → Integrations**, disconnect GSC, and reconnect to issue a fresh token.

**Wrong property was connected**
Disconnect the current property from **Settings → Integrations** and repeat the connection flow to select a different one.

**"Insufficient permissions" error**
Your Google account role in GSC is set to Restricted User. Ask the property owner to upgrade your role to Full User or Owner, then reconnect.
