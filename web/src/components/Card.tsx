import React from "react";

type CardProps = React.PropsWithChildren<{
  title?: string;
}>;

export function Card({ title, children }: CardProps) {
  return (
    <section
      style={{
        background: "var(--color-surface-elevated)",
        borderRadius: "var(--radius-lg)",
        padding: "var(--spacing-lg)",
        boxShadow: "0 4px 16px rgba(0,0,0,0.08)",
      }}
    >
      {title ? <h3 style={{ marginTop: 0 }}>{title}</h3> : null}
      {children}
    </section>
  );
}
