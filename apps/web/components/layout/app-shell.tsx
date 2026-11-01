import type { ReactNode } from "react";

import { LogoutButton } from "@/components/auth/logout-button";
import { BrandMark } from "@/components/brand-mark";
import { DesktopNavigation, MobileNavigation } from "@/components/layout/app-navigation";
import { StatusBadge } from "@/components/ui/status-badge";

type AppShellProps = {
  children: ReactNode;
  userEmail: string;
};

function AccountSummary({ userEmail }: { userEmail: string }) {
  return (
    <div className="rounded-3xl border border-white/10 bg-white/5 p-4">
      <div className="flex items-center gap-3">
        <span
          aria-hidden="true"
          className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-amber-300 text-sm font-bold uppercase text-emerald-950"
        >
          {userEmail.slice(0, 1)}
        </span>
        <div className="min-w-0">
          <p className="text-xs text-white/45">Signed in as</p>
          <p className="truncate text-sm font-semibold text-white">{userEmail}</p>
        </div>
      </div>
      <div className="mt-4 border-t border-white/10 pt-4 [&_button]:w-full [&_button]:border-white/15 [&_button]:bg-white/10 [&_button]:text-white [&_button]:hover:bg-white/15">
        <LogoutButton />
      </div>
    </div>
  );
}

export function AppShell({ children, userEmail }: AppShellProps) {
  return (
    <div className="min-h-screen bg-[#f7f6f2] lg:grid lg:grid-cols-[17rem_minmax(0,1fr)]">
      <a
        className="fixed left-4 top-4 z-[100] -translate-y-24 rounded-full bg-amber-300 px-4 py-2 text-sm font-bold text-emerald-950 transition focus:translate-y-0 focus:outline-2 focus:outline-offset-2 focus:outline-emerald-950"
        href="#workspace-content"
      >
        Skip to main content
      </a>

      <aside className="sticky top-0 hidden h-screen flex-col overflow-y-auto bg-emerald-950 p-5 lg:flex">
        <div className="rounded-2xl bg-white px-3.5 py-3">
          <BrandMark href="/dashboard" />
        </div>
        <div className="mt-5">
          <StatusBadge tone="warning">Fixture data only</StatusBadge>
        </div>
        <DesktopNavigation />
        <div className="mt-auto pt-8">
          <AccountSummary userEmail={userEmail} />
        </div>
      </aside>

      <div className="min-w-0">
        <header className="sticky top-0 z-40 border-b border-emerald-950/10 bg-[#f7f6f2]/90 px-5 py-3 backdrop-blur lg:hidden">
          <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-4">
            <BrandMark href="/dashboard" />
            <MobileNavigation userEmail={userEmail} />
          </div>
        </header>
        <main
          className="mx-auto w-full max-w-7xl px-5 py-8 sm:px-8 sm:py-12 lg:px-12 lg:py-14"
          id="workspace-content"
          tabIndex={-1}
        >
          {children}
        </main>
      </div>
    </div>
  );
}
