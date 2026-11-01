import type { ButtonHTMLAttributes } from "react";

export type ButtonVariant = "primary" | "secondary" | "quiet" | "danger";

const variantStyles: Record<ButtonVariant, string> = {
  primary:
    "bg-emerald-950 text-white shadow-sm hover:bg-emerald-800 focus-visible:outline-emerald-700",
  secondary:
    "border border-emerald-950/15 bg-white text-emerald-950 hover:border-emerald-950/30 hover:bg-emerald-50 focus-visible:outline-emerald-700",
  quiet: "bg-transparent text-emerald-900 hover:bg-emerald-950/5 focus-visible:outline-emerald-700",
  danger: "bg-red-800 text-white hover:bg-red-700 focus-visible:outline-red-700",
};

export function buttonStyles(variant: ButtonVariant = "primary") {
  return `inline-flex min-h-11 items-center justify-center rounded-full px-5 py-2.5 text-sm font-semibold transition focus-visible:outline-2 focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:opacity-50 ${variantStyles[variant]}`;
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
};

export function Button({
  className = "",
  variant = "primary",
  type = "button",
  ...props
}: ButtonProps) {
  return <button className={`${buttonStyles(variant)} ${className}`} type={type} {...props} />;
}
