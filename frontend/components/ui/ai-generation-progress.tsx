"use client";

import { useState, useEffect, useRef } from "react";
import { Check, Feather, Sparkles, Search, PenTool, FileCheck, Wand2, Eye, Palette, ImageIcon, BookOpen } from "lucide-react";
import { clsx } from "clsx";

type GenerationType = "article" | "outline" | "image";

interface Phase {
  label: string;
  icon: React.ElementType;
  duration: number; // seconds before auto-advancing
}

const PHASES: Record<GenerationType, Phase[]> = {
  article: [
    { label: "Analyzing your outline", icon: Search, duration: 8 },
    { label: "Researching topic & keywords", icon: BookOpen, duration: 12 },
    { label: "Writing introduction & structure", icon: PenTool, duration: 25 },
    { label: "Generating section content", icon: Feather, duration: 35 },
    { label: "Polishing & optimizing for SEO", icon: Sparkles, duration: 25 },
    { label: "Finalizing article", icon: FileCheck, duration: 999 },
  ],
  outline: [
    { label: "Analyzing keyword intent", icon: Search, duration: 5 },
    { label: "Researching topic depth", icon: BookOpen, duration: 8 },
    { label: "Structuring sections", icon: PenTool, duration: 10 },
    { label: "Optimizing flow & readability", icon: Sparkles, duration: 8 },
    { label: "Finalizing outline", icon: FileCheck, duration: 999 },
  ],
  image: [
    { label: "Analyzing your prompt", icon: Eye, duration: 5 },
    { label: "Composing scene & elements", icon: Palette, duration: 10 },
    { label: "Generating image", icon: ImageIcon, duration: 20 },
    { label: "Enhancing quality & details", icon: Wand2, duration: 15 },
    { label: "Finalizing image", icon: FileCheck, duration: 999 },
  ],
};

const TIPS: Record<GenerationType, string[]> = {
  article: [
    "AI-generated articles typically take 60\u201390 seconds",
    "The article will follow your outline structure exactly",
    "You can edit and refine the content after generation",
    "SEO keywords are woven in naturally throughout",
  ],
  outline: [
    "Outlines usually generate in 15\u201330 seconds",
    "Each section is optimized for reader engagement",
    "You can regenerate individual sections later",
  ],
  image: [
    "Image generation typically takes 30\u201360 seconds",
    "More descriptive prompts produce better results",
    "You can regenerate with different styles",
  ],
};

interface AIGenerationProgressProps {
  type: GenerationType;
  title?: string;
  keyword?: string;
  isGenerating: boolean;
}

