import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";

import { LogoutButton } from "@/components/auth/logout-button";
import { BrandMark } from "@/components/brand-mark";
import { getAuthenticationState } from "@/lib/auth-server";

export const instant = false;

export const metadata: Metadata = {
  title: "Your dashboard - NewsFlow AI",
  description: "Your protected NewsFlow AI content workspace.",
};

const workspaceSteps = [
  {
    number: "01",
    title: "Choose an authorised story",
    detail: "Article browsing arrives in the next product stage.",
  },
  {
    number: "02",
    title: "Generate a grounded draft",
    detail: "Every claim will remain linked to permitted source facts.",
  },
  {
    number: "03",
    title: "Review and save",
    detail: "You keep final editorial control before anything leaves the workspace.",
  },
] as const;

function AuthenticationUnavailable() {
  return (
    <main className="grid min-h-screen place-items-center bg-[#f7f6f2] px-5 py-12">
      <div className="w-full max-w-lg rounded-3xl border border-emerald-950/10 bg-white p-7 text-center shadow-xl shadow-emerald-950/5 sm:p-10">
        <div className="mx-auto w-fit">
          <BrandMark />
        </div>
        <p className="mt-8 font-mono text-xs font-semibold uppercase tracking-[0.2em] text-amber-700">
          Temporary connection problem
        </p>
        <h1 className="mt-3 text-3xl font-semibold tracking-[-0.035em] text-emerald-950">
          We cannot confirm your session right now.
        </h1>
        <p className="mt-4 leading-7 text-emerald-950/60">
          Your account has not been changed. Check that the backend is running, then try the
          dashboard again.
        </p>
        <Link
          className="mt-7 inline-flex min-h-11 items-center justify-center rounded-full bg-emerald-950 px-5 py-2.5 text-sm font-semibold text-white hover:bg-emerald-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800"
          href="/dashboard"
        >
          Try again
        </Link>
      </div>
    </main>
  );
}

export default async function DashboardPage() {
  const authentication = await getAuthenticationState();
  if (authentication.status === "unauthenticated") {
    redirect("/login?reason=authentication_required");
  }
  if (authentication.status === "unavailable") {
    return <AuthenticationUnavailable />;
  }

  const { user } = authentication;

  return (
    <main className="min-h-screen bg-[#f7f6f2]">
      <header className="border-b border-emerald-950/10 bg-white/80 backdrop-blur">
        <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-5 px-5 py-4 sm:px-8 lg:px-12">
          <BrandMark />
          <div className="flex items-center gap-3 sm:gap-5">
            <div className="hidden text-right sm:block">
              <p className="text-xs font-medium text-emerald-950/45">Signed in as</p>
              <p className="max-w-64 truncate text-sm font-semibold text-emerald-950">
                {user.email}
              </p>
            </div>
            <LogoutButton />
          </div>
        </div>
      </header>

      <div className="mx-auto w-full max-w-7xl px-5 py-10 sm:px-8 sm:py-14 lg:px-12 lg:py-16">
        <section className="grid gap-8 lg:grid-cols-[1fr_auto] lg:items-end">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-800/10 bg-white px-3 py-1.5 text-xs font-semibold text-emerald-800 shadow-sm">
              <span className="h-2 w-2 rounded-full bg-emerald-600" />
              Account session active
            </div>
            <p className="mt-7 font-mono text-xs font-semibold uppercase tracking-[0.22em] text-emerald-700">
              Your protected workspace
            </p>
            <h1 className="mt-3 max-w-3xl text-4xl font-semibold tracking-[-0.045em] text-emerald-950 text-balance sm:text-5xl lg:text-6xl">
              Your NewsFlow dashboard is ready.
            </h1>
            <p className="mt-5 max-w-2xl text-lg leading-8 text-emerald-950/60">
              The secure account foundation is in place. Article selection and generation tools will
              arrive here as the next stages are completed.
            </p>
          </div>
          <div className="rounded-2xl border border-amber-700/15 bg-amber-50 px-5 py-4 lg:max-w-xs">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-amber-800">
              Data access status
            </p>
            <p className="mt-2 text-sm leading-6 text-emerald-950/70">
              Fixture mode remains active. No live CNN content is connected.
            </p>
          </div>
        </section>

        <section aria-labelledby="account-overview" className="mt-12">
          <h2 className="sr-only" id="account-overview">
            Account overview
          </h2>
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="rounded-2xl border border-emerald-950/10 bg-white p-5 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-950/45">
                Account
              </p>
              <p className="mt-3 text-lg font-semibold text-emerald-950">Active</p>
              <p className="mt-1 truncate text-sm text-emerald-950/55">{user.email}</p>
            </div>
            <div className="rounded-2xl border border-emerald-950/10 bg-white p-5 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-950/45">
                Saved content
              </p>
              <p className="mt-3 text-lg font-semibold text-emerald-950">0 items</p>
              <p className="mt-1 text-sm text-emerald-950/55">Your library starts clean.</p>
            </div>
            <div className="rounded-2xl border border-emerald-950/10 bg-white p-5 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-950/45">
                Source mode
              </p>
              <p className="mt-3 text-lg font-semibold text-emerald-950">Synthetic fixtures</p>
              <p className="mt-1 text-sm text-emerald-950/55">Safe for development.</p>
            </div>
          </div>
        </section>

        <section className="mt-6 overflow-hidden rounded-3xl border border-emerald-950/10 bg-emerald-950 text-white shadow-xl shadow-emerald-950/10">
          <div className="grid lg:grid-cols-[0.72fr_1.28fr]">
            <div className="border-b border-white/10 p-7 sm:p-9 lg:border-b-0 lg:border-r">
              <p className="font-mono text-xs font-semibold uppercase tracking-[0.2em] text-amber-300">
                What comes next
              </p>
              <h2 className="mt-4 text-3xl font-semibold tracking-[-0.035em]">
                A deliberate content workflow.
              </h2>
              <p className="mt-4 text-sm leading-7 text-white/60">
                The dashboard is intentionally simple while the core creation features are built and
                tested.
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
        </section>
      </div>
    </main>
  );
}
