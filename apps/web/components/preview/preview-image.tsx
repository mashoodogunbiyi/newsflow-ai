"use client";

import Image from "next/image";
import { useState } from "react";

import { isPreviewImageId, type PreviewImageSelection } from "@/types/preview";

const AI_IMAGE_DESIGNATION = "AI-generated illustration";

function ImageFallback({ unavailable = false }: { unavailable?: boolean }) {
  return (
    <div
      className="grid min-h-52 place-items-center bg-emerald-950/[0.035] px-6 py-10 text-center sm:min-h-64"
      data-testid={unavailable ? "preview-image-error" : "preview-image-empty"}
      role={unavailable ? "status" : undefined}
    >
      <div className="max-w-sm">
        <span
          aria-hidden="true"
          className="mx-auto grid h-11 w-11 place-items-center rounded-2xl border border-emerald-950/10 bg-white text-lg text-emerald-800 shadow-sm"
        >
          {unavailable ? "!" : "+"}
        </span>
        <p className="mt-4 text-sm font-semibold text-emerald-950">
          {unavailable ? "Illustration unavailable" : "No illustration selected"}
        </p>
        <p className="mt-1 text-xs leading-5 text-emerald-950/55">
          {unavailable
            ? "The private image could not be displayed. The draft and source remain available for review."
            : "The text and source can still be reviewed without an image."}
        </p>
      </div>
    </div>
  );
}

function PreviewImageAsset({ image }: { image: PreviewImageSelection }) {
  const [failed, setFailed] = useState(false);

  if (failed || !isPreviewImageId(image.id)) {
    return <ImageFallback unavailable />;
  }

  const altText =
    image.altText.trim() || "AI-generated illustration prepared for the selected article.";

  return (
    <div className="relative aspect-[4/3] min-h-52 overflow-hidden bg-emerald-950/5 sm:min-h-64">
      <Image
        alt={altText}
        className="object-cover"
        fill
        onError={() => setFailed(true)}
        sizes="(max-width: 1279px) 100vw, 40vw"
        src={`/api/images/${encodeURIComponent(image.id)}/content`}
        unoptimized
      />
    </div>
  );
}

export function PreviewImage({ image }: { image: PreviewImageSelection | null }) {
  return (
    <figure className="border-t border-emerald-950/10">
      {image ? <PreviewImageAsset image={image} key={image.id} /> : <ImageFallback />}
      {image ? (
        <figcaption className="flex flex-col gap-1 border-t border-emerald-950/10 bg-amber-50 px-4 py-3 text-xs leading-5 text-amber-950 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <span className="font-semibold">{AI_IMAGE_DESIGNATION}</span>
          <span>Not authentic news photography</span>
        </figcaption>
      ) : null}
    </figure>
  );
}
