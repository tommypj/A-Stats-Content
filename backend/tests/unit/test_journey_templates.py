"""
Tests for email journey HTML templates.
"""

import pytest

from adapters.email.journey_templates import JourneyTemplates

FRONTEND_URL = "https://app.example.com"


@pytest.fixture
def templates():
    return JourneyTemplates(FRONTEND_URL)


# ── Branded layout tests ────────────────────────────────────────


class TestBaseLayout:
    """Tests for the shared branded layout wrapper."""

    def test_layout_contains_brand_logo(self, templates: JourneyTemplates):
        html, _ = templates.welcome("Alice")
        assert "linear-gradient(135deg, #ed8f73, #da7756)" in html

    def test_layout_contains_brand_name(self, templates: JourneyTemplates):
        html, _ = templates.welcome("Alice")
        assert "A-Stats Content" in html

    def test_layout_background_color(self, templates: JourneyTemplates):
        html, _ = templates.welcome("Alice")
        assert "#FFF8F0" in html

    def test_layout_container_styles(self, templates: JourneyTemplates):
        html, _ = templates.welcome("Alice")
        assert "max-width: 560px" in html
        assert "border-radius: 16px" in html

    def test_layout_font_family(self, templates: JourneyTemplates):
        html, _ = templates.welcome("Alice")
        assert "Segoe UI" in html
        assert "BlinkMacSystemFont" in html


class TestCtaButton:
    """Tests for the CTA button helper."""

    def test_cta_button_style(self, templates: JourneyTemplates):
        html, _ = templates.welcome("Alice")
        assert "background: #da7756" in html
        assert "border-radius: 12px" in html

    def test_cta_button_contains_link(self, templates: JourneyTemplates):
        html, _ = templates.welcome("Alice")
        assert f"{FRONTEND_URL}/dashboard" in html


# ── Unsubscribe link tests ──────────────────────────────────────

# Journey templates that MUST have an unsubscribe link
JOURNEY_METHODS = [
    "welcome",
    "first_outline_nudge",
    "outline_to_article_nudge",
    "outline_reminder",
    "connect_tools",
    "inactive_7_days",
    "inactive_21_days",
    "inactive_45_days",
    "power_user_features",
]

# System templates that MUST NOT have an unsubscribe link
SYSTEM_METHODS = [
    "unsubscribe_confirmation",
    "resubscribe_confirmation",
]


class TestUnsubscribeLinks:
    """All journey templates must include an unsubscribe link; system templates must not."""

    @pytest.mark.parametrize("method", JOURNEY_METHODS)
    def test_journey_template_has_unsubscribe(self, templates: JourneyTemplates, method: str):
        html, _ = getattr(templates, method)("TestUser")
        assert "Unsubscribe from these emails" in html
        assert "unsubscribe" in html.lower()

    @pytest.mark.parametrize("method", SYSTEM_METHODS)
    def test_system_template_no_unsubscribe(self, templates: JourneyTemplates, method: str):
        html, _ = getattr(templates, method)("TestUser")
        assert "Unsubscribe from these emails" not in html

    def test_week_one_recap_has_unsubscribe(self, templates: JourneyTemplates):
        html, _ = templates.week_one_recap("TestUser", 3, 2)
        assert "Unsubscribe from these emails" in html

    def test_usage_80_has_unsubscribe(self, templates: JourneyTemplates):
        html, _ = templates.usage_80_percent("TestUser", 8, 10, "articles")
        assert "Unsubscribe from these emails" in html

    def test_usage_100_has_unsubscribe(self, templates: JourneyTemplates):
        html, _ = templates.usage_100_percent("TestUser", "articles")
        assert "Unsubscribe from these emails" in html

    def test_audit_upsell_has_unsubscribe(self, templates: JourneyTemplates):
        html, _ = templates.audit_upsell("TestUser", 15)
        assert "Unsubscribe from these emails" in html

    def test_weekly_digest_has_unsubscribe(self, templates: JourneyTemplates):
        html, _ = templates.weekly_digest("TestUser", 5, 2)
        assert "Unsubscribe from these emails" in html

    def test_content_decay_has_unsubscribe(self, templates: JourneyTemplates):
        html, _ = templates.content_decay_alert("TestUser", "My Article", "traffic drop")
        assert "Unsubscribe from these emails" in html


# ── XSS escaping tests ─────────────────────────────────────────

XSS_PAYLOAD = '<script>alert("xss")</script>'
ESCAPED_SCRIPT = "&lt;script&gt;"


