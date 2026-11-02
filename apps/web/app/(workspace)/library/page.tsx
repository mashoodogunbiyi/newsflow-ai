import type { Metadata } from "next";
import Link from "next/link";

import { ContentLibrary, type LibrarySearchParams } from "@/components/library/content-library";
import { PageHeader } from "@/components/layout/page-header";
import { buttonStyles } from "@/components/ui/button";

export const metadata: Metadata = {
  title: "Content Library - NewsFlow AI",
  description: "Review your private NewsFlow AI content library.",
};

export default function LibraryPage({
  searchParams,
}: {
  searchParams: Promise<LibrarySearchParams>;
}) {
  return (
    <>
      <PageHeader
        actions={
          <Link className={buttonStyles("primary")} href="/generate">
            Create a post
          </Link>
        }
        description="Browse your private saved drafts, review their source references and selected illustrations, and reopen work to continue editing."
        eyebrow="Content Library"
        title="Your saved work, ready to continue."
      />
      <div className="mt-10">
        <ContentLibrary searchParams={searchParams} />
      </div>
    </>
  );
}
