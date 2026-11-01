import { DRAFT_LENGTH_GUIDANCE, type DraftEditorDocument } from "@/types/draft";

type CharacterCounterProps = {
  length: DraftEditorDocument["length"];
  text: string;
};

export function CharacterCounter({ length, text }: CharacterCounterProps) {
  const guidance = DRAFT_LENGTH_GUIDANCE[length];

  return (
    <div className="flex flex-col gap-1 text-xs leading-5 text-emerald-950/70 sm:flex-row sm:items-center sm:justify-between">
      <output aria-label="Draft character count" htmlFor="linkedin-draft-editor">
        {text.length.toLocaleString("en-GB")} {text.length === 1 ? "character" : "characters"}
      </output>
      <p>
        {guidance.label} application guidance: {guidance.wordGuidance}. This is not a claimed
        LinkedIn platform limit.
      </p>
    </div>
  );
}
