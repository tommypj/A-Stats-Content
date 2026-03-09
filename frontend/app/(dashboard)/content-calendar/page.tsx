"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import Link from "next/link";
import { api, Article } from "@/lib/api";
import { toast } from "sonner";
import {
  Calendar,
  ChevronLeft,
  ChevronRight,
  X,
  ExternalLink,
  RefreshCw,
  Plus,
  Loader2,
  Clock,
  Globe,
  AlertTriangle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { TierGate } from "@/components/ui/tier-gate";

// -------------------------------------------------------------------------
// Types
// -------------------------------------------------------------------------

interface CalendarItem {
  id: string;
  articleId: string;
  title: string;
  status: string;
  date: Date;
  href: string;
  isScheduled: boolean;
  autoPublish: boolean;
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
  // to the previous day in negative-offset timezones. Append T00:00:00 so
  // the string is treated as local time instead.
  if (/^\d{4}-\d{2}-\d{2}$/.test(isoString)) {
    return new Date(isoString + "T00:00:00");
  }
  return new Date(isoString);
}

function formatDateLabel(d: Date) {
  return d.toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });
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

const STATUS_PILLS: Record<string, PillConfig> = {
  draft: { bg: "bg-surface-tertiary", text: "text-text-secondary", dot: "bg-text-muted", label: "Draft" },
  generating: { bg: "bg-yellow-100", text: "text-yellow-800", dot: "bg-yellow-500", label: "Generating" },
  completed: { bg: "bg-green-100", text: "text-green-800", dot: "bg-green-500", label: "Ready" },
  published: { bg: "bg-purple-100", text: "text-purple-800", dot: "bg-purple-500", label: "Published" },
  failed: { bg: "bg-red-100", text: "text-red-700", dot: "bg-red-500", label: "Failed" },
};

function getPillConfig(status: string): PillConfig {
  return STATUS_PILLS[status] ?? STATUS_PILLS["draft"];
}

// -------------------------------------------------------------------------
// ContentPill — small pill shown in calendar cell
// -------------------------------------------------------------------------

function ContentPill({ item }: { item: CalendarItem }) {
  const cfg = getPillConfig(item.status);
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
      onClick={(e) => e.stopPropagation()}
    >
      <span className={cn("w-1.5 h-1.5 rounded-full shrink-0", cfg.dot)} />
      <span className="truncate">{item.title}</span>
      {item.autoPublish && item.isScheduled && (
        <Globe className="h-2.5 w-2.5 shrink-0 opacity-70" />
      )}
    </Link>
  );
}

// -------------------------------------------------------------------------
// ScheduleModal
// -------------------------------------------------------------------------

interface ScheduleModalProps {
  date: Date;
  articles: Article[];
  existingCount: number;
  scheduling: boolean;
  onSchedule: (articleId: string, hour: number, minute: number, autoPublish: boolean) => void;
  onClose: () => void;
}

