"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { copyPostText, type ExportResult } from "@/lib/content-export";

type CopyPostButtonProps = {
  text: string;
};

type CopyState = {
  result: ExportResult;
  text: string;
};

export function CopyPostButton({ text }: CopyPostButtonProps) {
  const [state, setState] = useState<CopyState | null>(null);
  const [copying, setCopying] = useState(false);
  const currentResult = state?.text === text ? state.result : null;
  const empty = text.trim().length === 0;

  async function copy() {
    setCopying(true);
    const result = await copyPostText(text);
    setState({ result, text });
    setCopying(false);
  }

  return (
    <div>
      <Button disabled={copying || empty} onClick={copy} type="button">
        {copying ? "Copying..." : "Copy Post"}
      </Button>
      <p
        aria-live="polite"
        className={`mt-2 min-h-5 text-xs leading-5 ${
          currentResult?.status === "error" || empty ? "text-red-800" : "text-emerald-800"
        }`}
        role={currentResult?.status === "error" ? "alert" : "status"}
      >
        {empty
          ? "Add reviewed text before copying."
          : currentResult?.status === "success"
            ? "Current edited post copied with its line breaks preserved."
            : currentResult?.status === "error"
              ? currentResult.message
              : "Copies the current edited text as plain text."}
      </p>
    </div>
  );
}
