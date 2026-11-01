import type { ReactNode } from "react";

type StatusBadgeProps = {
  children: ReactNode;
  tone?: "success" | "warning" | "neutral";
};

const toneStyles = {
  success: "border-emerald-700/15 bg-emerald-50 text-emerald-800 before:bg-emerald-600",
  warning: "border-amber-700/20 bg-amber-50 text-amber-800 before:bg-amber-500",
  neutral: "border-emerald-950/10 bg-white text-emerald-950/65 before:bg-emerald-950/30",
} as const;

export function StatusBadge({ children, tone = "neutral" }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold before:h-2 before:w-2 before:rounded-full ${toneStyles[tone]}`}
    >
      {children}
    </span>
  );
}
