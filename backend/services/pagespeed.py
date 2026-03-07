"""
Google PageSpeed Insights API integration.
"""

import logging
from typing import Any

import httpx

from infrastructure.config import get_settings

logger = logging.getLogger(__name__)

PAGESPEED_API_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"


async def fetch_pagespeed(url: str, strategy: str = "mobile") -> dict[str, Any] | None:
    """
    Fetch PageSpeed Insights data for a URL.

    Returns a dict with:
        performance_score: int (0-100)
        metrics: dict with LCP, FID, CLS, FCP, TTFB, SI, TBT
        opportunities: list of optimization suggestions
        diagnostics: list of diagnostic info

    Returns None on any error.
    """
    settings = get_settings()
    api_key = settings.google_pagespeed_api_key
    if not api_key:
        logger.debug("PageSpeed API key not configured, skipping")
        return None

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                PAGESPEED_API_URL,
                params={
                    "url": url,
                    "key": api_key,
                    "strategy": strategy,
                    "category": "performance",
                },
            )

            if response.status_code != 200:
                logger.warning(
                    "PageSpeed API returned %s for %s: %s",
                    response.status_code, url, response.text[:200],
                )
                return None

            data = response.json()

            # Extract Lighthouse results
            lighthouse = data.get("lighthouseResult", {})
            categories = lighthouse.get("categories", {})
            perf_category = categories.get("performance", {})
            performance_score = round((perf_category.get("score", 0) or 0) * 100)

            # Extract Core Web Vitals and key metrics from audits
            audits = lighthouse.get("audits", {})

            metrics = {}
            metric_keys = {
                "largest-contentful-paint": "lcp",
                "cumulative-layout-shift": "cls",
                "total-blocking-time": "tbt",
                "first-contentful-paint": "fcp",
                "speed-index": "si",
                "interactive": "tti",
            }
            for audit_key, short_name in metric_keys.items():
                audit = audits.get(audit_key, {})
                if audit:
                    metrics[short_name] = {
                        "value": audit.get("numericValue"),
                        "display": audit.get("displayValue", ""),
                        "score": round((audit.get("score", 0) or 0) * 100),
                    }

            # Extract field data (Chrome UX Report) if available
            field_data = {}
            loading_exp = data.get("loadingExperience", {})
            crux_metrics = loading_exp.get("metrics", {})
            for crux_key, crux_val in crux_metrics.items():
                field_data[crux_key] = {
                    "percentile": crux_val.get("percentile"),
                    "category": crux_val.get("category"),
                }

            # Extract top opportunities (things to fix)
            opportunities = []
            for audit_id, audit_data in audits.items():
                if (
                    audit_data.get("score") is not None
                    and audit_data["score"] < 1
                    and audit_data.get("details", {}).get("type") == "opportunity"
                ):
                    savings = audit_data.get("details", {}).get("overallSavingsMs", 0)
                    opportunities.append({
                        "id": audit_id,
                        "title": audit_data.get("title", ""),
                        "description": audit_data.get("description", ""),
                        "display_value": audit_data.get("displayValue", ""),
                        "savings_ms": savings,
                        "score": round((audit_data.get("score", 0) or 0) * 100),
                    })

            # Sort opportunities by potential savings
            opportunities.sort(key=lambda x: x.get("savings_ms", 0), reverse=True)

            # Extract diagnostics (informational items)
            diagnostics = []
            for audit_id, audit_data in audits.items():
                if (
                    audit_data.get("details", {}).get("type") == "table"
                    and audit_data.get("score") is not None
                    and audit_data["score"] < 1
                    and audit_id not in [o["id"] for o in opportunities]
                ):
                    diagnostics.append({
                        "id": audit_id,
                        "title": audit_data.get("title", ""),
                        "description": audit_data.get("description", ""),
                        "display_value": audit_data.get("displayValue", ""),
                    })

            return {
                "performance_score": performance_score,
                "strategy": strategy,
                "metrics": metrics,
                "field_data": field_data if field_data else None,
                "opportunities": opportunities[:10],  # Top 10
                "diagnostics": diagnostics[:10],
            }

    except httpx.RequestError as e:
        logger.warning("PageSpeed API request failed for %s: %s", url, e)
        return None
    except Exception as e:
        logger.warning("PageSpeed processing error for %s: %s", url, e)
        return None
