import type { Metadata } from "next";

import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";

export const metadata: Metadata = {
  title: "Create Post - NewsFlow AI",
  description: "Prepare a source-grounded LinkedIn post in NewsFlow AI.",
};

export default function GeneratePage() {
  return (
    <>
      <PageHeader
        description="This route is ready for the authorised article selector, generation preferences, review editor, and image preview planned for the next interface tasks."
        eyebrow="Create Post"
        title="Build from permitted facts, not guesswork."
      />

      <div className="mt-10 grid gap-6 xl:grid-cols-[minmax(0,1.25fr)_minmax(18rem,0.75fr)]">
        <Card>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-2xl font-semibold tracking-[-0.03em]">Choose a source</h2>
            <StatusBadge tone="warning">Interface foundation</StatusBadge>
          </div>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-emerald-950/55">
            Live source selection is not part of NFA-56. This disabled control demonstrates the
            shared input treatment without exposing restricted content.
          </p>
          <div className="mt-7">
            <Input
              disabled
              helpText="Authorised article browsing will be connected in a later task."
              id="article-search"
              label="Search authorised articles"
              placeholder="Search by title or topic"
              type="search"
            />
          </div>
          <Button className="mt-6" disabled>
            Continue with selected article
          </Button>
        </Card>

        <Card tone="muted">
          <p className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">
            Creation checklist
          </p>
          <ol className="mt-5 space-y-4 text-sm leading-6 text-emerald-950/65">
            <li className="flex gap-3">
              <span className="font-mono font-semibold text-emerald-700">01</span>
              Select an article with current AI-processing rights.
            </li>
            <li className="flex gap-3">
              <span className="font-mono font-semibold text-emerald-700">02</span>
              Choose tone and length, then generate a grounded draft.
            </li>
            <li className="flex gap-3">
              <span className="font-mono font-semibold text-emerald-700">03</span>
              Review every claim and illustration before saving.
            </li>
          </ol>
        </Card>
      </div>
    </>
  );
}
