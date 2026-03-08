"use client";

import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  Sparkles,
  FileText,
  BarChart3,
  ArrowRight,
  Check,
  Share2,
  BookOpen,
  Plus,
  ChevronRight,
  Zap,
  Bell,
  TrendingUp,
  Clock,
  CreditCard,
  ShieldCheck,
  Calendar,
} from "lucide-react";
import PublicNav from "./PublicNav";
import PublicFooter from "./PublicFooter";
import { api, type BlogPostCard } from "@/lib/api";

/* ───────────────────────── Scroll-reveal hook ───────────────────────── */

function useScrollReveal() {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          el.classList.add("revealed");
          observer.unobserve(el);
        }
      },
      { threshold: 0.15 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return ref;
}

function RevealSection({
  children,
  className = "",
  direction,
}: {
  children: React.ReactNode;
  className?: string;
  direction?: "left" | "right";
}) {
  const ref = useScrollReveal();
  const cls =
    direction === "left"
      ? "scroll-reveal-left"
      : direction === "right"
        ? "scroll-reveal-right"
        : "scroll-reveal";
  return (
    <div ref={ref} className={`${cls} ${className}`}>
      {children}
    </div>
  );
}

/* ───────────────────────── Mockup components ───────────────────────── */

function HeroMockup() {
  return (
    <div className="relative pt-6 pb-6 px-4">
      {/* Integration badges — stacked above the card on mobile, overlapping top-left on desktop */}
      <div className="flex flex-wrap gap-2 mb-3 lg:absolute lg:top-0 lg:left-0 lg:z-10 lg:flex-col lg:gap-1.5 lg:mb-0">
        {/* WordPress */}
        <div className="bg-white rounded-xl shadow-soft border border-surface-tertiary px-3 py-2 flex items-center gap-2">
          <div className="h-6 w-6 rounded flex items-center justify-center text-white text-xs font-bold" style={{ backgroundColor: "#21759B" }}>W</div>
          <div>
            <div className="text-xs font-semibold text-text-primary leading-none">WordPress</div>
            <div className="text-xs text-green-500 leading-none mt-0.5">Connected</div>
          </div>
        </div>
        {/* Google Search Console */}
        <div className="bg-white rounded-xl shadow-soft border border-surface-tertiary px-3 py-2 flex items-center gap-2">
          <div className="h-6 w-6 rounded flex items-center justify-center text-white text-xs font-bold" style={{ backgroundColor: "#4285F4" }}>G</div>
          <div>
            <div className="text-xs font-semibold text-text-primary leading-none">Search Console</div>
            <div className="text-xs text-green-500 leading-none mt-0.5">Connected</div>
          </div>
        </div>
        {/* PageSpeed */}
        <div className="bg-white rounded-xl shadow-soft border border-surface-tertiary px-3 py-2 flex items-center gap-2">
          <div className="h-6 w-6 rounded flex items-center justify-center text-white text-xs font-bold" style={{ backgroundColor: "#F4B400" }}>⚡</div>
          <div>
            <div className="text-xs font-semibold text-text-primary leading-none">PageSpeed</div>
            <div className="text-xs text-green-500 leading-none mt-0.5">Score: 94</div>
          </div>
        </div>
      </div>

      {/* Main article card */}
      <div className="bg-white rounded-2xl shadow-[0_4px_32px_rgba(0,0,0,0.10)] border border-surface-tertiary overflow-hidden">
        {/* Editor header */}
        <div className="flex items-center justify-between px-4 py-3 bg-surface-secondary border-b border-surface-tertiary">
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-green-400" />
            <span className="text-xs font-medium text-text-primary">Article Ready</span>
          </div>
          <span className="text-xs text-text-muted">2,847 words · ~11 min read</span>
        </div>

        {/* Content */}
        <div className="p-5">
          <div className="inline-flex items-center gap-1.5 text-xs bg-primary-50 text-primary-600 px-2.5 py-1 rounded-full mb-3 font-medium">
            Keyword: seo best practices 2026
          </div>
          <h4 className="text-sm font-bold text-text-primary mb-2 leading-snug">
            10 Best SEO Practices for 2026: A Complete Guide
          </h4>
          <div className="space-y-1.5 mb-3">
            <div className="h-1.5 w-full rounded-full bg-surface-tertiary" />
            <div className="h-1.5 w-11/12 rounded-full bg-surface-tertiary" />
            <div className="h-1.5 w-4/5 rounded-full bg-surface-tertiary" />
          </div>
          <div className="text-xs font-semibold text-text-primary mb-1.5">1. Optimize for Search Intent</div>
          <div className="space-y-1.5 mb-4">
            <div className="h-1.5 w-full rounded-full bg-surface-tertiary" />
            <div className="h-1.5 w-10/12 rounded-full bg-surface-tertiary" />
          </div>
          {/* Score + CTA */}
          <div className="flex items-center gap-4 pt-3 border-t border-surface-tertiary">
            <div className="flex-1">
              <div className="flex justify-between text-xs mb-1.5">
                <span className="text-text-muted">SEO Score</span>
                <span className="font-semibold text-primary-600">94 / 100</span>
              </div>
              <div className="h-1.5 rounded-full bg-surface-tertiary overflow-hidden">
                <div className="h-full w-[94%] rounded-full bg-gradient-to-r from-primary-400 to-primary-500" />
              </div>
            </div>
            <div className="text-xs bg-primary-500 text-white px-3 py-1.5 rounded-lg font-medium whitespace-nowrap">
              Publish →
            </div>
          </div>
        </div>
      </div>

      {/* AEO score — bottom right */}
      <div className="absolute -bottom-2 -right-2 z-10 bg-primary-950 rounded-2xl shadow-soft p-4 text-center">
        <div className="flex items-center gap-1 mb-1 justify-center">
          <Zap className="h-3 w-3 text-primary-400" />
          <span className="text-xs text-primary-300 font-medium">AEO Score</span>
        </div>
        <div className="text-3xl font-bold text-primary-400 leading-none mb-1">82</div>
        <div className="text-xs text-primary-300">
          <span className="text-green-400 font-semibold">+12</span> this month
        </div>
      </div>
    </div>
  );
}

