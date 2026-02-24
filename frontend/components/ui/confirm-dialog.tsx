"use client";

import { useEffect, useRef } from "react";
import { AlertTriangle, Trash2 } from "lucide-react";

interface ConfirmDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "danger" | "warning" | "default";
  isLoading?: boolean;
}

export function ConfirmDialog({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  variant = "default",
  isLoading = false,
}: ConfirmDialogProps) {
  const cancelRef = useRef<HTMLButtonElement>(null);

  // Handle Escape key to close
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  // Auto-focus cancel button on open
  useEffect(() => {
    if (isOpen) {
      // Use rAF so the DOM is painted before focusing
      const frame = requestAnimationFrame(() => {
        cancelRef.current?.focus();
      });
      return () => cancelAnimationFrame(frame);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const iconBg =
    variant === "danger"
      ? "bg-red-50"
      : variant === "warning"
        ? "bg-yellow-50"
        : "bg-primary-50";

  const confirmBtnClass =
    variant === "danger"
      ? "bg-red-600 hover:bg-red-700"
      : variant === "warning"
        ? "bg-yellow-600 hover:bg-yellow-700"
        : "bg-primary-600 hover:bg-primary-700";

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Dialog */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="confirm-dialog-title"
          aria-describedby="confirm-dialog-message"
          className="bg-surface rounded-2xl border border-surface-tertiary shadow-lg max-w-md w-full p-6 space-y-4"
        >
          {/* Icon + Title */}
          <div className="flex items-start gap-3">
            <div
              className={`h-10 w-10 rounded-xl flex items-center justify-center flex-shrink-0 ${iconBg}`}
            >
              {variant === "danger" ? (
                <Trash2 className="h-5 w-5 text-red-500" />
              ) : (
                <AlertTriangle
                  className={`h-5 w-5 ${
                    variant === "warning" ? "text-yellow-500" : "text-primary-500"
                  }`}
                />
              )}
            </div>
            <div>
              <h3
                id="confirm-dialog-title"
                className="text-lg font-display font-semibold text-text-primary"
              >
                {title}
              </h3>
              <p
                id="confirm-dialog-message"
                className="mt-1 text-sm text-text-secondary"
              >
                {message}
              </p>
            </div>
          </div>

          {/* Buttons */}
          <div className="flex justify-end gap-3 pt-2">
            <button
              ref={cancelRef}
              onClick={onClose}
              disabled={isLoading}
              className="btn-secondary"
            >
              {cancelLabel}
            </button>
            <button
              onClick={onConfirm}
              disabled={isLoading}
              className={`px-4 py-2 rounded-xl text-sm font-medium text-white transition-colors ${confirmBtnClass} disabled:opacity-50`}
            >
              {isLoading ? "Processing..." : confirmLabel}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
