import React, { useEffect, useRef } from "react";

type ModalProps = React.PropsWithChildren<{
  open: boolean;
  onClose: () => void;
  labelledBy?: string;
  describedBy?: string;
  initialFocusSelector?: string;
}>;

function focusableElements(container: HTMLElement): HTMLElement[] {
  return Array.from(
    container.querySelectorAll<HTMLElement>(
      'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ),
  ).filter((element) => !element.hasAttribute("hidden") && element.getAttribute("aria-hidden") !== "true");
}

export function Modal({ open, onClose, labelledBy, describedBy, initialFocusSelector, children }: ModalProps) {
  const dialogRef = useRef<HTMLDivElement | null>(null);
  const lastFocusedElementRef = useRef<HTMLElement | null>(null);
  const onCloseRef = useRef(onClose);

  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    if (!open) {
      return;
    }
    lastFocusedElementRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const dialog = dialogRef.current;
    const initialTarget =
      (dialog?.querySelector<HTMLElement>(initialFocusSelector ?? '[data-autofocus="true"]') ?? null);
    const focusables = dialog ? focusableElements(dialog) : [];
    (initialTarget ?? focusables[0] ?? dialog)?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onCloseRef.current();
        return;
      }
      if (event.key !== "Tab" || !dialog) {
        return;
      }
      const nextFocusables = focusableElements(dialog);
      if (!nextFocusables.length) {
        event.preventDefault();
        dialog.focus();
        return;
      }
      const first = nextFocusables[0];
      const last = nextFocusables[nextFocusables.length - 1];
      const activeElement = document.activeElement instanceof HTMLElement ? document.activeElement : null;
      if (event.shiftKey && activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      lastFocusedElementRef.current?.focus();
    };
  }, [open]);

  if (!open) return null;
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby={labelledBy}
      aria-describedby={describedBy}
      className="chronos-dialog-overlay"
      onClick={onClose}
    >
      <div
        className="chronos-dialog"
        ref={dialogRef}
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  );
}
