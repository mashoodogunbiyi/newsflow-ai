export const GENERATION_TONES = [
  {
    description: "Clear, polished writing for a broad professional audience.",
    label: "Professional",
    value: "professional",
  },
  {
    description: "Approachable writing that invites readers into the discussion.",
    label: "Conversational",
    value: "conversational",
  },
  {
    description: "Structured writing that focuses on context, meaning, and implications.",
    label: "Analytical",
    value: "analytical",
  },
] as const;

export const GENERATION_LENGTHS = [
  {
    description: "A focused draft of approximately 80 to 120 words.",
    label: "Short",
    value: "short",
  },
  {
    description: "A balanced draft of approximately 130 to 200 words.",
    label: "Medium",
    value: "medium",
  },
  {
    description: "A detailed draft of approximately 220 to 320 words.",
    label: "Long",
    value: "long",
  },
] as const;

export const GENERATION_LANGUAGES = [
  {
    description: "Write the complete draft in English.",
    label: "English",
    value: "english",
  },
  {
    description: "Write the complete draft in French.",
    label: "French",
    value: "french",
  },
  {
    description: "Write the complete draft in Spanish.",
    label: "Spanish",
    value: "spanish",
  },
] as const;

export type GenerationTone = (typeof GENERATION_TONES)[number]["value"];
export type GenerationLength = (typeof GENERATION_LENGTHS)[number]["value"];
export type GenerationLanguage = (typeof GENERATION_LANGUAGES)[number]["value"];

export type GenerationRequest = {
  article_id: string;
  language: GenerationLanguage;
  length: GenerationLength;
  tone: GenerationTone;
};

export type GroundingStatus = "passed_automated_checks" | "review_required" | "rejected";

export type GenerationWarning = {
  category:
    "structure" | "source_reference" | "insufficient_context" | "unsupported_claim" | "legacy_data";
  code: string;
  message: string;
  severity: "review" | "blocking";
};

export type GenerationResponse = {
  article_id: string;
  created_at: string;
  draft: string;
  generation_id: string;
  grounding_policy_version: "grounding_v1";
  grounding_status: GroundingStatus;
  length: GenerationLength;
  review_required: true;
  source_attribution: string;
  source_name: string;
  source_title: string;
  source_url: string;
  status: "draft";
  tone: GenerationTone;
  validation_warnings: GenerationWarning[];
};

export function isGenerationTone(value: unknown): value is GenerationTone {
  return GENERATION_TONES.some((option) => option.value === value);
}

export function isGenerationLength(value: unknown): value is GenerationLength {
  return GENERATION_LENGTHS.some((option) => option.value === value);
}

export function isGenerationLanguage(value: unknown): value is GenerationLanguage {
  return GENERATION_LANGUAGES.some((option) => option.value === value);
}

export function isArticleId(value: unknown): value is string {
  return (
    typeof value === "string" &&
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNonemptyString(value: unknown, maximumLength: number): value is string {
  return typeof value === "string" && value.trim().length > 0 && value.length <= maximumLength;
}

function isHttpsUrl(value: unknown): value is string {
  if (typeof value !== "string") {
    return false;
  }

  try {
    return new URL(value).protocol === "https:";
  } catch {
    return false;
  }
}

function isGroundingStatus(value: unknown): value is GroundingStatus {
  return value === "passed_automated_checks" || value === "review_required" || value === "rejected";
}

function isGenerationWarning(value: unknown): value is GenerationWarning {
  if (!isRecord(value)) {
    return false;
  }

  return (
    isNonemptyString(value.code, 100) &&
    (value.category === "structure" ||
      value.category === "source_reference" ||
      value.category === "insufficient_context" ||
      value.category === "unsupported_claim" ||
      value.category === "legacy_data") &&
    (value.severity === "review" || value.severity === "blocking") &&
    isNonemptyString(value.message, 240)
  );
}

export function isGenerationResponse(value: unknown): value is GenerationResponse {
  if (!isRecord(value)) {
    return false;
  }

  const warnings = value.validation_warnings;
  if (
    !isGroundingStatus(value.grounding_status) ||
    !Array.isArray(warnings) ||
    !warnings.every(isGenerationWarning)
  ) {
    return false;
  }

  if (value.grounding_status === "passed_automated_checks" && warnings.length > 0) {
    return false;
  }
  if (value.grounding_status !== "passed_automated_checks" && warnings.length === 0) {
    return false;
  }
  if (
    value.grounding_status === "rejected" &&
    !warnings.some((item) => item.severity === "blocking")
  ) {
    return false;
  }

  return (
    isArticleId(value.generation_id) &&
    isArticleId(value.article_id) &&
    isNonemptyString(value.draft, 12_000) &&
    isGenerationTone(value.tone) &&
    isGenerationLength(value.length) &&
    isNonemptyString(value.source_title, 300) &&
    isNonemptyString(value.source_name, 200) &&
    isHttpsUrl(value.source_url) &&
    isNonemptyString(value.source_attribution, 500) &&
    value.status === "draft" &&
    value.review_required === true &&
    value.grounding_policy_version === "grounding_v1" &&
    typeof value.created_at === "string" &&
    !Number.isNaN(Date.parse(value.created_at))
  );
}
