"use client";

import { useRef, useState, useEffect } from "react";
import {
  motion,
  useScroll,
  useSpring,
  useTransform,
  useMotionValueEvent,
  AnimatePresence,
} from "framer-motion";
import {
  Search,
  FileText,
  BarChart3,
  Globe,
  Share2,
  Sparkles,
  ArrowRight,
} from "lucide-react";
import Link from "next/link";

const workflowSteps = [
  {
    icon: Search,
    title: "Keyword opportunity detected",
    desc: "Ranking + AI visibility potential automatically found.",
    impact: "+320 search volume",
    detail:
      "High-intent topic discovered with strong SERP gap and AI-answer potential.",
    metric: "24%",
    metricLabel: "Traffic growth",
  },
  {
    icon: FileText,
    title: "Article generated",
    desc: "Full SEO structure + topical authority created.",
    impact: "SEO score 91",
    detail:
      "Outline, headings, entity coverage, and expert-style structure generated in minutes.",
    metric: "48%",
    metricLabel: "Content velocity",
  },
  {
    icon: BarChart3,
    title: "Optimization applied",
    desc: "Semantic coverage + gaps improved.",
    impact: "+18 score boost",
    detail:
      "On-page gaps closed, internal linking opportunities suggested, and structure improved.",
    metric: "72%",
    metricLabel: "SEO coverage",
  },
  {
    icon: Globe,
    title: "Published to WordPress",
    desc: "Live instantly with schema + metadata.",
    impact: "Live in 12s",
    detail:
      "Content shipped to production with metadata and publish-ready formatting.",
    metric: "96%",
    metricLabel: "Time saved",
  },
  {
    icon: Share2,
    title: "Distribution triggered",
    desc: "Social + refresh cycles scheduled.",
    impact: "4 channels",
    detail:
      "Promotion kicks in automatically so the page earns attention after publish.",
    metric: "128%",
    metricLabel: "Reach multiplier",
  },
  {
    icon: Sparkles,
    title: "AI citation detected",
    desc: "Answer engines start referencing content.",
    impact: "+3 citations",
    detail:
      "Visibility compounds as the article gets picked up in AI-generated answers.",
    metric: "148%",
    metricLabel: "Compounded growth",
  },
];

/* ─── Desktop: scroll-driven version ─── */