export function AIGenerationProgress({
  type,
  title,
  keyword,
  isGenerating,
}: AIGenerationProgressProps) {
  const phases = PHASES[type];
  const tips = TIPS[type];
  const [currentPhase, setCurrentPhase] = useState(0);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [currentTip, setCurrentTip] = useState(0);
  const startTimeRef = useRef<number>(Date.now());
  const phaseTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Reset on new generation
  useEffect(() => {
    if (isGenerating) {
      setCurrentPhase(0);
      setElapsedSeconds(0);
      setCurrentTip(0);
      startTimeRef.current = Date.now();
    }
  }, [isGenerating]);

  // Elapsed time counter
  useEffect(() => {
    if (!isGenerating) return;

    const interval = setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - startTimeRef.current) / 1000));
    }, 1000);

    return () => clearInterval(interval);
  }, [isGenerating]);

  // Phase auto-advancement
  useEffect(() => {
    if (!isGenerating) return;

    const advancePhase = () => {
      setCurrentPhase((prev) => {
        const next = prev + 1;
        if (next >= phases.length) return prev; // Stay on last phase

        // Schedule next advancement
        phaseTimerRef.current = setTimeout(advancePhase, phases[next].duration * 1000);
        return next;
      });
    };

    phaseTimerRef.current = setTimeout(advancePhase, phases[0].duration * 1000);

    return () => {
      if (phaseTimerRef.current) clearTimeout(phaseTimerRef.current);
    };
  }, [isGenerating, phases]);

  // Tip rotation
  useEffect(() => {
    if (!isGenerating || tips.length <= 1) return;

    const interval = setInterval(() => {
      setCurrentTip((prev) => (prev + 1) % tips.length);
    }, 6000);

    return () => clearInterval(interval);
  }, [isGenerating, tips]);

  if (!isGenerating) return <div className="hidden" aria-hidden="true" />;

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <div className="space-y-6 py-2">
      {/* Header with animated icon */}
      <div className="flex flex-col items-center text-center">
        <div className="relative mb-4">
          <div className="h-16 w-16 rounded-2xl bg-primary-100 flex items-center justify-center">
            <Feather className="h-8 w-8 text-primary-600 animate-writing" />
          </div>
          <div className="absolute -top-1 -right-1 h-5 w-5 rounded-full bg-primary-500 flex items-center justify-center">
            <Sparkles className="h-3 w-3 text-white animate-pulse" />
          </div>
        </div>

        <h3 className="text-lg font-display font-semibold text-text-primary">
          {type === "article" && "Writing Your Article"}
          {type === "outline" && "Crafting Your Outline"}
          {type === "image" && "Creating Your Image"}
        </h3>
        {(title || keyword) && (
          <p className="text-sm text-text-secondary mt-1 max-w-sm">
            {title ? `"${title}"` : keyword ? `For: ${keyword}` : ""}
          </p>
        )}
      </div>

      {/* Phase stepper */}
      <div className="space-y-1">
        {phases.map((phase, index) => {
          const PhaseIcon = phase.icon;
          const isCompleted = index < currentPhase;
          const isCurrent = index === currentPhase;
          const isPending = index > currentPhase;

          return (
            <div
              key={phase.label}
              className={clsx(
                "flex items-center gap-3 px-4 py-2.5 rounded-xl transition-all duration-500",
                isCurrent && "bg-primary-50 border border-primary-200",
                isCompleted && "opacity-60",
                isPending && "opacity-30"
              )}
            >
              {/* Status icon */}
              <div
                className={clsx(
                  "h-8 w-8 rounded-lg flex items-center justify-center shrink-0 transition-all duration-500",
                  isCompleted && "bg-primary-500",
                  isCurrent && "bg-primary-100",
                  isPending && "bg-surface-secondary"
                )}
              >
                {isCompleted ? (
                  <Check className="h-4 w-4 text-white" />
                ) : (
                  <PhaseIcon
                    className={clsx(
                      "h-4 w-4 transition-all",
                      isCurrent
                        ? "text-primary-600 animate-pulse"
                        : "text-text-muted"
                    )}
                  />
                )}
              </div>

              {/* Label */}
              <span
                className={clsx(
                  "text-sm font-medium transition-colors duration-500",
                  isCurrent && "text-primary-700",
                  isCompleted && "text-text-secondary line-through decoration-primary-300",
                  isPending && "text-text-muted"
                )}
              >
                {phase.label}
              </span>

              {/* Current phase indicator */}
              {isCurrent && (
                <div className="ml-auto flex items-center gap-1.5">
                  <span className="relative flex h-2.5 w-2.5">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary-400 opacity-75" />
                    <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-primary-500" />
                  </span>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Bottom section: elapsed time + rotating tip */}
      <div className="pt-2 border-t border-surface-tertiary">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-medium text-text-muted">
            Elapsed: {formatTime(elapsedSeconds)}
          </span>
          <span className="text-xs text-text-muted">
            Step {currentPhase + 1} of {phases.length}
          </span>
        </div>

        {/* Rotating tip */}
        <div className="flex items-start gap-2 px-3 py-2.5 bg-surface-secondary rounded-lg min-h-[2.75rem]">
          <Sparkles className="h-3.5 w-3.5 text-primary-400 mt-0.5 shrink-0" />
          <p
            key={currentTip}
            className="text-xs text-text-secondary animate-fade-in"
          >
            {tips[currentTip]}
          </p>
        </div>
      </div>
    </div>
  );
}
