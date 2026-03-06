"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { api, Article, Outline } from "@/lib/api";
import { toast } from "sonner";
import {
  Calendar,
  ChevronLeft,
  ChevronRight,
  FileText,
  Sparkles,
  X,
  ExternalLink,
  RefreshCw,
  Plus,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";

// -------------------------------------------------------------------------
// Types
// -------------------------------------------------------------------------

type ContentItemType = "outline" | "article";

interface CalendarItem {
  id: string;
  /** Raw article id (without "article-" prefix), only set for type==="article" */
  articleId?: string;
  type: ContentItemType;
  title: string;
  status: string;
  date: Date;
  href: string;
  /** Whether this item was placed by an explicit planned_date */
  isScheduled: boolean;
}

// -------------------------------------------------------------------------
// Helpers
// -------------------------------------------------------------------------

const WEEKDAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

function toLocalDateKey(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function parseDate(isoString: string): Date {
  // Date-only strings ("2026-03-15") are parsed as UTC by JS, which shifts
  // to the previous day in negative-offset timezones.  Append T00:00:00 so
  // the string is treated as local time instead.
  if (/^\d{4}-\d{2}-\d{2}$/.test(isoString)) {
    return new Date(isoString + "T00:00:00");
  }
  return new Date(isoString);
}

// -------------------------------------------------------------------------
// Pill styling per status
// -------------------------------------------------------------------------

interface PillConfig {
  bg: string;
  text: string;
  dot: string;
  label: string;
}

const OUTLINE_PILL: PillConfig = {
  bg: "bg-blue-100",
  text: "text-blue-800",
  dot: "bg-blue-500",
  label: "Outline",
};

const ARTICLE_STATUS_PILLS: Record<string, PillConfig> = {
  draft: {
    bg: "bg-gray-100",
    text: "text-gray-700",
    dot: "bg-gray-400",
    label: "Draft",
  },
  generating: {
    bg: "bg-yellow-100",
    text: "text-yellow-800",
    dot: "bg-yellow-500",
    label: "Generating",
  },
  completed: {
    bg: "bg-green-100",
    text: "text-green-800",
    dot: "bg-green-500",
    label: "Ready",
  },
  published: {
    bg: "bg-purple-100",
    text: "text-purple-800",
    dot: "bg-purple-500",
    label: "Published",
  },
  failed: {
    bg: "bg-red-100",
    text: "text-red-700",
    dot: "bg-red-500",
    label: "Failed",
  },
};

function getPillConfig(item: CalendarItem): PillConfig {
  if (item.type === "outline") return OUTLINE_PILL;
  return ARTICLE_STATUS_PILLS[item.status] ?? ARTICLE_STATUS_PILLS["draft"];
}

// -------------------------------------------------------------------------
// ContentPill
// -------------------------------------------------------------------------

function ContentPill({ item }: { item: CalendarItem }) {
  const cfg = getPillConfig(item);
  return (
    <Link
      href={item.href}
      className={cn(
        "flex items-center gap-1 text-xs px-2 py-0.5 rounded-full truncate max-w-full",
        "transition-opacity hover:opacity-80",
        cfg.bg,
        cfg.text
      )}
      title={item.title}
    >
      <span className={cn("w-1.5 h-1.5 rounded-full shrink-0", cfg.dot)} />
      <span className="truncate">{item.title}</span>
    </Link>
  );
}

// -------------------------------------------------------------------------
// ScheduleModal — shown when clicking an empty day cell
// -------------------------------------------------------------------------

interface ScheduleModalProps {
  date: Date;
  articles: Article[];
  scheduling: boolean;
  onSchedule: (articleId: string) => void;
  onClose: () => void;
}

function ScheduleModal({
  date,
  articles,
  scheduling,
  onSchedule,
  onClose,
}: ScheduleModalProps) {
  const unscheduled = articles.filter((a) => !a.planned_date);

  const formatDate = (d: Date) =>
    d.toLocaleDateString("en-US", {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
    });

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 z-30 bg-black/20" onClick={onClose} />

      {/* Modal */}
      <div className="fixed inset-0 z-40 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-2xl border border-surface-tertiary w-full max-w-md flex flex-col max-h-[80vh]">
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-surface-tertiary">
            <div>
              <p className="text-xs text-text-secondary uppercase tracking-wide font-semibold">
                Schedule content for
              </p>
              <p className="text-sm font-semibold text-text-primary">
                {formatDate(date)}
              </p>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg hover:bg-surface-secondary transition-colors"
            >
              <X className="h-4 w-4 text-text-secondary" />
            </button>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto px-5 py-4">
            {unscheduled.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-sm text-text-secondary">
                  All your articles already have a planned date.
                </p>
                <Link
                  href="/outlines/new"
                  className="mt-3 inline-block text-sm text-primary-600 hover:underline"
                >
                  Create a new outline
                </Link>
              </div>
            ) : (
              <div className="space-y-2">
                <p className="text-xs text-text-secondary mb-3">
                  Select an article to schedule on this date:
                </p>
                {unscheduled.map((article) => {
                  const cfg =
                    ARTICLE_STATUS_PILLS[article.status] ??
                    ARTICLE_STATUS_PILLS["draft"];
                  return (
                    <button
                      key={article.id}
                      disabled={scheduling}
                      onClick={() => onSchedule(article.id)}
                      className="w-full flex items-start gap-3 p-3 rounded-xl border border-surface-tertiary hover:bg-surface-secondary transition-colors text-left group disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <span
                        className={cn(
                          "mt-1 w-2 h-2 rounded-full shrink-0",
                          cfg.dot
                        )}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-text-primary truncate">
                          {article.title}
                        </p>
                        <p
                          className={cn(
                            "text-xs font-medium mt-0.5",
                            cfg.text
                          )}
                        >
                          {cfg.label}
                        </p>
                      </div>
                      {scheduling ? (
                        <Loader2 className="h-4 w-4 text-text-secondary animate-spin shrink-0 mt-0.5" />
                      ) : (
                        <Plus className="h-4 w-4 text-text-secondary opacity-0 group-hover:opacity-100 transition-opacity shrink-0 mt-0.5" />
                      )}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}

// -------------------------------------------------------------------------
// Day detail panel (slide-in from the right side)
// -------------------------------------------------------------------------

interface DayPanelProps {
  date: Date | null;
  items: CalendarItem[];
  onClose: () => void;
  onRefresh: () => void;
}

function DayPanel({ date, items, onClose, onRefresh }: DayPanelProps) {
  if (!date) return null;

  const outlines = items.filter((i) => i.type === "outline");
  const articles = items.filter((i) => i.type === "article");

  const formatDateLabel = (d: Date) =>
    d.toLocaleDateString("en-US", {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
    });

  const handleUnschedule = async (articleId: string) => {
    try {
      await api.articles.update(articleId, { planned_date: null });
      toast.success("Article unscheduled");
      onClose();
      onRefresh();
    } catch {
      toast.error("Failed to unschedule article");
    }
  };

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 z-30 bg-black/20" onClick={onClose} />

      {/* Panel */}
      <div className="fixed right-0 top-0 bottom-0 z-40 w-full max-w-80 sm:w-80 bg-white shadow-2xl border-l border-surface-tertiary flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-4 border-b border-surface-tertiary">
          <div>
            <p className="text-xs text-text-secondary uppercase tracking-wide font-semibold">
              Content for
            </p>
            <p className="text-sm font-semibold text-text-primary">
              {formatDateLabel(date)}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-surface-secondary transition-colors"
          >
            <X className="h-4 w-4 text-text-secondary" />
          </button>
        </div>

        {/* Content list */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
          {items.length === 0 && (
            <p className="text-sm text-text-secondary text-center py-8">
              No content on this day.
            </p>
          )}

          {outlines.length > 0 && (
            <section>
              <p className="text-xs uppercase tracking-wider font-semibold text-text-secondary mb-2 flex items-center gap-1.5">
                <FileText className="h-3.5 w-3.5" />
                Outlines
              </p>
              <div className="space-y-2">
                {outlines.map((item) => (
                  <PanelItemRow key={item.id} item={item} />
                ))}
              </div>
            </section>
          )}

          {articles.length > 0 && (
            <section>
              <p className="text-xs uppercase tracking-wider font-semibold text-text-secondary mb-2 flex items-center gap-1.5">
                <Sparkles className="h-3.5 w-3.5" />
                Articles
              </p>
              <div className="space-y-2">
                {articles.map((item) => (
                  <PanelItemRow
                    key={item.id}
                    item={item}
                    onUnschedule={
                      item.isScheduled && item.articleId
                        ? () => handleUnschedule(item.articleId!)
                        : undefined
                    }
                  />
                ))}
              </div>
            </section>
          )}
        </div>
      </div>
    </>
  );
}

interface PanelItemRowProps {
  item: CalendarItem;
  onUnschedule?: () => void;
}

function PanelItemRow({ item, onUnschedule }: PanelItemRowProps) {
  const cfg = getPillConfig(item);

  return (
    <div className="flex items-start gap-2">
      <Link
        href={item.href}
        className="flex-1 flex items-start gap-3 p-3 rounded-xl border border-surface-tertiary hover:bg-surface-secondary transition-colors group min-w-0"
      >
        <span className={cn("mt-1 w-2 h-2 rounded-full shrink-0", cfg.dot)} />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-text-primary truncate">
            {item.title}
          </p>
          <p className={cn("text-xs font-medium mt-0.5", cfg.text)}>
            {cfg.label}
            {item.type === "outline" ? " · Outline" : " · Article"}
          </p>
        </div>
        <ExternalLink className="h-3.5 w-3.5 text-text-secondary opacity-0 group-hover:opacity-100 transition-opacity shrink-0 mt-0.5" />
      </Link>

      {onUnschedule && (
        <button
          onClick={onUnschedule}
          title="Unschedule"
          className="p-2 rounded-lg hover:bg-red-50 hover:text-red-600 text-text-secondary transition-colors shrink-0 mt-0.5"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  );
}

// -------------------------------------------------------------------------
// Main page
// -------------------------------------------------------------------------

export default function ContentCalendarPage() {
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth()); // 0-indexed

  const [articles, setArticles] = useState<Article[]>([]);
  const [outlines, setOutlines] = useState<Outline[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Day detail panel state
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);

  // Schedule modal state
  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [scheduleDate, setScheduleDate] = useState<Date | null>(null);
  const [scheduling, setScheduling] = useState(false);

  // -----------------------------------------------------------------------
  // Data loading — paginate through all items (API caps at 100 per page)
  // -----------------------------------------------------------------------
  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const fetchAll = async <T,>(
        fetcher: (params: {
          page: number;
          page_size: number;
        }) => Promise<{ items: T[]; pages: number }>
      ): Promise<T[]> => {
        const first = await fetcher({ page: 1, page_size: 100 });
        if (first.pages <= 1) return first.items;
        const remaining = await Promise.all(
          Array.from({ length: first.pages - 1 }, (_, i) =>
            fetcher({ page: i + 2, page_size: 100 })
          )
        );
        return [...first.items, ...remaining.flatMap((r) => r.items)];
      };

      const [allArticles, allOutlines] = await Promise.all([
        fetchAll(api.articles.list),
        fetchAll(api.outlines.list),
      ]);
      setArticles(allArticles);
      setOutlines(allOutlines);
    } catch {
      setError("Failed to load content. Please try again.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // -----------------------------------------------------------------------
  // Build calendar items from raw data
  // -----------------------------------------------------------------------
  const calendarItems: CalendarItem[] = [
    ...outlines.map(
      (o): CalendarItem => ({
        id: `outline-${o.id}`,
        type: "outline",
        title: o.title || o.keyword,
        status: o.status,
        date: parseDate(o.created_at),
        href: `/outlines/${o.id}`,
        isScheduled: false,
      })
    ),
    ...articles.map(
      (a): CalendarItem => ({
        id: `article-${a.id}`,
        articleId: a.id,
        type: "article",
        title: a.title,
        status: a.status,
        // Priority: planned_date > published_at (for published) > created_at
        date: a.planned_date
          ? parseDate(a.planned_date)
          : a.status === "published" && a.published_at
          ? parseDate(a.published_at)
          : parseDate(a.created_at),
        href: `/articles/${a.id}`,
        isScheduled: !!a.planned_date,
      })
    ),
  ];

  // Group by local date key
  const itemsByDate = new Map<string, CalendarItem[]>();
  for (const item of calendarItems) {
    const key = toLocalDateKey(item.date);
    if (!itemsByDate.has(key)) itemsByDate.set(key, []);
    itemsByDate.get(key)!.push(item);
  }

  // -----------------------------------------------------------------------
  // Calendar grid calculation
  // -----------------------------------------------------------------------
  const firstDay = new Date(year, month, 1);
  const lastDay = new Date(year, month + 1, 0);
  const startPadding = firstDay.getDay(); // 0=Sunday
  const daysInMonth = lastDay.getDate();

  const gridCells: (number | null)[] = [
    ...Array(startPadding).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ];
  while (gridCells.length % 7 !== 0) gridCells.push(null);

  // -----------------------------------------------------------------------
  // Month navigation
  // -----------------------------------------------------------------------
  const goToPrevMonth = () => {
    if (month === 0) {
      setMonth(11);
      setYear((y) => y - 1);
    } else {
      setMonth((m) => m - 1);
    }
    setSelectedDate(null);
  };

  const goToNextMonth = () => {
    if (month === 11) {
      setMonth(0);
      setYear((y) => y + 1);
    } else {
      setMonth((m) => m + 1);
    }
    setSelectedDate(null);
  };

  const goToToday = () => {
    setYear(today.getFullYear());
    setMonth(today.getMonth());
    setSelectedDate(null);
  };

  const isToday = (day: number) =>
    day === today.getDate() &&
    month === today.getMonth() &&
    year === today.getFullYear();

  const isWeekend = (colIndex: number) => colIndex === 0 || colIndex === 6;

  // -----------------------------------------------------------------------
  // Day click handler
  // -----------------------------------------------------------------------
  const handleDayClick = (day: number) => {
    const clicked = new Date(year, month, day);
    const key = toLocalDateKey(clicked);
    const items = itemsByDate.get(key) ?? [];

    if (items.length > 0) {
      // Show day panel for days with content
      setSelectedDate(clicked);
    } else {
      // Show schedule modal for empty days
      setScheduleDate(clicked);
      setShowScheduleModal(true);
    }
  };

  // -----------------------------------------------------------------------
  // Schedule an article to a date
  // -----------------------------------------------------------------------
  const handleSchedule = async (articleId: string) => {
    if (!scheduleDate) return;
    setScheduling(true);
    try {
      await api.articles.update(articleId, {
        planned_date: toLocalDateKey(scheduleDate),
      });
      toast.success("Article scheduled");
      setShowScheduleModal(false);
      setScheduleDate(null);
      loadData();
    } catch {
      toast.error("Failed to schedule article");
    } finally {
      setScheduling(false);
    }
  };

  // Items for the detail panel
  const panelItems = selectedDate
    ? (itemsByDate.get(toLocalDateKey(selectedDate)) ?? [])
    : [];

  // -----------------------------------------------------------------------
  // Legend definition
  // -----------------------------------------------------------------------
  const legendItems = [
    { dot: "bg-blue-500", label: "Outline" },
    { dot: "bg-gray-400", label: "Article — Draft" },
    { dot: "bg-yellow-500", label: "Article — Generating" },
    { dot: "bg-green-500", label: "Article — Ready" },
    { dot: "bg-purple-500", label: "Article — Published" },
    { dot: "bg-red-500", label: "Article — Failed" },
  ];

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------
  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      {/* Page header */}
      <div className="mb-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-1">
          <div>
            <h1 className="font-bold flex items-center gap-3">
              <Calendar className="h-6 w-6 sm:h-8 sm:w-8 text-primary-500" />
              Content Calendar
            </h1>
            <p className="text-text-secondary mt-1">
              Track your content pipeline — from outline to published article.
              Click an empty day to schedule content.
            </p>
          </div>
          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 rounded-xl border border-surface-tertiary text-sm font-medium text-text-secondary hover:bg-surface-secondary transition-colors disabled:opacity-50"
          >
            <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
            Refresh
          </button>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="mb-4 px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Calendar card */}
      <div className="card overflow-hidden">
        {/* Month navigation header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-surface-tertiary">
          <button
            onClick={goToPrevMonth}
            className="p-2 rounded-lg hover:bg-surface-secondary transition-colors"
            aria-label="Previous month"
          >
            <ChevronLeft className="h-5 w-5 text-text-secondary" />
          </button>

          <div className="flex items-center gap-4">
            <h2 className="text-lg font-semibold text-text-primary">
              {MONTH_NAMES[month]} {year}
            </h2>
            <button
              onClick={goToToday}
              className="px-3 py-1 text-xs font-medium rounded-lg bg-primary-50 text-primary-700 hover:bg-primary-100 transition-colors border border-primary-200"
            >
              Today
            </button>
          </div>

          <button
            onClick={goToNextMonth}
            className="p-2 rounded-lg hover:bg-surface-secondary transition-colors"
            aria-label="Next month"
          >
            <ChevronRight className="h-5 w-5 text-text-secondary" />
          </button>
        </div>

        {/* Loading skeleton */}
        {loading && (
          <div className="flex items-center justify-center h-96">
            <div className="text-center">
              <div className="w-10 h-10 border-4 border-primary-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
              <p className="text-sm text-text-secondary">Loading calendar...</p>
            </div>
          </div>
        )}

        {/* Grid */}
        {!loading && (
          <div className="overflow-x-auto">
            {/* Weekday header row */}
            <div className="grid grid-cols-7 border-b border-surface-tertiary min-w-[500px]">
              {WEEKDAY_LABELS.map((label, i) => (
                <div
                  key={label}
                  className={cn(
                    "py-2 text-center text-xs font-semibold uppercase tracking-wide",
                    isWeekend(i) ? "text-text-secondary/60" : "text-text-secondary"
                  )}
                >
                  {label}
                </div>
              ))}
            </div>

            {/* Day cells */}
            <div className="grid grid-cols-7 min-w-[500px]">
              {gridCells.map((day, cellIdx) => {
                const colIdx = cellIdx % 7;
                const key =
                  day !== null
                    ? toLocalDateKey(new Date(year, month, day))
                    : `empty-${cellIdx}`;
                const dayItems = day !== null ? (itemsByDate.get(key) ?? []) : [];
                const visibleItems = dayItems.slice(0, 3);
                const overflow = dayItems.length - visibleItems.length;
                const today_ = day !== null && isToday(day);
                const weekend = isWeekend(colIdx);
                const isLastRow = cellIdx >= gridCells.length - 7;
                const isLastCol = colIdx === 6;
                const hasItems = dayItems.length > 0;

                return (
                  <div
                    key={`${cellIdx}-${day}`}
                    onClick={() => day !== null && handleDayClick(day)}
                    className={cn(
                      "min-h-[80px] md:min-h-[110px] p-1 md:p-1.5 border-b border-r border-surface-tertiary flex flex-col gap-1",
                      isLastRow && "border-b-0",
                      isLastCol && "border-r-0",
                      today_ && "bg-primary-50 border-primary-200",
                      weekend && !today_ && "bg-surface-secondary/50",
                      day !== null &&
                        "cursor-pointer hover:bg-surface-secondary/70 transition-colors",
                      day === null && "bg-surface-secondary/20"
                    )}
                  >
                    {day !== null && (
                      <>
                        {/* Day number */}
                        <div className="flex items-center justify-between">
                          <span
                            className={cn(
                              "text-xs font-medium w-6 h-6 flex items-center justify-center rounded-full",
                              today_
                                ? "bg-primary-600 text-white font-bold"
                                : "text-text-secondary"
                            )}
                          >
                            {day}
                          </span>
                          {/* Show + hint on empty days (desktop only) */}
                          {!hasItems && (
                            <Plus className="h-3 w-3 text-text-secondary/40 hidden md:block" />
                          )}
                        </div>

                        {/* Content pills */}
                        <div className="flex flex-col gap-0.5 min-w-0">
                          {visibleItems.map((item) => (
                            <ContentPill key={item.id} item={item} />
                          ))}
                          {overflow > 0 && (
                            <span className="text-xs text-text-secondary px-1.5 font-medium">
                              +{overflow} more
                            </span>
                          )}
                        </div>
                      </>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="mt-5 flex flex-wrap items-center justify-center gap-x-5 gap-y-2">
        {legendItems.map(({ dot, label }) => (
          <div
            key={label}
            className="flex items-center gap-1.5 text-sm text-text-secondary"
          >
            <span className={cn("w-2.5 h-2.5 rounded-full", dot)} />
            {label}
          </div>
        ))}
      </div>

      {/* Day detail panel */}
      <DayPanel
        date={selectedDate}
        items={panelItems}
        onClose={() => setSelectedDate(null)}
        onRefresh={loadData}
      />

      {/* Schedule modal */}
      {showScheduleModal && scheduleDate && (
        <ScheduleModal
          date={scheduleDate}
          articles={articles}
          scheduling={scheduling}
          onSchedule={handleSchedule}
          onClose={() => {
            setShowScheduleModal(false);
            setScheduleDate(null);
          }}
        />
      )}
    </div>
  );
}
