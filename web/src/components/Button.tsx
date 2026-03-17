import React from "react";

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary";
};

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", className, ...props },
  ref,
) {
  const classes = ["chronos-button", variant === "primary" ? "chronos-button--primary" : "chronos-button--secondary", className]
    .filter(Boolean)
    .join(" ");
  const background = variant === "primary" ? "var(--color-brand-primary)" : "var(--color-brand-secondary)";
  return (
    <button
      className={classes}
      ref={ref}
      style={{
        background,
        color: "#ffffff",
        borderRadius: "var(--radius-md)",
        border: "1px solid transparent",
        padding: "var(--spacing-sm) var(--spacing-md)",
      }}
      {...props}
    />
  );
});
