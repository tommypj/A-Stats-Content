"use client";

import { useRef, useState, useEffect } from "react";
import {
  motion,
  useScroll,
  useSpring,
  useTransform,
  useMotionValueEvent,
} from "framer-motion";
import {
  Search,
  FileText,
  BarChart3,
  Globe,
  Share2,
  Sparkles,
} from "lucide-react";

const workflowSteps = [
  {
    icon: Search,
    title: "Keyword opportunity detected",
    desc: "Ranking + AI visibility potential automatically found.",
    impact: "+320 search volume",
    detail:
      "High-intent topic discovered with strong SERP gap and AI-answer potential.",
  },
  {
    icon: FileText,
    title: "Article generated",
    desc: "Full SEO structure + topical authority created.",
    impact: "SEO score 91",
    detail:
      "Outline, headings, entity coverage, and expert-style structure generated in minutes.",
  },
  {
    icon: BarChart3,
    title: "Optimization applied",
    desc: "Semantic coverage + gaps improved.",
    impact: "+18 score boost",
    detail:
      "On-page gaps closed, internal linking opportunities suggested, and structure improved.",
  },
  {
    icon: Globe,
    title: "Published to WordPress",
    desc: "Live instantly with schema + metadata.",
    impact: "Live in 12s",
    detail:
      "Content shipped to production with metadata and publish-ready formatting.",
  },
  {
    icon: Share2,
    title: "Distribution triggered",
    desc: "Social + refresh cycles scheduled.",
    impact: "4 channels scheduled",
    detail:
      "Promotion kicks in automatically so the page earns attention after publish.",
  },
  {
    icon: Sparkles,
    title: "AI citation detected",
    desc: "Answer engines start referencing content.",
    impact: "+3 new citations",
    detail:
      "Visibility compounds as the article gets picked up in AI-generated answers.",
  },
];

function useProgressTransform(
  progress: ReturnType<typeof useSpring>,
  index: number,
  total: number
) {
  const start = index / total;
  const peak = Math.min(start + 0.12, (index + 1) / total);
  const end = (index + 1) / total;

  const opacity = useTransform(progress, [start, peak, end], [0.3, 1, 0.45]);
  const scale = useTransform(progress, [start, peak, end], [0.98, 1.03, 1]);
  const y = useTransform(progress, [start, end], [12, 0]);

  return { opacity, scale, y };
}

function useCardTransform(
  progress: ReturnType<typeof useSpring>,
  index: number,
  total: number
) {
  const start = index / total;
  const peak = Math.min(start + 0.12, (index + 1) / total);
  const end = (index + 1) / total;

  const opacity = useTransform(progress, [start, peak, end], [0.2, 1, 0.25]);
  const scale = useTransform(progress, [start, peak, end], [0.94, 1, 0.96]);

  return { opacity, scale };
}

function WorkflowStep({
  step,
  index,
  progress,
}: {
  step: (typeof workflowSteps)[0];
  index: number;
  progress: ReturnType<typeof useSpring>;
}) {
  const { opacity, scale, y } = useProgressTransform(
    progress,
    index,
    workflowSteps.length
  );
  const Icon = step.icon;

  return (
    <motion.div
      style={{ opacity, scale, y }}
      className="relative rounded-2xl border border-primary-800/60 bg-primary-900 p-6 backdrop-blur"
    >
      <div className="absolute -left-[37px] top-7 hidden h-3 w-3 rounded-full border-2 border-primary-400/40 bg-primary-950 lg:block" />
      <div className="flex items-center gap-3 mb-2">
        <div className="h-8 w-8 rounded-lg bg-primary-800 flex items-center justify-center flex-shrink-0">
          <Icon className="h-4 w-4 text-primary-300" />
        </div>
        <span className="text-xs font-medium text-primary-400 uppercase tracking-wider">
          Step {String(index + 1).padStart(2, "0")}
        </span>
      </div>
      <div className="mt-1 text-lg font-display font-semibold text-cream-100">
        {step.title}
      </div>
      <div className="mt-1.5 text-sm text-primary-200/60">{step.desc}</div>
    </motion.div>
  );
}

function ImpactCard({
  step,
  index,
  progress,
}: {
  step: (typeof workflowSteps)[0];
  index: number;
  progress: ReturnType<typeof useSpring>;
}) {
  const { opacity, scale } = useCardTransform(
    progress,
    index,
    workflowSteps.length
  );

  return (
    <motion.div
      style={{ opacity, scale }}
      className="rounded-2xl border border-primary-800/60 bg-primary-900 p-5"
    >
      <div className="text-xs text-primary-200/50 uppercase tracking-wider">
        Signal {String(index + 1).padStart(2, "0")}
      </div>
      <div className="mt-2 text-lg font-display font-semibold text-cream-100">
        {step.impact}
      </div>
      <div className="mt-2 text-sm text-primary-200/55">{step.detail}</div>
    </motion.div>
  );
}

