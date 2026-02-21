"use client";

import { forwardRef, TextareaHTMLAttributes, useId } from "react";
import { cn } from "@/lib/utils";

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, label, error, helperText, id: providedId, ...props }, ref) => {
    const generatedId = useId();
    const id = providedId || generatedId;
    const errorId = `${id}-error`;
    const helperId = `${id}-helper`;
    return (
      <div className="w-full">
        {label && (
          <label htmlFor={id} className="block text-sm font-medium text-text-secondary mb-1.5">
            {label}
          </label>
        )}
        <textarea
          id={id}
          className={cn(
            "w-full rounded-xl border bg-surface px-4 py-2.5 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 transition-all duration-200 resize-none",
            error
              ? "border-red-500 focus:border-red-500 focus:ring-red-500/20"
              : "border-surface-tertiary focus:border-primary-500 focus:ring-primary-500/20",
            className
          )}
          aria-invalid={!!error}
          aria-describedby={error ? errorId : helperText ? helperId : undefined}
          ref={ref}
          {...props}
        />
        {error && <p id={errorId} className="mt-1.5 text-xs text-red-500">{error}</p>}
        {helperText && !error && (
          <p id={helperId} className="mt-1.5 text-xs text-text-muted">{helperText}</p>
        )}
      </div>
    );
  }
);

Textarea.displayName = "Textarea";

export { Textarea };
