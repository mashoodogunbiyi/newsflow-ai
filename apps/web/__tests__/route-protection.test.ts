import { describe, expect, test } from "vitest";

import { shouldOptimisticallyRedirectFromDashboard } from "@/lib/route-protection";

describe("dashboard route protection", () => {
  test("redirects a dashboard request with no session cookie", () => {
    expect(shouldOptimisticallyRedirectFromDashboard("/dashboard", false)).toBe(true);
  });

  test("lets the dashboard perform the authoritative check when a cookie exists", () => {
    expect(shouldOptimisticallyRedirectFromDashboard("/dashboard", true)).toBe(false);
  });

  test("does not redirect unrelated public pages", () => {
    expect(shouldOptimisticallyRedirectFromDashboard("/login", false)).toBe(false);
  });
});
