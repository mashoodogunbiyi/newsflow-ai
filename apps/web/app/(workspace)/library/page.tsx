import type { Metadata } from "next";
import Link from "next/link";

import { PageHeader } from "@/components/layout/page-header";
import { buttonStyles } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";

export const metadata: Metadata = {
  title: "Content Library - NewsFlow AI",
  description: "Review your private NewsFlow AI content library.",
};

export default function LibraryPage() {
  return (
    <>
      <PageHeader
        actions={
          <Link className={buttonStyles("primary")} href="/generate">
            Create a post
          </Link>
        }
        description="Saved drafts and illustrations will remain private to your account and appear here after the content-management interface is connected."
        eyebrow="Content Library"
        title="Your work, organised around ownership."
      />

      <Card className="mt-10 grid min-h-[24rem] place-items-center text-center">
        <div className="max-w-lg">
          <StatusBadge tone="neutral">0 saved items</StatusBadge>
          <h2 className="mt-5 text-3xl font-semibold tracking-[-0.035em]">
            Your library is ready for its first draft.
          </h2>
          <p className="mt-4 leading-7 text-emerald-950/70">
            The route and private shell are in place. Saving, filtering, editing, and exporting will
            be connected by their dedicated Jira tasks.
          </p>
          <Link className={`${buttonStyles("secondary")} mt-7`} href="/generate">
            Visit Create Post
          </Link>
        </div>
      </Card>
    </>
  );
}
