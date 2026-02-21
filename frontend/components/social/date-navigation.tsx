"use client";

import { Button } from "@/components/ui/button";
import { ChevronLeft, ChevronRight, Calendar } from "lucide-react";
import { format, startOfToday } from "date-fns";

interface DateNavigationProps {
  selectedDate: Date;
  onDateChange: (date: Date) => void;
  onToday: () => void;
  className?: string;
}

export function DateNavigation({
  selectedDate,
  onDateChange,
  onToday,
  className = "",
}: DateNavigationProps) {
  const handlePrevious = () => {
    const newDate = new Date(selectedDate);
    newDate.setMonth(newDate.getMonth() - 1);
    onDateChange(newDate);
  };

  const handleNext = () => {
    const newDate = new Date(selectedDate);
    newDate.setMonth(newDate.getMonth() + 1);
    onDateChange(newDate);
  };

  const isToday = format(selectedDate, "yyyy-MM") === format(startOfToday(), "yyyy-MM");

  return (
    <div className={`flex items-center justify-between ${className}`}>
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          onClick={handlePrevious}
          aria-label="Previous month"
        >
          <ChevronLeft className="h-5 w-5" />
        </Button>
        <h2 className="text-xl font-semibold min-w-[200px] text-center">
          {format(selectedDate, "MMMM yyyy")}
        </h2>
        <Button
          variant="ghost"
          size="icon"
          onClick={handleNext}
          aria-label="Next month"
        >
          <ChevronRight className="h-5 w-5" />
        </Button>
      </div>
      <Button
        variant="outline"
        size="sm"
        onClick={onToday}
        disabled={isToday}
        leftIcon={<Calendar className="h-4 w-4" />}
      >
        Today
      </Button>
    </div>
  );
}
