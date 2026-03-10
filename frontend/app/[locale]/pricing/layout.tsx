import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Pricing — Plans for Every Content Team",
  description:
    "Choose the A-Stats plan that fits your content production needs. Free tier included. Scale from solo creator to enterprise team with AI-powered SEO articles.",
  openGraph: {
    title: "A-Stats Pricing — Plans for Every Content Team",
    description:
      "AI-powered SEO content generation starting free. Upgrade for bulk generation, white-label, and team features.",
    url: "https://a-stats.app/pricing",
  },
};

export default function PricingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
