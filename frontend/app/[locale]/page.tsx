"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import {
  Sparkles,
  FileText,
  Image as ImageIcon,
  BarChart3,
  ArrowRight,
  Check,
  Share2,
  BookOpen,
  Menu,
  X,
  Plus,
  ChevronRight,
} from "lucide-react";

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
    icon: ImageIcon,
    title: "AI Image Creation",
    description:
      "Generate on-brand visuals and featured images that match your content and style.",
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
      "We went from publishing twice a month to twice a week. The AI-generated articles consistently rank on page one within weeks.",
    author: "Sarah K.",
    role: "Content Director, GrowthLab",
    initials: "SK",
  },
  {
    quote:
      "The Knowledge Vault feature is a game-changer. The AI finally sounds like our brand instead of generic fluff.",
    author: "Marcus T.",
    role: "Founder, Indie SaaS Blog",
    initials: "MT",
  },
  {
    quote:
      "I replaced three separate tools with this one platform. Content creation, SEO tracking, and social scheduling — all in one place.",
    author: "Elena R.",
    role: "Freelance Content Strategist",
    initials: "ER",
  },
];

const plans = [
  {
    name: "Starter",
    monthlyPrice: 29,
    yearlyPrice: 24,
    description: "For creators getting started",
    features: [
      "10 articles per month",
      "Basic SEO optimization",
      "5 AI images",
      "Email support",
    ],
  },
  {
    name: "Professional",
    monthlyPrice: 79,
    yearlyPrice: 66,
    description: "For growing content teams",
    features: [
      "50 articles per month",
      "Advanced SEO tools",
      "25 AI images",
      "WordPress integration",
      "Social media scheduling",
      "Priority support",
    ],
    popular: true,
  },
  {
    name: "Enterprise",
    monthlyPrice: 199,
    yearlyPrice: 166,
    description: "For agencies & large teams",
    features: [
      "Unlimited articles",
      "Full SEO suite",
      "Unlimited AI images",
      "Custom integrations",
      "Knowledge Vault",
      "Dedicated support",
      "API access",
    ],
  },
];

const faqs = [
  {
    q: "Is there a free trial?",
    a: "Yes! Every account starts with a free tier — no credit card required. You can generate up to 10 articles to try the platform before upgrading.",
  },
  {
    q: "Can I cancel anytime?",
    a: "Absolutely. There are no contracts or cancellation fees. You can downgrade or cancel your subscription at any time from your account settings.",
  },
  {
    q: "Who owns the generated content?",
    a: "You do — 100%. All content generated on our platform is yours to use, publish, and repurpose however you like.",
  },
  {
    q: "Do you offer API access?",
    a: "Yes, API access is available on the Enterprise plan. You can integrate our content generation and SEO tools directly into your existing workflows.",
  },
  {
    q: "How does the WordPress integration work?",
    a: "Connect your WordPress site in one click. Once linked, you can push articles directly from our editor to your blog — complete with formatting, images, and meta data.",
  },
  {
    q: "What languages are supported?",
    a: "We currently support content generation in English, Spanish, French, German, Portuguese, and Dutch — with more languages coming soon.",
  },
];

/* ───────────────────────── Page Component ───────────────────────── */

