import React from "react";

type InputFieldProps = React.InputHTMLAttributes<HTMLInputElement>;

export const InputField = React.forwardRef<HTMLInputElement, InputFieldProps>(function InputField(
  { className, ...props },
  ref,
) {
  return (
    <input
      className={["chronos-input", className].filter(Boolean).join(" ")}
      ref={ref}
      {...props}
    />
  );
});
