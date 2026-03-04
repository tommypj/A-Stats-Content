export interface DocArticle {
  slug: string;
  title: string;
  description: string;
  category: string;
}

export interface DocCategory {
  slug: string;
  title: string;
  description: string;
  icon: string; // lucide icon name
  articles: DocArticle[];
}

export const DOC_CATEGORIES: DocCategory[] = [
  {
    slug: "getting-started",
    title: "Getting Started",
    description: "Set up your account and create your first content.",
    icon: "Rocket",
    articles: [
      { slug: "welcome", title: "Welcome to A-Stats", description: "An overview of the platform and what you can do.", category: "getting-started" },
      { slug: "quick-start", title: "Quick Start Guide", description: "Get up and running in under 5 minutes.", category: "getting-started" },
      { slug: "your-first-article", title: "Your First Article", description: "Step-by-step guide to creating your first AI-generated article.", category: "getting-started" },
      { slug: "understanding-projects", title: "Understanding Projects", description: "How projects organize your content and team.", category: "getting-started" },
    ],
  },
  {
    slug: "content-generation",
    title: "Content Generation",
    description: "Create outlines, articles, and manage your content pipeline.",
    icon: "PenTool",
    articles: [
      { slug: "creating-outlines", title: "Creating Outlines", description: "Generate AI-powered content outlines for your articles.", category: "content-generation" },
      { slug: "generating-articles", title: "Generating Articles", description: "Turn outlines into full SEO-optimized articles.", category: "content-generation" },
      { slug: "article-editor", title: "Article Editor", description: "Edit, format, and polish your generated content.", category: "content-generation" },
      { slug: "ai-settings", title: "AI Writing Settings", description: "Customize tone, style, and voice for AI content.", category: "content-generation" },
      { slug: "bulk-content", title: "Bulk Content Generation", description: "Generate multiple articles at once for scale.", category: "content-generation" },
      { slug: "content-calendar", title: "Content Calendar", description: "Plan and schedule your content pipeline.", category: "content-generation" },
    ],
  },
  {
    slug: "seo",
    title: "SEO",
    description: "Optimize your content for search engines.",
    icon: "Search",
    articles: [
      { slug: "seo-scoring", title: "SEO Scoring", description: "Understand the 10-point SEO scoring system.", category: "seo" },
      { slug: "keyword-research", title: "Keyword Research", description: "Find and target the right keywords.", category: "seo" },
      { slug: "publishing-to-wordpress", title: "Publishing to WordPress", description: "Push articles directly to your WordPress site.", category: "seo" },
    ],
  },
  {
    slug: "aeo",
    title: "AEO",
    description: "Optimize your content for AI answer engines.",
    icon: "Bot",
    articles: [
      { slug: "what-is-aeo", title: "What is AEO?", description: "Answer Engine Optimization explained.", category: "aeo" },
      { slug: "aeo-scoring", title: "AEO Score Explained", description: "How the AEO scoring system works.", category: "aeo" },
      { slug: "improving-aeo-score", title: "Improving Your AEO Score", description: "Actionable tips to get cited by AI engines.", category: "aeo" },
    ],
  },
  {
    slug: "analytics",
    title: "Analytics",
    description: "Track performance with Google Search Console and content health.",
    icon: "BarChart3",
    articles: [
      { slug: "connecting-google-search-console", title: "Connecting Google Search Console", description: "Set up the GSC integration for performance data.", category: "analytics" },
      { slug: "keywords-and-pages", title: "Keywords & Pages", description: "Analyze keyword rankings and page performance.", category: "analytics" },
      { slug: "content-health-alerts", title: "Content Health Alerts", description: "Detect content decay and get alerted automatically.", category: "analytics" },
      { slug: "article-performance", title: "Article Performance", description: "Track clicks, impressions, and position for each article.", category: "analytics" },
      { slug: "revenue-attribution", title: "Revenue Attribution", description: "Connect content performance to revenue outcomes.", category: "analytics" },
    ],
  },
  {
    slug: "social-media",
    title: "Social Media",
    description: "Manage and schedule posts across social platforms.",
    icon: "Share2",
    articles: [
      { slug: "connecting-accounts", title: "Connecting Social Accounts", description: "Link your Twitter, LinkedIn, and Facebook accounts.", category: "social-media" },
      { slug: "composing-posts", title: "Composing Posts", description: "Write and format posts for each platform.", category: "social-media" },
      { slug: "scheduling", title: "Scheduling Posts", description: "Schedule posts for optimal engagement times.", category: "social-media" },
      { slug: "social-calendar", title: "Social Calendar", description: "View and manage your posting schedule.", category: "social-media" },
    ],
  },
  {
    slug: "knowledge-vault",
    title: "Knowledge Vault",
    description: "Upload documents to give AI context about your brand.",
    icon: "Database",
    articles: [
      { slug: "overview", title: "Knowledge Vault Overview", description: "What the Knowledge Vault is and how it works.", category: "knowledge-vault" },
      { slug: "uploading-sources", title: "Uploading Sources", description: "Add PDFs, documents, and text files as knowledge sources.", category: "knowledge-vault" },
      { slug: "querying-knowledge", title: "Querying Knowledge", description: "Ask questions and get answers from your uploaded sources.", category: "knowledge-vault" },
    ],
  },
  {
    slug: "images",
    title: "Images",
    description: "Generate and manage AI images for your content.",
    icon: "Image",
    articles: [
      { slug: "generating-images", title: "Generating AI Images", description: "Create images using AI for your articles.", category: "images" },
      { slug: "image-library", title: "Image Library", description: "Browse, search, and manage your generated images.", category: "images" },
    ],
  },
  {
    slug: "projects-and-teams",
    title: "Projects & Teams",
    description: "Collaborate with your team on content projects.",
    icon: "Users",
    articles: [
      { slug: "creating-projects", title: "Creating Projects", description: "Set up projects to organize your content.", category: "projects-and-teams" },
      { slug: "team-members-and-roles", title: "Team Members & Roles", description: "Invite team members and manage permissions.", category: "projects-and-teams" },
      { slug: "brand-voice", title: "Brand Voice", description: "Configure your brand's writing style and guidelines.", category: "projects-and-teams" },
      { slug: "project-integrations", title: "Project Integrations", description: "Connect WordPress and other tools to your project.", category: "projects-and-teams" },
    ],
  },
  {
    slug: "agency-mode",
    title: "Agency Mode",
    description: "Manage multiple clients with white-label branding.",
    icon: "Building2",
    articles: [
      { slug: "overview", title: "Agency Mode Overview", description: "How agency mode works for managing clients.", category: "agency-mode" },
      { slug: "managing-clients", title: "Managing Clients", description: "Add, edit, and organize client workspaces.", category: "agency-mode" },
      { slug: "white-label-branding", title: "White-Label Branding", description: "Customize branding for each client.", category: "agency-mode" },
      { slug: "client-portal", title: "Client Portal", description: "Share reports and content with clients via a branded portal.", category: "agency-mode" },
    ],
  },
  {
    slug: "billing-and-plans",
    title: "Billing & Plans",
    description: "Manage your subscription and understand usage limits.",
    icon: "CreditCard",
    articles: [
      { slug: "plans-and-pricing", title: "Plans & Pricing", description: "Compare plans and understand what's included.", category: "billing-and-plans" },
      { slug: "managing-subscription", title: "Managing Your Subscription", description: "Upgrade, downgrade, or cancel your plan.", category: "billing-and-plans" },
      { slug: "usage-limits", title: "Usage Limits", description: "Understand generation limits and how they reset.", category: "billing-and-plans" },
    ],
  },
  {
    slug: "account-and-settings",
    title: "Account & Settings",
    description: "Manage your profile, security, and preferences.",
    icon: "Settings",
    articles: [
      { slug: "profile-settings", title: "Profile Settings", description: "Update your name, email, and avatar.", category: "account-and-settings" },
      { slug: "security", title: "Security", description: "Change your password and manage sessions.", category: "account-and-settings" },
      { slug: "notifications", title: "Notifications", description: "Configure email and in-app notification preferences.", category: "account-and-settings" },
    ],
  },
];