function ContentGenMockup() {
  return (
    <div className="aspect-[4/3] rounded-2xl bg-gradient-to-br from-primary-50 via-cream-100 to-terra-400/10 p-4 flex items-center justify-center">
      <div className="w-full bg-white/80 backdrop-blur-sm rounded-xl shadow-soft border border-surface-tertiary overflow-hidden">
        <div className="flex items-center justify-between px-3 py-2.5 bg-surface-secondary border-b border-surface-tertiary">
          <span className="text-xs font-semibold text-text-primary">New Article</span>
          <div className="flex items-center gap-1.5">
            <div className="h-1.5 w-1.5 rounded-full bg-yellow-400 animate-pulse" />
            <span className="text-xs text-yellow-600 font-medium">Generating…</span>
          </div>
        </div>
        <div className="p-3 space-y-2.5">
          {/* Keyword input */}
          <div className="rounded-lg border border-primary-300 bg-primary-50/60 px-2.5 py-1.5 text-xs text-primary-700 font-medium">
            content marketing strategy for startups
          </div>
          {/* Steps */}
          <div className="flex items-center gap-1.5">
            {[
              { label: "Outline", done: true },
              { label: "Article", active: true },
              { label: "Images", pending: true },
            ].map((step, i) => (
              <div key={step.label} className="flex items-center gap-1.5">
                <div className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                  step.done ? "bg-green-100 text-green-700" :
                  step.active ? "bg-yellow-100 text-yellow-700" :
                  "bg-surface-tertiary text-text-muted"
                }`}>
                  {step.done && <Check className="h-2.5 w-2.5" />}
                  {step.label}
                </div>
                {i < 2 && <div className="h-px w-2 bg-surface-tertiary" />}
              </div>
            ))}
          </div>
          {/* Outline preview */}
          <div className="space-y-1">
            {[
              { text: "Introduction", active: true },
              { text: "What is Content Marketing?", active: false },
              { text: "5 Key Strategies", active: false },
              { text: "Case Studies & Examples", active: false },
            ].map((h) => (
              <div key={h.text} className={`flex items-center gap-1.5 text-xs ${h.active ? "text-text-primary font-medium" : "text-text-muted"}`}>
                <div className={`h-1 w-1 rounded-full flex-shrink-0 ${h.active ? "bg-primary-500" : "bg-surface-tertiary"}`} />
                {h.text}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function SeoAnalyticsMockup() {
  return (
    <div className="aspect-[4/3] rounded-2xl bg-gradient-to-br from-primary-50 via-cream-100 to-terra-400/10 p-4 flex items-center justify-center">
      <div className="w-full bg-white/80 backdrop-blur-sm rounded-xl shadow-soft border border-surface-tertiary overflow-hidden">
        <div className="flex items-center justify-between px-3 py-2.5 bg-surface-secondary border-b border-surface-tertiary">
          <span className="text-xs font-semibold text-text-primary">SEO Analytics</span>
          <div className="flex items-center gap-1 text-xs text-green-600 font-medium">
            <div className="h-1.5 w-1.5 rounded-full bg-green-400" />
            GSC Live
          </div>
        </div>
        <div className="p-3 space-y-2.5">
          {/* Stats */}
          <div className="grid grid-cols-3 gap-1.5">
            {[
              { label: "Impressions", value: "18.4K" },
              { label: "Clicks", value: "1,203" },
              { label: "Avg. Pos.", value: "6.2" },
            ].map((s) => (
              <div key={s.label} className="text-center p-1.5 rounded-lg bg-surface-secondary">
                <div className="text-sm font-bold text-text-primary">{s.value}</div>
                <div className="text-xs text-text-muted leading-tight">{s.label}</div>
              </div>
            ))}
          </div>
          {/* Rankings */}
          <div className="space-y-1.5">
            {[
              { kw: "content marketing strategy", pos: 4, up: true },
              { kw: "seo article generator", pos: 7, up: true },
              { kw: "ai content creation", pos: 12, up: false },
            ].map((r) => (
              <div key={r.kw} className="flex items-center justify-between text-xs">
                <span className="text-text-secondary truncate">{r.kw}</span>
                <div className="flex items-center gap-1.5 flex-shrink-0 ml-2">
                  <span className={`font-semibold ${r.pos <= 5 ? "text-green-600" : r.pos <= 10 ? "text-yellow-600" : "text-text-muted"}`}>#{r.pos}</span>
                  <span className={r.up ? "text-green-500" : "text-text-muted"}>
                    {r.up ? "↑" : "→"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function SocialMediaMockup() {
  return (
    <div className="aspect-[4/3] rounded-2xl bg-gradient-to-br from-primary-50 via-cream-100 to-terra-400/10 p-4 flex items-center justify-center">
      <div className="w-full bg-white/80 backdrop-blur-sm rounded-xl shadow-soft border border-surface-tertiary overflow-hidden">
        <div className="flex items-center justify-between px-3 py-2.5 bg-surface-secondary border-b border-surface-tertiary">
          <span className="text-xs font-semibold text-text-primary">Social Scheduler</span>
          <div className="flex items-center gap-1">
            {[["in", "#0077B5"], ["𝕏", "#000"], ["f", "#1877F2"]].map(([l, c]) => (
              <div key={l} style={{ backgroundColor: c }} className="h-5 w-5 rounded text-white flex items-center justify-center font-bold text-[10px] leading-none">
                {l}
              </div>
            ))}
          </div>
        </div>
        <div className="p-3 space-y-2.5">
          {/* Post preview */}
          <div className="rounded-lg border border-surface-tertiary p-2.5 bg-white">
            <div className="flex items-center gap-2 mb-1.5">
              <div className="h-6 w-6 rounded-full bg-primary-100 flex items-center justify-center text-xs font-bold text-primary-600 flex-shrink-0">A</div>
              <div>
                <div className="text-xs font-semibold text-text-primary leading-none">A-Stats</div>
                <div className="text-xs text-text-muted leading-none mt-0.5">Today · 2:00 PM</div>
              </div>
            </div>
            <p className="text-xs text-text-secondary leading-relaxed">
              Just published: &quot;10 Best SEO Practices for 2026&quot; 🚀 Our AI-generated article hit page 1 in 3 weeks...
            </p>
          </div>
          {/* Platform row */}
          <div className="flex items-center justify-between text-xs">
            <span className="text-text-muted">Posting to 3 platforms</span>
            <span className="text-primary-600 font-medium">View Calendar →</span>
          </div>
          {/* Queue */}
          <div className="flex gap-1.5">
            {["Mon", "Tue", "Wed", "Thu", "Fri"].map((d, i) => (
              <div key={d} className={`flex-1 rounded py-1 text-center text-xs font-medium ${i < 2 ? "bg-primary-100 text-primary-600" : i === 2 ? "bg-primary-500 text-white" : "bg-surface-tertiary text-text-muted"}`}>
                {d}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ───────────────────────── Data ───────────────────────── */

const features = [
  {
    icon: Sparkles,
    title: "AI Article Generation",
    description:
      "Generate full-length, SEO-optimized articles from a single keyword or topic — ready to publish.",
  },
  {
    icon: FileText,
    title: "Smart Outlines",
    description:
      "Create structured content plans with headings, subheadings, and key points before writing.",
  },
  {
    icon: Zap,
    title: "AEO Tracking",
    description:
      "Track when ChatGPT, Perplexity, and Google AI Overviews cite your content. Be the first to know when AI engines discover — or drop — your pages.",
  },
  {
    icon: BarChart3,
    title: "SEO Analytics",
    description:
      "Track rankings with Google Search Console integration and actionable performance insights.",
  },
  {
    icon: Share2,
    title: "Social Media Scheduling",
    description:
      "Create and schedule social posts across platforms — all from one dashboard.",
  },
  {
    icon: BookOpen,
    title: "Knowledge Vault",
    description:
      "Upload brand documents and style guides so the AI writes in your voice, every time.",
  },
];

const steps = [
  {
    number: "1",
    title: "Define your topic",
    description:
      "Enter a keyword, choose your tone and audience, and let the AI understand your goals.",
  },
  {
    number: "2",
    title: "AI generates content",
    description:
      "Get outlines, full articles, and matching images — all optimized for search engines.",
  },
  {
    number: "3",
    title: "Publish & track",
    description:
      "Push to WordPress, schedule social posts, and monitor performance with built-in analytics.",
  },
];

const showcases = [
  {
    title: "Content Generation That Actually Ranks",
    description:
      "Our AI doesn't just write — it researches. Every article is built on keyword analysis, competitor insights, and SEO best practices so you rank from day one.",
    bullets: [
      "Full-length articles from a single keyword",
      "Built-in keyword density and readability scoring",
      "Auto-generated meta titles, descriptions & schema",
    ],
  },
  {
    title: "SEO Analytics You Can Act On",
    description:
      "Connect Google Search Console and get a clear view of what's working. Track impressions, clicks, and rankings — then let AI suggest your next move.",
    bullets: [
      "Google Search Console integration",
      "Keyword ranking & click-through tracking",
      "AI-powered content recommendations",
    ],
  },
  {
    title: "Social Media, Simplified",
    description:
      "Turn every article into a week of social content. Schedule posts across platforms and keep your audience engaged without the extra work.",
    bullets: [
      "Auto-generate social posts from articles",
      "Multi-platform scheduling (LinkedIn, X, Facebook)",
      "Calendar view for planning & coordination",
    ],
  },
];

const testimonials = [
  {
    quote:
      "We went from publishing twice a month to twice a week — and organic traffic grew 340% in 6 months. The AI articles consistently rank on page one within weeks.",
    author: "Sarah K.",
    role: "Content Director, GrowthLab",
    metric: "340% traffic growth",
    initials: "SK",
  },
  {
    quote:
      "The Knowledge Vault feature is a game-changer. The AI finally sounds like our brand instead of generic fluff. Our editorial review time dropped from 3 hours to 20 minutes per article.",
    author: "Marcus T.",
    role: "Founder, Indie SaaS Blog",
    metric: "89% less editing time",
    initials: "MT",
  },
  {
    quote:
      "I replaced three separate tools with this one platform and saved $247/month. Content creation, SEO tracking, and social scheduling — all in one place with better results.",
    author: "Elena R.",
    role: "Freelance Content Strategist",
    metric: "$247/mo saved",
    initials: "ER",
  },
];

const plans = [
  {
    name: "Free",
    monthlyPrice: 0,
    yearlyPrice: 0,
    description: "Try it out, no credit card needed",
    features: [
      "3 articles per month",
      "3 AI images per month",
      "5 social posts per month",
      "3 keyword researches per month",
      "3 AI improvements per article",
      "Basic SEO analysis",
      "Community support",
    ],
    cta: "Get Started Free",
    href: "/register",
  },
  {
    name: "Starter",
    monthlyPrice: 29,
    yearlyPrice: 24,
    description: "For solo creators & bloggers",
    features: [
      "30 articles per month",
      "10 AI images per month",
      "20 social posts per month",
      "30 keyword researches per month",
      "3 AI improvements per article",
      "Advanced SEO analysis",
      "WordPress integration",
      "3 project members",
      "Priority email support",
    ],
    cta: "Start Starter",
    href: "/register",
  },
  {
    name: "Professional",
    monthlyPrice: 79,
    yearlyPrice: 66,
    description: "For growing content teams",
    features: [
      "100 articles per month",
      "50 AI images per month",
      "100 social posts per month",
      "100 keyword researches per month",
      "3 AI improvements per article",
      "Google Search Console integration",
      "Social media scheduling",
      "Knowledge Vault",
      "Bulk content generation",
      "10 project members",
      "Priority support",
    ],
    popular: true,
    cta: "Start Professional",
    href: "/register",
  },
  {
    name: "Enterprise",
    monthlyPrice: 199,
    yearlyPrice: 166,
    description: "For agencies & large teams",
    features: [
      "300 articles per month",
      "200 AI images per month",
      "300 social posts per month",
      "300 keyword researches per month",
      "3 AI improvements per article",
      "Full analytics suite + AEO tracking",
      "White-label agency mode",
      "Client portals & branding",
      "Unlimited project members",
      "API access",
      "Dedicated support & SLA",
    ],
    cta: "Start Enterprise",
    href: "/register",
  },
];

const faqs = [
  {
    q: "Is there a free trial?",
    a: "Yes. Every account starts on the free tier with no credit card required. You can generate articles and explore the platform before upgrading.",
  },
  {
    q: "Can I cancel my subscription anytime?",
    a: "Yes. There are no contracts or cancellation fees. You can downgrade or cancel from your account settings at any time.",
  },
  {
    q: "Who owns the content generated by A-Stats?",
    a: "You do — 100%. All content generated on our platform belongs to you to publish, repurpose, or sell.",
  },
  {
    q: "What is Answer Engine Optimization (AEO)?",
    a: "AEO is the practice of optimizing your content to be cited by AI systems like ChatGPT, Perplexity, and Google AI Overviews. A-Stats tracks your AEO score and alerts you when AI engines start or stop citing your pages.",
  },
  {
    q: "Does A-Stats integrate with WordPress?",
    a: "Yes. Connect your WordPress site in your project settings. Once linked, you can publish articles directly from the A-Stats editor complete with formatting, images, and metadata.",
  },
  {
    q: "What languages are supported?",
    a: "A-Stats supports content generation in English, Spanish, French, German, Romanian, and more languages are being added regularly.",
  },
];

const integrations = [
  { name: "WordPress", abbr: "W", bg: "#21759B" },
  { name: "Google Search Console", abbr: "G", bg: "#4285F4" },
  { name: "LinkedIn", abbr: "in", bg: "#0077B5" },
  { name: "X (Twitter)", abbr: "𝕏", bg: "#000000" },
  { name: "Facebook", abbr: "f", bg: "#1877F2" },
  { name: "Claude AI", abbr: "◆", bg: "#7C3AED" },
];

/* ───────────────────────── Page Component ───────────────────────── */

export default function LandingPageClient() {
  const [yearlyBilling, setYearlyBilling] = useState(false);
  const [blogPosts, setBlogPosts] = useState<BlogPostCard[]>([]);
  const [showStickyCta, setShowStickyCta] = useState(false);
  const heroRef = useRef<HTMLElement>(null);

  useEffect(() => {
    api.blog.list({ page_size: 3 }).then((res) => {
      if (res?.items?.length) setBlogPosts(res.items);
    }).catch(() => {});
  }, []);

  const handleScroll = useCallback(() => {
    if (!heroRef.current) return;
    const heroBottom = heroRef.current.getBoundingClientRect().bottom;
    setShowStickyCta(heroBottom < -100);
  }, []);

  useEffect(() => {
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, [handleScroll]);

  return (
    <div className="min-h-screen bg-surface overflow-x-hidden">
      {/* ─── 1. Navigation ─── */}
      <PublicNav />

      {/* ─── 2. Hero Section ─── */}
      <section ref={heroRef} className="pt-28 pb-20 lg:pt-36 lg:pb-28">
        <div className="page-container">
          <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
            {/* Left — text */}
            <div>
              <div className="hero-animate inline-flex items-center gap-2 rounded-full bg-primary-50 px-4 py-1.5 text-sm text-primary-600 mb-6">
                <Sparkles className="h-4 w-4" />
                <span>AI-Powered Content & SEO Platform</span>
              </div>
              <h1 className="hero-animate-delay-1 text-4xl md:text-5xl lg:text-6xl font-display font-bold text-text-primary leading-[1.1] tracking-tight">
                Rank on Google.{" "}
                <span className="gradient-text">Get Cited by AI.</span>
              </h1>
              <p className="hero-animate-delay-2 mt-6 text-lg text-text-secondary max-w-lg leading-relaxed">
                From keyword to published article — AI-generated content that
                ranks on Google <em>and</em> gets cited by ChatGPT, Perplexity,
                and Google AI Overviews. All from one platform.
              </p>
              <div className="hero-animate-delay-3 mt-8 flex flex-col sm:flex-row gap-4">
                <Link
                  href="/register"
                  className="btn-primary text-base px-8 py-3"
                >
                  Get Started Free
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
                <Link
                  href="#how-it-works"
                  className="btn-secondary text-base px-8 py-3"
                >
                  See How It Works
                </Link>
              </div>
              {/* Social proof */}
              <div className="hero-animate-delay-3 mt-8 flex flex-wrap gap-x-8 gap-y-3 text-sm">
                <span className="flex items-center gap-2 text-text-primary font-semibold">
                  <span className="text-primary-500 text-lg">2,000+</span> content teams
                </span>
                <span className="flex items-center gap-2 text-text-primary font-semibold">
                  <span className="text-primary-500 text-lg">500K+</span> articles generated
                </span>
                <span className="flex items-center gap-2 text-text-primary font-semibold">
                  <span className="text-primary-500 text-lg">4.8/5</span> avg. rating
                </span>
              </div>

              {/* Powered by */}
              <p className="hero-animate-delay-3 mt-4 text-xs text-text-muted">
                Powered by <span className="font-medium text-text-secondary">Claude</span>, <span className="font-medium text-text-secondary">GPT-4o</span> & <span className="font-medium text-text-secondary">Gemini</span> — each model used where it performs best.
              </p>

              {/* Trust indicators */}
              <div className="hero-animate-delay-3 mt-6 flex flex-wrap gap-6 text-sm text-text-muted">
                <span className="flex items-center gap-1.5">
                  <CreditCard className="h-4 w-4 text-primary-400" />
                  No credit card required
                </span>
                <span className="flex items-center gap-1.5">
                  <Clock className="h-4 w-4 text-terra-400" />
                  Setup in under 5 minutes
                </span>
                <span className="flex items-center gap-1.5">
                  <ShieldCheck className="h-4 w-4 text-earth-400" />
                  Cancel anytime
                </span>
              </div>
            </div>

            {/* Right — product mockup */}
            <div className="hero-animate-delay-2 relative mx-auto max-w-sm lg:max-w-none">
              <HeroMockup />
            </div>
          </div>
        </div>
      </section>

      {/* ─── 3. Integrations Bar ─── */}
      <section className="py-10 bg-white border-y border-surface-tertiary/50">
        <div className="page-container">
          <p className="text-center text-xs font-semibold text-text-muted uppercase tracking-widest mb-7">
            Works with the tools you already use
          </p>
          <div className="flex flex-wrap items-center justify-center gap-6 lg:gap-10">
            {integrations.map(({ name, abbr, bg }) => (
              <div key={name} className="flex items-center gap-2.5 text-text-secondary">
                <div
                  className="h-7 w-7 rounded-md flex items-center justify-center text-white text-xs font-bold flex-shrink-0"
                  style={{ backgroundColor: bg }}
                >
                  {abbr}
                </div>
                <span className="text-sm font-medium">{name}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── 4. Features Grid ─── */}
      <section id="features" className="py-20 lg:py-28 bg-white">
        <div className="page-container">
          <RevealSection className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-display font-bold text-text-primary">
              Everything You Need for{" "}
              <span className="gradient-text">Content Success</span>
            </h2>
            <p className="mt-4 text-text-secondary max-w-2xl mx-auto">
              One platform to research, write, optimize, publish, and track —
              powered by AI that understands SEO.
            </p>
          </RevealSection>

          <RevealSection>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              {features.map((feature) => (
                <div
                  key={feature.title}
                  className="stagger-child card p-6 hover:shadow-soft-lg hover:-translate-y-1 transition-all duration-300"
                >
                  <div className="h-12 w-12 rounded-xl bg-primary-50 flex items-center justify-center mb-4">
                    <feature.icon className="h-6 w-6 text-primary-500" />
                  </div>
                  <h3 className="font-display text-lg font-semibold text-text-primary mb-2">
                    {feature.title}
                  </h3>
                  <p className="text-sm text-text-secondary leading-relaxed">
                    {feature.description}
                  </p>
                </div>
              ))}
            </div>
          </RevealSection>
        </div>
      </section>

      {/* ─── 5. How It Works ─── */}
      <section
        id="how-it-works"
        className="py-20 lg:py-28 bg-surface-secondary"
      >
        <div className="page-container">
          <RevealSection className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-display font-bold text-text-primary">
              How It Works
            </h2>
            <p className="mt-4 text-text-secondary max-w-2xl mx-auto">
              Three simple steps from idea to published, ranking content.
            </p>
          </RevealSection>

          <RevealSection>
            <div className="grid md:grid-cols-3 gap-8 lg:gap-12 relative">
              {/* Connecting line (desktop) */}
              <div className="hidden md:block absolute top-10 left-[20%] right-[20%] h-px bg-surface-tertiary" />

              {steps.map((step) => (
                <div key={step.number} className="stagger-child text-center relative">
                  <div className="inline-flex items-center justify-center h-14 w-14 rounded-full bg-primary-500 text-white text-xl font-display font-bold mb-5 relative z-10">
                    {step.number}
                  </div>
                  <h3 className="font-display text-lg font-semibold text-text-primary mb-2">
                    {step.title}
                  </h3>
                  <p className="text-sm text-text-secondary leading-relaxed max-w-xs mx-auto">
                    {step.description}
                  </p>
                </div>
              ))}
            </div>
          </RevealSection>
        </div>
      </section>

      {/* ─── 6. Feature Showcase (alternating rows) ─── */}
      <section className="py-20 lg:py-28 bg-white">
        <div className="page-container space-y-24">
          {showcases.map((item, i) => {
            const Visual = i === 0 ? ContentGenMockup : i === 1 ? SeoAnalyticsMockup : SocialMediaMockup;
            return (
              <div
                key={item.title}
                className={`grid lg:grid-cols-2 gap-12 lg:gap-16 items-center ${
                  i % 2 === 1 ? "lg:[direction:rtl]" : ""
                }`}
              >
                {/* Text */}
                <RevealSection
                  direction={i % 2 === 0 ? "left" : "right"}
                  className={i % 2 === 1 ? "lg:[direction:ltr]" : ""}
                >
                  <h3 className="text-2xl md:text-3xl font-display font-bold text-text-primary mb-4">
                    {item.title}
                  </h3>
                  <p className="text-text-secondary leading-relaxed mb-6">
                    {item.description}
                  </p>
                  <ul className="space-y-3">
                    {item.bullets.map((b) => (
                      <li
                        key={b}
                        className="flex items-start gap-3 text-sm text-text-secondary"
                      >
                        <ChevronRight className="h-4 w-4 text-primary-500 mt-0.5 flex-shrink-0" />
                        {b}
                      </li>
                    ))}
                  </ul>
                </RevealSection>

                {/* Feature mockup */}
                <RevealSection
                  direction={i % 2 === 0 ? "right" : "left"}
                  className={i % 2 === 1 ? "lg:[direction:ltr]" : ""}
                >
                  <Visual />
                </RevealSection>
              </div>
            );
          })}
        </div>
      </section>

      {/* ─── 6b. AEO Section ─── */}
      <section className="py-20 lg:py-28 bg-primary-950">
        <div className="page-container">
          <RevealSection className="text-center mb-16">
            <div className="inline-flex items-center gap-2 rounded-full bg-primary-800/60 px-4 py-1.5 text-sm text-primary-300 mb-6 border border-primary-700/50">
              <Zap className="h-4 w-4" />
              <span>NEW — Answer Engine Optimization</span>
            </div>
            <h2 className="text-3xl md:text-4xl font-display font-bold text-cream-100">
              Get Found by AI, Not Just Google
            </h2>
            <p className="mt-4 text-primary-200/70 max-w-2xl mx-auto leading-relaxed">
              The next wave of search happens inside ChatGPT, Perplexity, and
              Google AI Overviews. A-Stats tracks your AEO score so you know
              exactly when — and how — AI engines cite your content.
            </p>
          </RevealSection>

          <RevealSection>
            <div className="grid md:grid-cols-3 gap-6 mb-12">
              <div className="stagger-child rounded-2xl bg-primary-900 border border-primary-800/60 p-6">
                <div className="h-12 w-12 rounded-xl bg-primary-800 flex items-center justify-center mb-4">
                  <Zap className="h-6 w-6 text-primary-300" />
                </div>
                <h3 className="font-display text-lg font-semibold text-cream-100 mb-2">
                  AEO Score Tracking
                </h3>
                <p className="text-sm text-primary-200/70 leading-relaxed">
                  See how AI answer engines perceive each of your pages with a
                  0–100 AEO score updated regularly.
                </p>
              </div>

              <div className="stagger-child rounded-2xl bg-primary-900 border border-primary-800/60 p-6">
                <div className="h-12 w-12 rounded-xl bg-primary-800 flex items-center justify-center mb-4">
                  <Bell className="h-6 w-6 text-primary-300" />
                </div>
                <h3 className="font-display text-lg font-semibold text-cream-100 mb-2">
                  Citation Alerts
                </h3>
                <p className="text-sm text-primary-200/70 leading-relaxed">
                  Get notified when AI systems start or stop citing your content
                  so you can act before rankings drop.
                </p>
              </div>

              <div className="stagger-child rounded-2xl bg-primary-900 border border-primary-800/60 p-6">
                <div className="h-12 w-12 rounded-xl bg-primary-800 flex items-center justify-center mb-4">
                  <TrendingUp className="h-6 w-6 text-primary-300" />
                </div>
                <h3 className="font-display text-lg font-semibold text-cream-100 mb-2">
                  Answer-Ready Structure
                </h3>
                <p className="text-sm text-primary-200/70 leading-relaxed">
                  Get AI recommendations on how to restructure your content to
                  win featured AI answers.
                </p>
              </div>
            </div>

            {/* AEO Score mockup card */}
            <div className="max-w-sm mx-auto rounded-2xl bg-primary-900 border border-primary-800/60 p-8 text-center">
              <p className="text-sm font-medium text-primary-300 mb-4 uppercase tracking-widest">
                AEO Score
              </p>
              <div className="text-7xl font-display font-bold text-primary-400 mb-2">
                82
              </div>
              <p className="text-sm text-primary-300 mb-6">
                <span className="text-primary-400 font-medium">+12</span> this
                month
              </p>
              <div className="w-full h-2 rounded-full bg-primary-800 overflow-hidden">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-primary-500 to-primary-400"
                  style={{ width: "82%" }}
                />
              </div>
            </div>
          </RevealSection>
        </div>
      </section>

      {/* ─── 6c. Who It's For ─── */}
      <section className="py-20 lg:py-28 bg-surface-secondary">
        <div className="page-container">
          <RevealSection className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-display font-bold text-text-primary">
              Built for <span className="gradient-text">Every Content Team</span>
            </h2>
            <p className="mt-4 text-text-secondary max-w-2xl mx-auto">
              Whether you&apos;re a solo blogger or a 50-person agency, A-Stats scales with you.
            </p>
          </RevealSection>

          <RevealSection>
            <div className="grid md:grid-cols-3 gap-6">
              {[
                {
                  title: "Solo Creators & Bloggers",
                  description: "Write and publish SEO-optimized articles faster than ever. No team needed — the AI handles research, writing, and optimization.",
                  features: ["Full article generation", "WordPress publishing", "Basic SEO analysis"],
                  plan: "Free / Starter",
                },
                {
                  title: "Growing Content Teams",
                  description: "Collaborate on content strategy, track rankings, and keep your editorial calendar full with AI-assisted workflows.",
                  features: ["Team collaboration", "Google Search Console", "Social scheduling"],
                  plan: "Professional",
                },
                {
                  title: "Agencies & Enterprises",
                  description: "Manage multiple clients with white-label portals, bulk generation, API access, and dedicated support.",
                  features: ["White-label mode", "Bulk generation", "Client portals & API"],
                  plan: "Enterprise",
                },
              ].map((segment) => (
                <div key={segment.title} className="stagger-child card p-6">
                  <h3 className="font-display text-lg font-semibold text-text-primary mb-2">
                    {segment.title}
                  </h3>
                  <p className="text-sm text-text-secondary leading-relaxed mb-4">
                    {segment.description}
                  </p>
                  <ul className="space-y-2 mb-4">
                    {segment.features.map((f) => (
                      <li key={f} className="flex items-center gap-2 text-sm text-text-secondary">
                        <Check className="h-3.5 w-3.5 text-primary-500 flex-shrink-0" />
                        {f}
                      </li>
                    ))}
                  </ul>
                  <p className="text-xs font-medium text-primary-600">
                    Recommended: {segment.plan}
                  </p>
                </div>
              ))}
            </div>
          </RevealSection>
        </div>
      </section>

      {/* ─── 7. Testimonials ─── */}
      <section className="py-20 lg:py-28 bg-white">
        <div className="page-container">
          <RevealSection className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-display font-bold text-text-primary">
              Loved by Content Creators
            </h2>
            <p className="mt-4 text-text-secondary max-w-2xl mx-auto">
              See what our users have to say about the platform.
            </p>
          </RevealSection>

          <RevealSection>
            <div className="grid md:grid-cols-3 gap-6">
              {testimonials.map((t) => (
                <div
                  key={t.author}
                  className="stagger-child card p-6 flex flex-col"
                >
                  {t.metric && (
                    <div className="inline-flex self-start items-center gap-1.5 text-xs font-semibold text-primary-600 bg-primary-50 px-2.5 py-1 rounded-full mb-3">
                      <TrendingUp className="h-3 w-3" />
                      {t.metric}
                    </div>
                  )}
                  <p className="text-text-secondary text-sm leading-relaxed flex-1 italic">
                    &ldquo;{t.quote}&rdquo;
                  </p>
                  <div className="mt-6 flex items-center gap-3">
                    <div className="h-10 w-10 rounded-full bg-primary-100 flex items-center justify-center text-sm font-semibold text-primary-600">
                      {t.initials}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-text-primary">
                        {t.author}
                      </p>
                      <p className="text-xs text-text-muted">{t.role}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </RevealSection>
        </div>
      </section>

      {/* ─── 8. Pricing ─── */}
      <section id="pricing" className="py-20 lg:py-28 bg-healing-cream">
        <div className="page-container">
          <RevealSection className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-display font-bold text-text-primary">
              Simple, Transparent Pricing
            </h2>
            <p className="mt-4 text-text-secondary max-w-2xl mx-auto">
              Choose the plan that fits your content needs. Upgrade or downgrade
              anytime.
            </p>

            {/* Billing toggle */}
            <div className="mt-8 inline-flex items-center gap-3 bg-white rounded-full p-1 shadow-sm">
              <button
                className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
                  !yearlyBilling
                    ? "bg-primary-500 text-white"
                    : "text-text-secondary hover:text-text-primary"
                }`}
                onClick={() => setYearlyBilling(false)}
              >
                Monthly
              </button>
              <button
                className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
                  yearlyBilling
                    ? "bg-primary-500 text-white"
                    : "text-text-secondary hover:text-text-primary"
                }`}
                onClick={() => setYearlyBilling(true)}
              >
                Yearly
                <span className="ml-1.5 text-xs opacity-80">Save 17%</span>
              </button>
            </div>
          </RevealSection>

          {/* Trust badges */}
          <div className="flex flex-wrap items-center justify-center gap-6 text-xs text-text-muted mb-10">
            <span className="flex items-center gap-1.5">
              <ShieldCheck className="h-4 w-4 text-green-500" />
              SSL Secured Checkout
            </span>
            <span className="flex items-center gap-1.5">
              <CreditCard className="h-4 w-4 text-text-muted" />
              Cancel anytime — no contracts
            </span>
            <span className="flex items-center gap-1.5">
              <Clock className="h-4 w-4 text-text-muted" />
              14-day money-back guarantee
            </span>
          </div>

          <RevealSection>
            <div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-6 max-w-7xl mx-auto">
              {plans.map((plan) => (
                <div
                  key={plan.name}
                  className={`stagger-child card p-8 relative flex flex-col ${
                    plan.popular
                      ? "border-2 border-primary-500 shadow-soft-lg"
                      : "border-surface-tertiary"
                  }`}
                >
                  {plan.popular && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-gradient-to-r from-primary-500 to-terra-500 text-white text-xs font-medium px-4 py-1 rounded-full">
                      Most Popular
                    </div>
                  )}
                  <div className="text-center mb-6">
                    <h3 className="font-display text-xl font-semibold text-text-primary">
                      {plan.name}
                    </h3>
                    <p className="text-sm text-text-secondary mt-1">
                      {plan.description}
                    </p>
                    <div className="mt-4">
                      {plan.monthlyPrice === 0 ? (
                        <span className="text-4xl font-display font-bold text-text-primary">Free</span>
                      ) : (
                        <>
                          {yearlyBilling && (
                            <span className="text-lg text-text-muted line-through mr-1.5">
                              ${plan.monthlyPrice}
                            </span>
                          )}
                          <span className="text-4xl font-display font-bold text-text-primary">
                            ${yearlyBilling ? plan.yearlyPrice : plan.monthlyPrice}
                          </span>
                          <span className="text-text-muted">/month</span>
                        </>
                      )}
                    </div>
                    {yearlyBilling && plan.monthlyPrice > 0 && (
                      <p className="text-xs text-primary-600 mt-1">
                        Billed annually &middot; Save ${(plan.monthlyPrice - plan.yearlyPrice) * 12}/yr
                      </p>
                    )}
                  </div>
                  <ul className="space-y-3 mb-8 flex-1">
                    {plan.features.map((feature) => (
                      <li
                        key={feature}
                        className="flex items-center gap-3 text-sm"
                      >
                        <Check className="h-4 w-4 text-primary-500 flex-shrink-0" />
                        <span className="text-text-secondary">{feature}</span>
                      </li>
                    ))}
                  </ul>
                  <Link
                    href={plan.href}
                    className={`w-full text-center ${
                      plan.popular ? "btn-primary" : "btn-secondary"
                    }`}
                  >
                    {plan.cta}
                  </Link>
                </div>
              ))}
            </div>
          </RevealSection>
        </div>
      </section>

      {/* ─── 8b. From Our Blog ─── */}
      {blogPosts.length > 0 && (
        <section className="py-20 lg:py-28 bg-surface-secondary">
          <div className="page-container">
            <RevealSection className="text-center mb-12">
              <h2 className="text-3xl md:text-4xl font-display font-bold text-text-primary">
                From Our <span className="gradient-text">Blog</span>
              </h2>
              <p className="mt-4 text-text-secondary max-w-2xl mx-auto">
                SEO tips, content strategy, and product updates from the A-Stats team.
              </p>
            </RevealSection>

            <RevealSection>
              <div className="grid md:grid-cols-3 gap-6">
                {blogPosts.map((post) => (
                  <article
                    key={post.id}
                    className="stagger-child card overflow-hidden group flex flex-col hover:shadow-soft-lg hover:-translate-y-1 transition-all duration-300"
                  >
                    <Link
                      href={`/blog/${post.slug}`}
                      className="block relative overflow-hidden bg-surface-secondary flex-shrink-0"
                      style={{ paddingBottom: "56.25%", height: 0 }}
                    >
                      {post.featured_image_url ? (
                        <Image
                          src={post.featured_image_url}
                          alt={post.featured_image_alt || post.title}
                          fill
                          className="object-cover group-hover:scale-105 transition-transform duration-300"
                          sizes="(max-width: 768px) 100vw, 33vw"
                        />
                      ) : (
                        <div className="absolute inset-0 bg-gradient-to-br from-primary-50 to-primary-100 flex items-center justify-center">
                          <span className="text-primary-300 text-4xl font-bold">A</span>
                        </div>
                      )}
                      {post.category && (
                        <span className="absolute top-3 left-3 px-2.5 py-1 bg-primary-600 text-white text-xs font-semibold rounded-full">
                          {post.category.name}
                        </span>
                      )}
                    </Link>
                    <div className="p-5 flex flex-col flex-1">
                      <Link href={`/blog/${post.slug}`} className="flex-1">
                        <h3 className="text-base font-bold text-text-primary leading-snug mb-2 group-hover:text-primary-600 transition-colors line-clamp-2">
                          {post.title}
                        </h3>
                      </Link>
                      {(post.excerpt || post.meta_description) && (
                        <p className="text-sm text-text-secondary leading-relaxed mb-3 line-clamp-2">
                          {post.excerpt || post.meta_description}
                        </p>
                      )}
                      <div className="flex items-center gap-3 text-xs text-text-muted mt-auto pt-3 border-t border-surface-tertiary">
                        {post.published_at && (
                          <span className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            {new Date(post.published_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                          </span>
                        )}
                        {post.reading_time_minutes && (
                          <>
                            <span className="text-surface-tertiary">&middot;</span>
                            <span className="flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              {post.reading_time_minutes}m read
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                  </article>
                ))}
              </div>

              <div className="text-center mt-10">
                <Link
                  href="/blog"
                  className="btn-secondary inline-flex items-center gap-2 text-sm"
                >
                  View All Posts
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </div>
            </RevealSection>
          </div>
        </section>
      )}

      {/* ─── 9. FAQ ─── */}
      <section className="py-20 lg:py-28 bg-white">
        <div className="page-container max-w-3xl">
          <RevealSection className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-display font-bold text-text-primary">
              Frequently Asked Questions
            </h2>
          </RevealSection>

          <RevealSection>
            <div className="space-y-3">
              {faqs.map((faq) => (
                <details
                  key={faq.q}
                  className="faq-item card overflow-hidden group"
                >
                  <summary className="flex items-center justify-between px-6 py-4 cursor-pointer">
                    <span className="font-medium text-text-primary text-sm pr-4">
                      {faq.q}
                    </span>
                    <Plus className="faq-icon h-4 w-4 text-text-muted flex-shrink-0" />
                  </summary>
                  <div className="faq-answer px-6 pb-4">
                    <p className="text-sm text-text-secondary leading-relaxed">
                      {faq.a}
                    </p>
                  </div>
                </details>
              ))}
            </div>
          </RevealSection>
        </div>
      </section>

      {/* ─── 10. Final CTA ─── */}
      <section className="py-20 lg:py-28 bg-gradient-to-br from-primary-500 via-primary-600 to-terra-600">
        <div className="page-container text-center">
          <RevealSection>
            <h2 className="text-3xl md:text-4xl font-display font-bold text-white">
              Ready to Create Content That Ranks?
            </h2>
            <p className="mt-4 text-primary-100 max-w-2xl mx-auto">
              Join 2,000+ creators using AI to write better content, grow
              organic traffic, and save hours every week. Start free — no credit card required.
            </p>
            <Link
              href="/register"
              className="mt-8 inline-flex btn bg-white text-primary-600 hover:bg-primary-50 text-base px-8 py-3 shadow-soft"
            >
              Get Started Free
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
            <p className="mt-4 text-xs text-primary-200/70">
              Free tier includes 3 articles, 3 images & 5 social posts per month
            </p>
          </RevealSection>
        </div>
      </section>

      {/* ─── 11. Footer ─── */}
      <PublicFooter />

      {/* ─── Sticky CTA Bar ─── */}
      <div
        className={`fixed bottom-0 left-0 right-0 z-40 bg-white/90 backdrop-blur-lg border-t border-surface-tertiary shadow-[0_-4px_20px_rgba(0,0,0,0.08)] transition-transform duration-300 ${
          showStickyCta ? "translate-y-0" : "translate-y-full"
        }`}
      >
        <div className="page-container flex items-center justify-between py-3">
          <p className="hidden sm:block text-sm text-text-secondary">
            <span className="font-semibold text-text-primary">Start free</span> — no credit card required
          </p>
          <div className="flex items-center gap-3 w-full sm:w-auto">
            <Link
              href="/register"
              className="btn-primary text-sm px-6 py-2.5 w-full sm:w-auto text-center"
            >
              Get Started Free
              <ArrowRight className="ml-2 h-4 w-4 inline" />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
