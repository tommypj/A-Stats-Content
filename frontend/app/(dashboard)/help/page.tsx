"use client";

import { Card } from "@/components/ui/card";
import {
  BookOpen,
  MessageCircle,
  Mail,
  ExternalLink,
  FileText,
  Sparkles,
  Image as ImageIcon,
  BarChart3,
  Share2,
  HelpCircle,
  ChevronRight,
} from "lucide-react";
import Link from "next/link";

const guides = [
  {
    title: "Creating Outlines",
    description: "Learn how to generate AI-powered content outlines for your articles.",
    icon: FileText,
    href: "/outlines",
  },
  {
    title: "Writing Articles",
    description: "Generate SEO-optimized articles from your outlines using AI.",
    icon: Sparkles,
    href: "/articles",
  },
  {
    title: "Image Generation",
    description: "Create custom AI-generated images for your content.",
    icon: ImageIcon,
    href: "/images",
  },
  {
    title: "Analytics & SEO",
    description: "Connect Google Search Console and track your content performance.",
    icon: BarChart3,
    href: "/analytics",
  },
  {
    title: "Social Media",
    description: "Schedule and publish content across Twitter, LinkedIn, and Facebook.",
    icon: Share2,
    href: "/social",
  },
];

const faqs = [
  {
    question: "How do I generate my first article?",
    answer:
      "Start by creating an outline in the Outlines section. Once your outline is ready, click 'Generate Article' to create a full SEO-optimized article using AI.",
  },
  {
    question: "What AI models are used for content generation?",
    answer:
      "We use Anthropic's Claude for text generation and Replicate's Flux model for image generation, ensuring high-quality outputs.",
  },
  {
    question: "How do I connect my social media accounts?",
    answer:
      "Go to Social > Accounts and click 'Connect Account'. Follow the OAuth flow to authorize your Twitter, LinkedIn, or Facebook accounts.",
  },
  {
    question: "How does the Knowledge Vault work?",
    answer:
      "Upload documents (PDF, DOCX, TXT) to your Knowledge Vault. The AI will use this context when generating content, making articles more accurate and relevant to your brand.",
  },
  {
    question: "Can I cancel my subscription at any time?",
    answer:
      "Yes, you can cancel your subscription at any time from Settings > Subscription. You'll retain access until the end of your billing period.",
  },
  {
    question: "How do I connect Google Search Console?",
    answer:
      "Go to Analytics and click 'Connect Google Search Console'. You'll need to authorize access with your Google account that has Search Console access.",
  },
];

export default function HelpPage() {
  return (
    <div className="space-y-8 max-w-4xl animate-in">
      <div>
        <h1 className="text-2xl font-display font-bold text-text-primary">Help & Support</h1>
        <p className="mt-1 text-text-secondary">
          Find guides, FAQs, and ways to get help with A-Stats.
        </p>
      </div>

      {/* Quick Start Guides */}
      <div>
        <h2 className="text-lg font-display font-semibold text-text-primary mb-4">
          Quick Start Guides
        </h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {guides.map((guide) => (
            <Link key={guide.title} href={guide.href}>
              <Card className="p-5 hover:shadow-md transition-all group cursor-pointer h-full">
                <div className="h-10 w-10 rounded-xl bg-primary-50 flex items-center justify-center mb-3">
                  <guide.icon className="h-5 w-5 text-primary-500" />
                </div>
                <h3 className="font-display font-semibold text-text-primary group-hover:text-primary-600 transition-colors">
                  {guide.title}
                </h3>
                <p className="text-sm text-text-secondary mt-1">{guide.description}</p>
                <div className="flex items-center gap-1 mt-3 text-sm text-primary-500 font-medium">
                  <span>Learn more</span>
                  <ChevronRight className="h-4 w-4 group-hover:translate-x-1 transition-transform" />
                </div>
              </Card>
            </Link>
          ))}
        </div>
      </div>

      {/* FAQs */}
      <div>
        <h2 className="text-lg font-display font-semibold text-text-primary mb-4">
          Frequently Asked Questions
        </h2>
        <div className="space-y-3">
          {faqs.map((faq, index) => (
            <Card key={index} className="p-5">
              <div className="flex items-start gap-3">
                <HelpCircle className="h-5 w-5 text-primary-500 mt-0.5 shrink-0" />
                <div>
                  <h3 className="font-medium text-text-primary">{faq.question}</h3>
                  <p className="text-sm text-text-secondary mt-1">{faq.answer}</p>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>

      {/* Contact Support */}
      <Card className="p-6">
        <h2 className="text-lg font-display font-semibold text-text-primary mb-4">
          Need More Help?
        </h2>
        <div className="grid sm:grid-cols-2 gap-4">
          <a
            href="mailto:support@astats.app"
            className="flex items-center gap-3 p-4 rounded-xl bg-surface-secondary hover:bg-surface-tertiary transition-colors"
          >
            <Mail className="h-5 w-5 text-primary-500" />
            <div>
              <p className="font-medium text-text-primary">Email Support</p>
              <p className="text-sm text-text-secondary">support@astats.app</p>
            </div>
          </a>
          <a
            href="https://docs.astats.app"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-3 p-4 rounded-xl bg-surface-secondary hover:bg-surface-tertiary transition-colors"
          >
            <BookOpen className="h-5 w-5 text-primary-500" />
            <div>
              <p className="font-medium text-text-primary flex items-center gap-1">
                Documentation <ExternalLink className="h-3.5 w-3.5" />
              </p>
              <p className="text-sm text-text-secondary">Browse the full docs</p>
            </div>
          </a>
        </div>
      </Card>
    </div>
  );
}
