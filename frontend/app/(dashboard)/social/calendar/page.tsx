"use client";

import { useState } from "react";
import { CalendarView } from "@/components/social/calendar-view";
import { DateNavigation } from "@/components/social/date-navigation";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { api, parseApiError, SocialPlatform } from "@/lib/api";
import { Calendar, Filter, Plus } from "lucide-react";
import { useRouter } from "next/navigation";
import { startOfToday, startOfMonth, endOfMonth, format } from "date-fns";
import { cn } from "@/lib/utils";
import { TierGate } from "@/components/ui/tier-gate";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

type ViewMode = "month" | "week" | "day";

function getDateRange(selectedDate: Date, view: ViewMode) {
  let startDate: Date;
  let endDate: Date;

  if (view === "month") {
    startDate = startOfMonth(selectedDate);
    endDate = endOfMonth(selectedDate);
  } else if (view === "week") {
    const weekStart = new Date(selectedDate);
    weekStart.setDate(selectedDate.getDate() - selectedDate.getDay());
    startDate = weekStart;
    endDate = new Date(weekStart);
    endDate.setDate(weekStart.getDate() + 6);
  } else {
    // day view
    startDate = new Date(selectedDate);
    endDate = new Date(selectedDate);
  }

  return {
    start_date: format(startDate, "yyyy-MM-dd"),
    end_date: format(endDate, "yyyy-MM-dd"),
  };
}

export default function SocialCalendarPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [view, setView] = useState<ViewMode>("month");
  const [selectedDate, setSelectedDate] = useState<Date>(startOfToday());
  const [filterPlatform, setFilterPlatform] = useState<SocialPlatform | "all">("all");

  const { start_date, end_date } = getDateRange(selectedDate, view);

  const { data: postsData, isLoading: loading } = useQuery({
    queryKey: ["social", "posts", { start_date, end_date }],
    queryFn: () =>
      api.social.posts({
        start_date,
        end_date,
        page_size: 200,
      }),
    staleTime: 30_000,
  });

  const posts = postsData?.items ?? [];

  const rescheduleMutation = useMutation({
    mutationFn: ({ postId, newDate }: { postId: string; newDate: Date }) =>
      api.social.reschedule(postId, newDate.toISOString()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["social", "posts"] });
    },
    onError: (error) => {
      toast.error(parseApiError(error).message);
    },
  });

  const handlePostClick = (postId: string) => {
    router.push(`/social/posts/${postId}`);
  };

  const handleCreatePost = (date: Date) => {
    // Navigate to compose page with pre-filled date
    router.push(`/social/compose?date=${format(date, "yyyy-MM-dd'T'HH:mm")}`);
  };

  const handleReschedule = async (postId: string, newDate: Date) => {
    rescheduleMutation.mutate({ postId, newDate });
  };

  const handleToday = () => {
    setSelectedDate(startOfToday());
  };

  return (
    <TierGate minimum="starter" feature="Content Calendar">
    <div className="space-y-6 max-w-7xl">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-display font-bold text-text-primary flex items-center gap-3">
              <Calendar className="h-8 w-8 text-primary-500" />
              Social Media Calendar
            </h1>
            <p className="text-text-secondary mt-1">
              Schedule and manage your social media posts
            </p>
          </div>
          <Button
            onClick={() => router.push("/social/compose")}
            leftIcon={<Plus className="h-5 w-5" />}
          >
            New Post
          </Button>
        </div>

        {/* View Controls */}
        <div className="flex items-center justify-between gap-4">
          <DateNavigation
            selectedDate={selectedDate}
            onDateChange={setSelectedDate}
            onToday={handleToday}
          />

          <div className="flex items-center gap-3">
            {/* Platform Filter */}
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-text-secondary" />
              <select
                value={filterPlatform}
                onChange={(e) => setFilterPlatform(e.target.value as SocialPlatform | "all")}
                className="px-3 py-2 border border-surface-tertiary rounded-lg text-sm bg-surface focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="all">All Platforms</option>
                <option value="twitter">Twitter</option>
                <option value="linkedin">LinkedIn</option>
                <option value="facebook">Facebook</option>
                <option value="instagram">Instagram</option>
              </select>
            </div>

            {/* View Switcher */}
            <div className="flex items-center gap-1 bg-surface-secondary rounded-lg p-1">
              <button
                onClick={() => setView("month")}
                className={cn(
                  "px-4 py-2 rounded-md text-sm font-medium transition-colors",
                  view === "month"
                    ? "bg-surface shadow-sm"
                    : "text-text-secondary hover:text-text-primary"
                )}
              >
                Month
              </button>
              <button
                onClick={() => setView("week")}
                className={cn(
                  "px-4 py-2 rounded-md text-sm font-medium transition-colors",
                  view === "week"
                    ? "bg-surface shadow-sm"
                    : "text-text-secondary hover:text-text-primary"
                )}
              >
                Week
              </button>
              <button
                onClick={() => setView("day")}
                className={cn(
                  "px-4 py-2 rounded-md text-sm font-medium transition-colors",
                  view === "day"
                    ? "bg-surface shadow-sm"
                    : "text-text-secondary hover:text-text-primary"
                )}
              >
                Day
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Calendar */}
      {loading ? (
        <div className="flex items-center justify-center h-96 bg-surface rounded-xl border border-surface-tertiary">
          <div className="text-center">
            <div className="w-12 h-12 border-4 border-primary-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-text-secondary">Loading calendar...</p>
          </div>
        </div>
      ) : (
        <CalendarView
          posts={posts}
          view={view}
          selectedDate={selectedDate}
          onDateChange={setSelectedDate}
          onPostClick={handlePostClick}
          onCreatePost={handleCreatePost}
          onReschedule={handleReschedule}
          filterPlatform={filterPlatform}
        />
      )}

      {/* Legend */}
      <div className="mt-6 flex items-center justify-center gap-6 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-green-500 rounded"></div>
          <span className="text-text-secondary">Posted</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-yellow-500 rounded"></div>
          <span className="text-text-secondary">Pending</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-red-500 rounded"></div>
          <span className="text-text-secondary">Failed</span>
        </div>
      </div>
    </div>
    </TierGate>
  );
}
