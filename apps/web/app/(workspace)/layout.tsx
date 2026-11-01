import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { AppShell } from "@/components/layout/app-shell";
import { AuthenticationUnavailable } from "@/components/layout/authentication-unavailable";
import { getAuthenticationState } from "@/lib/auth-server";

export const instant = false;

export const metadata: Metadata = {
  title: "Workspace - NewsFlow AI",
  description: "Your protected NewsFlow AI content workspace.",
};

export default async function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  const authentication = await getAuthenticationState();
  if (authentication.status === "unauthenticated") {
    redirect("/login?reason=authentication_required");
  }
  if (authentication.status === "unavailable") {
    return <AuthenticationUnavailable />;
  }

  return <AppShell userEmail={authentication.user.email}>{children}</AppShell>;
}
