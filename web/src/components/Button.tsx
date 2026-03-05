import React from "react";

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary";
};

export function Button({ variant = "primary", ...props }: ButtonProps) {
  const bg = variant === "primary" ? "var(--color-brand-primary)" : "var(--color-brand-secondary)";
  return (
    <button
      style={{
        background: bg,
        color: "white",
        borderRadius: "var(--radius-md)",
        border: "none",
        padding: "var(--spacing-sm) var(--spacing-md)",
      }}
      {...props}
    />
  );
}
