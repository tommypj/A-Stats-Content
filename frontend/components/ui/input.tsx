"use client";

import { forwardRef, InputHTMLAttributes, useId } from "react";
import { cn } from "@/lib/utils";

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: React.ReactNode;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, label, error, helperText, leftIcon, rightIcon, id: providedId, ...props }, ref) => {
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
        <div className="relative">
          {leftIcon && (
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted">
              {leftIcon}
            </div>
          )}
          <input
            id={id}
            type={type}
            className={cn(
              "w-full rounded-xl border bg-surface py-2.5 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 transition-all duration-200",
              leftIcon ? "pl-9 sm:pl-10 pr-3 sm:pr-4" : "px-3 sm:px-4",
              rightIcon ? "pr-9 sm:pr-10" : "",
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
          {rightIcon && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted">
              {rightIcon}
            </div>
          )}
        </div>
        {error && <p id={errorId} className="mt-1.5 text-xs text-red-500">{error}</p>}
        {helperText && !error && (
          <p id={helperId} className="mt-1.5 text-xs text-text-muted">{helperText}</p>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";

export { Input };
