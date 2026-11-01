import {
  isArticleId,
  isGenerationLength,
  isGenerationResponse,
  isGenerationTone,
  type GenerationRequest,
  type GenerationResponse,
} from "@/types/generation";

type GenerationFailureReason =
  | "authentication_required"
  | "generation_restricted"
  | "invalid_request"
  | "request_conflict"
  | "usage_limited"
  | "unavailable";

export type GenerationResult =
  | { data: GenerationResponse; status: "success" }
  | {
      message: string;
      reason: GenerationFailureReason;
      retryAfterSeconds: number | null;
      status: "error";
    };

type ApiErrorPayload = {
  error?: {
    code?: unknown;
    message?: unknown;
  };
};

function readCookie(name: string) {
  const prefix = `${encodeURIComponent(name)}=`;
  const cookie = document.cookie
    .split(";")
    .map((item) => item.trim())
    .find((item) => item.startsWith(prefix));
  if (!cookie) {
    return null;
  }

  try {
    return decodeURIComponent(cookie.slice(prefix.length));
  } catch {
    return null;
  }
}

function parseRetryAfter(value: string | null) {
  if (!value || !/^\d+$/.test(value)) {
    return null;
  }

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

function failureForStatus(status: number): {
  fallback: string;
  reason: GenerationFailureReason;
} {
  if (status === 401) {
    return {
      fallback: "Your session has expired. Sign in again to generate a draft.",
      reason: "authentication_required",
    };
  }
  if (status === 403) {
    return {
      fallback: "This article is not currently authorised for draft generation.",
      reason: "generation_restricted",
    };
  }
  if (status === 404) {
    return {
      fallback: "The selected article is no longer available. Choose another article.",
      reason: "invalid_request",
    };
  }
  if (status === 409) {
    return {
      fallback: "A matching generation request is already active. Please wait before retrying.",
      reason: "request_conflict",
    };
  }
  if (status === 422) {
    return {
      fallback: "The selected article or writing preferences are not valid for generation.",
      reason: "invalid_request",
    };
  }
  if (status === 429) {
    return {
      fallback: "Your generation allowance is temporarily limited. Please try again later.",
      reason: "usage_limited",
    };
  }

  return {
    fallback: "Draft generation is temporarily unavailable. Your selections are still here.",
    reason: "unavailable",
  };
}

export function createGenerationRequestKey() {
  return `generation:${globalThis.crypto.randomUUID()}`;
}

export async function generateLinkedInDraft(
  request: GenerationRequest,
  idempotencyKey: string,
): Promise<GenerationResult> {
  if (
    !isArticleId(request.article_id) ||
    !isGenerationTone(request.tone) ||
    !isGenerationLength(request.length) ||
    !/^generation:[0-9a-f-]{36}$/i.test(idempotencyKey)
  ) {
    return {
      message: "Choose a valid article, tone, and post length before generating.",
      reason: "invalid_request",
      retryAfterSeconds: null,
      status: "error",
    };
  }

  const csrfToken = readCookie("newsflow_csrf");
  if (!csrfToken) {
    return {
      message: "Your session could not be confirmed. Sign in again to generate a draft.",
      reason: "authentication_required",
      retryAfterSeconds: null,
      status: "error",
    };
  }

  let response: Response;
  try {
    response = await fetch("/api/generations", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": idempotencyKey,
        "X-CSRF-Token": csrfToken,
      },
      body: JSON.stringify(request),
    });
  } catch {
    return {
      message: "Draft generation is temporarily unavailable. Your selections are still here.",
      reason: "unavailable",
      retryAfterSeconds: null,
      status: "error",
    };
  }

  if (!response.ok) {
    let { fallback, reason } = failureForStatus(response.status);
    const safeError = await readSafeError(response, fallback);
    if (response.status === 403 && safeError.code === "csrf_validation_failed") {
      fallback = "Your session could not be confirmed. Sign in again to generate a draft.";
      reason = "authentication_required";
    }
    return {
      message: reason === "authentication_required" ? fallback : safeError.message,
      reason,
      retryAfterSeconds: parseRetryAfter(response.headers.get("retry-after")),
      status: "error",
    };
  }

  try {
    const payload: unknown = await response.json();
    if (
      !isGenerationResponse(payload) ||
      payload.article_id !== request.article_id ||
      payload.tone !== request.tone ||
      payload.length !== request.length
    ) {
      throw new Error("The generation response did not match the request.");
    }
    return { data: payload, status: "success" };
  } catch {
    return {
      message: "The generated draft response could not be verified. Please try again.",
      reason: "unavailable",
      retryAfterSeconds: null,
      status: "error",
    };
  }
}
