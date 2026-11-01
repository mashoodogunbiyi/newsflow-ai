import Link from "next/link";

import { BrandMark } from "@/components/brand-mark";
import { buttonStyles } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export function AuthenticationUnavailable() {
  return (
    <main className="grid min-h-screen place-items-center bg-[#f7f6f2] px-5 py-12">
      <Card className="w-full max-w-lg text-center">
        <div className="mx-auto w-fit">
          <BrandMark />
        </div>
        <p className="mt-8 font-mono text-xs font-semibold uppercase tracking-[0.2em] text-amber-700">
          Temporary connection problem
        </p>
        <h1 className="mt-3 text-3xl font-semibold tracking-[-0.035em] text-emerald-950">
          We cannot confirm your session right now.
        </h1>
        <p className="mt-4 leading-7 text-emerald-950/70">
          Your account has not been changed. Check that the backend is running, then try again.
        </p>
        <Link className={`${buttonStyles("primary")} mt-7`} href="/dashboard">
          Try again
        </Link>
      </Card>
    </main>
  );
}
