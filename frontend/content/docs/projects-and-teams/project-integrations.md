## Overview

Project integrations connect the platform to external tools so you can publish content, pull analytics data, and distribute to social media without leaving your workflow. All integrations are configured per project — each project maintains its own independent set of connections.

Access integrations at **Project Settings > Integrations**.

## WordPress Integration

### What It Does
Connecting WordPress enables one-click publishing of finished articles directly to your WordPress site. Articles are sent via the WordPress REST API and can be published immediately or saved as drafts.

### How to Connect

1. Open **Project Settings > Integrations > WordPress**.
2. Enter your WordPress site URL (for example, `https://yoursite.com`).
3. Enter your WordPress username.
4. Generate an **Application Password** in WordPress (Users > Profile > Application Passwords) and paste it here.
5. Click **Test Connection** to verify the credentials work.
6. Click **Save**.

> **Tip:** Application Passwords are available in WordPress 5.6 and later. They are separate from your login password and can be revoked at any time from the WordPress admin without affecting your account.

### Publishing Articles

Once connected, an article editor gains a **Publish to WordPress** button. You can:
- Publish immediately (sets status to Published in WordPress)
- Save as draft (for further editing in WordPress before publishing)
- Set a featured image from your Image Library that is uploaded to WordPress with the article

### Troubleshooting WordPress Connection

| Error | Likely Cause | Fix |
|-------|-------------|-----|
| 401 Unauthorized | Wrong username or application password | Re-enter credentials |
| 403 Forbidden | User lacks Editor role in WordPress | Assign the correct role in WordPress |
| Connection refused | REST API disabled or blocked | Enable REST API in WordPress settings |

## Google Search Console (GSC) Integration

### What It Does
Connecting GSC pulls organic search performance data — impressions, clicks, click-through rate, and average position — for the website associated with this project. This data powers analytics features including Content Decay Detection and SEO scoring.

### How to Connect

1. Open **Project Settings > Integrations > Google Search Console**.
2. Click **Connect Google Search Console**.
3. You are redirected to Google's OAuth authorization screen.
4. Select the Google account that has access to the GSC property for this project's website.
5. Grant the requested permissions (read-only access to Search Console data).
6. You are redirected back to the platform with the connection established.

> **Tip:** You must have the Google account that owns or has verified the property in GSC. If your site is managed by a different Google account than the one you use for this platform, log into that account in your browser before clicking Connect.

### Data Freshness

Google Search Console data lags by approximately 2–3 days. Impressions and click data you see in analytics are not real-time; they reflect performance from 2–3 days prior. This is a Google-side limitation.

### Disconnecting GSC

Click **Disconnect** next to the GSC connection. This removes the stored OAuth tokens. Historical data already pulled is not deleted; it remains visible in analytics. To refresh data after reconnecting, trigger a manual data sync from the analytics section.

## Social Media Accounts

### Supported Platforms

The platform supports scheduling and publishing to:
- **LinkedIn** — Personal profiles and company pages
- **X (Twitter)** — Personal accounts
- **Facebook** — Pages (not personal profiles)
- **Instagram** — Business and Creator accounts connected via Facebook

### Connecting a Social Account

1. Open **Project Settings > Integrations > Social Media**.
2. Click **Connect Account** next to the platform you want to add.
3. Authorize the platform's OAuth screen.
4. Select the specific page or profile to connect (for LinkedIn company pages and Facebook pages, you will see a list of pages you manage).
5. Click **Confirm**.

The connected account appears in the social accounts list with its name, platform, and connection status.

### Connection Health

Social media access tokens expire periodically. When a token expires:
- The account status changes to **Reconnect Required** in the integrations list.
- Scheduled posts to that account will fail with a notification.
- Click **Reconnect** and re-authorize to restore the connection.

> **Tip:** Check your social account connection status regularly, especially around quarterly token expiry periods. Setting a calendar reminder to review integrations once a month prevents unexpected publishing failures.

### Removing a Social Account

Click the remove icon next to an account in the social accounts list. This disconnects the account and removes the stored credentials. Scheduled posts targeting that account will be set to error status and will not be sent.

## Managing Multiple Integrations

Projects can have multiple integrations active simultaneously. A typical well-connected project might have:
- One WordPress connection (for publishing)
- One GSC connection (for analytics)
- Two or three social accounts (LinkedIn, X, Facebook)

There is no limit to the number of social accounts per project. You can connect multiple accounts from the same platform — for example, both a personal LinkedIn profile and a company page.
