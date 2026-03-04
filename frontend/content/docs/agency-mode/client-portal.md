## What is the Client Portal?

The client portal is a read-focused interface that lets your clients view their content, analytics, and reports without needing a full platform account. It is accessed via a unique, shareable link that you generate per client. The portal displays your agency's branding and shows only the data associated with that specific client's projects.

## How Portal Access Works

Portal access is token-based. When you enable the portal for a client, the platform generates a secure access token and constructs a unique URL. Anyone who has that URL can view the portal as that client — there is no separate login required.

This makes sharing simple: you paste the link into an email, Slack message, or project management tool. The client clicks it and immediately sees their branded dashboard.

Portal tokens are valid for **365 days** from the date they are generated. After 365 days, the token expires and the client receives a "portal access expired" message. You can regenerate a new token at any time to restore access.

> **Tip:** Because anyone with the portal link can view the client's portal, treat portal links with appropriate care. If a link is accidentally shared with the wrong party, regenerate the token immediately to invalidate the old link.

## Enabling Portal Access for a Client

1. Navigate to **Agency** in the sidebar and open the client record.
2. Click the **Portal** tab within the client record.
3. Toggle **Enable Client Portal** to on.
4. The portal URL appears with a copy button.
5. Click **Copy Link** and share it with your client.

A notification email is sent to the client's primary contact email when the portal is first enabled, containing the portal link and brief instructions.

## What Clients See in the Portal

Once in the portal, clients can view:

### Content Overview
- A list of all articles in their associated projects, with status (Draft, In Review, Published, Scheduled)
- Outline summaries and status
- Content production metrics for the current month

### Analytics Reports
- Organic search performance data (impressions, clicks, CTR, position) pulled from Google Search Console
- Content health indicators and decay alerts
- AEO (Answer Engine Optimization) scores where available

### Social Media
- Scheduled and published social media posts
- Post performance metrics (impressions, engagement) for connected accounts

Clients cannot create, edit, publish, or delete any content. The portal is a viewing and review interface only.

## Sharing Content for Approval

To direct a client's attention to specific content:

1. Open the client's portal settings.
2. Click **Share Content Link** next to any article or report.
3. The link takes the client directly to that item within the portal.

Alternatively, send the client the top-level portal URL and ask them to navigate to the relevant section. Articles are sorted by status, with "In Review" items appearing first to make pending approvals easy to find.

## Portal Permissions

The current portal is read-only for all clients. Clients cannot:
- Edit article content or titles
- Approve or reject articles (approval workflows are managed within your agency dashboard)
- Connect or modify integrations
- Invite other users to the portal

If you need clients to take action on content (for example, marking an article as approved), handle that communication outside the platform and update the article status yourself.

> **Tip:** Use the Notes field on articles to leave messages for client review, such as "Please review Section 3 — the statistics need your sign-off before we publish."

## Regenerating a Portal Token

If a portal link needs to be invalidated (for example, it was shared in error, or the client contact changed):

1. Open the client record and navigate to the **Portal** tab.
2. Click **Regenerate Token**.
3. Confirm the regeneration.

The old URL immediately stops working. The new URL is displayed and can be copied and shared with the client. If portal invite emails are enabled, a new invitation email is sent to the primary contact.

## Disabling Portal Access

To temporarily revoke portal access without deleting the client record:

1. Open the client's **Portal** tab.
2. Toggle **Enable Client Portal** to off.

The portal link stops working immediately. The client's data and the client record are not deleted. Toggle the portal back on at any time to restore access (a new token is generated).

## Portal Link Expiry

Portal tokens expire after 365 days as a security measure. When a token approaches expiry:

- The portal settings page shows an expiry warning.
- You receive an in-app notification 30 days before expiry.

Regenerate the token before it expires to ensure continuity of access for your client. Expired tokens return an error page to the client, asking them to contact their agency for an updated link.
