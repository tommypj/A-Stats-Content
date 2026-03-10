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
import { useTranslations } from "next-intl";
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

function HeroMockup({ t }: { t: (key: string) => string }) {
  return (
    <div className="relative pt-6 pb-6 px-4">
      {/* Integration badges — stacked above the card on mobile, overlapping top-left on desktop */}
      <div className="flex flex-wrap gap-2 mb-3 lg:absolute lg:top-0 lg:left-0 lg:z-10 lg:flex-col lg:gap-1.5 lg:mb-0">
        {/* WordPress */}
        <div className="bg-white rounded-xl shadow-soft border border-surface-tertiary px-3 py-2 flex items-center gap-2">
          <div className="h-6 w-6 rounded flex items-center justify-center text-white text-xs font-bold" style={{ backgroundColor: "#21759B" }}>W</div>
          <div>
            <div className="text-xs font-semibold text-text-primary leading-none">{t("hero.mockupWordPress")}</div>
            <div className="text-xs text-green-500 leading-none mt-0.5">{t("hero.mockupConnected")}</div>
          </div>
        </div>
        {/* Google Search Console */}
        <div className="bg-white rounded-xl shadow-soft border border-surface-tertiary px-3 py-2 flex items-center gap-2">
          <div className="h-6 w-6 rounded flex items-center justify-center text-white text-xs font-bold" style={{ backgroundColor: "#4285F4" }}>G</div>
          <div>
            <div className="text-xs font-semibold text-text-primary leading-none">{t("hero.mockupSearchConsole")}</div>
            <div className="text-xs text-green-500 leading-none mt-0.5">{t("hero.mockupConnected")}</div>
          </div>
        </div>
        {/* PageSpeed */}
        <div className="bg-white rounded-xl shadow-soft border border-surface-tertiary px-3 py-2 flex items-center gap-2">
          <div className="h-6 w-6 rounded flex items-center justify-center text-white text-xs font-bold" style={{ backgroundColor: "#F4B400" }}>⚡</div>
          <div>
            <div className="text-xs font-semibold text-text-primary leading-none">{t("hero.mockupPageSpeed")}</div>
            <div className="text-xs text-green-500 leading-none mt-0.5">{t("hero.mockupPageSpeedScore")}</div>
          </div>
        </div>
      </div>

      {/* Main article card */}
      <div className="bg-white rounded-2xl shadow-[0_4px_32px_rgba(0,0,0,0.10)] border border-surface-tertiary overflow-hidden">
        {/* Editor header */}
        <div className="flex items-center justify-between px-4 py-3 bg-surface-secondary border-b border-surface-tertiary">
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-green-400" />
            <span className="text-xs font-medium text-text-primary">{t("hero.mockupArticleReady")}</span>
          </div>
          <span className="text-xs text-text-muted">{t("hero.mockupWordCount")}</span>
        </div>

        {/* Content */}
        <div className="p-5">
          <div className="inline-flex items-center gap-1.5 text-xs bg-primary-50 text-primary-600 px-2.5 py-1 rounded-full mb-3 font-medium">
            {t("hero.mockupKeyword")}
          </div>
          <h4 className="text-sm font-bold text-text-primary mb-2 leading-snug">
            {t("hero.mockupArticleTitle")}
          </h4>
          <div className="space-y-1.5 mb-3">
            <div className="h-1.5 w-full rounded-full bg-surface-tertiary" />
            <div className="h-1.5 w-11/12 rounded-full bg-surface-tertiary" />
            <div className="h-1.5 w-4/5 rounded-full bg-surface-tertiary" />
          </div>
          <div className="text-xs font-semibold text-text-primary mb-1.5">{t("hero.mockupHeading1")}</div>
          <div className="space-y-1.5 mb-4">
            <div className="h-1.5 w-full rounded-full bg-surface-tertiary" />
            <div className="h-1.5 w-10/12 rounded-full bg-surface-tertiary" />
          </div>
          {/* Score + CTA */}
          <div className="flex items-center gap-4 pt-3 border-t border-surface-tertiary">
            <div className="flex-1">
              <div className="flex justify-between text-xs mb-1.5">
                <span className="text-text-muted">{t("hero.mockupSeoScore")}</span>
                <span className="font-semibold text-primary-600">{t("hero.mockupSeoScoreValue")}</span>
              </div>
              <div className="h-1.5 rounded-full bg-surface-tertiary overflow-hidden">
                <div className="h-full w-[94%] rounded-full bg-gradient-to-r from-primary-400 to-primary-500" />
              </div>
            </div>
            <div className="text-xs bg-primary-500 text-white px-3 py-1.5 rounded-lg font-medium whitespace-nowrap">
              {t("hero.mockupPublish")}
            </div>
          </div>
        </div>
      </div>

      {/* AEO score — bottom right */}
      <div className="absolute -bottom-2 -right-2 z-10 bg-primary-950 rounded-2xl shadow-soft p-4 text-center">
        <div className="flex items-center gap-1 mb-1 justify-center">
          <Zap className="h-3 w-3 text-primary-400" />
          <span className="text-xs text-primary-300 font-medium">{t("hero.mockupAeoScore")}</span>
        </div>
        <div className="text-3xl font-bold text-primary-400 leading-none mb-1">{t("hero.mockupAeoValue")}</div>
        <div className="text-xs text-primary-300">
          <span className="text-green-400 font-semibold">{t("hero.mockupAeoChange")}</span> {t("hero.mockupAeoThisMonth")}
        </div>
      </div>
    </div>
  );
}

