import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import WorkspaceLayout from "@/app/(workspace)/layout";

const authentication = vi.hoisted(() => ({
  getState: vi.fn(),
}));
const navigation = vi.hoisted(() => ({
  pathname: "/dashboard",
  redirect: vi.fn(),
  refresh: vi.fn(),
  replace: vi.fn(),
}));

vi.mock("@/lib/auth-server", () => ({
  getAuthenticationState: authentication.getState,
}));

vi.mock("next/navigation", () => ({
  redirect: navigation.redirect,
  usePathname: () => navigation.pathname,
  useRouter: () => navigation,
}));

describe("protected workspace layout", () => {
  beforeEach(() => {
    authentication.getState.mockReset();
    navigation.redirect.mockReset();
    navigation.redirect.mockImplementation(() => {
      throw new Error("NEXT_REDIRECT");
    });
  });

  afterEach(() => cleanup());

  test("redirects before rendering private content when authentication is absent", async () => {
    authentication.getState.mockResolvedValue({ status: "unauthenticated" });

    await expect(WorkspaceLayout({ children: <p>Restricted private content</p> })).rejects.toThrow(
      "NEXT_REDIRECT",
    );
    expect(navigation.redirect).toHaveBeenCalledWith("/login?reason=authentication_required");
    expect(screen.queryByText("Restricted private content")).toBeNull();
  });

  test("shows a safe connection state without rendering private content", async () => {
    authentication.getState.mockResolvedValue({ status: "unavailable" });

    render(await WorkspaceLayout({ children: <p>Restricted private content</p> }));

    expect(screen.getByRole("heading", { name: /cannot confirm your session/i })).toBeDefined();
    expect(screen.queryByText("Restricted private content")).toBeNull();
  });

  test("renders the shared shell only after FastAPI confirms the session", async () => {
    authentication.getState.mockResolvedValue({
      status: "authenticated",
      user: {
        id: "9bb4cb73-dd34-4883-b823-2b67aa6a9128",
        email: "member@example.com",
      },
    });

    render(await WorkspaceLayout({ children: <p>Restricted private content</p> }));

    expect(screen.getByText("Restricted private content")).toBeDefined();
    expect(screen.getByRole("navigation", { name: "Workspace" })).toBeDefined();
  });
});
