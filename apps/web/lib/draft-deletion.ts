export type DraftDeletionResult =
  | { status: "success" }
  | {
      status: "error";
      reason: "authentication_required" | "not_found" | "security_error" | "unavailable";
    };

function readCookie(name: string) {
  const prefix = `${name}=`;
  const match = document.cookie
    .split(";")
    .map((value) => value.trim())
    .find((value) => value.startsWith(prefix));
  return match ? decodeURIComponent(match.slice(prefix.length)) : null;
}

export async function deleteSavedDraft(draftId: string): Promise<DraftDeletionResult> {
  const csrfToken = readCookie("newsflow_csrf");
  if (!csrfToken) return { status: "error", reason: "security_error" };

  try {
    const response = await fetch(`/api/drafts/${encodeURIComponent(draftId)}`, {
      method: "DELETE",
      headers: { "X-CSRF-Token": csrfToken },
    });
    if (response.status === 204) return { status: "success" };
    if (response.status === 401) return { status: "error", reason: "authentication_required" };
    if (response.status === 403) return { status: "error", reason: "security_error" };
    if (response.status === 404) return { status: "error", reason: "not_found" };
    return { status: "error", reason: "unavailable" };
  } catch {
    return { status: "error", reason: "unavailable" };
  }
}
