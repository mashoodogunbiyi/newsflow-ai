import type { Metadata } from "next";
import Link from "next/link";

import { PageHeader } from "@/components/layout/page-header";
import { buttonStyles } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";

export const metadata: Metadata = {
  title: "Dashboard - NewsFlow AI",
  description: "Your protected NewsFlow AI workspace overview.",
};

const workspaceSteps = [
  {
    number: "01",
    title: "Choose an authorised story",
    detail: "Browse only the source information that current permissions allow.",
  },
  {
    number: "02",
    title: "Generate a grounded draft",
    detail: "Create a review-first LinkedIn draft from the permitted fact pack.",
  },
  {
    number: "03",
    title: "Review and save",
    detail: "Keep editorial control before copying, downloading, or publishing anything.",
  },
] as const;

export default function DashboardPage() {
  return (
    <>
      <PageHeader
        actions={
          <Link className={buttonStyles("primary")} href="/generate">
            Create a post
          </Link>
        }
        description="Move from authorised source selection to a reviewed LinkedIn draft and original illustration without losing track of rights or provenance."
        eyebrow="Workspace overview"
        title="Good work starts with a careful source."
      />

      <section aria-labelledby="workspace-status" className="mt-10">
        <h2 className="sr-only" id="workspace-status">
          Workspace status
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          <Card>
            <StatusBadge tone="success">Session active</StatusBadge>
            <p className="mt-5 text-2xl font-semibold tracking-[-0.03em]">Protected workspace</p>
            <p className="mt-2 text-sm leading-6 text-emerald-950/55">
              FastAPI validates your session before private pages are rendered.
            </p>
          </Card>
          <Card>
            <StatusBadge tone="neutral">0 saved items</StatusBadge>
            <p className="mt-5 text-2xl font-semibold tracking-[-0.03em]">Content library</p>
            <p className="mt-2 text-sm leading-6 text-emerald-950/55">
              Your personal library starts clean and remains owner-scoped.
            </p>
          </Card>
          <Card className="sm:col-span-2 xl:col-span-1">
            <StatusBadge tone="warning">Fixture mode</StatusBadge>
            <p className="mt-5 text-2xl font-semibold tracking-[-0.03em]">Synthetic sources</p>
            <p className="mt-2 text-sm leading-6 text-emerald-950/55">
              No live CNN information is connected while authorisation remains blocked.
            </p>
          </Card>
        </div>
      </section>

      <Card className="mt-6 overflow-hidden p-0 sm:p-0" tone="dark">
        <div className="grid lg:grid-cols-[0.72fr_1.28fr]">
          <div className="border-b border-white/10 p-7 sm:p-9 lg:border-b-0 lg:border-r">
            <p className="font-mono text-xs font-semibold uppercase tracking-[0.2em] text-amber-300">
              Review-first workflow
            </p>
            <h2 className="mt-4 text-3xl font-semibold tracking-[-0.035em]">
              A deliberate path from source to post.
            </h2>
            <p className="mt-4 text-sm leading-7 text-white/60">
              Every stage keeps human review, ownership, and source restrictions visible.
            </p>
          </div>
          <ol className="divide-y divide-white/10">
            {workspaceSteps.map((step) => (
              <li className="grid gap-3 p-6 sm:grid-cols-[3rem_1fr] sm:p-7" key={step.number}>
                <span className="font-mono text-sm font-semibold text-amber-300">
                  {step.number}
                </span>
                <div>
                  <h3 className="font-semibold">{step.title}</h3>
                  <p className="mt-1 text-sm leading-6 text-white/55">{step.detail}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </Card>
    </>
  );
}
