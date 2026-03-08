import Link from "next/link";
import Image from "next/image";

export default function PublicFooter() {
  return (
    <footer className="py-16 bg-primary-950 text-white">
      <div className="page-container">
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-10 mb-12">
          {/* Brand */}
          <div>
            <div className="flex items-center gap-2.5 mb-4">
              <Image src="/icon.png" alt="A-Stats" width={28} height={28} className="rounded-md" />
              <span className="font-display text-lg font-semibold">A-Stats</span>
            </div>
            <p className="text-sm text-primary-200/60 leading-relaxed">
              AI-powered content creation and SEO platform for modern creators.
            </p>
          </div>

          {/* Product */}
          <div>
            <h4 className="text-sm font-semibold mb-4 text-primary-100">Product</h4>
            <ul className="space-y-2.5">
              {[
                { label: "Features", href: "/#features" },
                { label: "Pricing", href: "/#pricing" },
                { label: "How It Works", href: "/#how-it-works" },
                { label: "Blog", href: "/blog" },
              ].map(({ label, href }) => (
                <li key={label}>
                  <Link href={href} className="text-sm text-primary-200/60 hover:text-white transition-colors">
                    {label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Resources */}
          <div>
            <h4 className="text-sm font-semibold mb-4 text-primary-100">Resources</h4>
            <ul className="space-y-2.5">
              {[
                { label: "Blog", href: "/blog" },
                { label: "Documentation", href: "/en/docs" },
                { label: "Help Center", href: "/en/docs/getting-started/quick-start" },
                { label: "API Reference", href: "/en/docs" },
              ].map(({ label, href }) => (
                <li key={label}>
                  <Link href={href} className="text-sm text-primary-200/60 hover:text-white transition-colors">
                    {label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Legal */}
          <div>
            <h4 className="text-sm font-semibold mb-4 text-primary-100">Legal</h4>
            <ul className="space-y-2.5">
              {[
                { label: "Privacy Policy", href: "/legal/privacy" },
                { label: "Terms of Service", href: "/legal/terms" },
                { label: "Cookie Policy", href: "/legal/cookies" },
              ].map(({ label, href }) => (
                <li key={label}>
                  <Link href={href} className="text-sm text-primary-200/60 hover:text-white transition-colors">
                    {label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="border-t border-primary-800 pt-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-xs text-primary-200/40">
            &copy; {new Date().getFullYear()} A-Stats. All rights reserved.
          </p>
          <div className="flex items-center gap-4">
            {[
              { icon: "𝕏", href: "https://x.com/AStatsApp", label: "X (Twitter)" },
              { icon: "in", href: "https://linkedin.com/company/a-stats", label: "LinkedIn" },
              { icon: "Gh", href: "https://github.com/a-stats", label: "GitHub" },
            ].map(({ icon, href, label }) => (
              <a
                key={icon}
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={label}
                className="h-8 w-8 rounded-full bg-primary-800/50 flex items-center justify-center text-xs text-primary-200/60 hover:bg-primary-700 hover:text-white transition-colors"
              >
                {icon}
              </a>
            ))}
          </div>
        </div>
      </div>
    </footer>
  );
}
