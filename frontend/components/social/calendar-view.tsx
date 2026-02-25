"use client";

import { useState } from "react";
import { SocialPost, SocialPlatform } from "@/lib/api";
import { PostStatusBadge } from "./post-status-badge";
import {
  format,
  startOfMonth,
  endOfMonth,
  startOfWeek,
  endOfWeek,
  addDays,
  isSameMonth,
  isSameDay,
  parseISO,
  startOfDay,
} from "date-fns";
import { cn } from "@/lib/utils";
import { Twitter, Linkedin, Facebook, Instagram, Plus } from "lucide-react";

interface CalendarPost {
  id: string;
  content: string;
  scheduled_at: string;
  status: string;
  platforms: string[];
}

interface CalendarViewProps {
  posts: SocialPost[];
  view: "month" | "week" | "day";
  selectedDate: Date;
  onDateChange: (date: Date) => void;
  onPostClick: (postId: string) => void;
  onCreatePost: (date: Date) => void;
  onReschedule?: (postId: string, newDate: Date) => void;
  filterPlatform?: SocialPlatform | "all";
}

const PLATFORM_COLORS: Record<SocialPlatform, string> = {
  twitter: "bg-[#1DA1F2] text-white",
  linkedin: "bg-[#0A66C2] text-white",
  facebook: "bg-[#1877F2] text-white",
  instagram: "bg-gradient-to-r from-[#E4405F] to-[#5B51D8] text-white",
};

const PLATFORM_ICONS: Record<SocialPlatform, React.ReactNode> = {
  twitter: <Twitter className="h-3 w-3" />,
  linkedin: <Linkedin className="h-3 w-3" />,
  facebook: <Facebook className="h-3 w-3" />,
  instagram: <Instagram className="h-3 w-3" />,
};

