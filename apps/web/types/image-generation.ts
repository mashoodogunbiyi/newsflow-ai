import { isPreviewImageId } from "@/types/preview";

export const IMAGE_STYLES = [
  {
    description: "A polished conceptual illustration suitable for a professional news post.",
    label: "Editorial",
    value: "editorial_illustration",
  },
  {
    description: "A clean illustration with simple forms and limited visual detail.",
    label: "Minimalist",
    value: "minimalist_illustration",
  },
  {
    description: "An abstract visual focused on technology, systems, and connection.",
    label: "Abstract technology",
    value: "abstract_technology",
  },
  {
    description: "A structured visual that communicates the topic without inventing data.",
    label: "Infographic style",
    value: "professional_infographic_style",
  },
] as const;

export const IMAGE_ASPECT_RATIOS = [
  { label: "Landscape", value: "landscape" },
  { label: "Square", value: "square" },
  { label: "Portrait", value: "portrait" },
] as const;

export const IMAGE_COMPOSITIONS = [
  { label: "Balanced", value: "balanced" },
  { label: "Focus left", value: "focal_point_left" },
  { label: "Focus right", value: "focal_point_right" },
] as const;

export type ImageStyle = (typeof IMAGE_STYLES)[number]["value"];
export type ImageAspectRatio = (typeof IMAGE_ASPECT_RATIOS)[number]["value"];
export type ImageComposition = (typeof IMAGE_COMPOSITIONS)[number]["value"];

export type ImagePreferences = {
  aspect_ratio: ImageAspectRatio;
  composition: ImageComposition;
  style: ImageStyle;
};

export type InitialImageRequest = ImagePreferences & {
  action: "generate";
  generation_id: string;
};

export type RegenerateImageRequest = ImagePreferences & {
  action: "regenerate";
  parent_image_id: string;
};

export type ImageGenerationRequest = InitialImageRequest | RegenerateImageRequest;

export type ImageVersion = {
  createdAt: string;
  generatedPostId: string;
  generationId: string;
  id: string;
  parentId: string | null;
  reviewRequired: true;
  safetyStatus: "pending" | "approved" | "blocked";
  sequence: number;
};

export function isImageStyle(value: unknown): value is ImageStyle {
  return IMAGE_STYLES.some((option) => option.value === value);
}

export function isImageAspectRatio(value: unknown): value is ImageAspectRatio {
  return IMAGE_ASPECT_RATIOS.some((option) => option.value === value);
}

export function isImageComposition(value: unknown): value is ImageComposition {
  return IMAGE_COMPOSITIONS.some((option) => option.value === value);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function parseImageVersion(value: unknown): ImageVersion | null {
  if (!isRecord(value)) {
    return null;
  }
  const imageId = value.image_id;
  const generationId = value.generation_id;
  const generatedPostId = value.generated_post_id;
  const parentId = value.parent_image_id;
  if (
    typeof imageId !== "string" ||
    !isPreviewImageId(imageId) ||
    typeof generationId !== "string" ||
    !isPreviewImageId(generationId) ||
    typeof generatedPostId !== "string" ||
    !isPreviewImageId(generatedPostId) ||
    !(parentId === null || (typeof parentId === "string" && isPreviewImageId(parentId))) ||
    !Number.isInteger(value.regeneration_sequence) ||
    Number(value.regeneration_sequence) < 0 ||
    value.status !== "completed" ||
    !(
      value.safety_status === "pending" ||
      value.safety_status === "approved" ||
      value.safety_status === "blocked"
    ) ||
    value.is_ai_generated !== true ||
    value.review_required !== true ||
    typeof value.created_at !== "string" ||
    Number.isNaN(Date.parse(value.created_at))
  ) {
    return null;
  }

  const sequence = Number(value.regeneration_sequence);
  if ((sequence === 0 && parentId !== null) || (sequence > 0 && parentId === null)) {
    return null;
  }

  return {
    createdAt: value.created_at,
    generatedPostId,
    generationId,
    id: imageId,
    parentId,
    reviewRequired: true,
    safetyStatus: value.safety_status,
    sequence,
  };
}
