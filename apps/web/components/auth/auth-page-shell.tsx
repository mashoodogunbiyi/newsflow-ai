import Link from "next/link";
import type { ReactNode } from "react";

import { BrandMark } from "@/components/brand-mark";

type AuthPageShellProps = {
  eyebrow: string;
  title: string;
  description: string;
  children: ReactNode;
  alternatePrompt: string;
  alternateHref: string;
  alternateLabel: string;
};

const trustPoints = [
  "Your password is protected with Argon2id hashing.",
  "Your session identifier is never available to browser scripts.",
  "Nothing is published without your review.",
] as const;

export function AuthPageShell({
  eyebrow,
  title,
  description,
  children,
  alternatePrompt,
  alternateHref,
  alternateLabel,
}: AuthPageShellProps) {
  return (
    <main className="min-h-screen bg-[#f7f6f2] lg:grid lg:grid-cols-[minmax(0,0.92fr)_minmax(34rem,1.08fr)]">
      <section className="relative hidden overflow-hidden bg-emerald-950 px-10 py-12 text-white lg:flex lg:min-h-screen lg:flex-col xl:px-16">
        <div
          aria-hidden="true"
          className="absolute -right-24 -top-24 h-80 w-80 rounded-full border border-amber-300/20"
        />
        <div
          aria-hidden="true"
          className="absolute -right-8 top-24 h-48 w-48 rounded-full border border-white/10"
        />
        <div className="relative">
          <div className="inline-flex rounded-2xl bg-white px-4 py-3 shadow-lg shadow-black/10">
            <BrandMark />
          </div>
        </div>

        <div className="relative my-auto max-w-xl py-16">
          <p className="font-mono text-xs font-semibold uppercase tracking-[0.22em] text-amber-300">
            A responsible content workspace
          </p>
          <h2 className="mt-5 text-4xl font-semibold leading-tight tracking-[-0.04em] text-balance xl:text-5xl">
            A clear place to turn trusted facts into thoughtful professional content.
          </h2>
          <p className="mt-6 max-w-lg text-lg leading-8 text-white/65">
            Your account keeps drafts, source evidence, and editorial decisions together without
            weakening the project&apos;s review-first safeguards.
          </p>

          <ul className="mt-10 space-y-4" aria-label="Account security features">
            {trustPoints.map((point) => (
              <li className="flex items-start gap-3 text-sm leading-6 text-white/75" key={point}>
                <span
                  aria-hidden="true"
                  className="mt-1 grid h-5 w-5 shrink-0 place-items-center rounded-full bg-amber-300 text-[0.7rem] font-bold text-emerald-950"
                >
                  ✓
                </span>
                {point}
              </li>
            ))}
          </ul>
        </div>

        <p className="relative text-sm text-white/45">Fixture mode - no live CNN content.</p>
      </section>

      <section className="flex min-h-screen flex-col px-5 py-6 sm:px-8 sm:py-8 lg:px-12 xl:px-20">
        <div className="flex items-center justify-between lg:justify-end">
          <div className="lg:hidden">
            <BrandMark />
          </div>
          <div className="flex items-center gap-2 text-sm text-emerald-950/60">
            <span className="hidden sm:inline">{alternatePrompt}</span>
            <Link
              className="rounded-full border border-emerald-950/15 bg-white px-4 py-2 font-semibold text-emerald-950 transition hover:border-emerald-950/30 hover:bg-emerald-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800"
              href={alternateHref}
            >
              {alternateLabel}
            </Link>
          </div>
        </div>

        <div className="mx-auto flex w-full max-w-lg flex-1 flex-col justify-center py-12 sm:py-16">
          <p className="font-mono text-xs font-semibold uppercase tracking-[0.2em] text-emerald-700">
            {eyebrow}
          </p>
          <h1 className="mt-3 text-4xl font-semibold tracking-[-0.04em] text-emerald-950 sm:text-5xl">
            {title}
          </h1>
          <p className="mt-4 max-w-md text-base leading-7 text-emerald-950/60">{description}</p>
          <div className="mt-9">{children}</div>
        </div>

        <div className="flex flex-wrap items-center justify-center gap-x-5 gap-y-2 border-t border-emerald-950/10 pt-5 text-xs text-emerald-950/45 sm:justify-between">
          <span>Secure cookie-based sessions</span>
          <Link className="hover:text-emerald-800" href="/">
            Return to homepage
          </Link>
        </div>
      </section>
    </main>
  );
}
