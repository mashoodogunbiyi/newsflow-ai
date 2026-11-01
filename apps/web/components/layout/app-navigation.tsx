"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { LogoutButton } from "@/components/auth/logout-button";

type NavigationItem = {
  href: string;
  icon: "account" | "create" | "dashboard" | "library";
  label: string;
};

const navigationItems: readonly NavigationItem[] = [
  { href: "/dashboard", icon: "dashboard", label: "Dashboard" },
  { href: "/generate", icon: "create", label: "Create Post" },
  { href: "/library", icon: "library", label: "Content Library" },
  { href: "/account", icon: "account", label: "Account" },
];

function NavigationIcon({ name }: { name: NavigationItem["icon"] }) {
  const common = {
    "aria-hidden": true,
    className: "h-5 w-5 shrink-0",
    fill: "none",
    stroke: "currentColor",
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    strokeWidth: 1.8,
    viewBox: "0 0 24 24",
  };

  if (name === "dashboard") {
    return (
      <svg {...common}>
        <rect height="7" rx="1.5" width="7" x="3" y="3" />
        <rect height="7" rx="1.5" width="7" x="14" y="3" />
        <rect height="7" rx="1.5" width="7" x="3" y="14" />
        <rect height="7" rx="1.5" width="7" x="14" y="14" />
      </svg>
    );
  }
  if (name === "create") {
    return (
      <svg {...common}>
        <path d="M12 5v14M5 12h14" />
        <circle cx="12" cy="12" r="9" />
      </svg>
    );
  }
  if (name === "library") {
    return (
      <svg {...common}>
        <path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v16H6.5A2.5 2.5 0 0 0 4 21.5z" />
        <path d="M4 5.5v16M8 7h8" />
      </svg>
    );
  }
  return (
    <svg {...common}>
      <circle cx="12" cy="8" r="4" />
      <path d="M4.5 21a7.5 7.5 0 0 1 15 0" />
    </svg>
  );
}

function NavigationLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();

  return (
    <ul className="space-y-1.5">
      {navigationItems.map((item) => {
        const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
        return (
          <li key={item.href}>
            <Link
              aria-current={isActive ? "page" : undefined}
              className={`flex min-h-11 items-center gap-3 rounded-2xl px-3.5 py-2.5 text-sm font-semibold transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-300 ${
                isActive
                  ? "bg-white text-emerald-950 shadow-sm"
                  : "text-white/65 hover:bg-white/10 hover:text-white"
              }`}
              href={item.href}
              onClick={onNavigate}
            >
              <NavigationIcon name={item.icon} />
              <span>{item.label}</span>
              {isActive ? (
                <span className="ml-auto h-2 w-2 rounded-full bg-amber-300" aria-hidden="true" />
              ) : null}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

export function DesktopNavigation() {
  return (
    <nav aria-label="Workspace" className="mt-8">
      <NavigationLinks />
    </nav>
  );
}

export function MobileNavigation({ userEmail }: { userEmail: string }) {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    }
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, []);

  return (
    <div className="relative lg:hidden">
      <button
        aria-controls="mobile-workspace-navigation"
        aria-expanded={isOpen}
        aria-label={isOpen ? "Close navigation" : "Open navigation"}
        className="grid h-11 w-11 place-items-center rounded-2xl border border-emerald-950/10 bg-white text-emerald-950 shadow-sm transition hover:bg-emerald-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700"
        onClick={() => setIsOpen((current) => !current)}
        type="button"
      >
        <span aria-hidden="true" className="space-y-1.5">
          <span className="block h-0.5 w-5 bg-current" />
          <span className="block h-0.5 w-5 bg-current" />
          <span className="block h-0.5 w-5 bg-current" />
        </span>
      </button>
      {isOpen ? (
        <nav
          aria-label="Mobile workspace"
          className="absolute right-0 top-14 z-50 w-[min(19rem,calc(100vw-2.5rem))] rounded-3xl border border-white/10 bg-emerald-950 p-3 shadow-2xl shadow-emerald-950/25"
          id="mobile-workspace-navigation"
        >
          <NavigationLinks onNavigate={() => setIsOpen(false)} />
          <div className="mt-3 border-t border-white/10 px-1 pt-3">
            <p className="px-3 text-xs text-white/45">Signed in as</p>
            <p className="mt-1 truncate px-3 text-sm font-semibold text-white">{userEmail}</p>
            <div className="mt-3 [&_button]:w-full [&_button]:border-white/15 [&_button]:bg-white/10 [&_button]:text-white [&_button]:hover:bg-white/15">
              <LogoutButton />
            </div>
          </div>
        </nav>
      ) : null}
    </div>
  );
}
