import { useEffect, useRef } from "react";

export interface KeyboardShortcut {
  /** The key to match (case-insensitive). E.g. "s", "n", "p", "/", "?". */
  key: string;
  /** Require Ctrl (Windows/Linux) or Cmd (Mac). */
  ctrl?: boolean;
  /**
   * Require Shift in addition to other modifiers.
   * Not needed for characters that are inherently shifted (e.g. "?"),
   * since those are matched by event.key directly.
   */
  shift?: boolean;
  handler: () => void;
}

// Characters that are produced by holding Shift — their event.key already
// encodes the shift state, so we must NOT additionally require shiftKey===false.
const INHERENTLY_SHIFTED_KEYS = new Set(["?", "!", "@", "#", "$", "%", "^", "&", "*", "(", ")"]);

/**
 * Registers global keyboard event listeners for the given shortcuts.
 *
 * Bare-key shortcuts (no ctrl) are suppressed when the user is typing
 * inside an input, textarea, or contenteditable element.
 * Modifier shortcuts (ctrl/cmd) are always evaluated so Ctrl+S works
 * inside the article textarea.
 */
export function useKeyboardShortcuts(shortcuts: KeyboardShortcut[]): void {
  const shortcutsRef = useRef(shortcuts);
  shortcutsRef.current = shortcuts;

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement;
      const isEditable =
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target.isContentEditable;

      for (const shortcut of shortcutsRef.current) {
        // Key match (case-insensitive)
        if (event.key.toLowerCase() !== shortcut.key.toLowerCase()) continue;

        // Ctrl/Cmd modifier
        const wantsCtrl = shortcut.ctrl ?? false;
        if (wantsCtrl !== (event.ctrlKey || event.metaKey)) continue;

        // Shift modifier — skip the check for inherently-shifted characters
        const wantsShift = shortcut.shift ?? false;
        const isInherentlyShifted = INHERENTLY_SHIFTED_KEYS.has(shortcut.key);
        if (!isInherentlyShifted && wantsShift !== event.shiftKey) continue;

        // Bare-key shortcuts are skipped inside editable fields
        if (isEditable && !wantsCtrl) continue;

        event.preventDefault();
        shortcut.handler();
        return;
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);
}