export function CalendarView({
  posts,
  view,
  selectedDate,
  onDateChange,
  onPostClick,
  onCreatePost,
  onReschedule,
  filterPlatform = "all",
}: CalendarViewProps) {
  const [draggedPost, setDraggedPost] = useState<string | null>(null);
  const [expandedDays, setExpandedDays] = useState<Set<string>>(new Set());

  // Filter posts by platform
  const filteredPosts = posts.filter((post) =>
    filterPlatform === "all" ? true : post.platforms.includes(filterPlatform)
  );

  // Group posts by date
  const postsByDate = filteredPosts.reduce((acc, post) => {
    const dateKey = format(parseISO(post.scheduled_at), "yyyy-MM-dd");
    if (!acc[dateKey]) {
      acc[dateKey] = [];
    }
    acc[dateKey].push(post);
    return acc;
  }, {} as Record<string, SocialPost[]>);

  const renderMonthView = () => {
    const monthStart = startOfMonth(selectedDate);
    const monthEnd = endOfMonth(selectedDate);
    const startDate = startOfWeek(monthStart, { weekStartsOn: 0 });
    const endDate = endOfWeek(monthEnd, { weekStartsOn: 0 });

    const rows: JSX.Element[] = [];
    let days: JSX.Element[] = [];
    let day = startDate;

    while (day <= endDate) {
      for (let i = 0; i < 7; i++) {
        const currentDay = day;
        const dateKey = format(currentDay, "yyyy-MM-dd");
        const dayPosts = postsByDate[dateKey] || [];
        const isCurrentMonth = isSameMonth(currentDay, selectedDate);
        const isToday = isSameDay(currentDay, new Date());

        days.push(
          <div
            key={currentDay.toString()}
            className={cn(
              "group min-h-[120px] border border-surface-tertiary p-2 cursor-pointer transition-colors",
              !isCurrentMonth && "bg-surface-secondary/50 text-text-secondary",
              isToday && "ring-2 ring-primary-500 ring-inset",
              "hover:bg-surface-secondary"
            )}
            onClick={() => onDateChange(currentDay)}
            onDragOver={(e) => {
              e.preventDefault();
              if (draggedPost && onReschedule) {
                e.currentTarget.classList.add("bg-primary-100");
              }
            }}
            onDragLeave={(e) => {
              e.currentTarget.classList.remove("bg-primary-100");
            }}
            onDrop={(e) => {
              e.preventDefault();
              e.currentTarget.classList.remove("bg-primary-100");
              if (draggedPost && onReschedule) {
                onReschedule(draggedPost, currentDay);
                setDraggedPost(null);
              }
            }}
          >
            <div className="flex items-center justify-between mb-2">
              <span
                className={cn(
                  "text-sm font-medium",
                  isToday && "text-primary-500 font-bold"
                )}
              >
                {format(currentDay, "d")}
              </span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onCreatePost(currentDay);
                }}
                className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-surface-tertiary rounded"
                aria-label="Create post"
              >
                <Plus className="h-4 w-4" />
              </button>
            </div>
            <div className="space-y-1">
              {(expandedDays.has(dateKey) ? dayPosts : dayPosts.slice(0, 3)).map((post) => (
                <div
                  key={post.id}
                  draggable={post.status === "pending" && !!onReschedule}
                  onDragStart={() => setDraggedPost(post.id)}
                  onDragEnd={() => setDraggedPost(null)}
                  onClick={(e) => {
                    e.stopPropagation();
                    onPostClick(post.id);
                  }}
                  className={cn(
                    "text-xs p-1.5 rounded cursor-pointer transition-all",
                    "bg-surface-secondary hover:bg-surface-tertiary",
                    "border-l-2 truncate",
                    post.status === "posted" && "border-green-500",
                    post.status === "failed" && "border-red-500",
                    post.status === "pending" && "border-yellow-500",
                    draggedPost === post.id && "opacity-50"
                  )}
                  title={post.content}
                >
                  <div className="flex items-center gap-1 mb-0.5">
                    {post.platforms.map((platform) => (
                      <span
                        key={platform}
                        className={cn(
                          "inline-flex items-center justify-center w-4 h-4 rounded-full",
                          PLATFORM_COLORS[platform as SocialPlatform]
                        )}
                      >
                        {PLATFORM_ICONS[platform as SocialPlatform]}
                      </span>
                    ))}
                  </div>
                  <span className="line-clamp-2">{post.content}</span>
                </div>
              ))}
              {dayPosts.length > 3 && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setExpandedDays((prev) => {
                      const next = new Set(prev);
                      if (next.has(dateKey)) {
                        next.delete(dateKey);
                      } else {
                        next.add(dateKey);
                      }
                      return next;
                    });
                  }}
                  className="text-xs text-primary-600 hover:text-primary-700 text-center py-1 w-full hover:bg-surface-secondary rounded transition-colors"
                >
                  {expandedDays.has(dateKey)
                    ? "Show less"
                    : `+${dayPosts.length - 3} more`}
                </button>
              )}
            </div>
          </div>
        );

        day = addDays(day, 1);
      }

      rows.push(
        <div key={day.toString()} className="grid grid-cols-7 gap-0">
          {days}
        </div>
      );
      days = [];
    }

    return (
      <div className="space-y-0">
        {/* Week day headers */}
        <div className="grid grid-cols-7 gap-0 border-b border-surface-tertiary">
          {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((day) => (
            <div
              key={day}
              className="text-center text-sm font-semibold py-3 text-text-secondary"
            >
              {day}
            </div>
          ))}
        </div>
        {rows}
      </div>
    );
  };

  const renderWeekView = () => {
    const weekStart = startOfWeek(selectedDate, { weekStartsOn: 0 });
    const days: JSX.Element[] = [];

    for (let i = 0; i < 7; i++) {
      const day = addDays(weekStart, i);
      const dateKey = format(day, "yyyy-MM-dd");
      const dayPosts = postsByDate[dateKey] || [];
      const isToday = isSameDay(day, new Date());

      days.push(
        <div
          key={day.toString()}
          className={cn(
            "flex-1 border-r border-surface-tertiary p-3 min-h-[400px]",
            isToday && "bg-primary-50"
          )}
        >
          <div className="text-center mb-3">
            <div className="text-xs text-text-secondary uppercase">
              {format(day, "EEE")}
            </div>
            <div
              className={cn(
                "text-2xl font-bold",
                isToday && "text-primary-500"
              )}
            >
              {format(day, "d")}
            </div>
          </div>
          <div className="space-y-2">
            {dayPosts.map((post) => (
              <div
                key={post.id}
                onClick={() => onPostClick(post.id)}
                className="p-2 bg-surface-secondary rounded-lg cursor-pointer hover:bg-surface-tertiary transition-colors border border-surface-tertiary"
              >
                <div className="flex items-center gap-2 mb-2">
                  {post.platforms.map((platform) => (
                    <span
                      key={platform}
                      className={cn(
                        "inline-flex items-center justify-center w-5 h-5 rounded-full",
                        PLATFORM_COLORS[platform as SocialPlatform]
                      )}
                    >
                      {PLATFORM_ICONS[platform as SocialPlatform]}
                    </span>
                  ))}
                  <PostStatusBadge status={post.status} />
                </div>
                <p className="text-sm line-clamp-3">{post.content}</p>
                <div className="text-xs text-text-secondary mt-2">
                  {format(parseISO(post.scheduled_at), "h:mm a")}
                </div>
              </div>
            ))}
          </div>
        </div>
      );
    }

    return <div className="flex gap-0 border-l border-surface-tertiary">{days}</div>;
  };

  const renderDayView = () => {
    const dateKey = format(selectedDate, "yyyy-MM-dd");
    const dayPosts = (postsByDate[dateKey] || []).sort((a, b) =>
      parseISO(a.scheduled_at).getTime() - parseISO(b.scheduled_at).getTime()
    );

    const hours: JSX.Element[] = [];
    for (let hour = 0; hour < 24; hour++) {
      const hourPosts = dayPosts.filter(
        (post) => parseISO(post.scheduled_at).getHours() === hour
      );

      hours.push(
        <div key={hour} className="flex border-b border-surface-tertiary min-h-[60px]">
          <div className="w-20 py-2 px-3 text-sm text-text-secondary border-r border-surface-tertiary">
            {format(new Date().setHours(hour, 0, 0, 0), "h:mm a")}
          </div>
          <div className="flex-1 p-2 space-y-2">
            {hourPosts.map((post) => (
              <div
                key={post.id}
                onClick={() => onPostClick(post.id)}
                className="p-3 bg-surface-secondary rounded-lg cursor-pointer hover:bg-surface-tertiary transition-colors border border-surface-tertiary"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    {post.platforms.map((platform) => (
                      <span
                        key={platform}
                        className={cn(
                          "inline-flex items-center justify-center w-5 h-5 rounded-full",
                          PLATFORM_COLORS[platform as SocialPlatform]
                        )}
                      >
                        {PLATFORM_ICONS[platform as SocialPlatform]}
                      </span>
                    ))}
                  </div>
                  <PostStatusBadge status={post.status} />
                </div>
                <p className="text-sm">{post.content}</p>
                <div className="text-xs text-text-secondary mt-2">
                  {format(parseISO(post.scheduled_at), "h:mm a")}
                </div>
              </div>
            ))}
          </div>
        </div>
      );
    }

    return <div className="border-t border-surface-tertiary">{hours}</div>;
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-surface-tertiary overflow-hidden">
      {view === "month" && renderMonthView()}
      {view === "week" && renderWeekView()}
      {view === "day" && renderDayView()}
    </div>
  );
}
