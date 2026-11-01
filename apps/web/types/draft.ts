import type {
  GenerationLength,
  GenerationResponse,
  GenerationWarning,
  GroundingStatus,
} from "@/types/generation";

export type DraftEditorDocument = {
  articleId: string;
  generatedText: string;
  generationId: string;
  groundingStatus: GroundingStatus;
  length: GenerationLength;
  sourceAttribution: string;
  sourceName: string;
  sourceTitle: string;
  sourceUrl: string;
  validationWarnings: GenerationWarning[];
};

export const DRAFT_LENGTH_GUIDANCE: Record<
  GenerationLength,
  { label: string; wordGuidance: string }
> = {
  short: {
    label: "Short",
    wordGuidance: "approximately 80 to 120 words",
  },
  medium: {
    label: "Medium",
    wordGuidance: "approximately 130 to 200 words",
  },
  long: {
    label: "Long",
    wordGuidance: "approximately 220 to 320 words",
  },
};

export function toDraftEditorDocument(response: GenerationResponse): DraftEditorDocument {
  return {
    articleId: response.article_id,
    generatedText: response.draft,
    generationId: response.generation_id,
    groundingStatus: response.grounding_status,
    length: response.length,
    sourceAttribution: response.source_attribution,
    sourceName: response.source_name,
    sourceTitle: response.source_title,
    sourceUrl: response.source_url,
    validationWarnings: response.validation_warnings,
  };
}
