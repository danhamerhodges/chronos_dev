import React from "react";

type InputFieldProps = React.InputHTMLAttributes<HTMLInputElement>;

export function InputField(props: InputFieldProps) {
  return (
    <input
      style={{
        width: "100%",
        border: "1px solid #c9d4e0",
        borderRadius: "var(--radius-sm)",
        padding: "var(--spacing-sm)",
      }}
      {...props}
    />
  );
}
