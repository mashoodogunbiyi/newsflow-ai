import { describe, expect, test } from "vitest";

import {
  isProtectedWorkspaceRoute,
  shouldOptimisticallyRedirectFromWorkspace,
} from "@/lib/route-protection";

describe("workspace route protection", () => {
  test.each(["/dashboard", "/generate", "/library", "/account"])(
    "redirects an unauthenticated request for %s",
    (pathname) => {
      expect(shouldOptimisticallyRedirectFromWorkspace(pathname, false)).toBe(true);
    },
  );

  test("protects nested workspace routes without matching similarly named public routes", () => {
    expect(isProtectedWorkspaceRoute("/library/123")).toBe(true);
    expect(isProtectedWorkspaceRoute("/library-public")).toBe(false);
  });

  test("lets the server layout perform the authoritative check when a cookie exists", () => {
    expect(shouldOptimisticallyRedirectFromWorkspace("/dashboard", true)).toBe(false);
  });

  test("does not redirect unrelated public pages", () => {
    expect(shouldOptimisticallyRedirectFromWorkspace("/login", false)).toBe(false);
  });
});