class TestXSSEscaping:
    """User-provided strings must be HTML-escaped."""

    def test_welcome_escapes_name(self, templates: JourneyTemplates):
        html, _ = templates.welcome(XSS_PAYLOAD)
        assert ESCAPED_SCRIPT in html
        assert "<script>" not in html

    def test_first_outline_nudge_escapes_name(self, templates: JourneyTemplates):
        html, _ = templates.first_outline_nudge(XSS_PAYLOAD)
        assert ESCAPED_SCRIPT in html
        assert "<script>" not in html

    def test_outline_to_article_escapes_name(self, templates: JourneyTemplates):
        html, _ = templates.outline_to_article_nudge(XSS_PAYLOAD)
        assert ESCAPED_SCRIPT in html

    def test_outline_reminder_escapes_name(self, templates: JourneyTemplates):
        html, _ = templates.outline_reminder(XSS_PAYLOAD)
        assert ESCAPED_SCRIPT in html

    def test_connect_tools_escapes_name(self, templates: JourneyTemplates):
        html, _ = templates.connect_tools(XSS_PAYLOAD)
        assert ESCAPED_SCRIPT in html

    def test_week_one_recap_escapes_name(self, templates: JourneyTemplates):
        html, _ = templates.week_one_recap(XSS_PAYLOAD, 1, 1)
        assert ESCAPED_SCRIPT in html

    def test_usage_80_escapes_name_and_resource(self, templates: JourneyTemplates):
        html, _ = templates.usage_80_percent(XSS_PAYLOAD, 8, 10, XSS_PAYLOAD)
        assert html.count(ESCAPED_SCRIPT) >= 2
        assert "<script>" not in html

    def test_usage_100_escapes_name_and_resource(self, templates: JourneyTemplates):
        html, _ = templates.usage_100_percent(XSS_PAYLOAD, XSS_PAYLOAD)
        assert html.count(ESCAPED_SCRIPT) >= 2

    def test_power_user_escapes_name(self, templates: JourneyTemplates):
        html, _ = templates.power_user_features(XSS_PAYLOAD)
        assert ESCAPED_SCRIPT in html

    def test_audit_upsell_escapes_name(self, templates: JourneyTemplates):
        html, _ = templates.audit_upsell(XSS_PAYLOAD, 5)
        assert ESCAPED_SCRIPT in html

    def test_inactive_7_escapes_name(self, templates: JourneyTemplates):
        html, _ = templates.inactive_7_days(XSS_PAYLOAD)
        assert ESCAPED_SCRIPT in html

    def test_inactive_21_escapes_name(self, templates: JourneyTemplates):
        html, _ = templates.inactive_21_days(XSS_PAYLOAD)
        assert ESCAPED_SCRIPT in html

    def test_inactive_45_escapes_name(self, templates: JourneyTemplates):
        html, _ = templates.inactive_45_days(XSS_PAYLOAD)
        assert ESCAPED_SCRIPT in html

    def test_weekly_digest_escapes_name(self, templates: JourneyTemplates):
        html, _ = templates.weekly_digest(XSS_PAYLOAD, 1, 0)
        assert ESCAPED_SCRIPT in html

    def test_content_decay_escapes_all_fields(self, templates: JourneyTemplates):
        html, _ = templates.content_decay_alert(XSS_PAYLOAD, XSS_PAYLOAD, XSS_PAYLOAD)
        assert html.count(ESCAPED_SCRIPT) >= 3
        assert "<script>" not in html

    def test_unsubscribe_confirmation_escapes_name(self, templates: JourneyTemplates):
        html, _ = templates.unsubscribe_confirmation(XSS_PAYLOAD)
        assert ESCAPED_SCRIPT in html

    def test_resubscribe_confirmation_escapes_name(self, templates: JourneyTemplates):
        html, _ = templates.resubscribe_confirmation(XSS_PAYLOAD)
        assert ESCAPED_SCRIPT in html


# ── Individual template content tests ───────────────────────────


class TestWelcome:
    def test_contains_user_name(self, templates: JourneyTemplates):
        html, _ = templates.welcome("Alice")
        assert "Alice" in html

    def test_subject_line(self, templates: JourneyTemplates):
        _, subject = templates.welcome("Alice")
        assert "ready" in subject.lower()

    def test_dashboard_cta(self, templates: JourneyTemplates):
        html, _ = templates.welcome("Alice")
        assert f"{FRONTEND_URL}/dashboard" in html


class TestFirstOutlineNudge:
    def test_contains_user_name(self, templates: JourneyTemplates):
        html, _ = templates.first_outline_nudge("Bob")
        assert "Bob" in html

    def test_subject_line(self, templates: JourneyTemplates):
        _, subject = templates.first_outline_nudge("Bob")
        assert "outline" in subject.lower()

    def test_outlines_cta(self, templates: JourneyTemplates):
        html, _ = templates.first_outline_nudge("Bob")
        assert "/outlines" in html


