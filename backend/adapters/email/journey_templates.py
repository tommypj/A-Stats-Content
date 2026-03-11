"""
Email journey templates for automated email sequences.

Provides branded HTML templates for onboarding, conversion,
retention, and system emails.
"""

from html import escape as html_escape


class JourneyTemplates:
    """Generates branded HTML email templates for user journey sequences."""

    def __init__(self, frontend_url: str):
        self._frontend_url = frontend_url.rstrip("/")

    def _cta_button(self, text: str, url: str) -> str:
        """Generate a branded CTA button."""
        return (
            f'<div style="text-align: center; margin: 32px 0;">'
            f'<a href="{url}" style="display: inline-block; background: #da7756; '
            f"color: white; text-decoration: none; padding: 14px 32px; "
            f'border-radius: 12px; font-weight: 500;">'
            f"{text}</a></div>"
        )

    def _base_layout(self, content: str, unsubscribe_url: str | None = None) -> str:
        """Wrap content in the branded email layout with optional unsubscribe footer."""
        unsub_footer = ""
        if unsubscribe_url:
            unsub_footer = (
                '<div style="text-align:center;padding-top:24px;'
                'border-top:1px solid #F1F3F5;margin-top:32px;">'
                f'<a href="{unsubscribe_url}" style="color:#8B8BA7;'
                'font-size:12px;text-decoration:underline;">'
                "Unsubscribe from these emails</a></div>"
            )

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #FFF8F0; padding: 40px 20px;">
    <div style="max-width: 560px; margin: 0 auto; background: white; border-radius: 16px; padding: 40px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
        <div style="text-align: center; margin-bottom: 32px;">
            <div style="width: 48px; height: 48px; background: linear-gradient(135deg, #ed8f73, #da7756); border-radius: 12px; margin: 0 auto;"></div>
            <h1 style="color: #1A1A2E; font-size: 24px; margin: 16px 0 0;">A-Stats Content</h1>
        </div>

        {content}

        {unsub_footer}
    </div>
