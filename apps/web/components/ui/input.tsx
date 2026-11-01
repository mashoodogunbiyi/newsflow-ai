import type { InputHTMLAttributes } from "react";

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  error?: string;
  helpText?: string;
  label: string;
};

export function Input({ className = "", error, helpText, id, label, ...props }: InputProps) {
  const inputId = id ?? props.name;
  if (!inputId) {
    throw new Error("A reusable Input requires an id or name.");
  }
  const descriptionId = error || helpText ? `${inputId}-description` : undefined;

  return (
    <div>
      <label className="text-sm font-semibold text-emerald-950" htmlFor={inputId}>
        {label}
      </label>
      <input
        aria-describedby={descriptionId}
        aria-invalid={error ? "true" : undefined}
        className={`mt-2 min-h-12 w-full rounded-2xl border bg-white px-4 py-3 text-base text-emerald-950 outline-none transition placeholder:text-emerald-950/65 focus:border-emerald-700 focus:ring-4 focus:ring-emerald-700/10 disabled:cursor-not-allowed disabled:bg-stone-100 disabled:text-emerald-950/50 ${
          error ? "border-red-700" : "border-emerald-950/15"
        } ${className}`}
        id={inputId}
        {...props}
      />
      {error || helpText ? (
        <p
          className={`mt-2 text-sm ${error ? "text-red-800" : "text-emerald-950/70"}`}
          id={descriptionId}
        >
          {error ?? helpText}
        </p>
      ) : null}
    </div>
  );
}
