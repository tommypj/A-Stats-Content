"use client";

import { useState } from "react";
import { Calendar, Clock, Zap, Lightbulb } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

interface SchedulePickerProps {
  selectedDate: string;
  onDateChange: (date: string) => void;
  timezone?: string;
  onTimezoneChange?: (timezone: string) => void;
}

const BEST_TIMES = [
  { label: "Morning (9 AM)", hour: 9, description: "Peak engagement time" },
  { label: "Lunch (12 PM)", hour: 12, description: "Midday check-ins" },
  { label: "Afternoon (3 PM)", hour: 15, description: "Work break time" },
  { label: "Evening (6 PM)", hour: 18, description: "After work hours" },
];

const COMMON_TIMEZONES = [
  { value: "America/New_York", label: "Eastern Time (ET)" },
  { value: "America/Chicago", label: "Central Time (CT)" },
  { value: "America/Denver", label: "Mountain Time (MT)" },
  { value: "America/Los_Angeles", label: "Pacific Time (PT)" },
  { value: "UTC", label: "UTC" },
  { value: "Europe/London", label: "London (GMT)" },
  { value: "Europe/Paris", label: "Paris (CET)" },
  { value: "Asia/Tokyo", label: "Tokyo (JST)" },
];

export function SchedulePicker({
  selectedDate,
  onDateChange,
  timezone = "America/New_York",
  onTimezoneChange,
}: SchedulePickerProps) {
  const [mode, setMode] = useState<"now" | "schedule">("schedule");

  const handlePostNow = () => {
    setMode("now");
    const now = new Date();
    onDateChange(now.toISOString());
  };

  const handleSchedule = () => {
    setMode("schedule");
  };

  const handleDateTimeChange = (date: string, time: string) => {
    const datetime = new Date(`${date}T${time}`);
    onDateChange(datetime.toISOString());
  };

  const handleBestTime = (hour: number) => {
    const now = new Date();
    const tomorrow = new Date(now);
    tomorrow.setDate(tomorrow.getDate() + 1);
    tomorrow.setHours(hour, 0, 0, 0);
    onDateChange(tomorrow.toISOString());
  };

  const getCurrentDateTime = () => {
    const date = new Date(selectedDate || new Date());
    const dateStr = date.toISOString().split("T")[0];
    const timeStr = date.toTimeString().slice(0, 5);
    return { dateStr, timeStr };
  };

  const { dateStr, timeStr } = getCurrentDateTime();

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Button
          type="button"
          variant={mode === "now" ? "primary" : "outline"}
          size="sm"
          onClick={handlePostNow}
          leftIcon={<Zap className="h-4 w-4" />}
        >
          Post Now
        </Button>
        <Button
          type="button"
          variant={mode === "schedule" ? "primary" : "outline"}
          size="sm"
          onClick={handleSchedule}
          leftIcon={<Calendar className="h-4 w-4" />}
        >
          Schedule
        </Button>
      </div>

      {mode === "schedule" && (
        <div className="space-y-4">
          {/* Date and Time Inputs */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                <Calendar className="h-4 w-4 inline mr-1" />
                Date
              </label>
              <input
                type="date"
                value={dateStr}
                onChange={(e) => handleDateTimeChange(e.target.value, timeStr)}
                min={new Date().toISOString().split("T")[0]}
                className="w-full px-3 py-2 border border-surface-tertiary rounded-xl bg-surface-primary text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                <Clock className="h-4 w-4 inline mr-1" />
                Time
              </label>
              <input
                type="time"
                value={timeStr}
                onChange={(e) => handleDateTimeChange(dateStr, e.target.value)}
                className="w-full px-3 py-2 border border-surface-tertiary rounded-xl bg-surface-primary text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
          </div>

          {/* Timezone Selector */}
          {onTimezoneChange && (
            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                Timezone
              </label>
              <select
                value={timezone}
                onChange={(e) => onTimezoneChange(e.target.value)}
                className="w-full px-3 py-2 border border-surface-tertiary rounded-xl bg-surface-primary text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                {COMMON_TIMEZONES.map((tz) => (
                  <option key={tz.value} value={tz.value}>
                    {tz.label}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Best Times Suggestions */}
          <Card className="p-4 bg-blue-500/5 border-blue-500/20">
            <div className="flex items-start gap-2 mb-3">
              <Lightbulb className="h-4 w-4 text-blue-500 flex-shrink-0 mt-0.5" />
              <div>
                <h4 className="text-sm font-medium text-text-primary">
                  Best Times to Post
                </h4>
                <p className="text-xs text-text-secondary mt-1">
                  Schedule for tomorrow at peak engagement times
                </p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {BEST_TIMES.map((time) => (
                <button
                  key={time.hour}
                  type="button"
                  onClick={() => handleBestTime(time.hour)}
                  className="p-2 border border-surface-tertiary rounded-lg hover:bg-surface-secondary transition-colors text-left"
                >
                  <p className="text-sm font-medium text-text-primary">
                    {time.label}
                  </p>
                  <p className="text-xs text-text-secondary">{time.description}</p>
                </button>
              ))}
            </div>
          </Card>

          {/* Scheduled Time Display */}
          <div className="p-3 bg-surface-secondary rounded-xl">
            <p className="text-sm text-text-secondary">Scheduled for:</p>
            <p className="text-lg font-semibold text-text-primary mt-1">
              {new Date(selectedDate).toLocaleDateString("en-US", {
                weekday: "long",
                year: "numeric",
                month: "long",
                day: "numeric",
              })}{" "}
              at{" "}
              {new Date(selectedDate).toLocaleTimeString("en-US", {
                hour: "numeric",
                minute: "2-digit",
                hour12: true,
              })}
            </p>
            <p className="text-xs text-text-tertiary mt-1">
              {timezone.replace("_", " ")}
            </p>
          </div>
        </div>
      )}

      {mode === "now" && (
        <Card className="p-4 bg-green-500/5 border-green-500/20">
          <div className="flex items-center gap-2 text-green-600">
            <Zap className="h-5 w-5" />
            <div>
              <p className="font-medium">Post will be published immediately</p>
              <p className="text-sm text-text-secondary mt-1">
                Your post will be sent to all selected platforms right away
              </p>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
