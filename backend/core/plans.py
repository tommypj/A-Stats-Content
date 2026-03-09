"""
Plan configuration for subscription tiers.

This module is the single source of truth for plan limits and features.
It lives in core/ so both service and API layers can import from it
without creating circular dependencies.
"""

# Maximum number of AI improvement passes allowed per article (all tiers)
ARTICLE_IMPROVE_LIMIT = 3

# Plan configuration with features and limits
PLANS = {
    "free": {
        "name": "Free",
        "price_monthly": 0,
        "price_yearly": 0,
        "features": [
            "3 articles per month",
            "3 outlines per month",
            "3 images per month",
            "3 keyword researches per month",
            f"{ARTICLE_IMPROVE_LIMIT} AI improvements per article",
            "Basic SEO analysis",
            "Community support",
        ],
        "limits": {
            "articles_per_month": 3,
            "outlines_per_month": 3,
            "images_per_month": 3,
            "social_posts_per_month": 0,
            "keyword_researches_per_month": 3,
            "site_audit_pages": 0,
            "site_audits_per_month": 0,
        },
    },
    "starter": {
        "name": "Starter",
        "price_monthly": 29,
        "price_yearly": 290,  # ~17% discount
        "features": [
            "30 articles per month",
            "30 outlines per month",
            "60 images per month",
            "30 social posts per month",
            "60 keyword researches per month",
            f"{ARTICLE_IMPROVE_LIMIT} AI improvements per article",
            "Advanced SEO analysis",
            "Google Search Console integration",
            "WordPress integration",
            "Social media scheduling",
            "5 site audits per month (10 pages each)",
            "Project management & collaboration",
            "Priority email support",
        ],
        "limits": {
            "articles_per_month": 30,
            "outlines_per_month": 30,
            "images_per_month": 60,
            "social_posts_per_month": 30,
            "keyword_researches_per_month": 60,
            "site_audit_pages": 10,
            "site_audits_per_month": 5,
        },
    },
    "professional": {
        "name": "Professional",
        "price_monthly": 79,
        "price_yearly": 790,  # ~17% discount
        "features": [
            "100 articles per month",
            "100 outlines per month",
            "200 images per month",
            "100 social posts per month",
            "200 keyword researches per month",
            f"{ARTICLE_IMPROVE_LIMIT} AI improvements per article",
            "Content decay detection & auto-alerts",
            "SEO reports",
            "Content calendar with auto-publish",
            "Social post analytics",
            "Competitor analysis",
            "Bulk content generation",
            "Knowledge Vault",
            "Article templates & tags",
            "Google Analytics 4 integration",
            "API access",
            "15 site audits per month (100 pages each)",
            "Priority support",
        ],
        "limits": {
            "articles_per_month": 100,
            "outlines_per_month": 100,
            "images_per_month": 200,
            "social_posts_per_month": 100,
            "keyword_researches_per_month": 200,
            "site_audit_pages": 100,
            "site_audits_per_month": 15,
        },
    },
    "enterprise": {
        "name": "Enterprise",
        "price_monthly": 199,
        "price_yearly": 1990,  # ~17% discount
        "features": [
            "300 articles per month",
            "300 outlines per month",
            "600 images per month",
            "300 social posts per month",
            "600 keyword researches per month",
            f"{ARTICLE_IMPROVE_LIMIT} AI improvements per article",
            "All Professional features",
            "White-label agency mode",
            "Client portals & branding",
            "Custom integrations",
            "50 site audits per month (1000 pages each)",
            "Dedicated support",
            "SLA guarantee",
        ],
        "limits": {
            "articles_per_month": 300,
            "outlines_per_month": 300,
            "images_per_month": 600,
            "social_posts_per_month": 300,
            "keyword_researches_per_month": 600,
            "site_audit_pages": 1000,
            "site_audits_per_month": 50,
        },
    },
}