// Flat list of all articles with category info
export function getAllArticles(): (DocArticle & { categoryTitle: string })[] {
  return DOC_CATEGORIES.flatMap((cat) =>
    cat.articles.map((article) => ({
      ...article,
      categoryTitle: cat.title,
    }))
  );
}

// Get a category by slug
export function getCategory(slug: string): DocCategory | undefined {
  return DOC_CATEGORIES.find((cat) => cat.slug === slug);
}

// Get an article by category + slug
export function getArticle(
  categorySlug: string,
  articleSlug: string
): (DocArticle & { categoryTitle: string }) | undefined {
  const cat = getCategory(categorySlug);
  if (!cat) return undefined;
  const article = cat.articles.find((a) => a.slug === articleSlug);
  if (!article) return undefined;
  return { ...article, categoryTitle: cat.title };
}

// Get prev/next articles for navigation
export function getPrevNextArticles(
  categorySlug: string,
  articleSlug: string
): { prev: DocArticle | null; next: DocArticle | null } {
  const all = getAllArticles();
  const idx = all.findIndex(
    (a) => a.category === categorySlug && a.slug === articleSlug
  );
  return {
    prev: idx > 0 ? all[idx - 1] : null,
    next: idx < all.length - 1 ? all[idx + 1] : null,
  };
}

// Search manifest for Fuse.js (client-side friendly)
export interface SearchableDoc {
  title: string;
  description: string;
  category: string;
  categoryTitle: string;
  slug: string;
  href: string;
}

export function getSearchableArticles(): SearchableDoc[] {
  return DOC_CATEGORIES.flatMap((cat) =>
    cat.articles.map((article) => ({
      title: article.title,
      description: article.description,
      category: article.category,
      categoryTitle: cat.title,
      slug: article.slug,
      href: `/docs/${article.category}/${article.slug}`,
    }))
  );
}