class TestOutlineToArticleNudge:
    def test_contains_user_name(self, templates: JourneyTemplates):
        html, _ = templates.outline_to_article_nudge("Carol")
        assert "Carol" in html

    def test_subject_mentions_article(self, templates: JourneyTemplates):
        _, subject = templates.outline_to_article_nudge("Carol")
        assert "article" in subject.lower()


class TestOutlineReminder:
    def test_contains_user_name(self, templates: JourneyTemplates):
        html, _ = templates.outline_reminder("Dan")
        assert "Dan" in html

    def test_subject_line(self, templates: JourneyTemplates):
        _, subject = templates.outline_reminder("Dan")
        assert "outline" in subject.lower()


class TestConnectTools:
    def test_contains_wordpress(self, templates: JourneyTemplates):
        html, _ = templates.connect_tools("Eve")
        assert "WordPress" in html

    def test_settings_cta(self, templates: JourneyTemplates):
        html, _ = templates.connect_tools("Eve")
        assert "/settings" in html


class TestWeekOneRecap:
    def test_shows_outlines_count(self, templates: JourneyTemplates):
        html, _ = templates.week_one_recap("Frank", 5, 3)
        assert "5" in html
        assert "3" in html

    def test_subject_includes_counts(self, templates: JourneyTemplates):
        _, subject = templates.week_one_recap("Frank", 5, 3)
        assert "5" in subject
        assert "3" in subject

    def test_singular_plural(self, templates: JourneyTemplates):
        html, _ = templates.week_one_recap("Frank", 1, 1)
        assert "1</strong> outline created" in html
        assert "1</strong> article generated" in html

    def test_plural_form(self, templates: JourneyTemplates):
        html, _ = templates.week_one_recap("Frank", 2, 0)
        assert "outlines created" in html
        assert "articles generated" in html


class TestUsage80Percent:
    def test_shows_usage_stats(self, templates: JourneyTemplates):
        html, _ = templates.usage_80_percent("Grace", 8, 10, "articles")
        assert "8 of 10" in html
        assert "articles" in html

    def test_billing_cta(self, templates: JourneyTemplates):
        html, _ = templates.usage_80_percent("Grace", 8, 10, "articles")
        assert "tab=billing" in html

    def test_subject_includes_counts(self, templates: JourneyTemplates):
        _, subject = templates.usage_80_percent("Grace", 8, 10, "articles")
        assert "8" in subject
        assert "10" in subject


class TestUsage100Percent:
    def test_shows_resource(self, templates: JourneyTemplates):
        html, _ = templates.usage_100_percent("Hank", "outlines")
        assert "outlines" in html

    def test_upgrade_cta(self, templates: JourneyTemplates):
        html, _ = templates.usage_100_percent("Hank", "outlines")
        assert "tab=billing" in html


class TestPowerUserFeatures:
    def test_mentions_bulk_workflows(self, templates: JourneyTemplates):
        html, _ = templates.power_user_features("Ivy")
        assert "Bulk" in html or "bulk" in html

    def test_billing_cta(self, templates: JourneyTemplates):
        html, _ = templates.power_user_features("Ivy")
        assert "tab=billing" in html


class TestAuditUpsell:
    def test_shows_issues_count(self, templates: JourneyTemplates):
        html, _ = templates.audit_upsell("Jack", 42)
        assert "42" in html

    def test_subject_includes_count(self, templates: JourneyTemplates):
        _, subject = templates.audit_upsell("Jack", 42)
        assert "42" in subject

    def test_singular_issue(self, templates: JourneyTemplates):
        html, _ = templates.audit_upsell("Jack", 1)
        assert "1 issue" in html
        assert "1 issues" not in html


class TestInactive7Days:
    def test_contains_user_name(self, templates: JourneyTemplates):
        html, _ = templates.inactive_7_days("Kate")
        assert "Kate" in html

    def test_dashboard_cta(self, templates: JourneyTemplates):
        html, _ = templates.inactive_7_days("Kate")
        assert f"{FRONTEND_URL}/dashboard" in html


class TestInactive21Days:
    def test_contains_user_name(self, templates: JourneyTemplates):
        html, _ = templates.inactive_21_days("Leo")
        assert "Leo" in html

    def test_mentions_new_features(self, templates: JourneyTemplates):
        html, _ = templates.inactive_21_days("Leo")
        assert "new" in html.lower() or "feature" in html.lower()