export default function ScrollWorkflow() {
  const sectionRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ["start start", "end end"],
  });
  const progress = useSpring(scrollYProgress, {
    stiffness: 90,
    damping: 20,
    mass: 0.2,
  });

  const panelY = useTransform(progress, [0, 1], [80, -80]);
  const panelScale = useTransform(progress, [0, 0.5, 1], [0.96, 1.02, 1.04]);
  const progressHeight = useTransform(progress, [0, 1], ["0%", "100%"]);
  const panelOpacity = useTransform(progress, [0, 0.15, 1], [0.5, 1, 1]);
  const glowOpacity = useTransform(progress, [0, 0.15], [0, 1]);

  // Track active step for the compounded outcome counter
  const [activeStep, setActiveStep] = useState(0);
  useMotionValueEvent(progress, "change", (v) => {
    const step = Math.min(
      Math.floor(v * workflowSteps.length),
      workflowSteps.length - 1
    );
    setActiveStep(step);
  });

  const compoundedPercentages = [24, 48, 72, 96, 128, 148];

  return (
    <section
      ref={sectionRef}
      id="how-it-works"
      className="relative h-[500vh] bg-primary-950"
    >
      <div className="sticky top-0 h-screen overflow-hidden">
        {/* Subtle background glow */}
        <motion.div
          style={{ opacity: glowOpacity }}
          className="absolute inset-0 bg-[radial-gradient(circle_at_50%_35%,rgba(98,120,98,0.15),transparent_40%)]"
        />

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-full grid lg:grid-cols-[0.95fr_1.05fr] gap-12 lg:gap-20 items-center">
          {/* Left side — steps */}
          <div className="relative py-12 lg:py-16">
            <div className="mb-8">
              <div className="inline-flex items-center gap-2 rounded-full border border-primary-700/50 bg-primary-800/60 px-4 py-1.5 text-sm text-primary-300">
                <Sparkles className="h-4 w-4" />
                How It Works
              </div>
              <h2 className="mt-5 text-3xl md:text-4xl lg:text-5xl font-display font-bold leading-tight text-cream-100">
                From keyword to{" "}
                <span className="bg-gradient-to-r from-primary-400 to-terra-400 bg-clip-text text-transparent">
                  published article
                </span>
              </h2>
              <p className="mt-4 max-w-xl text-base lg:text-lg text-primary-200/60">
                Each step reveals how A-Stats turns one opportunity into a full
                growth loop — writing, optimization, publishing, distribution,
                and AI-answer pickup.
              </p>
            </div>

            {/* Progress line */}
            <div className="absolute left-0 top-[220px] hidden h-[480px] w-px bg-primary-800/60 lg:block">
              <motion.div
                style={{ height: progressHeight }}
                className="w-px bg-gradient-to-b from-primary-400 via-primary-500 to-terra-400"
              />
            </div>

            {/* Steps */}
            <div className="space-y-4 lg:pl-8">
              {workflowSteps.map((step, i) => (
                <WorkflowStep
                  key={step.title}
                  step={step}
                  index={i}
                  progress={progress}
                />
              ))}
            </div>
          </div>

          {/* Right side — impact panel */}
          <motion.div
            style={{ y: panelY, scale: panelScale }}
            className="relative py-12 lg:py-16 hidden lg:block"
          >
            <motion.div
              style={{ opacity: panelOpacity }}
              className="absolute -inset-8 rounded-[32px] bg-primary-500/8 blur-3xl"
            />
            <div className="relative rounded-2xl border border-primary-800/60 bg-primary-900/95 shadow-[0_20px_80px_rgba(23,28,23,0.5)] overflow-hidden">
              <div className="p-8 md:p-10">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <div className="text-sm font-medium text-primary-400">
                      Live workflow impact
                    </div>
                    <div className="mt-1.5 text-2xl font-display font-bold text-cream-100">
                      Execution engine in motion
                    </div>
                  </div>
                  <div className="rounded-full border border-green-500/20 bg-green-500/10 px-3 py-1.5 text-xs font-medium text-green-400 flex-shrink-0">
                    Live simulation
                  </div>
                </div>

                <div className="mt-7 grid gap-4 md:grid-cols-2">
                  {workflowSteps.map((step, i) => (
                    <ImpactCard
                      key={step.title}
                      step={step}
                      index={i}
                      progress={progress}
                    />
                  ))}
                </div>

                {/* Compounded outcome */}
                <div className="mt-7 rounded-2xl border border-primary-800/60 bg-gradient-to-br from-primary-500/10 to-terra-500/10 p-6">
                  <div className="text-xs text-primary-200/50 uppercase tracking-wider">
                    Compounded outcome
                  </div>
                  <div className="mt-2 text-5xl font-display font-bold text-cream-100">
                    +{compoundedPercentages[activeStep]}%
                  </div>
                  <div className="mt-2 max-w-lg text-sm text-primary-200/55">
                    When the whole workflow is connected, content keeps working
                    through optimization, distribution, and AI visibility.
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
