## What is White-Label Branding?

White-label branding replaces the platform's own visual identity with your agency's branding in the client-facing portal. When your clients access their portal, they see your logo, your colors, and your agency name — not the platform's brand.

This creates a professional experience where the technology is invisible and your agency appears to be the provider of the content management system.

## What Gets Branded

Branding is applied to the **client portal** — the view that your clients see when they access their portal link. The following elements are customized:

| Element | What Changes |
|---------|-------------|
| Portal header logo | Replaced with your agency logo |
| Primary color | Used for buttons, links, and active states |
| Accent color | Used for highlights and badges |
| Agency name | Appears in the portal title and email communications |
| Browser tab title | Shows "[Your Agency] — Client Portal" |
| Email sender name | Portal invite emails are sent as "[Your Agency] via A-Stats" |

The client-facing portal URL and any email notifications reference your agency name, not the platform name.

> **Tip:** Your own agency dashboard (the view you use, not the client-facing portal) always shows the platform's standard branding. White-label branding applies exclusively to what clients see.

## Accessing Branding Settings

1. Navigate to **Agency** in the main sidebar.
2. Click the **Branding** tab (or navigate to **Agency Settings > Branding**).

## Uploading Your Logo

1. Click **Upload Logo** in the branding settings.
2. Select an image file from your computer.
3. Supported formats: PNG, SVG, JPEG.
4. Recommended size: **200 x 60 pixels** (horizontal logo format). Taller or wider images are scaled to fit.
5. Click **Save**.

The uploaded logo appears immediately in the preview on the right side of the branding settings page. Changes are reflected in the client portal within a few minutes.

> **Tip:** Use a PNG with a transparent background for best results. A logo on a transparent background adapts cleanly to both light and dark portal themes.

## Setting Colors

Use the color pickers to set your primary and accent brand colors. You can:
- Click the color swatch to open a color picker
- Type a hex code directly (for example, `#1A73E8`)

The preview panel on the right updates in real time as you adjust colors. Check that text remains readable against your chosen primary color — very dark or very light primary colors may reduce the contrast of button text.

**Primary color** — Main interactive elements: primary buttons, active navigation items, progress indicators.

**Accent color** — Secondary highlights: badges, tags, hover states, chart series colors.

## Portal Subdomain (Enterprise)

Enterprise plan accounts can configure a custom subdomain for the client portal. Instead of a generic platform URL, clients access their portal at a URL like:

`https://portal.youragency.com`

This requires:
1. Setting the desired subdomain in **Agency Settings > Branding > Custom Domain**.
2. Adding a CNAME DNS record at your domain registrar pointing the subdomain to the platform's portal host (the required CNAME target is shown in the settings page).
3. DNS propagation takes 24–48 hours after the CNAME is added.

SSL certificates are provisioned automatically once DNS propagation is detected.

Custom subdomain is available on the **Enterprise plan** only. Pro plan portals use a platform-hosted URL that includes your agency slug.

## Agency Name and Contact Details

Set your agency's display name, website URL, and support email in the branding settings. These appear:

- In the portal header subtitle
- In automated emails sent to clients (portal invites, report notifications)
- In the portal footer

The support email is shown to clients as a contact point in the portal. Make sure it is a monitored inbox.

## Previewing the Client Portal

The branding settings page includes a live preview panel that simulates what a client would see. The preview updates as you make changes. Use it to check:

- That your logo is visible and correctly sized
- That your primary color has sufficient contrast for button text
- That your agency name is displayed as expected

You can also open a real portal link in a private/incognito browser window to see the fully rendered portal without needing a client account.

## Applying Branding to Specific Clients

Branding settings apply to **all client portals** by default. There is currently one set of branding per agency account. If you need distinct branding for different clients (for example, if you run two agency brands), contact support to discuss Enterprise multi-brand configurations.
