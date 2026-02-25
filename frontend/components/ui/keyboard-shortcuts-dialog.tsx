"use client";

import { Keyboard, X } from "lucide-react";
import { useEffect, useRef } from "react";

interface ShortcutRow {
  keys: string[];
  description: string;
}

interface ShortcutSection {
  title: string;
  shortcuts: ShortcutRow[];
}

const SHORTCUT_SECTIONS: ShortcutSection[] = [
  {
    title: "Global",
    shortcuts: [
      { keys: ["?"], description: "Show keyboard shortcuts" },
      { keys: ["Ctrl", "/"], description: "Show keyboard shortcuts" },
    ],
  },
  {
    title: "Articles",
    shortcuts: [
      { keys: ["Ctrl", "S"], description: "Save article" },
      { keys: ["Ctrl", "Shift", "P"], description: "Publish to WordPress" },
      { keys: ["Ctrl", "N"], description: "New article" },
    ],
  },
  {
    title: "Outlines",
    shortcuts: [
      { keys: ["Ctrl", "N"], description: "New outline" },
    ],
  },
];

interface KeyboardShortcutsDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

export function KeyboardShortcutsDialog({ isOpen, onClose }: KeyboardShortcutsDialogProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  // Auto-focus close button on open
  useEffect(() => {
    if (isOpen) {
      const frame = requestAnimationFrame(() => {
        closeButtonRef.current?.focus();
      });
      return () => cancelAnimationFrame(frame);
    }
  }, [isOpen]);

  // Close on Escape + Tab focus trap
  useEffect(() => {
    if (!isOpen) return;
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        onClose();
        return;
      }
      if (e.key === "Tab" && dialogRef.current) {
        const focusable = Array.from(
          dialogRef.current.querySelectorAll<HTMLElement>(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
          )
        ).filter((el) => !el.hasAttribute("disabled"));
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey) {
          if (document.activeElement === first) {
            e.preventDefault();
            last.focus();
          }
        } else {
          if (document.activeElement === last) {
            e.preventDefault();
            first.focus();
          }
        }
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

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
          ref={dialogRef}
          role="dialog"
          aria-modal="true"
          aria-labelledby="kbd-shortcuts-title"
          className="bg-surface rounded-2xl border border-surface-tertiary shadow-xl w-full max-w-md"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-surface-tertiary">
            <div className="flex items-center gap-2">
              <Keyboard className="h-5 w-5 text-primary-600" />
              <h2
                id="kbd-shortcuts-title"
                className="font-display text-lg font-semibold text-text-primary"
              >
                Keyboard Shortcuts
              </h2>
            </div>
            <button
              ref={closeButtonRef}
              onClick={onClose}
              aria-label="Close keyboard shortcuts"
              className="p-1.5 rounded-lg text-text-muted hover:bg-surface-secondary hover:text-text-primary transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* Body */}
          <div className="px-6 py-4 space-y-5 max-h-[70vh] overflow-y-auto">
            {SHORTCUT_SECTIONS.map((section) => (
              <div key={section.title}>
                <p className="text-[11px] font-semibold uppercase tracking-wider text-text-muted mb-2">
                  {section.title}
                </p>
                <div className="space-y-1">
                  {section.shortcuts.map((row) => (
                    <div
                      key={row.description}
                      className="flex items-center justify-between py-1.5"
                    >
                      <span className="text-sm text-text-secondary">{row.description}</span>
                      <div className="flex items-center gap-1">
                        {row.keys.map((k, ki) => (
                          <span key={ki} className="flex items-center gap-1">
                            <kbd className="inline-flex items-center justify-center min-w-[28px] px-1.5 py-0.5 rounded-md border border-surface-tertiary bg-surface-secondary text-xs font-mono font-medium text-text-secondary shadow-sm">
                              {k}
                            </kbd>
                            {ki < row.keys.length - 1 && (
                              <span className="text-text-muted text-xs">+</span>
                            )}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* Footer hint */}
          <div className="px-6 py-3 border-t border-surface-tertiary">
            <p className="text-xs text-text-muted">
              Press <kbd className="inline-flex items-center justify-center px-1.5 py-0.5 rounded border border-surface-tertiary bg-surface-secondary text-xs font-mono">Esc</kbd> to close
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