export default function HomePage() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [yearlyBilling, setYearlyBilling] = useState(false);

  return (
    <div className="min-h-screen bg-surface overflow-x-hidden">
      {/* ─── 1. Navigation ─── */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-white/70 backdrop-blur-xl border-b border-surface-tertiary/60">
        <div className="page-container">
          <div className="flex h-16 items-center justify-between">
            {/* Logo */}
            <Link href="/" className="flex items-center gap-2.5">
              <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-primary-400 to-primary-600 shadow-sm" />
              <span className="font-display text-xl font-semibold text-text-primary">
                A-Stats
              </span>
            </Link>

            {/* Desktop links */}
            <div className="hidden md:flex items-center gap-8">
              {[
                { label: "Features", href: "#features" },
                { label: "How It Works", href: "#how-it-works" },
                { label: "Pricing", href: "#pricing" },
                { label: "Blog", href: "#" },
              ].map((link) => (
                <Link
                  key={link.label}
                  href={link.href}
                  className="text-sm text-text-secondary hover:text-text-primary transition-colors"
                >
                  {link.label}
                </Link>
              ))}
            </div>

            {/* Desktop CTA */}
            <div className="hidden md:flex items-center gap-4">
              <Link
                href="/login"
                className="text-sm text-text-secondary hover:text-text-primary transition-colors"
              >
                Sign In
              </Link>
              <Link href="/register" className="btn-primary text-sm">
                Get Started Free
              </Link>
            </div>

            {/* Mobile menu button */}
            <button
              className="md:hidden p-2 text-text-secondary hover:text-text-primary"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-label="Toggle menu"
            >
              {mobileMenuOpen ? (
                <X className="h-5 w-5" />
              ) : (
                <Menu className="h-5 w-5" />
              )}
            </button>
          </div>
        </div>

        {/* Mobile drawer */}
        {mobileMenuOpen && (
          <div className="md:hidden bg-white/95 backdrop-blur-xl border-b border-surface-tertiary animate-in">
            <div className="page-container py-4 flex flex-col gap-3">
              {[
                { label: "Features", href: "#features" },
                { label: "How It Works", href: "#how-it-works" },
                { label: "Pricing", href: "#pricing" },
                { label: "Blog", href: "#" },
              ].map((link) => (
                <Link
                  key={link.label}
                  href={link.href}
                  className="text-sm text-text-secondary hover:text-text-primary py-2"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  {link.label}
                </Link>
              ))}
              <hr className="border-surface-tertiary" />
              <Link
                href="/login"
                className="text-sm text-text-secondary py-2"
                onClick={() => setMobileMenuOpen(false)}
              >
                Sign In
              </Link>
              <Link
                href="/register"
                className="btn-primary text-sm text-center"
                onClick={() => setMobileMenuOpen(false)}
              >
                Get Started Free
              </Link>
            </div>
          </div>
        )}
      </nav>

      {/* ─── 2. Hero Section ─── */}
      <section className="pt-28 pb-20 lg:pt-36 lg:pb-28">
        <div className="page-container">
          <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
            {/* Left — text */}
            <div>
              <div className="hero-animate inline-flex items-center gap-2 rounded-full bg-primary-50 px-4 py-1.5 text-sm text-primary-600 mb-6">
                <Sparkles className="h-4 w-4" />
                <span>AI-Powered Content & SEO Platform</span>
              </div>
              <h1 className="hero-animate-delay-1 text-4xl md:text-5xl lg:text-6xl font-display font-bold text-text-primary leading-[1.1] tracking-tight">
                Create Content That{" "}
                <span className="gradient-text">Ranks</span>
              </h1>
              <p className="hero-animate-delay-2 mt-6 text-lg text-text-secondary max-w-lg leading-relaxed">
                From keyword to published article — generate SEO-optimized
                content, images, and social posts with AI. Then track
                performance, all in one platform.
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
              {/* Trust indicators */}
              <div className="hero-animate-delay-3 mt-10 flex flex-wrap gap-6 text-sm text-text-muted">
                <span className="flex items-center gap-1.5">
                  <span className="inline-block h-2 w-2 rounded-full bg-primary-400" />
                  1,000+ articles generated
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="inline-block h-2 w-2 rounded-full bg-terra-400" />
                  50+ happy creators
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="inline-block h-2 w-2 rounded-full bg-earth-400" />
                  No credit card required
                </span>
              </div>
            </div>

            {/* Right — decorative visual */}
            <div className="hero-animate-delay-2 relative hidden lg:block">
              <div className="relative aspect-[4/3] rounded-2xl overflow-hidden">
                {/* Background gradient card */}
                <div className="absolute inset-0 bg-gradient-to-br from-primary-100 via-cream-100 to-terra-400/20 rounded-2xl" />
                {/* Floating elements */}
                <div className="absolute top-8 left-8 right-8 bg-white/80 backdrop-blur-sm rounded-xl p-5 shadow-soft">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="h-3 w-3 rounded-full bg-primary-400" />
                    <div className="h-2 w-24 rounded-full bg-surface-tertiary" />
                  </div>
                  <div className="space-y-2">
                    <div className="h-2 w-full rounded-full bg-surface-tertiary" />
                    <div className="h-2 w-5/6 rounded-full bg-surface-tertiary" />
                    <div className="h-2 w-4/6 rounded-full bg-surface-tertiary" />
                  </div>
                </div>
                <div className="absolute bottom-8 right-8 bg-white/80 backdrop-blur-sm rounded-xl p-4 shadow-soft">
                  <div className="flex items-center gap-2 text-sm text-primary-600 font-medium">
                    <BarChart3 className="h-4 w-4" />
                    <span>SEO Score: 94</span>
                  </div>
                  <div className="mt-2 h-2 w-32 rounded-full bg-surface-tertiary overflow-hidden">
                    <div className="h-full w-[94%] rounded-full bg-gradient-to-r from-primary-400 to-primary-500" />
                  </div>
                </div>
                <div className="absolute bottom-8 left-8 bg-white/80 backdrop-blur-sm rounded-lg p-3 shadow-soft">
                  <div className="flex items-center gap-2 text-xs text-terra-600 font-medium">
                    <Sparkles className="h-3.5 w-3.5" />
                    AI Writing...
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ─── 3. Social Proof / Logo Bar ─── */}
      <section className="py-12 bg-surface-secondary border-y border-surface-tertiary/50">
        <div className="page-container">
          <p className="text-center text-sm text-text-muted mb-8">
            Trusted by content creators worldwide
          </p>
          <div className="flex flex-wrap items-center justify-center gap-x-12 gap-y-4">
            {[
              "ContentFlow",
              "BlogScale",
              "RankWise",
              "SEO Studio",
              "WriterHQ",
              "GrowthLab",
            ].map((name) => (
              <span
                key={name}
                className="text-lg font-display font-semibold text-text-muted/40 select-none"
              >
                {name}
              </span>
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
          {showcases.map((item, i) => (
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

              {/* Decorative visual */}
              <RevealSection
                direction={i % 2 === 0 ? "right" : "left"}
                className={i % 2 === 1 ? "lg:[direction:ltr]" : ""}
              >
                <div className="aspect-[4/3] rounded-2xl bg-gradient-to-br from-primary-50 via-cream-100 to-terra-400/10 flex items-center justify-center">
                  <div className="w-3/4 bg-white/60 backdrop-blur-sm rounded-xl p-6 shadow-soft">
                    <div className="flex items-center gap-2 mb-4">
                      <div className="h-3 w-3 rounded-full bg-primary-400" />
                      <div className="h-2 w-20 rounded-full bg-surface-tertiary" />
                    </div>
                    <div className="space-y-2">
                      <div className="h-2 w-full rounded-full bg-surface-tertiary" />
                      <div className="h-2 w-5/6 rounded-full bg-surface-tertiary" />
                      <div className="h-2 w-3/5 rounded-full bg-surface-tertiary" />
                    </div>
                  </div>
                </div>
              </RevealSection>
            </div>
          ))}
        </div>
      </section>

      {/* ─── 7. Testimonials ─── */}
      <section className="py-20 lg:py-28 bg-surface-secondary">
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

          <p className="text-center text-xs text-text-muted mt-8">
            * Placeholder testimonials for illustration purposes.
          </p>
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

          <RevealSection>
            <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
              {plans.map((plan) => (
                <div
                  key={plan.name}
                  className={`stagger-child card p-8 relative flex flex-col ${
                    plan.popular
                      ? "border-2 border-primary-500 shadow-soft-lg scale-[1.03]"
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
                      <span className="text-4xl font-display font-bold text-text-primary">
                        ${yearlyBilling ? plan.yearlyPrice : plan.monthlyPrice}
                      </span>
                      <span className="text-text-muted">/month</span>
                    </div>
                    {yearlyBilling && (
                      <p className="text-xs text-primary-600 mt-1">
                        Billed annually
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
                    href="/register"
                    className={`w-full text-center ${
                      plan.popular ? "btn-primary" : "btn-secondary"
                    }`}
                  >
                    Get Started
                  </Link>
                </div>
              ))}
            </div>
          </RevealSection>
        </div>
      </section>

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
              Join thousands of creators using AI to write better content, grow
              organic traffic, and save hours every week.
            </p>
            <Link
              href="/register"
              className="mt-8 inline-flex btn bg-white text-primary-600 hover:bg-primary-50 text-base px-8 py-3 shadow-soft"
            >
              Get Started Free
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </RevealSection>
        </div>
      </section>

      {/* ─── 11. Footer ─── */}
      <footer className="py-16 bg-primary-950 text-white">
        <div className="page-container">
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-10 mb-12">
            {/* Brand */}
            <div>
              <div className="flex items-center gap-2.5 mb-4">
                <div className="h-7 w-7 rounded-md bg-gradient-to-br from-primary-400 to-primary-600" />
                <span className="font-display text-lg font-semibold">
                  A-Stats
                </span>
              </div>
              <p className="text-sm text-primary-200/60 leading-relaxed">
                AI-powered content creation and SEO platform for modern
                creators.
              </p>
            </div>

            {/* Product */}
            <div>
              <h4 className="text-sm font-semibold mb-4 text-primary-100">
                Product
              </h4>
              <ul className="space-y-2.5">
                {["Features", "Pricing", "Integrations", "Changelog"].map(
                  (l) => (
                    <li key={l}>
                      <Link
                        href="#"
                        className="text-sm text-primary-200/60 hover:text-white transition-colors"
                      >
                        {l}
                      </Link>
                    </li>
                  )
                )}
              </ul>
            </div>

            {/* Resources */}
            <div>
              <h4 className="text-sm font-semibold mb-4 text-primary-100">
                Resources
              </h4>
              <ul className="space-y-2.5">
                {["Blog", "Documentation", "Help Center", "API Reference"].map(
                  (l) => (
                    <li key={l}>
                      <Link
                        href="#"
                        className="text-sm text-primary-200/60 hover:text-white transition-colors"
                      >
                        {l}
                      </Link>
                    </li>
                  )
                )}
              </ul>
            </div>

            {/* Legal */}
            <div>
              <h4 className="text-sm font-semibold mb-4 text-primary-100">
                Legal
              </h4>
              <ul className="space-y-2.5">
                {["Privacy Policy", "Terms of Service", "Cookie Policy"].map(
                  (l) => (
                    <li key={l}>
                      <Link
                        href="#"
                        className="text-sm text-primary-200/60 hover:text-white transition-colors"
                      >
                        {l}
                      </Link>
                    </li>
                  )
                )}
              </ul>
            </div>
          </div>

          {/* Bottom bar */}
          <div className="border-t border-primary-800 pt-8 flex flex-col sm:flex-row items-center justify-between gap-4">
            <p className="text-xs text-primary-200/40">
              &copy; {new Date().getFullYear()} A-Stats. All rights reserved.
            </p>
            <div className="flex items-center gap-4">
              {/* Social icon placeholders */}
              {["X", "Li", "Gh"].map((icon) => (
                <Link
                  key={icon}
                  href="#"
                  className="h-8 w-8 rounded-full bg-primary-800/50 flex items-center justify-center text-xs text-primary-200/60 hover:bg-primary-700 hover:text-white transition-colors"
                >
                  {icon}
                </Link>
              ))}
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
