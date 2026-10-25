import type { Metadata } from "next";

import { AuthPageShell } from "@/components/auth/auth-page-shell";
import { CredentialsForm } from "@/components/auth/credentials-form";

export const instant = false;

export const metadata: Metadata = {
  title: "Sign in - NewsFlow AI",
  description: "Sign in securely to your NewsFlow AI workspace.",
};

const reasonMessages: Record<string, string> = {
  authentication_required: "Sign in to continue to your dashboard.",
  logged_out: "You have been logged out securely.",
  session_expired: "Your session has ended. Sign in again to continue.",
};

export default async function LoginPage({ searchParams }: PageProps<"/login">) {
  const reason = (await searchParams).reason;
  const message = typeof reason === "string" ? reasonMessages[reason] : undefined;

  return (
    <AuthPageShell
      alternateHref="/register"
      alternateLabel="Create account"
      alternatePrompt="New to NewsFlow AI?"
      description="Return to your review-first workspace and continue where you left off."
      eyebrow="Welcome back"
      title="Sign in to NewsFlow AI"
    >
      {message ? (
        <p
          aria-live="polite"
          className="mb-5 rounded-xl border border-emerald-700/20 bg-emerald-50 px-4 py-3 text-sm leading-6 text-emerald-950"
          role="status"
        >
          {message}
        </p>
      ) : null}
      <CredentialsForm mode="login" />
    </AuthPageShell>
  );
}
