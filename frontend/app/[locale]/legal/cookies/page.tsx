import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Cookie Policy",
  description: "How A-Stats uses cookies and similar tracking technologies.",
};

export default function CookiePolicyPage() {
  const lastUpdated = "February 28, 2026";

  return (
    <article className="prose prose-neutral max-w-none">
      <h1 className="text-3xl font-bold text-text-primary mb-2">Cookie Policy</h1>
      <p className="text-sm text-text-muted mb-10">Last updated: {lastUpdated}</p>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-text-primary mb-3">1. What Are Cookies</h2>
        <p className="text-text-secondary leading-relaxed">
          Cookies are small text files stored on your device by your browser when you visit a
          website. They are widely used to make websites work efficiently and to provide information
          to site owners. Similar technologies include local storage and session storage.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-text-primary mb-3">2. How We Use Cookies</h2>
        <p className="text-text-secondary leading-relaxed mb-4">
          A-Stats Content uses a minimal set of cookies and browser storage. We do not use
          advertising or tracking cookies.
        </p>

        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse border border-surface-tertiary rounded-lg overflow-hidden">
            <thead>
              <tr className="bg-surface-secondary">
                <th className="text-left p-3 font-semibold text-text-primary border-b border-surface-tertiary">Name / Key</th>
                <th className="text-left p-3 font-semibold text-text-primary border-b border-surface-tertiary">Type</th>
                <th className="text-left p-3 font-semibold text-text-primary border-b border-surface-tertiary">Purpose</th>
                <th className="text-left p-3 font-semibold text-text-primary border-b border-surface-tertiary">Duration</th>
              </tr>
            </thead>
            <tbody className="text-text-secondary">
              <tr className="border-b border-surface-tertiary">
                <td className="p-3 font-mono text-xs">auth_token</td>
                <td className="p-3">Local Storage</td>
                <td className="p-3">Keeps you logged in between sessions (JWT)</td>
                <td className="p-3">Until logout or expiry</td>
              </tr>
              <tr className="border-b border-surface-tertiary">
                <td className="p-3 font-mono text-xs">NEXT_LOCALE</td>
                <td className="p-3">Cookie</td>
                <td className="p-3">Remembers your language preference</td>
                <td className="p-3">1 year</td>
              </tr>
              <tr>
                <td className="p-3 font-mono text-xs">__ls_*</td>
                <td className="p-3">Cookie</td>
                <td className="p-3">Set by LemonSqueezy during checkout to manage your session</td>
                <td className="p-3">Session</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-text-primary mb-3">3. Essential Cookies Only</h2>
        <p className="text-text-secondary leading-relaxed">
          We only use cookies that are strictly necessary to provide the Service. We do not use:
        </p>
        <ul className="list-disc pl-5 space-y-2 text-text-secondary mt-3">
          <li>Advertising or retargeting cookies</li>
          <li>Third-party analytics cookies (e.g. Google Analytics)</li>
          <li>Social media tracking pixels</li>
          <li>Behavioural profiling cookies</li>
        </ul>
        <p className="text-text-secondary leading-relaxed mt-4">
          Because we only use essential cookies, we do not display a cookie consent banner — these
          cookies cannot be refused without breaking core functionality of the Service.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-text-primary mb-3">4. Managing Cookies</h2>
        <p className="text-text-secondary leading-relaxed">
          You can control and delete cookies through your browser settings. Note that disabling
          cookies may prevent certain features from working correctly. To clear your authentication
          state, simply log out of the Service.
        </p>
        <p className="text-text-secondary leading-relaxed mt-3">
          For guidance on managing cookies in your browser, visit:
        </p>
        <ul className="list-disc pl-5 space-y-1 text-text-secondary mt-2">
          <li>
            <a href="https://support.google.com/chrome/answer/95647" target="_blank" rel="noopener noreferrer" className="text-primary-600 hover:underline">
              Google Chrome
            </a>
          </li>
          <li>
            <a href="https://support.mozilla.org/en-US/kb/cookies-information-websites-store-on-your-computer" target="_blank" rel="noopener noreferrer" className="text-primary-600 hover:underline">
              Mozilla Firefox
            </a>
          </li>
          <li>
            <a href="https://support.apple.com/guide/safari/manage-cookies-sfri11471" target="_blank" rel="noopener noreferrer" className="text-primary-600 hover:underline">
              Apple Safari
            </a>
          </li>
        </ul>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-text-primary mb-3">5. Changes to This Policy</h2>
        <p className="text-text-secondary leading-relaxed">
          We may update this Cookie Policy to reflect changes in our practices or for legal reasons.
          Material changes will be communicated in accordance with our{" "}
          <a href="/legal/privacy" className="text-primary-600 hover:underline">
            Privacy Policy
          </a>
          .
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-text-primary mb-3">6. Contact</h2>
        <p className="text-text-secondary leading-relaxed">
          Questions about our use of cookies? Contact us at{" "}
          <a href="mailto:privacy@astats.app" className="text-primary-600 hover:underline">
            privacy@astats.app
          </a>
          .
        </p>
      </section>
    </article>
  );
}
