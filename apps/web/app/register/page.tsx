import type { Metadata } from "next";

import { AuthPageShell } from "@/components/auth/auth-page-shell";
import { CredentialsForm } from "@/components/auth/credentials-form";

export const metadata: Metadata = {
  title: "Create your account - NewsFlow AI",
  description: "Create a secure NewsFlow AI account for your content workspace.",
};

export default function RegisterPage() {
  return (
    <AuthPageShell
      alternateHref="/login"
      alternateLabel="Sign in"
      alternatePrompt="Already have an account?"
      description="Create an account to keep your future drafts, source evidence, and saved content connected to you."
      eyebrow="Start your workspace"
      title="Create your account"
    >
      <CredentialsForm mode="register" />
    </AuthPageShell>
  );
}
