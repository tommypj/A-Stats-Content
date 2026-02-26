"use client";

import { forwardRef, HTMLAttributes, useEffect, useId } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "./button";

interface DialogProps extends HTMLAttributes<HTMLDivElement> {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  size?: "sm" | "md" | "lg" | "xl" | "full";
}

const Dialog = forwardRef<HTMLDivElement, DialogProps>(
  ({ className, isOpen, onClose, title, description, size = "md", children, ...props }, ref) => {
    // Generate unique IDs for ARIA attributes
    const titleId = useId();
    const descriptionId = useId();

    // Lock body scroll when dialog is open
    useEffect(() => {
      if (!isOpen) return;
      const previous = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      return () => {
        document.body.style.overflow = previous;
      };
    }, [isOpen]);

    // Handle ESC key
    useEffect(() => {
      const handleEsc = (e: KeyboardEvent) => {
        if (e.key === "Escape" && isOpen) {
          onClose();
        }
      };
      window.addEventListener("keydown", handleEsc);
      return () => window.removeEventListener("keydown", handleEsc);
    }, [isOpen, onClose]);

    // Focus trap: focus first focusable element when dialog opens
    useEffect(() => {
      if (isOpen) {
        const focusableElements = document.querySelectorAll(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        const firstFocusable = focusableElements[0] as HTMLElement;
        if (firstFocusable) {
          firstFocusable.focus();
        }
      }
    }, [isOpen]);

    if (!isOpen) return null;

    const sizeClasses = {
      sm: "max-w-md",
      md: "max-w-lg",
      lg: "max-w-2xl",
      xl: "max-w-4xl",
      full: "max-w-full",
    };

    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        {/* Backdrop */}
        <div
          className="absolute inset-0 bg-black/50 backdrop-blur-sm"
          onClick={onClose}
          aria-hidden="true"
        />

        {/* Dialog */}
        <div
          ref={ref}
          role="dialog"
          aria-modal="true"
          aria-labelledby={title ? titleId : undefined}
          aria-describedby={description ? descriptionId : undefined}
          className={cn(
            "relative bg-surface rounded-2xl shadow-xl border border-surface-tertiary w-full",
            "flex flex-col max-h-[calc(100dvh-2rem)]",
            sizeClasses[size],
            className
          )}
          {...props}
        >
          {/* Header */}
          {(title || description) && (
            <div className="flex items-start justify-between p-6 border-b border-surface-tertiary flex-shrink-0">
              <div>
                {title && (
                  <h2 id={titleId} className="font-display text-2xl font-bold text-text-primary">
                    {title}
                  </h2>
                )}
                {description && (
                  <p id={descriptionId} className="mt-1 text-sm text-text-secondary">{description}</p>
                )}
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={onClose}
                className="ml-4 -mr-2 -mt-2 min-h-[44px] min-w-[44px]"
                aria-label="Close dialog"
              >
                <X className="h-5 w-5" />
              </Button>
            </div>
          )}

          {/* Content */}
          <div className="p-6 overflow-y-auto">{children}</div>
        </div>
      </div>
    );
  }
);

Dialog.displayName = "Dialog";

export { Dialog };
