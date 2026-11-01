"use client";

import { Button } from "@/components/ui/button";

type ErrorStateProps = {
  description?: string;
  onRetry?: () => void;
  title?: string;
};

export function ErrorState({
  description = "We could not load this part of your workspace. Your account and saved content have not been changed.",
  onRetry,
  title = "Something went wrong.",
}: ErrorStateProps) {
  return (
    <div
      className="grid min-h-[24rem] place-items-center rounded-3xl border border-red-900/10 bg-white px-6 py-12 text-center"
      role="alert"
    >
      <div className="max-w-lg">
        <p className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-red-700">
          Safe recovery
        </p>
        <h1 className="mt-3 text-3xl font-semibold tracking-[-0.035em] text-emerald-950">
          {title}
        </h1>
        <p className="mt-4 leading-7 text-emerald-950/70">{description}</p>
        {onRetry ? (
          <Button className="mt-7" onClick={onRetry}>
            Try again
          </Button>
        ) : null}
      </div>
    </div>
  );
}
