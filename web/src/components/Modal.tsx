import React from "react";

type ModalProps = React.PropsWithChildren<{
  open: boolean;
  onClose: () => void;
}>;

export function Modal({ open, onClose, children }: ModalProps) {
  if (!open) return null;
  return (
    <div
      role="dialog"
      aria-modal="true"
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0, 0, 0, 0.4)",
        display: "grid",
        placeItems: "center",
      }}
      onClick={onClose}
    >
      <div
        style={{
          minWidth: 320,
          background: "white",
          borderRadius: "var(--radius-md)",
          padding: "var(--spacing-lg)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  );
}
