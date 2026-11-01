import type { GenerationFailure, GenerationOperationResult } from "@/types/generation-state";
import {
  isImageAspectRatio,
  isImageComposition,
  isImageStyle,
  parseImageVersion,
  type ImageGenerationRequest,
  type ImageVersion,
} from "@/types/image-generation";
import { isPreviewImageId } from "@/types/preview";

type ApiErrorPayload = { error?: { code?: unknown; message?: unknown } };

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

function parseRetryAfter(value: string | null) {
  if (!value || !/^\d+$/.test(value)) return null;
  const seconds = Number(value);
  return Number.isSafeInteger(seconds) && seconds > 0 ? Math.min(seconds, 3_600) : null;
}

async function readSafeError(response: Response, fallback: string) {
  try {
    const payload = (await response.json()) as ApiErrorPayload;
    const message = payload.error?.message;
    const code = payload.error?.code;
    return {
      code: typeof code === "string" && /^[a-z0-9_]{1,100}$/.test(code) ? code : null,
      message:
        typeof message === "string" && message.trim() && message.length <= 300 ? message : fallback,
    };
  } catch {
    return { code: null, message: fallback };
  }
}

function failureForStatus(status: number, retryAfterSeconds: number | null): GenerationFailure {
  if (status === 401) {
    return {
      category: "authentication",
      message: "Your session has expired. Sign in again to generate an illustration.",
      retryAfterSeconds: null,
      retryable: false,
    };
  }
  if (status === 403) {
    return {
      category: "permissions",
      message: "Current source rights or safety rules do not permit this illustration.",
      retryAfterSeconds: null,
      retryable: false,
    };
  }
  if (status === 404 || status === 422) {
    return {
      category: "validation",
      message: "The draft or image preferences are no longer valid for generation.",
      retryAfterSeconds: null,
      retryable: false,
    };
  }
  if (status === 409) {
    return {
      category: "conflict",
      message: "A matching image request is already being processed.",
      retryAfterSeconds,
      retryable: true,
    };
  }
  if (status === 429) {
    return {
      category: "usage_limit",
      message: "Your image generation allowance is temporarily limited.",
      retryAfterSeconds,
      retryable: true,
    };
  }
  if (status === 504) {
    return {
      category: "timeout",
      message: "The image provider took too long to respond. Please try again deliberately.",
      retryAfterSeconds,
      retryable: true,
    };
  }
  return {
    category: "service",
    message: "Illustration generation is temporarily unavailable. Your draft is still here.",
    retryAfterSeconds,
    retryable: true,
  };
}

export function createImageRequestKey() {
  return `image:${globalThis.crypto.randomUUID()}`;
}

function isValidRequest(request: ImageGenerationRequest) {
  const hasContext =
    request.action === "generate"
      ? isPreviewImageId(request.generation_id)
      : isPreviewImageId(request.parent_image_id);
  return (
    hasContext &&
    isImageStyle(request.style) &&
    isImageAspectRatio(request.aspect_ratio) &&
    isImageComposition(request.composition)
  );
}

export async function requestImageGeneration(
  request: ImageGenerationRequest,
  idempotencyKey: string,
  signal?: AbortSignal,
): Promise<GenerationOperationResult<ImageVersion>> {
  if (!isValidRequest(request) || !/^image:[0-9a-f-]{36}$/i.test(idempotencyKey)) {
    return {
      error: {
        category: "validation",
        message: "Choose valid image preferences before generating.",
        retryAfterSeconds: null,
        retryable: false,
      },
      status: "error",
    };
  }

  const csrfToken = readCookie("newsflow_csrf");
  if (!csrfToken) {
    return {
      error: failureForStatus(401, null),
      status: "error",
    };
  }

  const url =
    request.action === "generate"
      ? "/api/images"
      : `/api/images/${encodeURIComponent(request.parent_image_id)}/regenerate`;
  const body =
    request.action === "generate"
      ? {
          generation_id: request.generation_id,
          style: request.style,
          aspect_ratio: request.aspect_ratio,
          composition: request.composition,
        }
      : {
          style: request.style,
          aspect_ratio: request.aspect_ratio,
          composition: request.composition,
        };

  let response: Response;
  try {
    response = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": idempotencyKey,
        "X-CSRF-Token": csrfToken,
      },
      body: JSON.stringify(body),
      signal,
    });
  } catch {
    return {
      error: {
        category: "network",
        message: "The image service could not be reached. Your draft is still here.",
        retryAfterSeconds: null,
        retryable: true,
      },
      status: "error",
    };
  }

  if (!response.ok) {
    const retryAfterSeconds = parseRetryAfter(response.headers.get("retry-after"));
    let failure = failureForStatus(response.status, retryAfterSeconds);
    const safeError = await readSafeError(response, failure.message);
    if (response.status === 403 && safeError.code === "csrf_validation_failed") {
      failure = failureForStatus(401, null);
    }
    return {
      error: {
        ...failure,
        message: failure.category === "authentication" ? failure.message : safeError.message,
      },
      status: "error",
    };
  }

  try {
    const version = parseImageVersion(await response.json());
    const expectedParent = request.action === "regenerate" ? request.parent_image_id : null;
    if (!version || version.parentId !== expectedParent) {
      throw new Error("Unexpected image response.");
    }
    return { data: version, status: "success" };
  } catch {
    return {
      error: {
        category: "service",
        message: "The generated image response could not be verified. Please try again.",
        retryAfterSeconds: null,
        retryable: true,
      },
      status: "error",
    };
  }
}
