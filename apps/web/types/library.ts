import type { DraftEditorDocument } from "@/types/draft";
import { isArticleId, isGenerationLength, isGenerationTone } from "@/types/generation";
import type { PreviewImageSelection } from "@/types/preview";

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const IMAGE_MEDIA_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);

export type SavedDraftImage = {
  ai_disclosure_required: boolean;
  ai_generated: boolean;
  alt_text: string | null;
  height_px: number;
  id: string;
  mime_type: "image/jpeg" | "image/png" | "image/webp";
  width_px: number;
};

export type SavedDraft = {
  created_at: string;
  current_post_version_id: string;
  edited_text: string;
  generated_post_id: string;
  generation: {
    created_at: string;
    generation_id: string;
    model_identifier: string;
    original_post_version_id: string;
    prompt_version: string;
  };
  id: string;
  length: "long" | "medium" | "short";
  selected_image: SavedDraftImage | null;
  selected_image_id: string | null;
  source: {
    article_id: string;
    attribution: string;
    title: string;
    url: string;
  };
  status: "saved";
  title: string | null;
  tone: "analytical" | "conversational" | "professional";
  updated_at: string;
  version: number;
};

export type SavedDraftPage = {
  items: SavedDraft[];
  page: number;
  page_size: number;
  sort: "updated_at_desc";
  total_items: number;
  total_pages: number;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isUuid(value: unknown): value is string {
  return typeof value === "string" && UUID_PATTERN.test(value);
}

function isString(value: unknown, maximumLength: number, allowEmpty = false): value is string {
  return (
    typeof value === "string" &&
    value.length <= maximumLength &&
    (allowEmpty || value.trim().length > 0)
  );
}

function isPositiveInteger(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value) && value > 0;
}

function isNonnegativeInteger(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value) && value >= 0;
}

function isTimestamp(value: unknown): value is string {
  return typeof value === "string" && !Number.isNaN(Date.parse(value));
}

function isSafeSourceUrl(value: unknown): value is string {
  if (typeof value !== "string") {
    return false;
  }
  try {
    return new URL(value).protocol === "https:";
  } catch {
    return false;
  }
}

function isSavedDraftImage(value: unknown): value is SavedDraftImage {
  if (!isRecord(value)) {
    return false;
  }
  return (
    isUuid(value.id) &&
    (value.alt_text === null || isString(value.alt_text, 1_000)) &&
    typeof value.mime_type === "string" &&
    IMAGE_MEDIA_TYPES.has(value.mime_type) &&
    isPositiveInteger(value.width_px) &&
    isPositiveInteger(value.height_px) &&
    typeof value.ai_generated === "boolean" &&
    typeof value.ai_disclosure_required === "boolean"
  );
}

export function isSavedDraft(value: unknown): value is SavedDraft {
  if (!isRecord(value) || !isRecord(value.source) || !isRecord(value.generation)) {
    return false;
  }
  const selectedImageId = value.selected_image_id;
  const selectedImage = value.selected_image;
  if (selectedImageId !== null && !isUuid(selectedImageId)) {
    return false;
  }
  if (selectedImage !== null && !isSavedDraftImage(selectedImage)) {
    return false;
  }
  if (
    selectedImage !== null &&
    (selectedImageId === null || selectedImage.id !== selectedImageId)
  ) {
    return false;
  }

  return (
    isUuid(value.id) &&
    isUuid(value.generated_post_id) &&
    isUuid(value.current_post_version_id) &&
    (value.title === null || isString(value.title, 200)) &&
    isString(value.edited_text, 12_000) &&
    isGenerationTone(value.tone) &&
    isGenerationLength(value.length) &&
    value.status === "saved" &&
    isPositiveInteger(value.version) &&
    isArticleId(value.source.article_id) &&
    isString(value.source.title, 500) &&
    isSafeSourceUrl(value.source.url) &&
    isString(value.source.attribution, 1_000) &&
    isUuid(value.generation.generation_id) &&
    isUuid(value.generation.original_post_version_id) &&
    isString(value.generation.model_identifier, 200) &&
    isString(value.generation.prompt_version, 200) &&
    isTimestamp(value.generation.created_at) &&
    isTimestamp(value.created_at) &&
    isTimestamp(value.updated_at)
  );
}

export function isSavedDraftPage(value: unknown): value is SavedDraftPage {
  if (!isRecord(value) || !Array.isArray(value.items) || !value.items.every(isSavedDraft)) {
    return false;
  }
  if (
    !isPositiveInteger(value.page) ||
    !isPositiveInteger(value.page_size) ||
    value.page_size > 100 ||
    !isNonnegativeInteger(value.total_items) ||
    !isNonnegativeInteger(value.total_pages) ||
    value.sort !== "updated_at_desc"
  ) {
    return false;
  }
  return (
    value.items.length <= value.page_size &&
    value.total_pages ===
      (value.total_items === 0 ? 0 : Math.ceil(value.total_items / value.page_size))
  );
}

export function toSavedDraftEditorDocument(draft: SavedDraft): DraftEditorDocument {
  return {
    articleId: draft.source.article_id,
    generatedText: draft.edited_text,
    generationId: draft.generation.generation_id,
    groundingStatus: "review_required",
    length: draft.length,
    sourceAttribution: draft.source.attribution,
    sourceName: "Authorised article source",
    sourceTitle: draft.source.title,
    sourceUrl: draft.source.url,
    validationWarnings: [],
  };
}

export function toSavedDraftImageSelection(draft: SavedDraft): PreviewImageSelection | null {
  if (!draft.selected_image) {
    return null;
  }
  return {
    altText:
      draft.selected_image.alt_text?.trim() ||
      "AI-generated illustration selected for this saved draft.",
    id: draft.selected_image.id,
  };
}
