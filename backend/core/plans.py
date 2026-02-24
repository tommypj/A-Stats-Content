"""
Plan configuration for subscription tiers.

This module is the single source of truth for plan limits and features.
It lives in core/ so both service and API layers can import from it
without creating circular dependencies.
"""

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
        },
    },
    "starter": {
        "name": "Starter",
        "price_monthly": 29,
        "price_yearly": 290,  # ~17% discount
        "features": [
            "25 articles per month",
            "50 outlines per month",
            "10 images per month",
            "Advanced SEO analysis",
            "WordPress integration",
            "Priority email support",
        ],
        "limits": {
            "articles_per_month": 25,
            "outlines_per_month": 50,
            "images_per_month": 10,
        },
    },
    "professional": {
        "name": "Professional",
        "price_monthly": 79,
        "price_yearly": 790,  # ~17% discount
        "features": [
            "100 articles per month",
            "200 outlines per month",
            "50 images per month",
            "Google Search Console integration",
            "Advanced analytics",
            "API access",
            "Priority support",
        ],
        "limits": {
            "articles_per_month": 100,
            "outlines_per_month": 200,
            "images_per_month": 50,
        },
    },
    "enterprise": {
        "name": "Enterprise",
        "price_monthly": 199,
        "price_yearly": 1990,  # ~17% discount
        "features": [
            "Unlimited articles",
            "Unlimited outlines",
            "Unlimited images",
            "All integrations",
            "Advanced analytics",
            "API access",
            "Dedicated support",
            "Custom integrations",
            "SLA guarantee",
        ],
        "limits": {
            "articles_per_month": -1,  # -1 = unlimited
            "outlines_per_month": -1,
            "images_per_month": -1,
        },
    },
}
