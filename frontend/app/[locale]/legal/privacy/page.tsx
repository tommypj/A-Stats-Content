import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description: "How A-Stats collects, uses, and protects your personal data.",
};

export default function PrivacyPolicyPage() {
  const lastUpdated = "February 28, 2026";

  return (
    <article className="prose prose-neutral max-w-none">
      <h1 className="text-3xl font-bold text-text-primary mb-2">Privacy Policy</h1>
      <p className="text-sm text-text-muted mb-10">Last updated: {lastUpdated}</p>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-text-primary mb-3">1. Who We Are</h2>
        <p className="text-text-secondary leading-relaxed">
          A-Stats (&ldquo;we&rdquo;, &ldquo;us&rdquo;, &ldquo;our&rdquo;) operates A-Stats Content, an AI-powered SEO content
          platform. This Privacy Policy explains how we collect, use, disclose, and safeguard your
          information when you use our service. By using A-Stats Content you agree to the terms
          described here.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-text-primary mb-3">2. Information We Collect</h2>
        <h3 className="text-base font-semibold text-text-primary mb-2">Account Data</h3>
        <p className="text-text-secondary leading-relaxed mb-4">
          When you register, we collect your name, email address, and password (stored as a
          one-way hash). If you connect third-party accounts (Google Search Console, social media
          platforms), we store the OAuth tokens required to access those services on your behalf.
        </p>
        <h3 className="text-base font-semibold text-text-primary mb-2">Content You Create</h3>
        <p className="text-text-secondary leading-relaxed mb-4">
          Articles, outlines, images, keywords, and other content you generate or upload are stored
          to provide the service. You retain full ownership of your content.
        </p>
        <h3 className="text-base font-semibold text-text-primary mb-2">Usage Data</h3>
        <p className="text-text-secondary leading-relaxed mb-4">
          We collect standard server logs (IP address, browser type, pages visited, timestamps) to
          operate and improve the service. We track feature usage (e.g. articles generated this
          month) to enforce plan limits.
        </p>
        <h3 className="text-base font-semibold text-text-primary mb-2">Payment Data</h3>
        <p className="text-text-secondary leading-relaxed">
          Payments are processed by LemonSqueezy. We do not store your card details. We receive
          webhook notifications from LemonSqueezy confirming subscription status and store only
          non-sensitive subscription metadata (plan tier, billing cycle, expiry date).
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-text-primary mb-3">3. How We Use Your Information</h2>
        <ul className="list-disc pl-5 space-y-2 text-text-secondary">
          <li>Provide, maintain, and improve the A-Stats Content platform</li>
          <li>Process your subscription and manage plan limits</li>
          <li>Send transactional emails (account verification, password reset, project invitations)</li>
          <li>Respond to support requests</li>
          <li>Monitor for abuse, fraud, and security incidents</li>
          <li>Comply with legal obligations</li>
        </ul>
        <p className="text-text-secondary leading-relaxed mt-4">
          We do not sell your personal data. We do not use your content to train AI models.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-text-primary mb-3">4. Third-Party Services</h2>
        <p className="text-text-secondary leading-relaxed mb-3">
          We share data with third parties only as necessary to operate the service:
        </p>
        <ul className="list-disc pl-5 space-y-2 text-text-secondary">
          <li><strong>Anthropic</strong> — Your prompts and article context are sent to the Claude API to generate content. Anthropic&apos;s privacy policy governs their data handling.</li>
          <li><strong>Replicate</strong> — Image generation requests are processed via Replicate&apos;s hosted models.</li>
          <li><strong>LemonSqueezy</strong> — Payment processing and subscription management.</li>
          <li><strong>Resend</strong> — Transactional email delivery.</li>
          <li><strong>Railway / Vercel</strong> — Infrastructure hosting (database, backend, frontend).</li>
        </ul>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-text-primary mb-3">5. Data Retention</h2>
        <p className="text-text-secondary leading-relaxed">
          We retain your account data for as long as your account is active. If you delete your
          account, we will delete or anonymise your personal data within 30 days, except where we
          are required to retain it for legal or financial compliance purposes (e.g. billing records
          for up to 7 years).
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-text-primary mb-3">6. Your Rights</h2>
        <p className="text-text-secondary leading-relaxed mb-3">
          Depending on your jurisdiction, you may have the right to:
        </p>
        <ul className="list-disc pl-5 space-y-2 text-text-secondary">
          <li>Access the personal data we hold about you</li>
          <li>Correct inaccurate data</li>
          <li>Request deletion of your data (&ldquo;right to be forgotten&rdquo;)</li>
          <li>Object to or restrict processing of your data</li>
          <li>Receive a copy of your data in a portable format</li>
          <li>Withdraw consent at any time (where processing is based on consent)</li>
        </ul>
        <p className="text-text-secondary leading-relaxed mt-4">
          To exercise any of these rights, email us at{" "}
          <a href="mailto:privacy@astats.app" className="text-primary-600 hover:underline">
            privacy@astats.app
          </a>
          .
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-text-primary mb-3">7. Security</h2>
        <p className="text-text-secondary leading-relaxed">
          We implement industry-standard security measures including encryption at rest and in
          transit, hashed passwords, application passwords for third-party integrations, and
          regular security reviews. No system is perfectly secure; in the event of a breach we
          will notify affected users as required by applicable law.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-text-primary mb-3">8. Cookies</h2>
        <p className="text-text-secondary leading-relaxed">
          We use cookies and similar technologies as described in our{" "}
          <a href="/legal/cookies" className="text-primary-600 hover:underline">
            Cookie Policy
          </a>
          .
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-text-primary mb-3">9. Changes to This Policy</h2>
        <p className="text-text-secondary leading-relaxed">
          We may update this Privacy Policy from time to time. Material changes will be communicated
          by email or a prominent notice on the platform at least 14 days before taking effect.
          Continued use of the service after that date constitutes acceptance of the updated policy.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-text-primary mb-3">10. Contact</h2>
        <p className="text-text-secondary leading-relaxed">
          For privacy-related questions or requests, contact us at{" "}
          <a href="mailto:privacy@astats.app" className="text-primary-600 hover:underline">
            privacy@astats.app
          </a>
          .
        </p>
      </section>
    </article>
  );
}
