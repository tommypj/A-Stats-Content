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
            "10 articles per month",
            "10 outlines per month",
            "5 images per month",
            "Basic SEO analysis",
            "Community support",
        ],
        "limits": {
            "articles_per_month": 10,
            "outlines_per_month": 10,
            "images_per_month": 5,
            "social_posts_per_month": 5,
        },
    },
    "starter": {
        "name": "Starter",
        "price_monthly": 29,
        "price_yearly": 290,  # ~17% discount
        "features": [
            "10 articles per month",
            "10 outlines per month",
            "10 images per month",
            "10 social post sets per month",
            f"{ARTICLE_IMPROVE_LIMIT} AI improvements per article",
            "Advanced SEO analysis",
            "WordPress integration",
            "Priority email support",
        ],
        "limits": {
            "articles_per_month": 10,
            "outlines_per_month": 10,
            "images_per_month": 10,
            "social_posts_per_month": 10,
        },
    },
    "professional": {
        "name": "Professional",
        "price_monthly": 79,
        "price_yearly": 790,  # ~17% discount
        "features": [
            "50 articles per month",
            "50 outlines per month",
            "50 images per month",
            "50 social post sets per month",
            f"{ARTICLE_IMPROVE_LIMIT} AI improvements per article",
            "Google Search Console integration",
            "Advanced analytics",
            "API access",
            "Priority support",
        ],
        "limits": {
            "articles_per_month": 50,
            "outlines_per_month": 50,
            "images_per_month": 50,
            "social_posts_per_month": 50,
        },
    },
    "enterprise": {
        "name": "Enterprise",
        "price_monthly": 199,
        "price_yearly": 1990,  # ~17% discount
        "features": [
            "200 articles per month",
            "200 outlines per month",
            "200 images per month",
            "200 social post sets per month",
            f"{ARTICLE_IMPROVE_LIMIT} AI improvements per article",
            "All integrations",
            "Advanced analytics",
            "API access",
            "Dedicated support",
            "Custom integrations",
            "SLA guarantee",
        ],
        "limits": {
            "articles_per_month": 200,
            "outlines_per_month": 200,
            "images_per_month": 200,
            "social_posts_per_month": 200,
        },
    },
}
