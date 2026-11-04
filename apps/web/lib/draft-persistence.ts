import { isSavedDraft, type SavedDraft } from "@/types/library";

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export type SaveDraftInput = {
  editedText: string;
  generationId: string;
  selectedImageId: string | null;
  title: string;
};

export type SaveDraftResult =
  | { data: SavedDraft; status: "success" }
  | {
      message: string;
      reason: "authentication_required" | "conflict" | "invalid_request" | "unavailable";
      status: "error";
    };

function readCookie(name: string) {
  const prefix = `${encodeURIComponent(name)}=`;
  const cookie = document.cookie
    .split(";")
    .map((item) => item.trim())
    .find((item) => item.startsWith(prefix));
  if (!cookie) return null;
  try {
    return decodeURIComponent(cookie.slice(prefix.length));
  } catch {
    return null;
  }
}

async function safeErrorMessage(response: Response, fallback: string) {
  try {
    const payload = (await response.json()) as { error?: { message?: unknown } };
    const message = payload.error?.message;
    return typeof message === "string" && message.trim() && message.length <= 300
      ? message
      : fallback;
  } catch {
    return fallback;
  }
}

export async function saveGeneratedDraft(input: SaveDraftInput): Promise<SaveDraftResult> {
  const editedText = input.editedText;
  const title = input.title.trim();
  if (
    !UUID_PATTERN.test(input.generationId) ||
    (input.selectedImageId !== null && !UUID_PATTERN.test(input.selectedImageId)) ||
    !editedText.trim() ||
    editedText.length > 12_000 ||
    title.length > 200
  ) {
    return {
      status: "error",
      reason: "invalid_request",
      message: "Review the draft text and selected image before saving.",
    };
  }

  const csrfToken = readCookie("newsflow_csrf");
  if (!csrfToken) {
    return {
      status: "error",
      reason: "authentication_required",
      message: "Your session could not be confirmed. Sign in again before saving.",
    };
  }

  let response: Response;
  try {
    response = await fetch("/api/drafts", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": `draft:${globalThis.crypto.randomUUID()}`,
        "X-CSRF-Token": csrfToken,
      },
      body: JSON.stringify({
        generation_id: input.generationId,
        title: title || null,
        edited_text: editedText,
        selected_image_id: input.selectedImageId,
      }),
    });
  } catch {
    return {
      status: "error",
      reason: "unavailable",
      message: "The draft could not be saved right now. Your edits remain on this page.",
    };
  }

  if (!response.ok) {
    const reason =
      response.status === 401 || response.status === 403
        ? "authentication_required"
        : response.status === 409
          ? "conflict"
          : response.status === 422
            ? "invalid_request"
            : "unavailable";
    const fallback =
      reason === "authentication_required"
        ? "Your session has ended. Sign in again before saving."
        : reason === "conflict"
          ? "This generated draft is already saved. Open it from your content library."
          : reason === "invalid_request"
            ? "The draft could not be validated. Review it and try again."
            : "The draft could not be saved right now. Your edits remain on this page.";
    return { status: "error", reason, message: await safeErrorMessage(response, fallback) };
  }

  try {
    const payload: unknown = await response.json();
    if (!isSavedDraft(payload) || payload.generation.generation_id !== input.generationId) {
      throw new Error("Invalid saved draft response");
    }
    return { status: "success", data: payload };
  } catch {
    return {
      status: "error",
      reason: "unavailable",
      message: "The save response could not be verified. Check your library before retrying.",
    };
  }
}
