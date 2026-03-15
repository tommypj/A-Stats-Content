"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search,
  FileText,
  BarChart3,
  Globe,
  Share2,
  Sparkles,
  ArrowRight,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import Link from "next/link";

const workflowSteps = [
  {
    icon: Search,
    title: "Keyword opportunity detected",
    desc: "Ranking + AI visibility potential automatically found.",
    impact: "+320 search volume",
    detail:
      "High-intent topic discovered with strong SERP gap and AI-answer potential. A-Stats scans your niche, analyses competitor gaps, and surfaces the keywords most likely to drive traffic and AI citations.",
    metric: "24%",
    metricLabel: "Traffic growth",
  },
  {
    icon: FileText,
    title: "Article generated",
    desc: "Full SEO structure + topical authority created.",
    impact: "SEO score 91",
    detail:
      "Outline, headings, entity coverage, and expert-style structure generated in minutes. The AI pipeline produces a publish-ready article with proper semantic structure, internal linking hints, and schema-ready formatting.",
    metric: "48%",
    metricLabel: "Content velocity",
  },
  {
    icon: BarChart3,
    title: "Optimization applied",
    desc: "Semantic coverage + content gaps improved.",
    impact: "+18 score boost",
    detail:
      "On-page gaps closed, internal linking opportunities suggested, and structure improved. Every article is scored for SEO completeness so you know exactly what to improve before publishing.",
    metric: "72%",
    metricLabel: "SEO coverage",
  },
  {
    icon: Globe,
    title: "Published to WordPress",
    desc: "Live instantly with schema + metadata.",
    impact: "Live in 12s",
    detail:
      "Content shipped to your WordPress site with full metadata, featured images, SEO titles, and schema markup. One click, and your article is live and indexed — no copy-pasting or manual formatting.",
    metric: "96%",
    metricLabel: "Time saved",
  },
  {
    icon: Share2,
    title: "Distribution triggered",
    desc: "Social + refresh cycles scheduled.",
    impact: "4 channels",
    detail:
      "Promotion kicks in automatically: LinkedIn, Facebook, Instagram posts generated and scheduled from your article. Your content reaches audiences across every platform without extra effort.",
    metric: "128%",
    metricLabel: "Reach multiplier",
  },
  {
    icon: Sparkles,
    title: "AI citation detected",
    desc: "Answer engines start referencing content.",
    impact: "+3 citations",
    detail:
      "Visibility compounds as your article gets picked up in AI-generated answers. A-Stats tracks when ChatGPT, Gemini, and Perplexity cite your content — a new growth channel most tools ignore.",
    metric: "148%",
    metricLabel: "Compounded growth",
  },
];

