"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { downloadSelectedImage, type ExportResult } from "@/lib/content-export";

type DownloadImageButtonProps = {
  imageId: string | null;
};

type DownloadState = {
  imageId: string;
  result: ExportResult;
};

export function DownloadImageButton({ imageId }: DownloadImageButtonProps) {
  const [state, setState] = useState<DownloadState | null>(null);
  const [downloading, setDownloading] = useState(false);
  const currentResult = imageId && state?.imageId === imageId ? state.result : null;

  async function download() {
    if (!imageId) return;
    setDownloading(true);
    const result = await downloadSelectedImage(imageId);
    setState({ imageId, result });
    setDownloading(false);
  }

  return (
    <div>
      <Button
        disabled={downloading || imageId === null}
        onClick={download}
        type="button"
        variant="secondary"
      >
        {downloading ? "Preparing image..." : "Download Image"}
      </Button>
      <p
        aria-live="polite"
        className={`mt-2 min-h-5 text-xs leading-5 ${
          currentResult?.status === "error" ? "text-red-800" : "text-emerald-800"
        }`}
        role={currentResult?.status === "error" ? "alert" : "status"}
      >
        {!imageId
          ? "Select an approved generated illustration to enable download."
          : currentResult?.status === "success"
            ? "The AI-generated illustration download has started."
            : currentResult?.status === "error"
              ? currentResult.message
              : "Downloads the selected illustration through secure private delivery."}
      </p>
    </div>
  );
}