function ScheduleModal({
  date,
  articles,
  existingCount,
  scheduling,
  onSchedule,
  onClose,
}: ScheduleModalProps) {
  const [hour, setHour] = useState(9);
  const [minute, setMinute] = useState(0);
  const [autoPublish, setAutoPublish] = useState(false);

  // Only show completed articles without a planned_date
  const schedulable = articles.filter(
    (a) => a.status === "completed" && !a.planned_date
  );

  return (
    <>
      <div className="fixed inset-0 z-50 bg-black/20" onClick={onClose} />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-surface rounded-2xl shadow-2xl border border-surface-tertiary w-full max-w-md flex flex-col max-h-[80vh]">
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-surface-tertiary">
            <div>
              <p className="text-xs text-text-secondary uppercase tracking-wide font-semibold">
                Schedule content for
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

          {/* Body */}
          <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
            {/* Warning if day already has content */}
            {existingCount > 0 && (
              <div className="flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-xl">
                <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
                <p className="text-xs text-amber-800">
                  This day already has {existingCount} scheduled article{existingCount > 1 ? "s" : ""}.
                  Publishing multiple articles on the same day may cause keyword cannibalization.
                </p>
              </div>
            )}

            {/* Time picker */}
            <div>
              <label className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-2 flex items-center gap-1.5">
                <Clock className="h-3.5 w-3.5" />
                Publish time
              </label>
              <div className="flex items-center gap-2 mt-1">
                <select
                  value={hour}
                  onChange={(e) => setHour(Number(e.target.value))}
                  className="px-3 py-2 rounded-lg border border-surface-tertiary text-sm bg-surface"
                >
                  {Array.from({ length: 24 }, (_, i) => (
                    <option key={i} value={i}>
                      {String(i).padStart(2, "0")}
                    </option>
                  ))}
                </select>
                <span className="text-text-secondary font-medium">:</span>
                <select
                  value={minute}
                  onChange={(e) => setMinute(Number(e.target.value))}
                  className="px-3 py-2 rounded-lg border border-surface-tertiary text-sm bg-surface"
                >
                  {[0, 15, 30, 45].map((m) => (
                    <option key={m} value={m}>
                      {String(m).padStart(2, "0")}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Auto-publish toggle */}
            <label className="flex items-center gap-3 p-3 rounded-xl border border-surface-tertiary cursor-pointer hover:bg-surface-secondary transition-colors">
              <input
                type="checkbox"
                checked={autoPublish}
                onChange={(e) => setAutoPublish(e.target.checked)}
                className="h-4 w-4 rounded border-surface-tertiary text-primary-600 focus:ring-primary-500"
              />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-text-primary flex items-center gap-1.5">
                  <Globe className="h-3.5 w-3.5" />
                  Auto-publish to WordPress
                </p>
                <p className="text-xs text-text-secondary mt-0.5">
                  Automatically push to WordPress when the scheduled time arrives
                </p>
              </div>
            </label>

            {/* Article list */}
            {schedulable.length === 0 ? (
              <div className="text-center py-6">
                <p className="text-sm text-text-secondary">
                  No completed articles available to schedule.
                </p>
                <p className="text-xs text-text-secondary mt-1">
                  Only articles with status &quot;Ready&quot; can be scheduled.
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
                <p className="text-xs font-semibold text-text-secondary uppercase tracking-wide">
                  Select an article ({schedulable.length} available)
                </p>
                {schedulable.map((article) => {
                  const cfg = getPillConfig(article.status);
                  return (
                    <button
                      key={article.id}
                      disabled={scheduling}
                      onClick={() => onSchedule(article.id, hour, minute, autoPublish)}
                      className="w-full flex items-start gap-3 p-3 rounded-xl border border-surface-tertiary hover:bg-surface-secondary transition-colors text-left group disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <span className={cn("mt-1 w-2 h-2 rounded-full shrink-0", cfg.dot)} />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-text-primary truncate">
                          {article.title}
                        </p>
                        <p className="text-xs text-text-secondary mt-0.5">
                          {article.keyword}
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
// Day detail panel
// -------------------------------------------------------------------------

interface DayPanelProps {
  date: Date | null;
  items: CalendarItem[];
  onClose: () => void;
  onRefresh: () => void;
  onOpenSchedule: () => void;
}

function DayPanel({ date, items, onClose, onRefresh, onOpenSchedule }: DayPanelProps) {
  if (!date) return null;

  const scheduled = items.filter((i) => i.isScheduled);
  const published = items.filter((i) => !i.isScheduled);

  const handleUnschedule = async (articleId: string) => {
    try {
      await api.articles.update(articleId, { planned_date: null, auto_publish: false });
      toast.success("Article unscheduled");
      onClose();
      onRefresh();
    } catch {
      toast.error("Failed to unschedule article");
    }
  };

  return (
    <>
      <div className="fixed inset-0 z-50 bg-black/20" onClick={onClose} />
      <div className="fixed right-0 top-0 bottom-0 z-50 w-full max-w-80 sm:w-80 bg-surface shadow-2xl border-l border-surface-tertiary flex flex-col">
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

          {scheduled.length > 0 && (
            <section>
              <p className="text-xs uppercase tracking-wider font-semibold text-text-secondary mb-2 flex items-center gap-1.5">
                <Clock className="h-3.5 w-3.5" />
                Scheduled
              </p>
              <div className="space-y-2">
                {scheduled.map((item) => (
                  <PanelItemRow
                    key={item.id}
                    item={item}
                    onUnschedule={() => handleUnschedule(item.articleId)}
                  />
                ))}
              </div>
            </section>
          )}

          {published.length > 0 && (
            <section>
              <p className="text-xs uppercase tracking-wider font-semibold text-text-secondary mb-2 flex items-center gap-1.5">
                <Globe className="h-3.5 w-3.5" />
                Published
              </p>
              <div className="space-y-2">
                {published.map((item) => (
                  <PanelItemRow key={item.id} item={item} />
                ))}
              </div>
            </section>
          )}
        </div>

        {/* Schedule button at bottom */}
        <div className="px-4 py-3 border-t border-surface-tertiary">
          <button
            onClick={onOpenSchedule}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 transition-colors"
          >
            <Plus className="h-4 w-4" />
            Schedule Article
          </button>
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
  const cfg = getPillConfig(item.status);
  const time = item.date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });

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
          <div className="flex items-center gap-2 mt-0.5">
            <p className={cn("text-xs font-medium", cfg.text)}>
              {cfg.label}
            </p>
            {item.isScheduled && (
              <span className="text-xs text-text-secondary">{time}</span>
            )}
            {item.autoPublish && (
              <span title="Auto-publish enabled"><Globe className="h-3 w-3 text-primary-500" /></span>
            )}
          </div>
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
  const [month, setMonth] = useState(today.getMonth());

  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Day panel
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);

  // Schedule modal
  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [scheduleDate, setScheduleDate] = useState<Date | null>(null);
  const [scheduling, setScheduling] = useState(false);

  // ---------------------------------------------------------------------------
  // Data loading
  // ---------------------------------------------------------------------------
  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const fetchAll = async <T,>(
        fetcher: (params: { page: number; page_size: number }) => Promise<{ items: T[]; pages: number }>
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

      const allArticles = await fetchAll(api.articles.list);
      setArticles(allArticles);
    } catch {
      setError("Failed to load content. Please try again.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // ---------------------------------------------------------------------------
  // Build calendar items — only scheduled + published articles
  // ---------------------------------------------------------------------------
  const calendarItems: CalendarItem[] = useMemo(() => {
    const items: CalendarItem[] = [];
    for (const a of articles) {
      // Scheduled articles (have a planned_date)
      if (a.planned_date) {
        items.push({
          id: `scheduled-${a.id}`,
          articleId: a.id,
          title: a.title,
          status: a.status,
          date: parseDate(a.planned_date),
          href: `/articles/${a.id}`,
          isScheduled: true,
          autoPublish: a.auto_publish ?? false,
        });
      }
      // Published articles (show on published_at date, but not if already shown via planned_date)
      else if (a.status === "published" && a.published_at) {
        items.push({
          id: `published-${a.id}`,
          articleId: a.id,
          title: a.title,
          status: a.status,
          date: parseDate(a.published_at),
          href: `/articles/${a.id}`,
          isScheduled: false,
          autoPublish: false,
        });
      }
    }
    return items;
  }, [articles]);

  // Group by local date key
  const itemsByDate = useMemo(() => {
    const map = new Map<string, CalendarItem[]>();
    for (const item of calendarItems) {
      const key = toLocalDateKey(item.date);
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(item);
    }
    return map;
  }, [calendarItems]);

  // Stats for the month header
  const monthStats = useMemo(() => {
    let scheduled = 0;
    let published = 0;
    const monthPrefix = `${year}-${String(month + 1).padStart(2, "0")}`;
    for (const [key, items] of itemsByDate) {
      if (key.startsWith(monthPrefix)) {
        for (const item of items) {
          if (item.isScheduled) scheduled++;
          else published++;
        }
      }
    }
    return { scheduled, published };
  }, [itemsByDate, year, month]);

  // ---------------------------------------------------------------------------
  // Calendar grid
  // ---------------------------------------------------------------------------
  const firstDay = new Date(year, month, 1);
  const lastDay = new Date(year, month + 1, 0);
  const startPadding = firstDay.getDay();
  const daysInMonth = lastDay.getDate();

  const gridCells: (number | null)[] = [
    ...Array(startPadding).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ];
  while (gridCells.length % 7 !== 0) gridCells.push(null);

  // ---------------------------------------------------------------------------
  // Navigation
  // ---------------------------------------------------------------------------
  const goToPrevMonth = () => {
    if (month === 0) { setMonth(11); setYear((y) => y - 1); }
    else { setMonth((m) => m - 1); }
    setSelectedDate(null);
  };

  const goToNextMonth = () => {
    if (month === 11) { setMonth(0); setYear((y) => y + 1); }
    else { setMonth((m) => m + 1); }
    setSelectedDate(null);
  };

  const goToToday = () => {
    setYear(today.getFullYear());
    setMonth(today.getMonth());
    setSelectedDate(null);
  };

  const isToday = (day: number) =>
    day === today.getDate() && month === today.getMonth() && year === today.getFullYear();

  const isWeekend = (colIndex: number) => colIndex === 0 || colIndex === 6;

  // ---------------------------------------------------------------------------
  // Day click — always opens panel
  // ---------------------------------------------------------------------------
  const handleDayClick = (day: number) => {
    setSelectedDate(new Date(year, month, day));
  };

  // ---------------------------------------------------------------------------
  // Open schedule modal (from panel or from day click)
  // ---------------------------------------------------------------------------
  const openScheduleForDate = (d: Date) => {
    setScheduleDate(d);
    setShowScheduleModal(true);
    setSelectedDate(null);
  };

  // ---------------------------------------------------------------------------
  // Schedule handler
  // ---------------------------------------------------------------------------
  const handleSchedule = async (
    articleId: string,
    hour: number,
    minute: number,
    autoPublish: boolean
  ) => {
    if (!scheduleDate) return;
    setScheduling(true);
    try {
      // Build ISO datetime string in local time
      const d = new Date(scheduleDate);
      d.setHours(hour, minute, 0, 0);
      await api.articles.update(articleId, {
        planned_date: d.toISOString(),
        auto_publish: autoPublish,
      });
      toast.success(
        autoPublish
          ? "Article scheduled for auto-publish"
          : "Article scheduled"
      );
      setShowScheduleModal(false);
      setScheduleDate(null);
      loadData();
    } catch {
      toast.error("Failed to schedule article");
    } finally {
      setScheduling(false);
    }
  };

  // Panel items
  const panelItems = selectedDate
    ? (itemsByDate.get(toLocalDateKey(selectedDate)) ?? [])
    : [];

  // ---------------------------------------------------------------------------
  // Legend
  // ---------------------------------------------------------------------------
  const legendItems: { dot?: string; icon?: boolean; label: string }[] = [
    { dot: "bg-green-500", label: "Scheduled — Ready" },
    { dot: "bg-purple-500", label: "Published" },
    { icon: true, label: "Auto-publish" },
  ];

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <TierGate minimum="professional" feature="Content Calendar">
    <div className="space-y-6 max-w-7xl">
      {/* Page header */}
      <div className="mb-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-1">
          <div>
            <h1 className="font-bold flex items-center gap-3">
              <Calendar className="h-6 w-6 sm:h-8 sm:w-8 text-primary-500" />
              Content Calendar
            </h1>
            <p className="text-text-secondary mt-1">
              Schedule and track your publishing pipeline. Click any day to view details or schedule content.
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

      {/* Error */}
      {error && (
        <div className="mb-4 px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Calendar card */}
      <div className="card overflow-hidden">
        {/* Month nav */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-surface-tertiary">
          <button
            onClick={goToPrevMonth}
            className="p-2 rounded-lg hover:bg-surface-secondary transition-colors"
            aria-label="Previous month"
          >
            <ChevronLeft className="h-5 w-5 text-text-secondary" />
          </button>

          <div className="flex items-center gap-4">
            <div className="text-center">
              <h2 className="text-lg font-semibold text-text-primary">
                {MONTH_NAMES[month]} {year}
              </h2>
              {!loading && (monthStats.scheduled > 0 || monthStats.published > 0) && (
                <p className="text-xs text-text-secondary mt-0.5">
                  {monthStats.scheduled > 0 && (
                    <span className="text-green-700">{monthStats.scheduled} scheduled</span>
                  )}
                  {monthStats.scheduled > 0 && monthStats.published > 0 && " · "}
                  {monthStats.published > 0 && (
                    <span className="text-purple-700">{monthStats.published} published</span>
                  )}
                </p>
              )}
            </div>
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

        {/* Loading */}
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

            <div className="grid grid-cols-7 min-w-[500px]">
              {gridCells.map((day, cellIdx) => {
                const colIdx = cellIdx % 7;
                const key = day !== null
                  ? toLocalDateKey(new Date(year, month, day))
                  : `empty-${cellIdx}`;
                const dayItems = day !== null ? (itemsByDate.get(key) ?? []) : [];
                const visibleItems = dayItems.slice(0, 3);
                const overflow = dayItems.length - visibleItems.length;
                const today_ = day !== null && isToday(day);
                const weekend = isWeekend(colIdx);
                const isLastRow = cellIdx >= gridCells.length - 7;
                const isLastCol = colIdx === 6;

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
                      day !== null && "cursor-pointer hover:bg-surface-secondary/70 transition-colors",
                      day === null && "bg-surface-secondary/20"
                    )}
                  >
                    {day !== null && (
                      <>
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
                          {dayItems.length === 0 && (
                            <Plus className="h-3 w-3 text-text-secondary/40 hidden md:block" />
                          )}
                        </div>

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
        {legendItems.map(({ dot, icon, label }) => (
          <div
            key={label}
            className="flex items-center gap-1.5 text-sm text-text-secondary"
          >
            {icon ? (
              <Globe className="h-3 w-3 text-primary-500" />
            ) : (
              <span className={cn("w-2.5 h-2.5 rounded-full", dot)} />
            )}
            {label}
          </div>
        ))}
      </div>

      {/* Day panel */}
      <DayPanel
        date={selectedDate}
        items={panelItems}
        onClose={() => setSelectedDate(null)}
        onRefresh={loadData}
        onOpenSchedule={() => selectedDate && openScheduleForDate(selectedDate)}
      />

      {/* Schedule modal */}
      {showScheduleModal && scheduleDate && (
        <ScheduleModal
          date={scheduleDate}
          articles={articles}
          existingCount={itemsByDate.get(toLocalDateKey(scheduleDate))?.length ?? 0}
          scheduling={scheduling}
          onSchedule={handleSchedule}
          onClose={() => {
            setShowScheduleModal(false);
            setScheduleDate(null);
          }}
        />
      )}
    </div>
    </TierGate>
  );
}
