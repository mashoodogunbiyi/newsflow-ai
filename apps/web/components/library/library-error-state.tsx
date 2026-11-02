"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { Button, buttonStyles } from "@/components/ui/button";

type LibraryErrorStateProps = {
  reason: "invalid_request" | "not_found" | "unavailable";
};

export function LibraryErrorState({ reason }: LibraryErrorStateProps) {
  const router = useRouter();
  const missing = reason === "not_found";
  const invalid = reason === "invalid_request";
  const title = missing
    ? "This saved draft is no longer available."
    : invalid
      ? "This content-library link is not valid."
      : "Your saved drafts could not be loaded.";
  const description = missing
    ? "It may have been removed or may not belong to this account. Private record details are not disclosed."
    : invalid
      ? "Return to the first library page and choose a saved draft again."
      : "The backend may be temporarily unavailable. Your drafts have not been changed.";

  return (
    <section
      className="rounded-3xl border border-red-900/10 bg-white px-6 py-12 text-center"
      role="alert"
    >
      <div className="mx-auto max-w-xl">
        <p className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-red-700">
          Safe recovery
        </p>
        <h2 className="mt-3 text-3xl font-semibold tracking-[-0.035em] text-emerald-950">
          {title}
        </h2>
        <p className="mt-4 leading-7 text-emerald-950/70">{description}</p>
        <div className="mt-7 flex flex-wrap justify-center gap-3">
          {reason === "unavailable" ? (
            <Button onClick={() => router.refresh()}>Try again</Button>
          ) : null}
          <Link
            className={buttonStyles(reason === "unavailable" ? "secondary" : "primary")}
            href="/library"
          >
            Return to library
          </Link>
        </div>
      </div>
    </section>
  );
}
