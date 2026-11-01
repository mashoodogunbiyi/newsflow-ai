"use client";

import Image from "next/image";

import type { ImageVersion } from "@/types/image-generation";

export type DisplayImageVersion = ImageVersion & { altText: string };

type ImageVersionGalleryProps = {
  disabled: boolean;
  onSelect: (version: DisplayImageVersion) => void;
  selectedId: string;
  versions: DisplayImageVersion[];
};

export function ImageVersionGallery({
  disabled,
  onSelect,
  selectedId,
  versions,
}: ImageVersionGalleryProps) {
  return (
    <fieldset className="mt-5" disabled={disabled}>
      <legend className="text-sm font-semibold text-emerald-950">Illustration versions</legend>
      <p className="mt-1 text-xs leading-5 text-emerald-950/70">
        The original remains available. Select the version shown in the LinkedIn preview.
      </p>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        {versions.map((version) => {
          const selected = selectedId === version.id;
          const versionLabel =
            version.sequence === 0 ? "Original" : `Version ${version.sequence + 1}`;
          return (
            <label
              className={`cursor-pointer overflow-hidden rounded-2xl border bg-white transition focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-emerald-700 ${
                selected ? "border-emerald-700 ring-1 ring-emerald-700" : "border-emerald-950/10"
              }`}
              key={version.id}
            >
              <span className="relative block aspect-[4/3] bg-emerald-950/5">
                <Image
                  alt={version.altText}
                  className="object-cover"
                  fill
                  sizes="(max-width: 639px) 100vw, 320px"
                  src={`/api/images/${encodeURIComponent(version.id)}/content`}
                  unoptimized
                />
              </span>
              <span className="flex items-center justify-between gap-3 border-t border-emerald-950/10 px-3 py-3">
                <span>
                  <span className="block text-sm font-semibold text-emerald-950">
                    {versionLabel}
                  </span>
                  <span className="block text-xs text-emerald-950/70">
                    AI-generated - review required
                  </span>
                </span>
                <input
                  aria-label={`Use ${versionLabel.toLowerCase()} in preview`}
                  checked={selected}
                  className="accent-emerald-800"
                  name="selected-image-version"
                  onChange={() => onSelect(version)}
                  type="radio"
                  value={version.id}
                />
              </span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}
