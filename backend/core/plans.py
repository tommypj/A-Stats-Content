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
            "5 social posts per month",
            "Basic SEO analysis",
            "Community support",
        ],
        "limits": {
            "articles_per_month": 3,
            "outlines_per_month": 3,
            "images_per_month": 3,
            "social_posts_per_month": 5,
        },
    },
    "starter": {
        "name": "Starter",
        "price_monthly": 29,
        "price_yearly": 290,  # ~17% discount
        "features": [
            "30 articles per month",
            "30 outlines per month",
            "10 images per month",
            "20 social posts per month",
            f"{ARTICLE_IMPROVE_LIMIT} AI improvements per article",
            "Advanced SEO analysis",
            "WordPress integration",
            "Priority email support",
        ],
        "limits": {
            "articles_per_month": 30,
            "outlines_per_month": 30,
            "images_per_month": 10,
            "social_posts_per_month": 20,
        },
    },
    "professional": {
        "name": "Professional",
        "price_monthly": 79,
        "price_yearly": 790,  # ~17% discount
        "features": [
            "100 articles per month",
            "100 outlines per month",
            "50 images per month",
            "100 social posts per month",
            f"{ARTICLE_IMPROVE_LIMIT} AI improvements per article",
            "Google Search Console integration",
            "Advanced analytics",
            "API access",
            "Priority support",
        ],
        "limits": {
            "articles_per_month": 100,
            "outlines_per_month": 100,
            "images_per_month": 50,
            "social_posts_per_month": 100,
        },
    },
    "enterprise": {
        "name": "Enterprise",
        "price_monthly": 199,
        "price_yearly": 1990,  # ~17% discount
        "features": [
            "300 articles per month",
            "300 outlines per month",
            "200 images per month",
            "300 social posts per month",
            f"{ARTICLE_IMPROVE_LIMIT} AI improvements per article",
            "All integrations",
            "Advanced analytics",
            "API access",
            "Dedicated support",
            "Custom integrations",
            "SLA guarantee",
        ],
        "limits": {
            "articles_per_month": 300,
            "outlines_per_month": 300,
            "images_per_month": 200,
            "social_posts_per_month": 300,
        },
    },
}
