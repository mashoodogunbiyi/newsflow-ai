import type { GenerationWarning, GroundingStatus } from "@/types/generation";

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export type PreviewImageSelection = {
  altText: string;
  id: string;
};

export type PreviewSourceReference = {
  attribution: string;
  name: string;
  title: string;
  url: string;
};

export type LinkedInPreviewContent = {
  draftText: string;
  groundingStatus: GroundingStatus;
  image: PreviewImageSelection | null;
  source: PreviewSourceReference;
  warnings: GenerationWarning[];
};

export function isPreviewImageId(value: string) {
  return UUID_PATTERN.test(value);
}
