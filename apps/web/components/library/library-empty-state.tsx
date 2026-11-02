import Link from "next/link";

import { buttonStyles } from "@/components/ui/button";

export function LibraryEmptyState() {
  return (
    <section className="rounded-3xl border border-emerald-950/10 bg-white px-6 py-14 text-center">
      <div className="mx-auto max-w-xl">
        <p className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">
          Private content library
        </p>
        <h2 className="mt-3 text-3xl font-semibold tracking-[-0.035em] text-emerald-950">
          You have not saved any drafts yet.
        </h2>
        <p className="mt-4 leading-7 text-emerald-950/70">
          Choose an authorised article, generate a draft, review it carefully, and save it to build
          your personal library.
        </p>
        <Link className={`${buttonStyles("primary")} mt-7`} href="/dashboard">
          Browse authorised articles
        </Link>
      </div>
    </section>
  );
}
