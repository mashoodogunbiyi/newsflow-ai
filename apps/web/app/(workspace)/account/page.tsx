import type { Metadata } from "next";

import { PageHeader } from "@/components/layout/page-header";
import { Card } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";

export const metadata: Metadata = {
  title: "Account - NewsFlow AI",
  description: "Review your NewsFlow AI account security status.",
};

export default function AccountPage() {
  return (
    <>
      <PageHeader
        description="Your session and private content remain controlled by the FastAPI backend. Account-management actions will be added only with matching backend authorisation."
        eyebrow="Account"
        title="Security stays behind every screen."
      />

      <div className="mt-10 grid gap-6 lg:grid-cols-2">
        <Card>
          <StatusBadge tone="success">Authenticated session</StatusBadge>
          <h2 className="mt-5 text-2xl font-semibold tracking-[-0.03em]">Session protection</h2>
          <p className="mt-3 text-sm leading-7 text-emerald-950/55">
            The browser keeps the session identifier in an HTTP-only cookie. Client-side code does
            not store or display the identifier.
          </p>
        </Card>
        <Card>
          <StatusBadge tone="neutral">Backend enforced</StatusBadge>
          <h2 className="mt-5 text-2xl font-semibold tracking-[-0.03em]">Content ownership</h2>
          <p className="mt-3 text-sm leading-7 text-emerald-950/55">
            Navigation visibility does not grant access. FastAPI must still authorise every private
            content request using the authenticated owner.
          </p>
        </Card>
      </div>
    </>
  );
}
