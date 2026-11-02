import { isPreviewImageId } from "@/types/preview";

export type ExportFailureReason =
  | "authentication_required"
  | "clipboard_denied"
  | "clipboard_unavailable"
  | "empty_content"
  | "image_not_found"
  | "invalid_image"
  | "service_unavailable";

export type ExportResult =
  { status: "success" } | { message: string; reason: ExportFailureReason; status: "error" };

const DOWNLOAD_FILENAME_PATTERN =
  /^attachment;\s*filename="(newsflow-ai-illustration-[0-9a-f-]{36}\.(?:jpg|png|webp))"$/i;
const ALLOWED_MEDIA_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);

export async function copyPostText(text: string): Promise<ExportResult> {
  if (!text.trim()) {
    return {
      status: "error",
      reason: "empty_content",
      message: "Add reviewed text before copying the post.",
    };
  }
  if (!navigator.clipboard?.writeText) {
    return {
      status: "error",
      reason: "clipboard_unavailable",
      message: "Clipboard copying is not supported by this browser.",
    };
  }
  try {
    await navigator.clipboard.writeText(text);
    return { status: "success" };
  } catch {
    return {
      status: "error",
      reason: "clipboard_denied",
      message: "Clipboard access was denied. Check your browser permission and try again.",
    };
  }
}

function downloadFailure(status: number): ExportResult {
  if (status === 401) {
    return {
      status: "error",
      reason: "authentication_required",
      message: "Your session has expired. Sign in again before downloading.",
    };
  }
  if (status === 404) {
    return {
      status: "error",
      reason: "image_not_found",
      message: "The selected illustration is no longer available.",
    };
  }
  return {
    status: "error",
    reason: "service_unavailable",
    message: "The illustration could not be downloaded. Please try again.",
  };
}

export async function downloadSelectedImage(imageId: string): Promise<ExportResult> {
  if (!isPreviewImageId(imageId)) {
    return {
      status: "error",
      reason: "invalid_image",
      message: "Select a valid generated illustration before downloading.",
    };
  }

  let response: Response;
  try {
    response = await fetch(`/api/images/${encodeURIComponent(imageId)}/download`, {
      method: "GET",
      credentials: "same-origin",
      cache: "no-store",
    });
  } catch {
    return downloadFailure(503);
  }
  if (!response.ok) {
    return downloadFailure(response.status);
  }

  const mediaType = response.headers.get("content-type")?.split(";", 1)[0].trim();
  const disposition = response.headers.get("content-disposition") ?? "";
  const filename = DOWNLOAD_FILENAME_PATTERN.exec(disposition)?.[1];
  if (!mediaType || !ALLOWED_MEDIA_TYPES.has(mediaType) || !filename) {
    return downloadFailure(503);
  }

  try {
    const objectUrl = URL.createObjectURL(await response.blob());
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = filename;
    link.hidden = true;
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(objectUrl);
    return { status: "success" };
  } catch {
    return downloadFailure(503);
  }
}