export default function ScrollWorkflow() {
  const [activeStep, setActiveStep] = useState(0);
  const activeData = workflowSteps[activeStep];
  const ActiveIcon = activeData.icon;

  const goNext = () =>
    setActiveStep((s) => Math.min(s + 1, workflowSteps.length - 1));
  const goPrev = () => setActiveStep((s) => Math.max(s - 1, 0));

  return (
    <section id="how-it-works" className="bg-primary-950 py-20 lg:py-28">
      <div className="page-container">
        {/* Header */}
        <div className="text-center mb-12 lg:mb-16">
          <div className="inline-flex items-center gap-2 rounded-full border border-primary-700/50 bg-primary-800/60 px-4 py-1.5 text-sm text-primary-300 mb-5">
            <Sparkles className="h-4 w-4" />
            How It Works
          </div>
          <h2 className="text-3xl md:text-4xl font-display font-bold leading-tight text-cream-100">
            From keyword to{" "}
            <span className="bg-gradient-to-r from-primary-400 to-terra-400 bg-clip-text text-transparent">
              published article
            </span>
          </h2>
          <p className="mt-4 max-w-2xl mx-auto text-base text-primary-200/60 leading-relaxed">
            Six steps. One platform. A-Stats turns a single keyword into a full
            growth loop — writing, optimization, publishing, distribution, and
            AI-answer pickup.
          </p>
        </div>

        {/* Main content */}
        <div className="grid lg:grid-cols-[1fr_1.15fr] gap-8 lg:gap-12 items-start">
          {/* Left — step selector */}
          <div className="relative">
            {/* Progress line (desktop) */}
            <div className="absolute left-[15px] top-0 bottom-0 w-px bg-primary-800/60 hidden lg:block">
              <motion.div
                className="w-px bg-gradient-to-b from-primary-400 via-primary-500 to-terra-400"
                animate={{
                  height: `${((activeStep + 1) / workflowSteps.length) * 100}%`,
                }}
                transition={{ duration: 0.4, ease: "easeOut" }}
              />
            </div>

            <div className="space-y-2 lg:pl-10">
              {workflowSteps.map((step, i) => {
                const Icon = step.icon;
                const isActive = i === activeStep;
                const isPast = i < activeStep;

                return (
                  <button
                    key={step.title}
                    onClick={() => setActiveStep(i)}
                    className={`relative w-full text-left rounded-xl border px-4 py-3.5 transition-all duration-300 ${
                      isActive
                        ? "border-primary-600/80 bg-primary-900 shadow-[0_0_20px_rgba(98,120,98,0.1)]"
                        : "border-primary-800/40 bg-primary-900/40 hover:bg-primary-900/70 hover:border-primary-800/60"
                    }`}
                  >
                    {/* Dot on progress line (desktop) */}
                    <div
                      className={`absolute -left-[36px] top-1/2 -translate-y-1/2 h-3 w-3 rounded-full border-2 transition-all duration-300 hidden lg:block ${
                        isActive
                          ? "border-primary-400 bg-primary-400 scale-125"
                          : isPast
                            ? "border-primary-500 bg-primary-500"
                            : "border-primary-700 bg-primary-950"
                      }`}
                    />

                    <div className="flex items-center gap-3">
                      <div
                        className={`h-8 w-8 rounded-lg flex items-center justify-center flex-shrink-0 transition-colors duration-300 ${
                          isActive
                            ? "bg-primary-500 text-white"
                            : isPast
                              ? "bg-primary-700 text-primary-300"
                              : "bg-primary-800/80 text-primary-400/60"
                        }`}
                      >
                        <Icon className="h-4 w-4" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div
                          className={`text-sm font-display font-semibold transition-colors duration-300 ${
                            isActive
                              ? "text-cream-100"
                              : "text-cream-100/60"
                          }`}
                        >
                          {step.title}
                        </div>
                        <div
                          className={`text-xs transition-colors duration-300 truncate ${
                            isActive
                              ? "text-primary-200/60"
                              : "text-primary-200/30"
                          }`}
                        >
                          {step.desc}
                        </div>
                      </div>
                      <span
                        className={`text-xs font-medium px-2 py-0.5 rounded-full flex-shrink-0 transition-colors duration-300 ${
                          isActive
                            ? "bg-primary-500/20 text-primary-300"
                            : "text-primary-200/30"
                        }`}
                      >
                        {String(i + 1).padStart(2, "0")}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Right — detail panel */}
          <div>
            <div className="relative rounded-2xl border border-primary-800/60 bg-primary-900/95 shadow-[0_16px_60px_rgba(23,28,23,0.4)] overflow-hidden">
              <div className="p-6 sm:p-8">
                {/* Panel header */}
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-3">
                    <button
                      onClick={goPrev}
                      disabled={activeStep === 0}
                      className="h-8 w-8 rounded-lg border border-primary-800/60 flex items-center justify-center text-primary-300 hover:bg-primary-800/60 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </button>
                    <span className="text-xs font-medium text-primary-400 uppercase tracking-wider">
                      Step {activeStep + 1} of {workflowSteps.length}
                    </span>
                    <button
                      onClick={goNext}
                      disabled={activeStep === workflowSteps.length - 1}
                      className="h-8 w-8 rounded-lg border border-primary-800/60 flex items-center justify-center text-primary-300 hover:bg-primary-800/60 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                      <ChevronRight className="h-4 w-4" />
                    </button>
                  </div>
                  <div className="rounded-full border border-green-500/20 bg-green-500/10 px-3 py-1 text-xs font-medium text-green-400">
                    Live simulation
                  </div>
                </div>

                {/* Animated content */}
                <AnimatePresence mode="wait">
                  <motion.div
                    key={activeStep}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -16 }}
                    transition={{ duration: 0.3, ease: "easeOut" }}
                  >
                    {/* Step title + icon */}
                    <div className="flex items-start gap-4 mb-5">
                      <div className="h-14 w-14 rounded-xl bg-primary-500/15 flex items-center justify-center flex-shrink-0">
                        <ActiveIcon className="h-7 w-7 text-primary-300" />
                      </div>
                      <div>
                        <h3 className="text-xl sm:text-2xl font-display font-bold text-cream-100">
                          {activeData.title}
                        </h3>
                        <p className="text-sm text-primary-300/70 mt-1">
                          {activeData.desc}
                        </p>
                      </div>
                    </div>

                    {/* Detail text */}
                    <p className="text-sm text-primary-200/65 leading-relaxed mb-6">
                      {activeData.detail}
                    </p>

                    {/* Impact metrics */}
                    <div className="grid grid-cols-2 gap-4">
                      <div className="rounded-xl border border-primary-800/60 bg-primary-950/60 p-4">
                        <div className="text-xs text-primary-200/45 uppercase tracking-wider">
                          Impact
                        </div>
                        <div className="mt-2 text-2xl font-display font-bold text-cream-100">
                          {activeData.impact}
                        </div>
                      </div>
                      <div className="rounded-xl border border-primary-800/60 bg-primary-950/60 p-4">
                        <div className="text-xs text-primary-200/45 uppercase tracking-wider">
                          {activeData.metricLabel}
                        </div>
                        <div className="mt-2 text-2xl font-display font-bold text-primary-400">
                          +{activeData.metric}
                        </div>
                      </div>
                    </div>
                  </motion.div>
                </AnimatePresence>

                {/* Compounded progress bar */}
                <div className="mt-6 rounded-xl border border-primary-800/60 bg-gradient-to-r from-primary-500/8 to-terra-500/8 p-4">
                  <div className="flex items-center justify-between mb-2.5">
                    <span className="text-xs text-primary-200/45 uppercase tracking-wider">
                      Compounded growth
                    </span>
                    <span className="text-base font-display font-bold text-cream-100">
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
                  <div className="flex justify-between mt-2 text-xs text-primary-200/30">
                    <span>Start</span>
                    <span>Full loop</span>
                  </div>
                </div>
              </div>
            </div>

            {/* CTA */}
            <div className="mt-8 text-center">
              <Link
                href="/register"
                className="inline-flex items-center gap-2 btn bg-primary-500 text-white hover:bg-primary-600 px-6 py-2.5 text-sm rounded-xl"
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
