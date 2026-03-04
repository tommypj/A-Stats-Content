## WordPress Integration Overview

A-Stats can publish articles directly to your WordPress site using the WordPress REST API. Once connected, you can push any article to WordPress as a draft or live post without copying and pasting content manually. Updates to the article in A-Stats can be synced back to the same WordPress post.

The integration works with any self-hosted WordPress site running version 5.0 or later. WordPress.com sites on a Business plan or higher also support the REST API.

---

## Connecting Your WordPress Site

### Step 1 — Create an Application Password in WordPress

WordPress requires an Application Password for REST API authentication. This is separate from your regular login password.

1. Log in to your WordPress admin panel.
2. Go to **Users > Profile** (or **Users > All Users** and edit your account).
3. Scroll down to the **Application Passwords** section.
4. In the "New Application Password Name" field, enter a label such as "A-Stats."
5. Click **Add New Application Password**.
6. WordPress will display a password in the format `xxxx xxxx xxxx xxxx xxxx xxxx`. Copy this password immediately — it will not be shown again.

> Tip: Use a dedicated WordPress user account for the A-Stats integration rather than your personal admin account. Give it the Editor role so it can publish posts but cannot change site settings.

### Step 2 — Add Credentials in A-Stats

1. In A-Stats, go to **Settings > Integrations**.
2. Under WordPress, click **Connect Site**.
3. Fill in the following fields:
   - **Site URL** — your WordPress site's root URL, e.g., `https://example.com`. Do not include a trailing slash.
   - **Username** — the WordPress username for the account you created the Application Password on.
   - **Application Password** — the password you copied from WordPress, spaces included or removed (both formats are accepted).
4. Click **Test Connection**. A-Stats will make a test API call to verify the credentials are valid.
5. If the test passes, click **Save**. Your site will now appear in the integrations list.

### Troubleshooting Connection Failures

| Error | Likely Cause | Fix |
|---|---|---|
| 401 Unauthorized | Wrong username or password | Re-copy the Application Password from WordPress |
| 403 Forbidden | REST API disabled | Check if a security plugin is blocking the API (see below) |
| Could not reach site | Wrong Site URL | Confirm the URL resolves in a browser and has no redirect |
| SSL error | Self-signed certificate | A-Stats requires a valid SSL certificate on the WordPress site |

**Security plugins blocking the REST API** — plugins like Wordfence, iThemes Security, and All-In-One WP Security can block REST API requests from external IPs. Check your security plugin settings and whitelist A-Stats or temporarily disable the plugin to test.

**Permalink structure** — the WordPress REST API requires pretty permalinks. Go to **Settings > Permalinks** in WordPress and make sure you are not using the Plain (numeric ID) permalink structure.

---

## Publishing an Article

### From the Article Editor

1. Open the article you want to publish.
2. Click the **Publish** button in the top-right toolbar.
3. The publish panel slides out from the right side of the screen.
4. Select your connected WordPress site from the **Destination** dropdown.
5. Choose a status: **Draft** or **Published**.
6. Optionally configure:
   - **Post category** — select from your existing WordPress categories
   - **Post tags** — add tags that exist in WordPress
   - **Featured image** — select an image to use as the WordPress featured image
   - **Publish date** — schedule the post to go live at a future date and time
7. Click **Push to WordPress**.

A-Stats will confirm success with a notification and store the WordPress post ID alongside the article. A link to the live post (or draft preview) appears in the article settings panel under **Published Locations**.

> Tip: Always push as Draft first to review the formatting in the WordPress editor before setting it live. Rich text from A-Stats translates to standard HTML, but custom WordPress themes may render some elements differently.

---

## Draft vs. Published Status

**Draft** — the post is saved in WordPress but is not publicly visible. Use this when you want to review the post, apply a featured image manually, or make final edits in the WordPress editor before going live.

**Published** — the post is immediately visible on your site. Suitable when the article has been fully reviewed and approved in A-Stats.

> Tip: If your workflow involves a human editor reviewing every post before it goes live, always default to Draft in the integration settings. You can change the default in **Settings > Integrations > WordPress > [Site Name] > Default Status**.

---

## Updating Existing Posts

If you make changes to an article in A-Stats that has already been pushed to WordPress, you can sync the update:

1. Open the article in the A-Stats editor.
2. Make your changes and save the article.
3. Click **Publish > Update WordPress Post**.
4. A-Stats will use the stored WordPress post ID to overwrite the existing post content.

The update replaces the post body and title. It does not change the post URL, category, tags, or featured image unless you explicitly update those fields in the publish panel.

> Tip: If you have made significant edits to a post directly in the WordPress editor after the initial push, those changes will be overwritten when you sync from A-Stats. Keep A-Stats as the single source of truth for article content to avoid conflicts.

---

## Managing Multiple WordPress Sites

You can connect more than one WordPress site to a single A-Stats project. This is useful for agency workflows where you manage content for multiple clients.

Each connected site appears as a separate option in the Destination dropdown when publishing. Sites are listed by the label you gave them during setup.

To disconnect a site, go to **Settings > Integrations > WordPress**, click the site, and click **Remove Connection**. Removing the connection does not delete any posts that have already been published to WordPress.

---

## Frequently Asked Questions

**Can I import existing WordPress posts into A-Stats?**
Not currently. The integration is publish-only. You can copy and paste content from WordPress into a new A-Stats article if you want to manage existing posts from A-Stats going forward.

**Does the integration support custom post types?**
Not at this time. A-Stats publishes to the standard `posts` endpoint. Custom post types require API extensions that vary by WordPress theme and plugin setup.

**Will images in my article be uploaded to WordPress?**
Images hosted on A-Stats are embedded via their A-Stats URLs. They will display correctly in the WordPress post as long as the A-Stats image URL is publicly accessible. If you want images hosted in your WordPress media library, upload them to WordPress first and insert them into your A-Stats article via their WordPress URL.
