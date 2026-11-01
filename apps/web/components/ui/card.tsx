import type { HTMLAttributes, ReactNode } from "react";

type CardProps = HTMLAttributes<HTMLDivElement> & {
  children: ReactNode;
  tone?: "default" | "muted" | "dark";
};

const toneStyles = {
  default: "border-emerald-950/10 bg-white text-emerald-950 shadow-sm",
  muted: "border-emerald-950/10 bg-stone-100/70 text-emerald-950",
  dark: "border-emerald-900 bg-emerald-950 text-white shadow-lg shadow-emerald-950/10",
} as const;

export function Card({ children, className = "", tone = "default", ...props }: CardProps) {
  return (
    <div className={`rounded-3xl border p-6 sm:p-7 ${toneStyles[tone]} ${className}`} {...props}>
      {children}
    </div>
  );
}
