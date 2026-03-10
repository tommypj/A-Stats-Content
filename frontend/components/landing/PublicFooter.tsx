"use client";

import Link from "next/link";
import Image from "next/image";
import { useTranslations } from "next-intl";

export default function PublicFooter() {
  const t = useTranslations("landing");

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
              {t("footer.brandDescription")}
            </p>
          </div>

          {/* Product */}
          <div>
            <h4 className="text-sm font-semibold mb-4 text-primary-100">{t("footer.productHeading")}</h4>
            <ul className="space-y-2.5">
              {[
                { label: t("footer.productFeatures"), href: "/#features" },
                { label: t("footer.productPricing"), href: "/#pricing" },
                { label: t("footer.productHowItWorks"), href: "/#how-it-works" },
                { label: t("footer.productBlog"), href: "/blog" },
              ].map(({ label, href }) => (
                <li key={href}>
                  <Link href={href} className="text-sm text-primary-200/60 hover:text-white transition-colors">
                    {label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Resources */}
          <div>
            <h4 className="text-sm font-semibold mb-4 text-primary-100">{t("footer.resourcesHeading")}</h4>
            <ul className="space-y-2.5">
              {[
                { label: t("footer.resourcesBlog"), href: "/blog" },
                { label: t("footer.resourcesDocumentation"), href: "/en/docs" },
                { label: t("footer.resourcesHelpCenter"), href: "/en/docs/getting-started/quick-start" },
                { label: t("footer.resourcesApiReference"), href: "/en/docs" },
              ].map(({ label, href }, i) => (
                <li key={i}>
                  <Link href={href} className="text-sm text-primary-200/60 hover:text-white transition-colors">
                    {label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Legal */}
          <div>
            <h4 className="text-sm font-semibold mb-4 text-primary-100">{t("footer.legalHeading")}</h4>
            <ul className="space-y-2.5">
              {[
                { label: t("footer.legalPrivacy"), href: "/legal/privacy" },
                { label: t("footer.legalTerms"), href: "/legal/terms" },
                { label: t("footer.legalCookies"), href: "/legal/cookies" },
              ].map(({ label, href }) => (
                <li key={href}>
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
            &copy; {new Date().getFullYear()} A-Stats. {t("footer.rights")}
          </p>
          <div className="flex items-center gap-4">
            {[
              { icon: "𝕏", href: "https://x.com/AStatsApp", label: t("footer.socialXLabel") },
              { icon: "in", href: "https://linkedin.com/company/a-stats", label: t("footer.socialLinkedInLabel") },
              { icon: "Gh", href: "https://github.com/a-stats", label: t("footer.socialGitHubLabel") },
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
