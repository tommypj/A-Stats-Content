## Overview

The platform sends notifications to keep you informed about important events — content that needs attention, billing changes, team activity, and analytics alerts. You can control which notifications you receive and how you receive them.

Notification preferences are in **Settings > Notifications**.

## Types of Notifications

### Content Notifications
Events related to articles, outlines, and AI generation:

| Notification | Default | Description |
|-------------|---------|-------------|
| Article published | On | Sent when an article is published to WordPress or another channel |
| Generation complete | On | Sent when a bulk generation job finishes |
| Generation failed | On | Sent when a generation attempt fails due to an error |
| Article in review | On | Sent when an article's status is changed to "In Review" |
| Content decay alert | On | Sent when an article shows signs of declining search performance |

### Team Notifications
Events related to your projects and team:

| Notification | Default | Description |
|-------------|---------|-------------|
| Team invitation accepted | On | Sent when someone you invited joins a project |
| New member joined | Off | Sent when any member joins a project you are in |
| Member role changed | Off | Sent when a team member's role is updated |
| Project archived | On | Sent when a project you are a member of is archived |

### Social Media Notifications
Events related to scheduled social media posts:

| Notification | Default | Description |
|-------------|---------|-------------|
| Post published | Off | Sent when a scheduled post is published successfully |
| Post failed | On | Sent when a scheduled post fails to publish |
| Account disconnected | On | Sent when a social media account's token expires or is revoked |

### Billing Notifications
Events related to your subscription and payments:

| Notification | Default | Description |
|-------------|---------|-------------|
| Payment successful | On | Sent when a subscription payment is processed |
| Payment failed | On | Sent when a payment attempt fails |
| Subscription renewed | On | Sent at each billing cycle renewal |
| Subscription canceled | On | Sent when your subscription is canceled |
| Usage at 80% | On | Sent when monthly generation usage reaches 80% of limit |
| Usage limit reached | On | Sent when monthly generation usage reaches 100% |
| Plan upgraded | On | Sent when your plan is upgraded |
| Plan downgraded | On | Sent when your plan changes to a lower tier |

### Analytics Notifications
Events related to SEO and performance monitoring:

| Notification | Default | Description |
|-------------|---------|-------------|
| Weekly analytics summary | Off | Weekly email digest of organic traffic performance |
| Content decay detected | On | Sent when content decay algorithms flag a new article |
| New ranking opportunity | Off | Sent when analytics identifies a new content opportunity |

## Email Notifications

Email notifications are sent to your account's primary email address. Each notification type can be toggled on or off independently.

To manage email notifications:
1. Go to **Settings > Notifications**.
2. Find the **Email Notifications** section.
3. Toggle individual notification types on or off.
4. Click **Save Preferences**.

> **Tip:** At minimum, keep billing notifications and generation failure notifications enabled. These are the notifications most likely to require immediate action from you.

### Notification Digest

Instead of receiving individual emails for every event, you can opt for a **Daily Digest** mode. When enabled, most email notifications are batched into a single daily email sent at your configured delivery time (default: 8:00 AM in your account timezone).

Critical notifications (payment failed, generation error, account security events) bypass the digest and are sent immediately regardless of this setting.

To enable the daily digest:
1. Go to **Settings > Notifications > Email Notifications**.
2. Toggle **Daily Digest Mode** to on.
3. Set your preferred delivery time.
4. Click **Save**.

## In-App Notifications

In-app notifications appear in the notification bell icon in the top-right corner of the dashboard. The bell shows an unread count badge when new notifications are waiting.

Click the bell to open the notification panel, which lists recent notifications in reverse chronological order. Each notification shows:
- A brief description of the event
- A timestamp
- A link to the relevant content or settings page
- A read/unread indicator

### Marking Notifications as Read
- Click any notification to mark it as read and navigate to the relevant page.
- Click **Mark all as read** at the top of the notification panel to clear the unread count without navigating anywhere.

In-app notifications are retained for **90 days** and then automatically cleared. If you need to reference a past notification older than 90 days, check your email (if email notifications were enabled for that type).

### In-App Notification Controls
Certain in-app notification types can be disabled if they are too frequent or not relevant to your workflow. Go to **Settings > Notifications > In-App Notifications** to control which event types create in-app notification entries.

## Agency Mode Notifications

If you use agency mode, additional notification types are available:

| Notification | Description |
|-------------|-------------|
| Portal token expiring | Sent 30 days before a client portal link expires |
| Portal token expired | Sent when a client portal token expires |
| Client content activity | Optional summary of content production per client |

Agency notifications appear in both the standard notification panel and email, following the same preferences you set for other notification types.

## Notification Troubleshooting

**Not receiving emails?**
- Check your spam or junk folder. Whitelist the platform's sending domain to ensure delivery.
- Verify your email address in **Settings > Profile** is correct and verified.
- Check that the specific notification type is toggled on in **Settings > Notifications**.

**Too many notifications?**
- Enable Daily Digest mode to batch most notifications into one email per day.
- Review and disable notification types that are not relevant to your workflow.

**Notification emails arriving at wrong time?**
- Verify your timezone in **Settings > Profile**. Digest delivery time and scheduled notification times are based on your account timezone.