class TestInactive45Days:
    def test_contains_user_name(self, templates: JourneyTemplates):
        html, _ = templates.inactive_45_days("Mia")
        assert "Mia" in html

    def test_subject_empathetic(self, templates: JourneyTemplates):
        _, subject = templates.inactive_45_days("Mia")
        assert len(subject) > 0


class TestWeeklyDigest:
    def test_shows_stats(self, templates: JourneyTemplates):
        html, _ = templates.weekly_digest("Nick", 7, 3)
        assert "7" in html
        assert "3" in html

    def test_subject_includes_stats(self, templates: JourneyTemplates):
        _, subject = templates.weekly_digest("Nick", 7, 3)
        assert "7" in subject
        assert "3" in subject


class TestContentDecayAlert:
    def test_shows_article_title(self, templates: JourneyTemplates):
        html, _ = templates.content_decay_alert("Olivia", "Best SEO Tools 2025", "traffic drop")
        assert "Best SEO Tools 2025" in html

    def test_shows_decay_type(self, templates: JourneyTemplates):
        html, _ = templates.content_decay_alert("Olivia", "My Article", "ranking decline")
        assert "ranking decline" in html

    def test_subject_includes_title(self, templates: JourneyTemplates):
        _, subject = templates.content_decay_alert("Olivia", "My Article", "traffic drop")
        assert "My Article" in subject


class TestUnsubscribeConfirmation:
    def test_contains_user_name(self, templates: JourneyTemplates):
        html, _ = templates.unsubscribe_confirmation("Pat")
        assert "Pat" in html

    def test_mentions_resubscribe(self, templates: JourneyTemplates):
        html, _ = templates.unsubscribe_confirmation("Pat")
        assert "re-enable" in html.lower() or "settings" in html.lower()

    def test_no_unsubscribe_link(self, templates: JourneyTemplates):
        html, _ = templates.unsubscribe_confirmation("Pat")
        assert "Unsubscribe from these emails" not in html


class TestResubscribeConfirmation:
    def test_contains_user_name(self, templates: JourneyTemplates):
        html, _ = templates.resubscribe_confirmation("Quinn")
        assert "Quinn" in html

    def test_subject_says_welcome_back(self, templates: JourneyTemplates):
        _, subject = templates.resubscribe_confirmation("Quinn")
        assert "back" in subject.lower() or "welcome" in subject.lower()

    def test_no_unsubscribe_link(self, templates: JourneyTemplates):
        html, _ = templates.resubscribe_confirmation("Quinn")
        assert "Unsubscribe from these emails" not in html


# ── Edge case tests ─────────────────────────────────────────────


class TestEdgeCases:
    def test_empty_user_name(self, templates: JourneyTemplates):
        html, _ = templates.welcome("")
        assert "Hi ," in html  # gracefully handles empty name

    def test_none_user_name(self, templates: JourneyTemplates):
        html, _ = templates.welcome(None)  # type: ignore[arg-type]
        assert "Hi ," in html

    def test_frontend_url_trailing_slash_stripped(self):
        t = JourneyTemplates("https://example.com/")
        html, _ = t.welcome("Alice")
        assert "https://example.com/dashboard" in html
        assert "https://example.com//dashboard" not in html

    def test_returns_tuple(self, templates: JourneyTemplates):
        result = templates.welcome("Alice")
        assert isinstance(result, tuple)
        assert len(result) == 2
        html, subject = result
        assert isinstance(html, str)
        assert isinstance(subject, str)

    def test_all_templates_return_valid_html(self, templates: JourneyTemplates):
        """Every template must return valid HTML with DOCTYPE."""
        methods_and_args = [
            ("welcome", ("User",)),
            ("first_outline_nudge", ("User",)),
            ("outline_to_article_nudge", ("User",)),
            ("outline_reminder", ("User",)),
            ("connect_tools", ("User",)),
            ("week_one_recap", ("User", 1, 1)),
            ("usage_80_percent", ("User", 8, 10, "articles")),
            ("usage_100_percent", ("User", "articles")),
            ("power_user_features", ("User",)),
            ("audit_upsell", ("User", 5)),
            ("inactive_7_days", ("User",)),
            ("inactive_21_days", ("User",)),
            ("inactive_45_days", ("User",)),
            ("weekly_digest", ("User", 3, 1)),
            ("content_decay_alert", ("User", "Title", "decay")),
            ("unsubscribe_confirmation", ("User",)),
            ("resubscribe_confirmation", ("User",)),
        ]
        for method_name, args in methods_and_args:
            html, subject = getattr(templates, method_name)(*args)
            assert "<!DOCTYPE html>" in html, f"{method_name} missing DOCTYPE"
            assert "</html>" in html, f"{method_name} missing closing html tag"
            assert len(subject) > 0, f"{method_name} has empty subject"
