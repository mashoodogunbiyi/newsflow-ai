"use client";

import { useGeneration, type GenerationOperation } from "@/hooks/use-generation";

export function useImageGeneration<TInput, TResult>(execute: GenerationOperation<TInput, TResult>) {
  return useGeneration({ execute, kind: "image" });
}
