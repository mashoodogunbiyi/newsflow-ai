import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, test } from "vitest";

type Rgb = [number, number, number];

function rgb(hex: string): Rgb {
  const cleaned = hex.replace("#", "");
  return [0, 2, 4].map((index) => Number.parseInt(cleaned.slice(index, index + 2), 16)) as Rgb;
}

function blend(foreground: Rgb, background: Rgb, opacity: number): Rgb {
  return foreground.map((channel, index) =>
    Math.round(channel * opacity + background[index] * (1 - opacity)),
  ) as Rgb;
}

function luminance(colour: Rgb) {
  const linear = colour.map((channel) => {
    const value = channel / 255;
    return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
}

function contrastRatio(foreground: Rgb, background: Rgb) {
  const values = [luminance(foreground), luminance(background)].sort((a, b) => b - a);
  return (values[0] + 0.05) / (values[1] + 0.05);
}

describe("NFA-65 contrast and motion safeguards", () => {
  test.each([
    ["primary text", rgb("#0e2b22"), rgb("#f7f6f2")],
    ["muted text", blend(rgb("#0e2b22"), rgb("#f7f6f2"), 0.7), rgb("#f7f6f2")],
    ["dark-panel secondary text", blend(rgb("#ffffff"), rgb("#022c22"), 0.75), rgb("#022c22")],
    ["emerald link", rgb("#047857"), rgb("#f7f6f2")],
    ["error text", rgb("#991b1b"), rgb("#fef2f2")],
    ["warning text", rgb("#451a03"), rgb("#fffbeb")],
  ])("%s meets the WCAG AA normal-text ratio", (_name, foreground, background) => {
    expect(contrastRatio(foreground as Rgb, background as Rgb)).toBeGreaterThanOrEqual(4.5);
  });

  test("global reduced-motion rules suppress animation and smooth scrolling", () => {
    const css = readFileSync(resolve(process.cwd(), "app/globals.css"), "utf8");

    expect(css).toContain("@media (prefers-reduced-motion: reduce)");
    expect(css).toContain("animation-duration: 0.01ms !important");
    expect(css).toContain("animation-iteration-count: 1 !important");
    expect(css).toContain("scroll-behavior: auto !important");
  });
});