function ContentGenMockup({ t }: { t: (key: string) => string }) {
  return (
    <div className="aspect-[4/3] rounded-2xl bg-gradient-to-br from-primary-50 via-cream-100 to-terra-400/10 p-4 flex items-center justify-center">
      <div className="w-full bg-white/80 backdrop-blur-sm rounded-xl shadow-soft border border-surface-tertiary overflow-hidden">
        <div className="flex items-center justify-between px-3 py-2.5 bg-surface-secondary border-b border-surface-tertiary">
          <span className="text-xs font-semibold text-text-primary">{t("showcases.mockupNewArticle")}</span>
          <div className="flex items-center gap-1.5">
            <div className="h-1.5 w-1.5 rounded-full bg-yellow-400 animate-pulse" />
            <span className="text-xs text-yellow-600 font-medium">{t("showcases.mockupGenerating")}</span>
          </div>
        </div>
        <div className="p-3 space-y-2.5">
          {/* Keyword input */}
          <div className="rounded-lg border border-primary-300 bg-primary-50/60 px-2.5 py-1.5 text-xs text-primary-700 font-medium">
            {t("showcases.mockupKeyword")}
          </div>
          {/* Steps */}
          <div className="flex items-center gap-1.5">
            {[
              { label: t("showcases.mockupStepOutline"), done: true },
              { label: t("showcases.mockupStepArticle"), active: true },
              { label: t("showcases.mockupStepImages"), pending: true },
            ].map((step, i) => (
              <div key={i} className="flex items-center gap-1.5">
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
              { text: t("showcases.mockupOutline1"), active: true },
              { text: t("showcases.mockupOutline2"), active: false },
              { text: t("showcases.mockupOutline3"), active: false },
              { text: t("showcases.mockupOutline4"), active: false },
            ].map((h, i) => (
              <div key={i} className={`flex items-center gap-1.5 text-xs ${h.active ? "text-text-primary font-medium" : "text-text-muted"}`}>
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

function SeoAnalyticsMockup({ t }: { t: (key: string) => string }) {
  return (
    <div className="aspect-[4/3] rounded-2xl bg-gradient-to-br from-primary-50 via-cream-100 to-terra-400/10 p-4 flex items-center justify-center">
      <div className="w-full bg-white/80 backdrop-blur-sm rounded-xl shadow-soft border border-surface-tertiary overflow-hidden">
        <div className="flex items-center justify-between px-3 py-2.5 bg-surface-secondary border-b border-surface-tertiary">
          <span className="text-xs font-semibold text-text-primary">{t("showcases.mockupSeoAnalytics")}</span>
          <div className="flex items-center gap-1 text-xs text-green-600 font-medium">
            <div className="h-1.5 w-1.5 rounded-full bg-green-400" />
            {t("showcases.mockupGscLive")}
          </div>
        </div>
        <div className="p-3 space-y-2.5">
          {/* Stats */}
          <div className="grid grid-cols-3 gap-1.5">
            {[
              { label: t("showcases.mockupImpressions"), value: t("showcases.mockupImpressionsValue") },
              { label: t("showcases.mockupClicks"), value: t("showcases.mockupClicksValue") },
              { label: t("showcases.mockupAvgPos"), value: t("showcases.mockupAvgPosValue") },
            ].map((s, i) => (
              <div key={i} className="text-center p-1.5 rounded-lg bg-surface-secondary">
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

function SocialMediaMockup({ t }: { t: (key: string) => string }) {
  return (
    <div className="aspect-[4/3] rounded-2xl bg-gradient-to-br from-primary-50 via-cream-100 to-terra-400/10 p-4 flex items-center justify-center">
      <div className="w-full bg-white/80 backdrop-blur-sm rounded-xl shadow-soft border border-surface-tertiary overflow-hidden">
        <div className="flex items-center justify-between px-3 py-2.5 bg-surface-secondary border-b border-surface-tertiary">
          <span className="text-xs font-semibold text-text-primary">{t("showcases.mockupSocialScheduler")}</span>
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
                <div className="text-xs font-semibold text-text-primary leading-none">{t("showcases.mockupPostBy")}</div>
                <div className="text-xs text-text-muted leading-none mt-0.5">{t("showcases.mockupPostTime")}</div>
              </div>
            </div>
            <p className="text-xs text-text-secondary leading-relaxed">
              {t("showcases.mockupPostText")}
            </p>
          </div>
          {/* Platform row */}
          <div className="flex items-center justify-between text-xs">
            <span className="text-text-muted">{t("showcases.mockupPostingTo")}</span>
            <span className="text-primary-600 font-medium">{t("showcases.mockupViewCalendar")}</span>
          </div>
          {/* Queue */}
          <div className="flex gap-1.5">
            {[t("showcases.mockupMon"), t("showcases.mockupTue"), t("showcases.mockupWed"), t("showcases.mockupThu"), t("showcases.mockupFri")].map((d, i) => (
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
  const t = useTranslations("landing");
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

  const features = [
    {
      icon: Sparkles,
      title: t("features.feature1Title"),
      description: t("features.feature1Description"),
    },
    {
      icon: FileText,
      title: t("features.feature2Title"),
      description: t("features.feature2Description"),
    },
    {
      icon: Zap,
      title: t("features.feature3Title"),
      description: t("features.feature3Description"),
    },
    {
      icon: BarChart3,
      title: t("features.feature4Title"),
      description: t("features.feature4Description"),
    },
    {
      icon: Share2,
      title: t("features.feature5Title"),
      description: t("features.feature5Description"),
    },
    {
      icon: BookOpen,
      title: t("features.feature6Title"),
      description: t("features.feature6Description"),
    },
  ];

  const steps = [
    {
      number: "1",
      title: t("howItWorks.step1Title"),
      description: t("howItWorks.step1Description"),
    },
    {
      number: "2",
      title: t("howItWorks.step2Title"),
      description: t("howItWorks.step2Description"),
    },
    {
      number: "3",
      title: t("howItWorks.step3Title"),
      description: t("howItWorks.step3Description"),
    },
  ];

  const showcases = [
    {
      title: t("showcases.showcase1Title"),
      description: t("showcases.showcase1Description"),
      bullets: [
        t("showcases.showcase1Bullet1"),
        t("showcases.showcase1Bullet2"),
        t("showcases.showcase1Bullet3"),
      ],
    },
    {
      title: t("showcases.showcase2Title"),
      description: t("showcases.showcase2Description"),
      bullets: [
        t("showcases.showcase2Bullet1"),
        t("showcases.showcase2Bullet2"),
        t("showcases.showcase2Bullet3"),
      ],
    },
    {
      title: t("showcases.showcase3Title"),
      description: t("showcases.showcase3Description"),
      bullets: [
        t("showcases.showcase3Bullet1"),
        t("showcases.showcase3Bullet2"),
        t("showcases.showcase3Bullet3"),
      ],
    },
  ];

  const testimonials = [
    {
      quote: t("testimonials.testimonial1Quote"),
      author: t("testimonials.testimonial1Author"),
      role: t("testimonials.testimonial1Role"),
      metric: t("testimonials.testimonial1Metric"),
      initials: "SK",
    },
    {
      quote: t("testimonials.testimonial2Quote"),
      author: t("testimonials.testimonial2Author"),
      role: t("testimonials.testimonial2Role"),
      metric: t("testimonials.testimonial2Metric"),
      initials: "MT",
    },
    {
      quote: t("testimonials.testimonial3Quote"),
      author: t("testimonials.testimonial3Author"),
      role: t("testimonials.testimonial3Role"),
      metric: t("testimonials.testimonial3Metric"),
      initials: "ER",
    },
  ];

  const plans = [
    {
      name: t("pricing.planFreeName"),
      monthlyPrice: 0,
      yearlyPrice: 0,
      description: t("pricing.planFreeDescription"),
      features: [
        t("pricing.planFreeFeature1"),
        t("pricing.planFreeFeature2"),
        t("pricing.planFreeFeature3"),
        t("pricing.planFreeFeature4"),
        t("pricing.planFreeFeature5"),
        t("pricing.planFreeFeature6"),
      ],
      cta: t("pricing.planFreeCta"),
      href: "/register",
    },
    {
      name: t("pricing.planStarterName"),
      monthlyPrice: 29,
      yearlyPrice: 24,
      description: t("pricing.planStarterDescription"),
      features: [
        t("pricing.planStarterFeature1"),
        t("pricing.planStarterFeature2"),
        t("pricing.planStarterFeature3"),
        t("pricing.planStarterFeature4"),
        t("pricing.planStarterFeature5"),
        t("pricing.planStarterFeature6"),
        t("pricing.planStarterFeature7"),
        t("pricing.planStarterFeature8"),
        t("pricing.planStarterFeature9"),
        t("pricing.planStarterFeature10"),
        t("pricing.planStarterFeature11"),
        t("pricing.planStarterFeature12"),
      ],
      cta: t("pricing.planStarterCta"),
      href: "/register",
    },
    {
      name: t("pricing.planProfessionalName"),
      monthlyPrice: 79,
      yearlyPrice: 66,
      description: t("pricing.planProfessionalDescription"),
      features: [
        t("pricing.planProfessionalFeature1"),
        t("pricing.planProfessionalFeature2"),
        t("pricing.planProfessionalFeature3"),
        t("pricing.planProfessionalFeature4"),
        t("pricing.planProfessionalFeature5"),
        t("pricing.planProfessionalFeature6"),
        t("pricing.planProfessionalFeature7"),
        t("pricing.planProfessionalFeature8"),
        t("pricing.planProfessionalFeature9"),
        t("pricing.planProfessionalFeature10"),
        t("pricing.planProfessionalFeature11"),
        t("pricing.planProfessionalFeature12"),
        t("pricing.planProfessionalFeature13"),
        t("pricing.planProfessionalFeature14"),
      ],
      popular: true,
      cta: t("pricing.planProfessionalCta"),
      href: "/register",
    },
    {
      name: t("pricing.planEnterpriseName"),
      monthlyPrice: 199,
      yearlyPrice: 166,
      description: t("pricing.planEnterpriseDescription"),
      features: [
        t("pricing.planEnterpriseFeature1"),
        t("pricing.planEnterpriseFeature2"),
        t("pricing.planEnterpriseFeature3"),
        t("pricing.planEnterpriseFeature4"),
        t("pricing.planEnterpriseFeature5"),
        t("pricing.planEnterpriseFeature6"),
        t("pricing.planEnterpriseFeature7"),
        t("pricing.planEnterpriseFeature8"),
        t("pricing.planEnterpriseFeature9"),
        t("pricing.planEnterpriseFeature10"),
        t("pricing.planEnterpriseFeature11"),
      ],
      cta: t("pricing.planEnterpriseCta"),
      href: "/register",
    },
  ];

  const faqs = [
    { q: t("faq.faq1Question"), a: t("faq.faq1Answer") },
    { q: t("faq.faq2Question"), a: t("faq.faq2Answer") },
    { q: t("faq.faq3Question"), a: t("faq.faq3Answer") },
    { q: t("faq.faq4Question"), a: t("faq.faq4Answer") },
    { q: t("faq.faq5Question"), a: t("faq.faq5Answer") },
    { q: t("faq.faq6Question"), a: t("faq.faq6Answer") },
  ];

  const whoItsForSegments = [
    {
      title: t("whoItsFor.segment1Title"),
      description: t("whoItsFor.segment1Description"),
      features: [
        t("whoItsFor.segment1Feature1"),
        t("whoItsFor.segment1Feature2"),
        t("whoItsFor.segment1Feature3"),
      ],
      plan: t("whoItsFor.segment1Plan"),
    },
    {
      title: t("whoItsFor.segment2Title"),
      description: t("whoItsFor.segment2Description"),
      features: [
        t("whoItsFor.segment2Feature1"),
        t("whoItsFor.segment2Feature2"),
        t("whoItsFor.segment2Feature3"),
      ],
      plan: t("whoItsFor.segment2Plan"),
    },
    {
      title: t("whoItsFor.segment3Title"),
      description: t("whoItsFor.segment3Description"),
      features: [
        t("whoItsFor.segment3Feature1"),
        t("whoItsFor.segment3Feature2"),
        t("whoItsFor.segment3Feature3"),
      ],
      plan: t("whoItsFor.segment3Plan"),
    },
  ];

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
                <span>{t("hero.badge")}</span>
              </div>
              <h1 className="hero-animate-delay-1 text-4xl md:text-5xl lg:text-6xl font-display font-bold text-text-primary leading-[1.1] tracking-tight">
                {t("hero.titleLine1")}{" "}
                <span className="gradient-text">{t("hero.titleHighlight")}</span>
              </h1>
              <p className="hero-animate-delay-2 mt-6 text-lg text-text-secondary max-w-lg leading-relaxed">
                {t.rich("hero.description", {
                  em: (chunks) => <em>{chunks}</em>,
                })}
              </p>
              <div className="hero-animate-delay-3 mt-8 flex flex-col sm:flex-row gap-4">
                <Link
                  href="/register"
                  className="btn-primary text-base px-8 py-3"
                >
                  {t("hero.cta")}
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
                <Link
                  href="#how-it-works"
                  className="btn-secondary text-base px-8 py-3"
                >
                  {t("hero.secondaryCta")}
                </Link>
              </div>
              {/* Social proof */}
              <div className="hero-animate-delay-3 mt-8 flex flex-wrap gap-x-8 gap-y-3 text-sm">
                <span className="flex items-center gap-2 text-text-primary font-semibold">
                  <span className="text-primary-500 text-lg">{t("hero.socialProofTeamsCount")}</span> {t("hero.socialProofTeamsLabel")}
                </span>
                <span className="flex items-center gap-2 text-text-primary font-semibold">
                  <span className="text-primary-500 text-lg">{t("hero.socialProofArticlesCount")}</span> {t("hero.socialProofArticlesLabel")}
                </span>
                <span className="flex items-center gap-2 text-text-primary font-semibold">
                  <span className="text-primary-500 text-lg">{t("hero.socialProofRatingCount")}</span> {t("hero.socialProofRatingLabel")}
                </span>
              </div>

              {/* Powered by */}
              <p className="hero-animate-delay-3 mt-4 text-xs text-text-muted">
                {t.rich("hero.poweredBy", {
                  claude: (chunks) => <span className="font-medium text-text-secondary">{chunks}</span>,
                  gpt: (chunks) => <span className="font-medium text-text-secondary">{chunks}</span>,
                  gemini: (chunks) => <span className="font-medium text-text-secondary">{chunks}</span>,
                })}
              </p>

              {/* Trust indicators */}
              <div className="hero-animate-delay-3 mt-6 flex flex-wrap gap-6 text-sm text-text-muted">
                <span className="flex items-center gap-1.5">
                  <CreditCard className="h-4 w-4 text-primary-400" />
                  {t("hero.trustNoCreditCard")}
                </span>
                <span className="flex items-center gap-1.5">
                  <Clock className="h-4 w-4 text-terra-400" />
                  {t("hero.trustSetup")}
                </span>
                <span className="flex items-center gap-1.5">
                  <ShieldCheck className="h-4 w-4 text-earth-400" />
                  {t("hero.trustCancel")}
                </span>
              </div>
            </div>

            {/* Right — product mockup */}
            <div className="hero-animate-delay-2 relative mx-auto max-w-sm lg:max-w-none">
              <HeroMockup t={t} />
            </div>
          </div>
        </div>
      </section>

      {/* ─── 3. Integrations Bar ─── */}
      <section className="py-10 bg-white border-y border-surface-tertiary/50">
        <div className="page-container">
          <p className="text-center text-xs font-semibold text-text-muted uppercase tracking-widest mb-7">
            {t("integrations.heading")}
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
              {t("features.title")}{" "}
              <span className="gradient-text">{t("features.titleHighlight")}</span>
            </h2>
            <p className="mt-4 text-text-secondary max-w-2xl mx-auto">
              {t("features.description")}
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
              {t("howItWorks.title")}
            </h2>
            <p className="mt-4 text-text-secondary max-w-2xl mx-auto">
              {t("howItWorks.description")}
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
                key={i}
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
                    {item.bullets.map((b, j) => (
                      <li
                        key={j}
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
                  <Visual t={t} />
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
              <span>{t("aeo.badge")}</span>
            </div>
            <h2 className="text-3xl md:text-4xl font-display font-bold text-cream-100">
              {t("aeo.title")}
            </h2>
            <p className="mt-4 text-primary-200/70 max-w-2xl mx-auto leading-relaxed">
              {t("aeo.description")}
            </p>
          </RevealSection>

          <RevealSection>
            <div className="grid md:grid-cols-3 gap-6 mb-12">
              <div className="stagger-child rounded-2xl bg-primary-900 border border-primary-800/60 p-6">
                <div className="h-12 w-12 rounded-xl bg-primary-800 flex items-center justify-center mb-4">
                  <Zap className="h-6 w-6 text-primary-300" />
                </div>
                <h3 className="font-display text-lg font-semibold text-cream-100 mb-2">
                  {t("aeo.card1Title")}
                </h3>
                <p className="text-sm text-primary-200/70 leading-relaxed">
                  {t("aeo.card1Description")}
                </p>
              </div>

              <div className="stagger-child rounded-2xl bg-primary-900 border border-primary-800/60 p-6">
                <div className="h-12 w-12 rounded-xl bg-primary-800 flex items-center justify-center mb-4">
                  <Bell className="h-6 w-6 text-primary-300" />
                </div>
                <h3 className="font-display text-lg font-semibold text-cream-100 mb-2">
                  {t("aeo.card2Title")}
                </h3>
                <p className="text-sm text-primary-200/70 leading-relaxed">
                  {t("aeo.card2Description")}
                </p>
              </div>

              <div className="stagger-child rounded-2xl bg-primary-900 border border-primary-800/60 p-6">
                <div className="h-12 w-12 rounded-xl bg-primary-800 flex items-center justify-center mb-4">
                  <TrendingUp className="h-6 w-6 text-primary-300" />
                </div>
                <h3 className="font-display text-lg font-semibold text-cream-100 mb-2">
                  {t("aeo.card3Title")}
                </h3>
                <p className="text-sm text-primary-200/70 leading-relaxed">
                  {t("aeo.card3Description")}
                </p>
              </div>
            </div>

            {/* AEO Score mockup card */}
            <div className="max-w-sm mx-auto rounded-2xl bg-primary-900 border border-primary-800/60 p-8 text-center">
              <p className="text-sm font-medium text-primary-300 mb-4 uppercase tracking-widest">
                {t("aeo.scoreLabel")}
              </p>
              <div className="text-7xl font-display font-bold text-primary-400 mb-2">
                {t("aeo.scoreValue")}
              </div>
              <p className="text-sm text-primary-300 mb-6">
                <span className="text-primary-400 font-medium">{t("aeo.scoreChange")}</span>{" "}
                {t("aeo.scoreThisMonth")}
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
              {t("whoItsFor.title")} <span className="gradient-text">{t("whoItsFor.titleHighlight")}</span>
            </h2>
            <p className="mt-4 text-text-secondary max-w-2xl mx-auto">
              {t("whoItsFor.description")}
            </p>
          </RevealSection>

          <RevealSection>
            <div className="grid md:grid-cols-3 gap-6">
              {whoItsForSegments.map((segment) => (
                <div key={segment.title} className="stagger-child card p-6">
                  <h3 className="font-display text-lg font-semibold text-text-primary mb-2">
                    {segment.title}
                  </h3>
                  <p className="text-sm text-text-secondary leading-relaxed mb-4">
                    {segment.description}
                  </p>
                  <ul className="space-y-2 mb-4">
                    {segment.features.map((f, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-text-secondary">
                        <Check className="h-3.5 w-3.5 text-primary-500 flex-shrink-0" />
                        {f}
                      </li>
                    ))}
                  </ul>
                  <p className="text-xs font-medium text-primary-600">
                    {t("whoItsFor.recommended", { plan: segment.plan })}
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
              {t("testimonials.title")}
            </h2>
            <p className="mt-4 text-text-secondary max-w-2xl mx-auto">
              {t("testimonials.description")}
            </p>
          </RevealSection>

          <RevealSection>
            <div className="grid md:grid-cols-3 gap-6">
              {testimonials.map((tm) => (
                <div
                  key={tm.author}
                  className="stagger-child card p-6 flex flex-col"
                >
                  {tm.metric && (
                    <div className="inline-flex self-start items-center gap-1.5 text-xs font-semibold text-primary-600 bg-primary-50 px-2.5 py-1 rounded-full mb-3">
                      <TrendingUp className="h-3 w-3" />
                      {tm.metric}
                    </div>
                  )}
                  <p className="text-text-secondary text-sm leading-relaxed flex-1 italic">
                    &ldquo;{tm.quote}&rdquo;
                  </p>
                  <div className="mt-6 flex items-center gap-3">
                    <div className="h-10 w-10 rounded-full bg-primary-100 flex items-center justify-center text-sm font-semibold text-primary-600">
                      {tm.initials}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-text-primary">
                        {tm.author}
                      </p>
                      <p className="text-xs text-text-muted">{tm.role}</p>
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
              {t("pricing.title")}
            </h2>
            <p className="mt-4 text-text-secondary max-w-2xl mx-auto">
              {t("pricing.description")}
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
                {t("pricing.monthly")}
              </button>
              <button
                className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
                  yearlyBilling
                    ? "bg-primary-500 text-white"
                    : "text-text-secondary hover:text-text-primary"
                }`}
                onClick={() => setYearlyBilling(true)}
              >
                {t("pricing.yearly")}
                <span className="ml-1.5 text-xs opacity-80">{t("pricing.yearlySave")}</span>
              </button>
            </div>
          </RevealSection>

          {/* Trust badges */}
          <div className="flex flex-wrap items-center justify-center gap-6 text-xs text-text-muted mb-10">
            <span className="flex items-center gap-1.5">
              <ShieldCheck className="h-4 w-4 text-green-500" />
              {t("pricing.trustSsl")}
            </span>
            <span className="flex items-center gap-1.5">
              <CreditCard className="h-4 w-4 text-text-muted" />
              {t("pricing.trustCancel")}
            </span>
            <span className="flex items-center gap-1.5">
              <Clock className="h-4 w-4 text-text-muted" />
              {t("pricing.trustMoneyBack")}
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
                      {t("pricing.mostPopular")}
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
                        <span className="text-4xl font-display font-bold text-text-primary">{t("pricing.free")}</span>
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
                          <span className="text-text-muted">{t("pricing.perMonth")}</span>
                        </>
                      )}
                    </div>
                    {yearlyBilling && plan.monthlyPrice > 0 && (
                      <p className="text-xs text-primary-600 mt-1">
                        {t("pricing.billedAnnually", { amount: (plan.monthlyPrice - plan.yearlyPrice) * 12 })}
                      </p>
                    )}
                  </div>
                  <ul className="space-y-3 mb-8 flex-1">
                    {plan.features.map((feature, i) => (
                      <li
                        key={i}
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
                {t("blog.title")} <span className="gradient-text">{t("blog.titleHighlight")}</span>
              </h2>
              <p className="mt-4 text-text-secondary max-w-2xl mx-auto">
                {t("blog.description")}
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
                      className="block relative overflow-hidden aspect-[16/9] bg-surface-secondary flex-shrink-0"
                    >
                      {post.featured_image_url ? (
                        <Image
                          src={post.featured_image_url}
                          alt={post.featured_image_alt || post.title}
                          fill
                          loading="lazy"
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
                              {t("blog.minuteRead", { minutes: post.reading_time_minutes })}
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
                  {t("blog.viewAllPosts")}
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
              {t("faq.title")}
            </h2>
          </RevealSection>

          <RevealSection>
            <div className="space-y-3">
              {faqs.map((faq, i) => (
                <details
                  key={i}
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
              {t("cta.title")}
            </h2>
            <p className="mt-4 text-primary-100 max-w-2xl mx-auto">
              {t("cta.description")}
            </p>
            <Link
              href="/register"
              className="mt-8 inline-flex btn bg-white text-primary-600 hover:bg-primary-50 text-base px-8 py-3 shadow-soft"
            >
              {t("cta.button")}
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
            <p className="mt-4 text-xs text-primary-200/70">
              {t("cta.subtext")}
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
            {t.rich("stickyCta.text", {
              bold: (chunks) => <span className="font-semibold text-text-primary">{chunks}</span>,
            })}
          </p>
          <div className="flex items-center gap-3 w-full sm:w-auto">
            <Link
              href="/register"
              className="btn-primary text-sm px-6 py-2.5 w-full sm:w-auto text-center"
            >
              {t("stickyCta.button")}
              <ArrowRight className="ml-2 h-4 w-4 inline" />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
