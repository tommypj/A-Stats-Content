import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Terms of Service",
  description: "Terms governing your use of A-Stats Content.",
};

export default function TermsOfServicePage() {
  const lastUpdated = "February 28, 2026";

  return (
    <article className="prose prose-neutral max-w-none">
      <h1 className="text-3xl font-bold text-text-primary mb-2">Terms of Service</h1>
      <p className="text-sm text-text-muted mb-10">Last updated: {lastUpdated}</p>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-text-primary mb-3">1. Agreement to Terms</h2>
        <p className="text-text-secondary leading-relaxed">
          By accessing or using A-Stats Content (the &ldquo;Service&rdquo;), operated by A-Stats
          (&ldquo;we&rdquo;, &ldquo;us&rdquo;, &ldquo;our&rdquo;), you agree to be bound by these Terms of Service. If you do
          not agree, do not use the Service.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-text-primary mb-3">2. Eligibility</h2>
        <p className="text-text-secondary leading-relaxed">
          You must be at least 18 years old and capable of forming a legally binding contract to use
          the Service. By using the Service, you represent that you meet these requirements.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-text-primary mb-3">3. Account Registration</h2>
        <p className="text-text-secondary leading-relaxed">
          You must provide accurate information when creating an account and keep it up to date.
          You are responsible for all activity that occurs under your account. Keep your credentials
          secure and notify us immediately at{" "}
          <a href="mailto:support@astats.app" className="text-primary-600 hover:underline">
            support@astats.app
          </a>{" "}
          if you suspect unauthorised access.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-text-primary mb-3">4. Subscriptions and Billing</h2>
        <p className="text-text-secondary leading-relaxed mb-4">
          The Service is offered on a subscription basis. Subscriptions automatically renew at the
          end of each billing period unless cancelled before the renewal date. All prices are in USD
          and exclusive of taxes unless stated otherwise.
        </p>
        <p className="text-text-secondary leading-relaxed mb-4">
          Payments are processed by LemonSqueezy. By subscribing you also agree to their{" "}
          <a
            href="https://www.lemonsqueezy.com/terms"
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary-600 hover:underline"
          >
            terms of service
          </a>
          .
        </p>
        <p className="text-text-secondary leading-relaxed">
          <strong>Refunds.</strong> We offer a 7-day money-back guarantee on your first purchase.
          After that period, subscriptions are non-refundable except where required by applicable law.
          To request a refund, contact{" "}
          <a href="mailto:billing@astats.app" className="text-primary-600 hover:underline">
            billing@astats.app
          </a>
          .
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-text-primary mb-3">5. Plan Limits</h2>
        <p className="text-text-secondary leading-relaxed">
          Each subscription plan includes a monthly allowance for articles, outlines, images, and
          social post sets. Unused allowances do not roll over to the next billing period. Limits
          reset on the first day of each billing cycle. Exceeding your plan limits will result in
          requests being declined until the next reset or an upgrade.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-text-primary mb-3">6. Your Content</h2>
        <p className="text-text-secondary leading-relaxed mb-4">
          You retain full ownership of all content you create using the Service. By using the
          Service, you grant us a limited licence to store and process your content solely to provide
          the Service.
        </p>
        <p className="text-text-secondary leading-relaxed">
          You are solely responsible for ensuring that your use of AI-generated content complies
          with applicable laws, platform policies, and any disclosure requirements. We make no
          warranty that AI-generated content is accurate, original, or free from third-party claims.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-text-primary mb-3">7. Acceptable Use</h2>
        <p className="text-text-secondary leading-relaxed mb-3">You agree not to:</p>
        <ul className="list-disc pl-5 space-y-2 text-text-secondary">
          <li>Use the Service to generate illegal, harmful, deceptive, or abusive content</li>
          <li>Circumvent plan limits through technical means (multiple accounts, API abuse, etc.)</li>
          <li>Reverse-engineer, decompile, or attempt to extract the source code of the Service</li>
          <li>Resell or sublicence access to the Service without our written consent</li>
          <li>Use the Service in a way that violates any applicable law or regulation</li>
          <li>Transmit malware, spam, or any other harmful code</li>
        </ul>
        <p className="text-text-secondary leading-relaxed mt-4">
          We reserve the right to suspend or terminate accounts that violate these terms without
          notice or refund.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-text-primary mb-3">8. Intellectual Property</h2>
        <p className="text-text-secondary leading-relaxed">
          The Service, including its design, software, trademarks, and branding, is owned by A-Stats
          and protected by intellectual property law. Nothing in these Terms transfers any ownership
          of our intellectual property to you.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-text-primary mb-3">9. Disclaimer of Warranties</h2>
        <p className="text-text-secondary leading-relaxed">
          THE SERVICE IS PROVIDED &ldquo;AS IS&rdquo; AND &ldquo;AS AVAILABLE&rdquo; WITHOUT WARRANTY OF ANY KIND.
          WE DISCLAIM ALL WARRANTIES, EXPRESS OR IMPLIED, INCLUDING FITNESS FOR A PARTICULAR
          PURPOSE, MERCHANTABILITY, AND NON-INFRINGEMENT. WE DO NOT WARRANT THAT THE SERVICE WILL
          BE UNINTERRUPTED, ERROR-FREE, OR THAT AI-GENERATED CONTENT WILL BE ACCURATE OR ORIGINAL.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-text-primary mb-3">10. Limitation of Liability</h2>
        <p className="text-text-secondary leading-relaxed">
          TO THE MAXIMUM EXTENT PERMITTED BY LAW, A-STATS SHALL NOT BE LIABLE FOR ANY INDIRECT,
          INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, OR LOSS OF PROFITS OR REVENUES,
          ARISING OUT OF OR RELATED TO YOUR USE OF THE SERVICE. OUR TOTAL CUMULATIVE LIABILITY
          SHALL NOT EXCEED THE AMOUNT PAID BY YOU TO US IN THE 12 MONTHS PRECEDING THE CLAIM.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-text-primary mb-3">11. Termination</h2>
        <p className="text-text-secondary leading-relaxed">
          You may cancel your subscription at any time from the billing settings page. We may
          suspend or terminate your account for violations of these Terms, non-payment, or if
          required by law. Upon termination, your access to the Service will cease and we will
          handle your data as described in our{" "}
          <a href="/legal/privacy" className="text-primary-600 hover:underline">
            Privacy Policy
          </a>
          .
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-text-primary mb-3">12. Changes to Terms</h2>
        <p className="text-text-secondary leading-relaxed">
          We may update these Terms from time to time. Material changes will be communicated at
          least 14 days in advance by email or in-app notice. Continued use of the Service after
          the effective date constitutes acceptance of the updated Terms.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-text-primary mb-3">13. Governing Law</h2>
        <p className="text-text-secondary leading-relaxed">
          These Terms are governed by and construed in accordance with the laws of the jurisdiction
          in which A-Stats is incorporated, without regard to conflict of law principles.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-text-primary mb-3">14. Contact</h2>
        <p className="text-text-secondary leading-relaxed">
          Questions about these Terms? Contact us at{" "}
          <a href="mailto:legal@astats.app" className="text-primary-600 hover:underline">
            legal@astats.app
          </a>
          .
        </p>
      </section>
    </article>
  );
}
