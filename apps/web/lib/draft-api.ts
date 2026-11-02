import { cookies } from "next/headers";

import {
  isSavedDraft,
  isSavedDraftPage,
  isSavedDraftVersion,
  isSavedDraftVersionPage,
  type SavedDraft,
  type SavedDraftPage,
  type SavedDraftVersion,
  type SavedDraftVersionPage,
} from "@/types/library";

const SESSION_COOKIE_NAME = "newsflow_session";
export const LIBRARY_PAGE_SIZE = 6;
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export type SavedDraftPageResult =
  | { data: SavedDraftPage; status: "success" }
  | {
      reason: "authentication_required" | "invalid_request" | "unavailable";
      status: "error";
    };

export type SavedDraftDetailResult =
  | { data: SavedDraft; status: "success" }
  | {
      reason: "authentication_required" | "invalid_request" | "not_found" | "unavailable";
      status: "error";
    };

export type SavedDraftVersionPageResult =
  | { data: SavedDraftVersionPage; status: "success" }
  | {
      reason: "authentication_required" | "invalid_request" | "not_found" | "unavailable";
      status: "error";
    };

export type SavedDraftVersionDetailResult =
  | { data: SavedDraftVersion; status: "success" }
  | {
      reason: "authentication_required" | "invalid_request" | "not_found" | "unavailable";
      status: "error";
    };

function getBackendBaseUrl() {
  const configuredUrl =
    process.env.API_INTERNAL_BASE_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "http://localhost:8000";

  return configuredUrl.replace(/\/+$/, "");
}

async function getSessionCookie() {
  return (await cookies()).get(SESSION_COOKIE_NAME)?.value;
}

function privateHeaders(sessionCookie: string) {
  return {
    Accept: "application/json",
    Cookie: `${SESSION_COOKIE_NAME}=${encodeURIComponent(sessionCookie)}`,
  };
}

export async function getSavedDraftPage(page = 1): Promise<SavedDraftPageResult> {
  if (!Number.isSafeInteger(page) || page < 1) {
    return { status: "error", reason: "invalid_request" };
  }
  const sessionCookie = await getSessionCookie();
  if (!sessionCookie) {
    return { status: "error", reason: "authentication_required" };
  }

  const parameters = new URLSearchParams({
    page: String(page),
    page_size: String(LIBRARY_PAGE_SIZE),
  });
  try {
    const response = await fetch(`${getBackendBaseUrl()}/api/v1/drafts?${parameters}`, {
      headers: privateHeaders(sessionCookie),
      cache: "no-store",
    });
    if (response.status === 401) {
      return { status: "error", reason: "authentication_required" };
    }
    if (response.status === 422) {
      return { status: "error", reason: "invalid_request" };
    }
    if (!response.ok) {
      return { status: "error", reason: "unavailable" };
    }

    const payload: unknown = await response.json();
    return isSavedDraftPage(payload)
      ? { status: "success", data: payload }
      : { status: "error", reason: "unavailable" };
  } catch {
    return { status: "error", reason: "unavailable" };
  }
}

export async function getSavedDraft(savedDraftId: string): Promise<SavedDraftDetailResult> {
  if (!UUID_PATTERN.test(savedDraftId)) {
    return { status: "error", reason: "invalid_request" };
  }
  const sessionCookie = await getSessionCookie();
  if (!sessionCookie) {
    return { status: "error", reason: "authentication_required" };
  }

  try {
    const response = await fetch(
      `${getBackendBaseUrl()}/api/v1/drafts/${encodeURIComponent(savedDraftId)}`,
      {
        headers: privateHeaders(sessionCookie),
        cache: "no-store",
      },
    );
    if (response.status === 401) {
      return { status: "error", reason: "authentication_required" };
    }
    if (response.status === 404) {
      return { status: "error", reason: "not_found" };
    }
    if (response.status === 422) {
      return { status: "error", reason: "invalid_request" };
    }
    if (!response.ok) {
      return { status: "error", reason: "unavailable" };
    }

    const payload: unknown = await response.json();
    return isSavedDraft(payload)
      ? { status: "success", data: payload }
      : { status: "error", reason: "unavailable" };
  } catch {
    return { status: "error", reason: "unavailable" };
  }
}

export async function getSavedDraftVersions(
  savedDraftId: string,
  page = 1,
): Promise<SavedDraftVersionPageResult> {
  if (!UUID_PATTERN.test(savedDraftId) || !Number.isSafeInteger(page) || page < 1) {
    return { status: "error", reason: "invalid_request" };
  }
  const sessionCookie = await getSessionCookie();
  if (!sessionCookie) {
    return { status: "error", reason: "authentication_required" };
  }
  const parameters = new URLSearchParams({ page: String(page), page_size: "20" });
  try {
    const response = await fetch(
      `${getBackendBaseUrl()}/api/v1/drafts/${encodeURIComponent(savedDraftId)}/versions?${parameters}`,
      { headers: privateHeaders(sessionCookie), cache: "no-store" },
    );
    if (response.status === 401) {
      return { status: "error", reason: "authentication_required" };
    }
    if (response.status === 404) {
      return { status: "error", reason: "not_found" };
    }
    if (response.status === 422) {
      return { status: "error", reason: "invalid_request" };
    }
    if (!response.ok) {
      return { status: "error", reason: "unavailable" };
    }
    const payload: unknown = await response.json();
    return isSavedDraftVersionPage(payload)
      ? { status: "success", data: payload }
      : { status: "error", reason: "unavailable" };
  } catch {
    return { status: "error", reason: "unavailable" };
  }
}

export async function getSavedDraftVersion(
  savedDraftId: string,
  versionId: string,
): Promise<SavedDraftVersionDetailResult> {
  if (!UUID_PATTERN.test(savedDraftId) || !UUID_PATTERN.test(versionId)) {
    return { status: "error", reason: "invalid_request" };
  }
  const sessionCookie = await getSessionCookie();
  if (!sessionCookie) {
    return { status: "error", reason: "authentication_required" };
  }
  try {
    const response = await fetch(
      `${getBackendBaseUrl()}/api/v1/drafts/${encodeURIComponent(savedDraftId)}/versions/${encodeURIComponent(versionId)}`,
      { headers: privateHeaders(sessionCookie), cache: "no-store" },
    );
    if (response.status === 401) {
      return { status: "error", reason: "authentication_required" };
    }
    if (response.status === 404) {
      return { status: "error", reason: "not_found" };
    }
    if (response.status === 422) {
      return { status: "error", reason: "invalid_request" };
    }
    if (!response.ok) {
      return { status: "error", reason: "unavailable" };
    }
    const payload: unknown = await response.json();
    return isSavedDraftVersion(payload)
      ? { status: "success", data: payload }
      : { status: "error", reason: "unavailable" };
  } catch {
    return { status: "error", reason: "unavailable" };
  }
}
