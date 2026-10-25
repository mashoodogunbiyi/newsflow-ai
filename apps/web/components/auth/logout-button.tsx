"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import type { ApiErrorPayload } from "@/lib/auth-types";

function readCookie(name: string) {
  const prefix = `${encodeURIComponent(name)}=`;
  const cookie = document.cookie
    .split(";")
    .map((item) => item.trim())
    .find((item) => item.startsWith(prefix));
  return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : null;
}

export function LogoutButton() {
  const router = useRouter();
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function logout() {
    const csrfToken = readCookie("newsflow_csrf");
    if (!csrfToken) {
      router.replace("/login?reason=session_expired");
      router.refresh();
      return;
    }

    setIsLoggingOut(true);
    setError(null);
    try {
      const response = await fetch("/api/auth/logout", {
        method: "POST",
        credentials: "same-origin",
        headers: { "X-CSRF-Token": csrfToken },
      });

      if (response.ok || response.status === 401) {
        router.replace("/login?reason=logged_out");
        router.refresh();
        return;
      }

      let message = "We could not log you out. Please try again.";
      try {
        const payload = (await response.json()) as ApiErrorPayload;
        message = payload.error?.message ?? message;
      } catch {
        // Retain the safe fallback message.
      }
      setError(message);
    } catch {
      setError("Authentication is temporarily unavailable. Please try again.");
    } finally {
      setIsLoggingOut(false);
    }
  }

  return (
    <div className="flex flex-col items-end gap-2">
      <button
        className="inline-flex min-h-10 items-center justify-center rounded-full border border-emerald-950/15 bg-white px-4 py-2 text-sm font-semibold text-emerald-950 transition hover:border-emerald-950/30 hover:bg-emerald-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800 disabled:cursor-wait disabled:opacity-60"
        disabled={isLoggingOut}
        onClick={logout}
        type="button"
      >
        {isLoggingOut ? "Logging out..." : "Log out"}
      </button>
      {error ? (
        <p aria-live="assertive" className="max-w-64 text-right text-xs text-red-800" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
