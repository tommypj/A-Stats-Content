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
import { useTranslations } from "next-intl";

const STEP_ICONS = [Search, FileText, BarChart3, Globe, Share2, Sparkles];

export default function ScrollWorkflow() {
  const t = useTranslations("landing.howItWorks");
  const [activeStep, setActiveStep] = useState(0);
  const ActiveIcon = STEP_ICONS[activeStep];

  const totalSteps = STEP_ICONS.length;

  const goNext = () =>
    setActiveStep((s) => Math.min(s + 1, totalSteps - 1));
  const goPrev = () => setActiveStep((s) => Math.max(s - 1, 0));

  const stepKey = (i: number, field: string) =>
    `step${i + 1}${field}` as Parameters<typeof t>[0];

  return (
    <section id="how-it-works" className="bg-primary-950 py-20 lg:py-28 overflow-hidden">
      <div className="page-container">
        {/* Header */}
        <div className="text-center mb-12 lg:mb-16">
          <div className="inline-flex items-center gap-2 rounded-full border border-primary-700/50 bg-primary-800/60 px-4 py-1.5 text-sm text-primary-300 mb-5">
            <Sparkles className="h-4 w-4" />
            {t("badge")}
          </div>
          <h2 className="text-3xl md:text-4xl font-display font-bold leading-tight text-cream-100">
            {t("title")}{" "}
            <span className="bg-gradient-to-r from-primary-400 to-terra-400 bg-clip-text text-transparent">
              {t("titleHighlight")}
            </span>
          </h2>
          <p className="mt-4 max-w-2xl mx-auto text-base text-primary-200/60 leading-relaxed">
            {t("description")}
          </p>
        </div>

        {/* Main content */}
        <div className="grid lg:grid-cols-[1fr_1.15fr] gap-8 lg:gap-12 items-start min-w-0">
          {/* Left — step selector */}
          <div className="relative min-w-0">
            {/* Progress line (desktop) */}
            <div className="absolute left-[15px] top-0 bottom-0 w-px bg-primary-800/60 hidden lg:block">
              <motion.div
                className="w-px bg-gradient-to-b from-primary-400 via-primary-500 to-terra-400"
                animate={{
                  height: `${((activeStep + 1) / totalSteps) * 100}%`,
                }}
                transition={{ duration: 0.4, ease: "easeOut" }}
              />
            </div>

            <div className="space-y-2 lg:pl-10">
              {STEP_ICONS.map((Icon, i) => {
                const isActive = i === activeStep;
                const isPast = i < activeStep;

                return (
                  <button
                    key={i}
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
                      <div className="min-w-0 flex-1 overflow-hidden">
                        <div
                          className={`text-sm font-display font-semibold transition-colors duration-300 truncate ${
                            isActive
                              ? "text-cream-100"
                              : "text-cream-100/60"
                          }`}
                        >
                          {t(stepKey(i, "Title"))}
                        </div>
                        <div
                          className={`text-xs transition-colors duration-300 truncate ${
                            isActive
                              ? "text-primary-200/60"
                              : "text-primary-200/30"
                          }`}
                        >
                          {t(stepKey(i, "Desc"))}
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
          <div className="min-w-0">
            <div className="relative rounded-2xl border border-primary-800/60 bg-primary-900/95 shadow-[0_16px_60px_rgba(23,28,23,0.4)] overflow-hidden min-w-0">
              <div className="p-5 sm:p-8">
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
                      {t("stepOf", { current: activeStep + 1, total: totalSteps })}
                    </span>
                    <button
                      onClick={goNext}
                      disabled={activeStep === totalSteps - 1}
                      className="h-8 w-8 rounded-lg border border-primary-800/60 flex items-center justify-center text-primary-300 hover:bg-primary-800/60 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                      <ChevronRight className="h-4 w-4" />
                    </button>
                  </div>
                  <div className="rounded-full border border-green-500/20 bg-green-500/10 px-3 py-1 text-xs font-medium text-green-400">
                    {t("liveSimulation")}
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
                          {t(stepKey(activeStep, "Title"))}
                        </h3>
                        <p className="text-sm text-primary-300/70 mt-1">
                          {t(stepKey(activeStep, "Desc"))}
                        </p>
                      </div>
                    </div>

                    {/* Detail text */}
                    <p className="text-sm text-primary-200/65 leading-relaxed mb-6">
                      {t(stepKey(activeStep, "Detail"))}
                    </p>

                    {/* Impact metrics */}
                    <div className="grid grid-cols-2 gap-4">
                      <div className="rounded-xl border border-primary-800/60 bg-primary-950/60 p-4">
                        <div className="text-xs text-primary-200/45 uppercase tracking-wider">
                          {t("impactLabel")}
                        </div>
                        <div className="mt-2 text-2xl font-display font-bold text-cream-100">
                          {t(stepKey(activeStep, "Impact"))}
                        </div>
                      </div>
                      <div className="rounded-xl border border-primary-800/60 bg-primary-950/60 p-4">
                        <div className="text-xs text-primary-200/45 uppercase tracking-wider">
                          {t(stepKey(activeStep, "MetricLabel"))}
                        </div>
                        <div className="mt-2 text-2xl font-display font-bold text-primary-400">
                          +{t(stepKey(activeStep, "Metric"))}
                        </div>
                      </div>
                    </div>
                  </motion.div>
                </AnimatePresence>

                {/* Compounded progress bar */}
                <div className="mt-6 rounded-xl border border-primary-800/60 bg-gradient-to-r from-primary-500/8 to-terra-500/8 p-4">
                  <div className="flex items-center justify-between mb-2.5">
                    <span className="text-xs text-primary-200/45 uppercase tracking-wider">
                      {t("compoundedGrowth")}
                    </span>
                    <span className="text-base font-display font-bold text-cream-100">
                      +{t(stepKey(activeStep, "Metric"))}
                    </span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-primary-800 overflow-hidden">
                    <motion.div
                      className="h-full rounded-full bg-gradient-to-r from-primary-500 to-terra-400"
                      animate={{
                        width: `${((activeStep + 1) / totalSteps) * 100}%`,
                      }}
                      transition={{ duration: 0.4, ease: "easeOut" }}
                    />
                  </div>
                  <div className="flex justify-between mt-2 text-xs text-primary-200/30">
                    <span>{t("progressStart")}</span>
                    <span>{t("progressEnd")}</span>
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
                {t("cta")}
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
