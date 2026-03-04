## AI Image Generation Overview

The platform integrates with **Replicate Flux** to generate high-quality images from text descriptions. You can create custom illustrations, article headers, social media visuals, and product mockups without leaving the platform or needing a separate design tool.

Generated images are stored in your project's Image Library and can be inserted directly into articles.

## Writing Effective Prompts

The quality of a generated image depends almost entirely on the quality of your prompt. A prompt is a plain-language description of what you want the image to look like.

### Structure of a Good Prompt

A strong prompt typically includes:

1. **Subject** — What is the main focus? ("a laptop on a wooden desk")
2. **Context or setting** — Where is it? ("in a bright, modern home office")
3. **Style or mood** — What should it feel like? ("clean, professional, minimal")
4. **Lighting** — How is it lit? ("soft natural light from the left")
5. **Technical details** — Any specific visual qualities ("high detail, photorealistic, 4K quality")

**Example prompt:**
> "A clean, minimal workspace with a laptop, notebook, and coffee mug on a white desk, soft natural window light, top-down flat lay perspective, professional photography style"

### What to Avoid
- Vague prompts like "a good image for my article" produce generic results.
- Extremely long prompts with conflicting instructions can confuse the model.
- Requesting text or logos inside the image — AI image models render text poorly. Add text overlays in a design tool after generation.

> **Tip:** Start with a clear subject and style, generate a first result, then refine the prompt based on what you see. Iteration is faster than trying to write a perfect prompt on the first attempt.

## Style Options

When generating an image, you can select a visual style to guide the output:

| Style | Best for |
|-------|---------|
| Photorealistic | Product showcases, authentic scenes, stock-photo replacements |
| Illustration | Blog headers, explainer content, friendly brand imagery |
| Minimal / Flat | Infographic elements, icon-style visuals, clean UI mockups |
| Cinematic | Hero banners, dramatic feature imagery |
| Watercolor | Lifestyle content, travel, wellness topics |

Combining a style selection with a descriptive prompt yields more consistent results than relying on the style selector alone.

## Resolution and Aspect Ratios

Images are generated at high resolution suitable for web publishing. Available aspect ratios include:

- **16:9** — Landscape, ideal for article headers and banners
- **1:1** — Square, ideal for social media posts
- **4:3** — Standard landscape for embedded article images
- **9:16** — Portrait, ideal for Instagram Stories and Pinterest

Select the aspect ratio before generating; you cannot crop or resize within the platform after generation.

> **Tip:** For article headers, use 16:9. For images embedded within article body text, 4:3 tends to work best with most layout templates.

## Generating an Image

1. Navigate to your project's **Images** section.
2. Click **Generate Image**.
3. Enter a descriptive prompt in the text field.
4. Select a style and aspect ratio.
5. Click **Generate**. Processing typically takes 10–30 seconds.
6. Review the result. If it does not meet your needs, adjust the prompt and regenerate.
7. Once satisfied, the image is automatically saved to your Image Library.

Each generation attempt counts as one image generation toward your monthly usage.

## Using Generated Images in Articles

1. Open an article in the editor.
2. Place your cursor where you want the image to appear.
3. Click the **Insert Image** button in the editor toolbar.
4. Select from your Image Library or generate a new image directly from the insert panel.
5. The image is embedded at the cursor position with a standard `<img>` tag.

Images inserted into articles are served from the platform's CDN with a long-lived cache header, so they load quickly for readers.

## Image Limits

Image generation is subject to your plan's monthly generation limit, which is shared with article and outline generation. Check your current usage in **Settings > Billing**.
