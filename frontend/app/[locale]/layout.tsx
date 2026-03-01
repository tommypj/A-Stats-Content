import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { NextIntlClientProvider } from "next-intl";
import { getMessages } from "next-intl/server";
import { Toaster } from "sonner";
import { Providers } from "@/components/providers";
import "../globals.css";

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

export default async function LocaleLayout({
  children,
  params: { locale },
}: {
  children: React.ReactNode;
  params: { locale: string };
}) {
  // Providing all messages to the client side
  const messages = await getMessages();

  return (
    <html lang={locale} className={inter.variable}>
      <body className="min-h-screen bg-healing-cream">
        <NextIntlClientProvider messages={messages}>
          <Providers>
            {children}
            <Toaster
              position="bottom-right"
              toastOptions={{
                style: {
                  background: "white",
                  border: "1px solid #f3ece0",
                  borderRadius: "12px",
                },
              }}
            />
          </Providers>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