function ScrollWorkflowDesktop() {
  const sectionRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ["start start", "end end"],
  });
  const progress = useSpring(scrollYProgress, {
    stiffness: 100,
    damping: 22,
    mass: 0.15,
  });

  const progressHeight = useTransform(progress, [0, 1], ["0%", "100%"]);

  const [activeStep, setActiveStep] = useState(0);
  useMotionValueEvent(progress, "change", (v) => {
    const step = Math.min(
      Math.floor(v * workflowSteps.length),
      workflowSteps.length - 1
    );
    setActiveStep(Math.max(0, step));
  });

  const activeData = workflowSteps[activeStep];
  const ActiveIcon = activeData.icon;

  return (
    <section
      ref={sectionRef}
      className="relative h-[280vh] hidden lg:block"
    >
      <div className="sticky top-0 h-screen overflow-hidden flex items-center">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 w-full grid lg:grid-cols-2 gap-16 items-center">
          {/* Left — header + step list */}
          <div className="relative">
            <div className="mb-6">
              <div className="inline-flex items-center gap-2 rounded-full border border-primary-700/50 bg-primary-800/60 px-4 py-1.5 text-sm text-primary-300">
                <Sparkles className="h-4 w-4" />
                How It Works
              </div>
              <h2 className="mt-4 text-3xl xl:text-4xl font-display font-bold leading-tight text-cream-100">
                From keyword to{" "}
                <span className="bg-gradient-to-r from-primary-400 to-terra-400 bg-clip-text text-transparent">
                  published article
                </span>
              </h2>
              <p className="mt-3 max-w-md text-sm text-primary-200/60 leading-relaxed">
                Each scroll step reveals how A-Stats turns one keyword into a
                full growth loop.
              </p>
            </div>

            {/* Progress line + steps */}
            <div className="relative">
              <div className="absolute left-0 top-0 h-full w-px bg-primary-800/60">
                <motion.div
                  style={{ height: progressHeight }}
                  className="w-px bg-gradient-to-b from-primary-400 via-primary-500 to-terra-400"
                />
              </div>

              <div className="space-y-2 pl-7">
                {workflowSteps.map((step, i) => {
                  const Icon = step.icon;
                  const isActive = i === activeStep;
                  return (
                    <motion.div
                      key={step.title}
                      animate={{
                        opacity: isActive ? 1 : 0.35,
                        scale: isActive ? 1 : 0.98,
                        x: isActive ? 0 : -4,
                      }}
                      transition={{ duration: 0.3, ease: "easeOut" }}
                      className="relative rounded-xl border border-primary-800/60 bg-primary-900/80 px-4 py-3"
                    >
                      {/* Dot on progress line */}
                      <div
                        className={`absolute -left-[33px] top-1/2 -translate-y-1/2 h-2.5 w-2.5 rounded-full border-2 transition-colors duration-300 ${
                          isActive
                            ? "border-primary-400 bg-primary-400"
                            : "border-primary-700 bg-primary-950"
                        }`}
                      />
                      <div className="flex items-center gap-3">
                        <div
                          className={`h-7 w-7 rounded-lg flex items-center justify-center flex-shrink-0 transition-colors duration-300 ${
                            isActive
                              ? "bg-primary-500 text-white"
                              : "bg-primary-800 text-primary-400"
                          }`}
                        >
                          <Icon className="h-3.5 w-3.5" />
                        </div>
                        <div className="min-w-0">
                          <div className="text-sm font-display font-semibold text-cream-100 truncate">
                            {step.title}
                          </div>
                          <div className="text-xs text-primary-200/50 truncate">
                            {step.desc}
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Right — active step detail panel */}
          <div className="relative">
            <div className="absolute -inset-6 rounded-[32px] bg-primary-500/5 blur-2xl" />
            <div className="relative rounded-2xl border border-primary-800/60 bg-primary-900/95 shadow-[0_16px_60px_rgba(23,28,23,0.4)] overflow-hidden">
              <div className="p-8">
                {/* Header */}
                <div className="flex items-center justify-between mb-6">
                  <div className="text-xs font-medium text-primary-400 uppercase tracking-wider">
                    Step {String(activeStep + 1).padStart(2, "0")} of{" "}
                    {workflowSteps.length}
                  </div>
                  <div className="rounded-full border border-green-500/20 bg-green-500/10 px-3 py-1 text-xs font-medium text-green-400">
                    Live simulation
                  </div>
                </div>

                {/* Active step content */}
                <AnimatePresence mode="wait">
                  <motion.div
                    key={activeStep}
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -12 }}
                    transition={{ duration: 0.3, ease: "easeOut" }}
                  >
                    <div className="flex items-center gap-4 mb-5">
                      <div className="h-12 w-12 rounded-xl bg-primary-500/20 flex items-center justify-center">
                        <ActiveIcon className="h-6 w-6 text-primary-300" />
                      </div>
                      <div>
                        <h3 className="text-xl font-display font-bold text-cream-100">
                          {activeData.title}
                        </h3>
                        <p className="text-sm text-primary-200/60 mt-0.5">
                          {activeData.desc}
                        </p>
                      </div>
                    </div>

                    <p className="text-sm text-primary-200/70 leading-relaxed mb-6">
                      {activeData.detail}
                    </p>

                    {/* Impact metrics */}
                    <div className="grid grid-cols-2 gap-4 mb-6">
                      <div className="rounded-xl border border-primary-800/60 bg-primary-950/50 p-4">
                        <div className="text-xs text-primary-200/50 uppercase tracking-wider">
                          Impact
                        </div>
                        <div className="mt-1.5 text-2xl font-display font-bold text-cream-100">
                          {activeData.impact}
                        </div>
                      </div>
                      <div className="rounded-xl border border-primary-800/60 bg-primary-950/50 p-4">
                        <div className="text-xs text-primary-200/50 uppercase tracking-wider">
                          {activeData.metricLabel}
                        </div>
                        <div className="mt-1.5 text-2xl font-display font-bold text-primary-400">
                          +{activeData.metric}
                        </div>
                      </div>
                    </div>
                  </motion.div>
                </AnimatePresence>

                {/* Compounded outcome bar */}
                <div className="rounded-xl border border-primary-800/60 bg-gradient-to-r from-primary-500/10 to-terra-500/10 p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-primary-200/50 uppercase tracking-wider">
                      Compounded growth
                    </span>
                    <span className="text-lg font-display font-bold text-cream-100">
                      +{workflowSteps[activeStep].metric}
                    </span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-primary-800 overflow-hidden">
                    <motion.div
                      className="h-full rounded-full bg-gradient-to-r from-primary-500 to-terra-400"
                      animate={{
                        width: `${((activeStep + 1) / workflowSteps.length) * 100}%`,
                      }}
                      transition={{ duration: 0.4, ease: "easeOut" }}
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* CTA below panel */}
            <div className="mt-6 text-center">
              <Link
                href="/register"
                className="inline-flex items-center gap-2 text-sm font-medium text-primary-300 hover:text-primary-200 transition-colors"
              >
                Start building your growth loop
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ─── Mobile: static step-by-step version ─── */

function ScrollWorkflowMobile() {
  return (
    <div className="lg:hidden px-4 sm:px-6 py-16">
      <div className="max-w-lg mx-auto">
        <div className="text-center mb-10">
          <div className="inline-flex items-center gap-2 rounded-full border border-primary-700/50 bg-primary-800/60 px-4 py-1.5 text-sm text-primary-300">
            <Sparkles className="h-4 w-4" />
            How It Works
          </div>
          <h2 className="mt-4 text-2xl sm:text-3xl font-display font-bold leading-tight text-cream-100">
            From keyword to{" "}
            <span className="bg-gradient-to-r from-primary-400 to-terra-400 bg-clip-text text-transparent">
              published article
            </span>
          </h2>
          <p className="mt-3 text-sm text-primary-200/60 leading-relaxed">
            Six steps. One platform. Full growth loop.
          </p>
        </div>

        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-[15px] top-0 bottom-0 w-px bg-gradient-to-b from-primary-500 via-primary-600 to-terra-400" />

          <div className="space-y-6">
            {workflowSteps.map((step, i) => {
              const Icon = step.icon;
              return (
                <div key={step.title} className="relative pl-10">
                  {/* Dot */}
                  <div className="absolute left-[9px] top-4 h-3 w-3 rounded-full border-2 border-primary-400 bg-primary-950" />

                  <div className="rounded-xl border border-primary-800/60 bg-primary-900 p-4">
                    <div className="flex items-center gap-3 mb-2">
                      <div className="h-7 w-7 rounded-lg bg-primary-500/20 flex items-center justify-center flex-shrink-0">
                        <Icon className="h-3.5 w-3.5 text-primary-300" />
                      </div>
                      <span className="text-xs font-medium text-primary-400 uppercase tracking-wider">
                        Step {String(i + 1).padStart(2, "0")}
                      </span>
                    </div>
                    <h3 className="text-base font-display font-semibold text-cream-100">
                      {step.title}
                    </h3>
                    <p className="mt-1 text-sm text-primary-200/60">
                      {step.desc}
                    </p>
                    <div className="mt-3 flex items-center gap-3">
                      <span className="text-sm font-display font-bold text-primary-400">
                        {step.impact}
                      </span>
                      <span className="text-xs text-primary-200/40">
                        {step.metricLabel}: +{step.metric}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="mt-10 text-center">
          <Link
            href="/register"
            className="inline-flex items-center gap-2 btn bg-primary-500 text-white hover:bg-primary-600 px-6 py-2.5 text-sm"
          >
            Start building your growth loop
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </div>
  );
}

/* ─── Main export ─── */

export default function ScrollWorkflow() {
  return (
    <section id="how-it-works" className="bg-primary-950">
      <ScrollWorkflowDesktop />
      <ScrollWorkflowMobile />
    </section>
  );
}