</body>
</html>"""

    # ── Phase 1: Onboarding ─────────────────────────────────────────

    def welcome(self, user_name: str) -> tuple[str, str]:
        """Welcome email after signup."""
        safe_name = html_escape(user_name or "")
        content = f"""
        <h2 style="color: #1A1A2E; font-size: 20px; margin-bottom: 16px;">Your account is ready!</h2>

        <p style="color: #4A4A68; line-height: 1.6; margin-bottom: 24px;">
            Hi {safe_name}, welcome to A-Stats Content! Here's what you can do right away:
        </p>

        <div style="background: #F8F9FA; border-radius: 12px; padding: 24px; margin-bottom: 24px;">
            <ul style="color: #4A4A68; margin: 0; padding-left: 20px; line-height: 1.8;">
                <li>Create SEO-optimized article outlines</li>
                <li>Generate full articles with AI</li>
                <li>Design custom AI images</li>
                <li>Publish directly to WordPress</li>
            </ul>
        </div>

        {self._cta_button("Go to Dashboard", f"{self._frontend_url}/dashboard")}
        """
        return (
            self._base_layout(content, f"{self._frontend_url}/email-preferences/unsubscribe/{{{{token}}}}"),
            "Your A-Stats account is ready — let's get started",
        )

    def first_outline_nudge(self, user_name: str) -> tuple[str, str]:
        """Nudge user to create their first outline."""
        safe_name = html_escape(user_name or "")
        content = f"""
        <h2 style="color: #1A1A2E; font-size: 20px; margin-bottom: 16px;">Create your first outline in 30 seconds</h2>

        <p style="color: #4A4A68; line-height: 1.6; margin-bottom: 24px;">
            Hi {safe_name}, the fastest way to start is with an article outline.
            Just enter a topic and our AI will research keywords, competitors, and structure for you.
        </p>

        {self._cta_button("Create an Outline", f"{self._frontend_url}/dashboard/outlines")}
        """
        return (
            self._base_layout(content, f"{self._frontend_url}/email-preferences/unsubscribe/{{{{token}}}}"),
            "Your first SEO outline is 30 seconds away",
        )

    def outline_to_article_nudge(self, user_name: str) -> tuple[str, str]:
        """Nudge user to generate an article from their outline."""
        safe_name = html_escape(user_name or "")
        content = f"""
        <h2 style="color: #1A1A2E; font-size: 20px; margin-bottom: 16px;">Great work! Now generate your article</h2>

        <p style="color: #4A4A68; line-height: 1.6; margin-bottom: 24px;">
            Hi {safe_name}, your outline is ready. Turn it into a full, SEO-optimized article
            with one click — our AI handles the rest.
        </p>

        {self._cta_button("Generate Article", f"{self._frontend_url}/dashboard/articles")}
        """
        return (
            self._base_layout(content, f"{self._frontend_url}/email-preferences/unsubscribe/{{{{token}}}}"),
            "Your outline is ready — generate your article now",
        )

    def outline_reminder(self, user_name: str) -> tuple[str, str]:
        """Remind user about their unfinished outline."""
        safe_name = html_escape(user_name or "")
        content = f"""
        <h2 style="color: #1A1A2E; font-size: 20px; margin-bottom: 16px;">Your outline is still waiting</h2>

        <p style="color: #4A4A68; line-height: 1.6; margin-bottom: 24px;">
            Hi {safe_name}, you have an outline that hasn't been turned into an article yet.
            Don't let your research go to waste — generate your article today.
        </p>

        {self._cta_button("View My Outlines", f"{self._frontend_url}/dashboard/articles")}
        """
        return (
            self._base_layout(content, f"{self._frontend_url}/email-preferences/unsubscribe/{{{{token}}}}"),
            "Your outline is waiting to become an article",
        )

    def connect_tools(self, user_name: str) -> tuple[str, str]:
        """Encourage user to connect integrations."""
        safe_name = html_escape(user_name or "")
        content = f"""
        <h2 style="color: #1A1A2E; font-size: 20px; margin-bottom: 16px;">Supercharge your workflow</h2>

        <p style="color: #4A4A68; line-height: 1.6; margin-bottom: 24px;">
            Hi {safe_name}, connect your tools to get the most out of A-Stats:
        </p>

        <div style="background: #F8F9FA; border-radius: 12px; padding: 24px; margin-bottom: 24px;">
            <ul style="color: #4A4A68; margin: 0; padding-left: 20px; line-height: 1.8;">
                <li><strong>WordPress</strong> — Publish articles with one click</li>
                <li><strong>Google Analytics</strong> — Track content performance</li>
                <li><strong>Site Audit</strong> — Find and fix SEO issues</li>
            </ul>
        </div>

        {self._cta_button("Connect Integrations", f"{self._frontend_url}/dashboard/settings?tab=integrations")}
        """
        return (
            self._base_layout(content, f"{self._frontend_url}/email-preferences/unsubscribe/{{{{token}}}}"),
            "Connect WordPress & GA4 to unlock your full workflow",
        )

    def week_one_recap(self, user_name: str, outlines_count: int, articles_count: int) -> tuple[str, str]:
        """Week 1 activity recap."""
        safe_name = html_escape(user_name or "")
        content = f"""
        <h2 style="color: #1A1A2E; font-size: 20px; margin-bottom: 16px;">Your first week in review</h2>

        <p style="color: #4A4A68; line-height: 1.6; margin-bottom: 24px;">
            Hi {safe_name}, here's what you accomplished this week:
        </p>

        <div style="background: #F8F9FA; border-radius: 12px; padding: 24px; margin-bottom: 24px;">
            <ul style="color: #4A4A68; margin: 0; padding-left: 20px; line-height: 1.8;">
                <li><strong>{outlines_count}</strong> outline{"s" if outlines_count != 1 else ""} created</li>
                <li><strong>{articles_count}</strong> article{"s" if articles_count != 1 else ""} generated</li>
            </ul>
        </div>

        <p style="color: #4A4A68; line-height: 1.6; margin-bottom: 24px;">
            Next up: try site audits, content decay alerts, or competitor analysis to level up your SEO game.
        </p>

        {self._cta_button("Go to Dashboard", f"{self._frontend_url}/dashboard")}
        """
        return (
            self._base_layout(content, f"{self._frontend_url}/email-preferences/unsubscribe/{{{{token}}}}"),
            f"Your week 1 recap: {outlines_count} outlines, {articles_count} articles",
        )

    # ── Phase 2: Conversion ─────────────────────────────────────────

    def usage_80_percent(self, user_name: str, current_usage: int, limit: int, resource: str) -> tuple[str, str]:
        """Alert user they've used 80% of a resource limit."""
        safe_name = html_escape(user_name or "")
        safe_resource = html_escape(resource or "")
        content = f"""
        <h2 style="color: #1A1A2E; font-size: 20px; margin-bottom: 16px;">You're almost at your limit</h2>

        <p style="color: #4A4A68; line-height: 1.6; margin-bottom: 24px;">
            Hi {safe_name}, you've used <strong>{current_usage} of {limit} {safe_resource}</strong>
            on your current plan. Upgrade to keep creating without interruption.
        </p>

        {self._cta_button("View Plans", f"{self._frontend_url}/dashboard/settings?tab=billing")}
        """
        return (
            self._base_layout(content, f"{self._frontend_url}/email-preferences/unsubscribe/{{{{token}}}}"),
            f"You've used {current_usage} of {limit} {resource}",
        )

    def usage_100_percent(self, user_name: str, resource: str) -> tuple[str, str]:
        """Alert user they've hit their resource limit."""
        safe_name = html_escape(user_name or "")
        safe_resource = html_escape(resource or "")
        content = f"""
        <h2 style="color: #1A1A2E; font-size: 20px; margin-bottom: 16px;">You've reached your {safe_resource} limit</h2>

        <p style="color: #4A4A68; line-height: 1.6; margin-bottom: 24px;">
            Hi {safe_name}, you've used all your {safe_resource} on the free plan.
            Upgrade now to continue creating content without limits.
        </p>

        {self._cta_button("Upgrade Now", f"{self._frontend_url}/dashboard/settings?tab=billing")}
        """
        return (
            self._base_layout(content, f"{self._frontend_url}/email-preferences/unsubscribe/{{{{token}}}}"),
            f"You've reached your {resource} limit — upgrade to continue",
        )

    def power_user_features(self, user_name: str) -> tuple[str, str]:
        """Promote premium features to active free users."""
        safe_name = html_escape(user_name or "")
        content = f"""
        <h2 style="color: #1A1A2E; font-size: 20px; margin-bottom: 16px;">Unlock pro features</h2>

        <p style="color: #4A4A68; line-height: 1.6; margin-bottom: 24px;">
            Hi {safe_name}, you're getting great results on the free plan. Imagine what you could do with:
        </p>

        <div style="background: #F8F9FA; border-radius: 12px; padding: 24px; margin-bottom: 24px;">
            <ul style="color: #4A4A68; margin: 0; padding-left: 20px; line-height: 1.8;">
                <li>Bulk content workflows</li>
                <li>Article templates</li>
                <li>Competitor analysis</li>
                <li>White-label reports</li>
            </ul>
        </div>

        {self._cta_button("See Plans", f"{self._frontend_url}/dashboard/settings?tab=billing")}
        """
        return (
            self._base_layout(content, f"{self._frontend_url}/email-preferences/unsubscribe/{{{{token}}}}"),
            "Unlock bulk workflows, templates, and more",
        )

    def audit_upsell(self, user_name: str, issues_count: int) -> tuple[str, str]:
        """Upsell after a site audit finds issues."""
        safe_name = html_escape(user_name or "")
        content = f"""
        <h2 style="color: #1A1A2E; font-size: 20px; margin-bottom: 16px;">Your site audit found {issues_count} issue{"s" if issues_count != 1 else ""}</h2>

        <p style="color: #4A4A68; line-height: 1.6; margin-bottom: 24px;">
            Hi {safe_name}, your latest site audit detected <strong>{issues_count} SEO issue{"s" if issues_count != 1 else ""}</strong>.
            Upgrade to get detailed fix recommendations and ongoing monitoring.
        </p>

        {self._cta_button("View Plans", f"{self._frontend_url}/dashboard/settings?tab=billing")}
        """
        return (
            self._base_layout(content, f"{self._frontend_url}/email-preferences/unsubscribe/{{{{token}}}}"),
            f"Your site audit found {issues_count} issues to fix",
        )

    # ── Phase 3: Retention ──────────────────────────────────────────

    def inactive_7_days(self, user_name: str) -> tuple[str, str]:
        """Re-engage after 7 days of inactivity."""
        safe_name = html_escape(user_name or "")
        content = f"""
        <h2 style="color: #1A1A2E; font-size: 20px; margin-bottom: 16px;">Your content might need attention</h2>

        <p style="color: #4A4A68; line-height: 1.6; margin-bottom: 24px;">
            Hi {safe_name}, it's been a week since your last visit. Your existing content may be
            losing rankings — check your dashboard for decay alerts and new opportunities.
        </p>

        {self._cta_button("Check My Dashboard", f"{self._frontend_url}/dashboard")}
        """
        return (
            self._base_layout(content, f"{self._frontend_url}/email-preferences/unsubscribe/{{{{token}}}}"),
            "Your content might need attention",
        )

    def inactive_21_days(self, user_name: str) -> tuple[str, str]:
        """Re-engage after 21 days of inactivity."""
        safe_name = html_escape(user_name or "")
        content = f"""
        <h2 style="color: #1A1A2E; font-size: 20px; margin-bottom: 16px;">Here's what's new on A-Stats</h2>

        <p style="color: #4A4A68; line-height: 1.6; margin-bottom: 24px;">
            Hi {safe_name}, we've been busy improving A-Stats while you were away.
            Come back and explore new features like content decay detection, competitor analysis,
            and improved AI article generation.
        </p>

        {self._cta_button("See What's New", f"{self._frontend_url}/dashboard")}
        """
        return (
            self._base_layout(content, f"{self._frontend_url}/email-preferences/unsubscribe/{{{{token}}}}"),
            "New features waiting for you on A-Stats",
        )

    def inactive_45_days(self, user_name: str) -> tuple[str, str]:
        """Final re-engagement after 45 days."""
        safe_name = html_escape(user_name or "")
        content = f"""
        <h2 style="color: #1A1A2E; font-size: 20px; margin-bottom: 16px;">We miss you!</h2>

        <p style="color: #4A4A68; line-height: 1.6; margin-bottom: 24px;">
            Hi {safe_name}, it's been a while. If you need any help getting started again
            or have questions about A-Stats, just reply to this email — we're here to help.
        </p>

        {self._cta_button("Return to Dashboard", f"{self._frontend_url}/dashboard")}
        """
        return (
            self._base_layout(content, f"{self._frontend_url}/email-preferences/unsubscribe/{{{{token}}}}"),
            "We'd love to help you get back on track",
        )

    # ── Phase 4: Ongoing ────────────────────────────────────────────

    def weekly_digest(self, user_name: str, articles_generated: int, decay_alerts: int) -> tuple[str, str]:
        """Weekly activity digest."""
        safe_name = html_escape(user_name or "")
        content = f"""
        <h2 style="color: #1A1A2E; font-size: 20px; margin-bottom: 16px;">Your weekly digest</h2>

        <p style="color: #4A4A68; line-height: 1.6; margin-bottom: 24px;">
            Hi {safe_name}, here's your content summary for the past week:
        </p>

        <div style="background: #F8F9FA; border-radius: 12px; padding: 24px; margin-bottom: 24px;">
            <ul style="color: #4A4A68; margin: 0; padding-left: 20px; line-height: 1.8;">
                <li><strong>{articles_generated}</strong> article{"s" if articles_generated != 1 else ""} generated</li>
                <li><strong>{decay_alerts}</strong> content decay alert{"s" if decay_alerts != 1 else ""}</li>
            </ul>
        </div>

        {self._cta_button("Go to Dashboard", f"{self._frontend_url}/dashboard")}
        """
        return (
            self._base_layout(content, f"{self._frontend_url}/email-preferences/unsubscribe/{{{{token}}}}"),
            f"Weekly digest: {articles_generated} articles, {decay_alerts} alerts",
        )

    def content_decay_alert(self, user_name: str, article_title: str, decay_type: str) -> tuple[str, str]:
        """Alert about content decay on a specific article."""
        safe_name = html_escape(user_name or "")
        safe_title = html_escape(article_title or "")
        safe_decay = html_escape(decay_type or "")
        content = f"""
        <h2 style="color: #1A1A2E; font-size: 20px; margin-bottom: 16px;">Content decay detected</h2>

        <p style="color: #4A4A68; line-height: 1.6; margin-bottom: 24px;">
            Hi {safe_name}, your article <strong>&ldquo;{safe_title}&rdquo;</strong> is losing rankings
            due to <strong>{safe_decay}</strong>. Review and refresh it to recover your positions.
        </p>

        {self._cta_button("Review Article", f"{self._frontend_url}/dashboard")}
        """
        return (
            self._base_layout(content, f"{self._frontend_url}/email-preferences/unsubscribe/{{{{token}}}}"),
            f'"{article_title}" is losing rankings — take action',
        )

    # ── System ──────────────────────────────────────────────────────

    def unsubscribe_confirmation(self, user_name: str) -> tuple[str, str]:
        """Confirm unsubscribe — no unsubscribe link needed."""
        safe_name = html_escape(user_name or "")
        content = f"""
        <h2 style="color: #1A1A2E; font-size: 20px; margin-bottom: 16px;">You've been unsubscribed</h2>

        <p style="color: #4A4A68; line-height: 1.6; margin-bottom: 24px;">
            Hi {safe_name}, you've been unsubscribed from A-Stats journey emails.
            You'll still receive essential account emails (password resets, billing).
        </p>

        <p style="color: #4A4A68; line-height: 1.6; margin-bottom: 24px;">
            Changed your mind? You can re-enable emails anytime from your settings.
        </p>

        {self._cta_button("Manage Email Preferences", f"{self._frontend_url}/dashboard/settings")}
        """
        return (
            self._base_layout(content),
            "You've been unsubscribed from A-Stats emails",
        )

    def resubscribe_confirmation(self, user_name: str) -> tuple[str, str]:
        """Confirm resubscribe — no unsubscribe link needed."""
        safe_name = html_escape(user_name or "")
        content = f"""
        <h2 style="color: #1A1A2E; font-size: 20px; margin-bottom: 16px;">Welcome back!</h2>

        <p style="color: #4A4A68; line-height: 1.6; margin-bottom: 24px;">
            Hi {safe_name}, you've re-subscribed to A-Stats journey emails.
            We'll keep you updated with tips, activity digests, and feature highlights.
        </p>

        {self._cta_button("Go to Dashboard", f"{self._frontend_url}/dashboard")}
        """
        return (
            self._base_layout(content),
            "Welcome back — you're subscribed to A-Stats emails again",
        )
