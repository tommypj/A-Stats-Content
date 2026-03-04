## Overview

The Image Library is the central repository for all images associated with a project. It stores every image you generate with AI, as well as any images you upload manually. From here you can browse, search, download, use in articles, and manage storage.

## Browsing Images

The Image Library displays images in a responsive grid. Each thumbnail shows the image along with its name, creation date, and dimensions.

Images are sorted by date by default, with the most recently created or uploaded images appearing first. You can switch to alphabetical order by name using the sort control in the top-right of the library view.

Click any image thumbnail to open a detail panel on the right side. The detail panel shows:

- Full-size preview
- File name and description
- Dimensions and file size
- Creation date and source (AI generated or uploaded)
- Direct URL (for copying into external tools)
- Action buttons (download, insert into article, delete)

## Searching Images

Use the search bar at the top of the library to filter images by name or description.

The search runs against the stored name and description fields, not image content itself. This means descriptive names and descriptions at upload or generation time make search significantly more effective.

> **Tip:** When generating AI images, use a concise but descriptive name when saving (for example "homepage-hero-laptop-desk" rather than "image-1"). This makes the library much easier to navigate as it grows.

## Filtering by Type

Use the filter controls to show only AI-generated images or only manually uploaded images. This is useful when you want to review what the AI has produced separately from your own assets.

## Downloading Images

To download an image:

1. Click the image thumbnail to open the detail panel.
2. Click **Download**.
3. The image is downloaded to your browser's default downloads location at its original resolution.

Downloaded images are standard web-optimized files (typically JPEG or PNG depending on generation settings) and can be used freely in external tools.

## Using Images in Articles

You can insert any library image directly into an article without downloading it first:

1. Open the article editor.
2. Position your cursor at the insertion point.
3. Click **Insert Image** in the editor toolbar.
4. Browse or search the library in the panel that opens.
5. Click the image you want to insert.

The image is embedded with a CDN-hosted URL, so article readers always receive a fast-loading version.

Alternatively, from the Image Library detail panel, click **Insert into Article**, then select the target article from the dropdown.

## Deleting Images

To delete an image:

1. Open the image detail panel.
2. Click **Delete**.
3. Confirm the deletion in the confirmation prompt.

Deletion is permanent and cannot be undone. If the deleted image was embedded in an article, it will appear as a broken image link in that article. Review article usage before deleting.

> **Tip:** Before deleting images, use the **Used in** field in the detail panel (if shown) to check whether any articles reference the image.

## Orphan Cleanup

The platform automatically identifies and flags orphan images — images that exist in storage but are not referenced by any article or other content. Orphan cleanup runs periodically and may remove very old orphaned images to free storage space. You will receive a notification before bulk orphan cleanup occurs.

To prevent an image from being treated as an orphan, insert it into at least one article or keep it referenced in a knowledge vault or other content record.

## Storage Limits

Storage capacity for images is tied to your subscription plan. Current usage is displayed at the top of the Image Library page as a simple used/total indicator.

| Plan | Image Storage |
|------|--------------|
| Free | 500 MB |
| Starter | 5 GB |
| Pro | 20 GB |
| Enterprise | 100 GB |

If you approach your storage limit, the platform will show a warning banner. At the limit, new uploads and generation will be blocked until you delete existing images or upgrade your plan.

> **Tip:** AI-generated images at high resolution can be 2–5 MB each. If you generate images frequently, review and prune unused images regularly to stay well within your storage limit.

## Bulk Actions

Select multiple images using the checkboxes that appear when you hover over thumbnails. With multiple images selected, you can:

- **Delete selected** — Permanently removes all selected images
- **Download selected** — Downloads a ZIP archive of the selected images

Bulk actions are useful for cleaning up a batch of rejected generation attempts at once.
