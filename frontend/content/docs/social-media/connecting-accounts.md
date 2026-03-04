## Supported Platforms

A-Stats supports direct publishing and scheduling to three social media platforms:

- **Twitter / X** — Connect your personal or brand account via Twitter OAuth.
- **LinkedIn** — Connect a personal profile or a LinkedIn Company Page.
- **Facebook** — Connect a Facebook Page (not a personal profile).

Each platform uses the OAuth authorization protocol — you are redirected to the platform's official authorization screen, grant access, and are returned to A-Stats. A-Stats never sees or stores your social media password.

> Note: Social media connections are scoped to your A-Stats account, not to a project. A connected Twitter account is available across all projects you belong to.

## Connecting Twitter / X

### Start the Connection

Go to **Social Media → Connected Accounts** and click **Connect Twitter / X**.

You will be redirected to Twitter's authorization page. Sign in to the Twitter account you want to connect if you are not already logged in.

### Grant Permissions

Twitter will show the permissions A-Stats is requesting:

- Read your profile information and tweets.
- Post tweets and schedule content on your behalf.

Click **Authorize app** to proceed.

### Return to A-Stats

After authorization, you will be redirected back to A-Stats and the account will appear in your connected accounts list with a green "Connected" status badge. The display name and profile picture from Twitter are pulled in automatically.

> Tip: If you manage multiple Twitter accounts, you can connect more than one. Use the **Switch Account** option on the Twitter sign-in screen to authorize a different account.

## Connecting LinkedIn

### Personal Profile vs. Company Page

A-Stats can post on behalf of a LinkedIn personal profile or on behalf of a LinkedIn Company Page that you administer. The distinction is made during the connection flow.

### Start the Connection

Click **Connect LinkedIn** on the Connected Accounts page. You will be redirected to LinkedIn's OAuth authorization screen.

### Grant Permissions

Approve the permissions requested, which include reading your profile and posting content. If you administer LinkedIn Company Pages, those pages will be listed after authorization and you can select which one to connect.

### Select Profile or Page

After returning to A-Stats, a selection dialog will appear if you have Company Pages available. Choose either your personal profile or a specific Company Page. Only one LinkedIn entity can be the active target per connected account slot.

> Tip: To post to both your personal profile and a Company Page, go through the Connect LinkedIn flow twice — once for each target.

## Connecting Facebook

### Requirements

Facebook connections in A-Stats link to **Facebook Pages**, not personal profiles. You must be an Administrator or Editor of the Page you want to connect.

### Start the Connection

Click **Connect Facebook** and complete the Facebook OAuth flow. You will be asked to grant A-Stats permission to manage your Pages and publish content.

### Select a Page

After authorization, A-Stats will list all Facebook Pages you administer. Select the Page you want to use for publishing. If you need to connect multiple Pages, repeat the connection flow.

> Tip: Facebook's permission model is strict. If A-Stats does not appear in your list of authorized apps after connecting, check that you did not skip the "What Facebook information does A-Stats want?" step during authorization.

## Managing Connected Accounts

All connected accounts are visible at **Social Media → Connected Accounts**. Each entry shows:

- The platform and account name.
- Connection status (Connected, Expired, or Error).
- The date the account was connected.

### Reconnecting an Expired Account

OAuth tokens issued by social platforms expire or get revoked when you change your password, revoke app access, or let the token age past the platform's expiry period. When a connection expires, A-Stats marks it with an "Expired" status and stops publishing to that account.

To reconnect, click the **Reconnect** button next to the expired account. This starts a fresh OAuth flow and issues a new token without losing your post history.

### Disconnecting an Account

To remove a connection, click the three-dot menu next to the account and select **Disconnect**. This revokes A-Stats's access token for that account. Any posts that were already published remain on the platform — disconnecting does not delete previously published content.

Scheduled posts targeting that account will be marked as failed after disconnection. Review your schedule before disconnecting to avoid missed posts.
