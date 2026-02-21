"use client";

import { cn } from "@/lib/utils";

interface DateRangePickerProps {
  value: number;
  onChange: (days: number) => void;
}

const ranges = [
  { label: "7 days", value: 7 },
  { label: "14 days", value: 14 },
  { label: "28 days", value: 28 },
  { label: "90 days", value: 90 },
];

export function DateRangePicker({ value, onChange }: DateRangePickerProps) {
  return (
    <div className="inline-flex items-center gap-1 p-1 bg-surface-secondary rounded-xl">
      {ranges.map((range) => (
        <button
          key={range.value}
          onClick={() => onChange(range.value)}
          className={cn(
            "px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200",
            value === range.value
              ? "bg-white text-primary-600 shadow-sm"
              : "text-text-secondary hover:text-text-primary hover:bg-white/50"
          )}
        >
          {range.label}
        </button>
      ))}
    </div>
  );
}
