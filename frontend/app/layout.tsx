import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Toaster } from "sonner";
import { Providers } from "@/components/providers";
import { ErrorBoundary } from "@/components/ui/error-boundary";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: {
    default: "A-Stats Content | AI-Powered SEO Content Platform",
    template: "%s | A-Stats Content",
  },
  description:
    "Create SEO-optimized therapeutic content with AI. Generate articles, outlines, and images for your wellness business.",
  keywords: [
    "AI content",
    "SEO optimization",
    "therapeutic content",
    "wellness blog",
    "content generation",
    "article writing",
  ],
  authors: [{ name: "A-Stats" }],
  icons: {
    icon: "/icon.svg",
    shortcut: "/icon.svg",
    apple: "/icon.svg",
  },
  openGraph: {
    type: "website",
    locale: "en_US",
    siteName: "A-Stats Content",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="min-h-screen bg-healing-cream">
        <Providers>
          <ErrorBoundary>
            {children}
          </ErrorBoundary>
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
      </body>
    </html>
  );
}
