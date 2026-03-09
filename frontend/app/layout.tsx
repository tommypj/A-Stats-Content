import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Script from "next/script";
import { Toaster } from "sonner";
import { Providers } from "@/components/providers";
import { ErrorBoundary } from "@/components/ui/error-boundary";
import { CookieBanner } from "@/components/ui/cookie-banner";
import "./globals.css";

const GA_MEASUREMENT_ID = process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID;

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: {
    default: "A-Stats | AI-Powered SEO & Content Platform",
    template: "%s | A-Stats",
  },
  description:
    "Generate SEO-optimized articles, track keyword rankings, and scale your content production with AI. From keyword to published article in minutes.",
  keywords: [
    "AI content generation",
    "SEO platform",
    "AI SEO tool",
    "content marketing",
    "bulk content generation",
    "AI article writer",
    "SEO analytics",
    "Answer Engine Optimization",
  ],
  authors: [{ name: "A-Stats" }],
  icons: {
    icon: "/icon.png",
    shortcut: "/icon.png",
    apple: "/icon.png",
  },
  openGraph: {
    type: "website",
    locale: "en_US",
    siteName: "A-Stats",
    url: "https://a-stats.app",
  },
  robots: {
    index: true,
    follow: true,
  },
};

const globalJsonLd = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": "https://a-stats.app/#organization",
      name: "A-Stats",
      url: "https://a-stats.app",
      logo: {
        "@type": "ImageObject",
        url: "https://a-stats.app/icon.png",
        width: 512,
        height: 512,
      },
      sameAs: [
        "https://twitter.com/astatsapp",
        "https://www.linkedin.com/company/a-stats",
      ],
    },
    {
      "@type": "WebSite",
      "@id": "https://a-stats.app/#website",
      url: "https://a-stats.app",
      name: "A-Stats",
      description:
        "AI-powered content creation and SEO/AEO platform for modern creators.",
      publisher: { "@id": "https://a-stats.app/#organization" },
      potentialAction: {
        "@type": "SearchAction",
        target: {
          "@type": "EntryPoint",
          urlTemplate: "https://a-stats.app/en/blog?search={search_term_string}",
        },
        "query-input": "required name=search_term_string",
      },
    },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="min-h-screen bg-healing-cream">
        {GA_MEASUREMENT_ID && (
          <>
            <Script
              src={`https://www.googletagmanager.com/gtag/js?id=${GA_MEASUREMENT_ID}`}
              strategy="afterInteractive"
            />
            <Script id="google-analytics" strategy="afterInteractive">
              {`
                window.dataLayer = window.dataLayer || [];
                function gtag(){dataLayer.push(arguments);}
                gtag('js', new Date());
                gtag('config', '${GA_MEASUREMENT_ID}');
              `}
            </Script>
          </>
        )}
        <Script
          src="https://app.lemonsqueezy.com/js/lemon.js"
          strategy="afterInteractive"
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(globalJsonLd) }}
        />
        <Providers>
          <ErrorBoundary>
            {children}
          </ErrorBoundary>
          <CookieBanner />
          <Toaster
            position="bottom-right"
            toastOptions={{
              style: {
                background: "#fdfcfa",
                border: "1px solid #f3ece0",
                borderRadius: "12px",
              },
            }}
          />
        </Providers>
      </body>
    </html>
  );
}
