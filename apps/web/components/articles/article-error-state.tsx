"use client";

import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";

export function ArticleErrorState({ invalidRequest = false }: { invalidRequest?: boolean }) {
  const router = useRouter();

  return (
    <section
      className="rounded-3xl border border-red-900/10 bg-white px-6 py-12 text-center"
      role="alert"
    >
      <div className="mx-auto max-w-xl">
        <p className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-red-700">
          Catalogue unavailable
        </p>
        <h2 className="mt-3 text-3xl font-semibold tracking-[-0.035em] text-emerald-950">
          {invalidRequest
            ? "This article page link is not valid."
            : "Articles could not be loaded."}
        </h2>
        <p className="mt-4 leading-7 text-emerald-950/70">
          {invalidRequest
            ? "Return to the first page and continue browsing the authorised catalogue."
            : "The backend may be temporarily unavailable. No account or article information has been changed."}
        </p>
        <div className="mt-7 flex flex-wrap justify-center gap-3">
          <Button onClick={() => router.refresh()}>Try again</Button>
          {invalidRequest ? (
            <Button onClick={() => router.replace("/dashboard")} variant="secondary">
              Return to first page
            </Button>
          ) : null}
        </div>
      </div>
    </section>
  );
}
