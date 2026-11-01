import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import WorkspaceError from "@/app/(workspace)/error";
import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { LoadingState } from "@/components/ui/loading-state";
import { StatusBadge } from "@/components/ui/status-badge";

const navigation = vi.hoisted(() => ({
  pathname: "/dashboard",
  refresh: vi.fn(),
  replace: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => navigation.pathname,
  useRouter: () => navigation,
}));

describe("NFA-56 workspace components", () => {
  beforeEach(() => {
    navigation.pathname = "/dashboard";
  });

  afterEach(() => {
    cleanup();
  });

  test("renders the application shell with an active route and private child content", () => {
    render(
      <AppShell userEmail="member@example.com">
        <h1>Private workspace content</h1>
      </AppShell>,
    );

    expect(screen.getByRole("heading", { name: "Private workspace content" })).toBeDefined();
    expect(screen.getByRole("link", { name: "Dashboard" }).getAttribute("aria-current")).toBe(
      "page",
    );
    expect(screen.getByRole("link", { name: "Create Post" }).getAttribute("aria-current")).toBe(
      null,
    );
    expect(screen.getByText("member@example.com")).toBeDefined();
    expect(screen.getByRole("link", { name: "Skip to main content" }).getAttribute("href")).toBe(
      "#workspace-content",
    );
  });

  test("opens and closes mobile navigation while managing keyboard focus", async () => {
    render(
      <AppShell userEmail="member@example.com">
        <p>Workspace</p>
      </AppShell>,
    );

    const openButton = screen.getByRole("button", { name: "Open navigation" });
    expect(openButton.getAttribute("aria-expanded")).toBe("false");

    fireEvent.click(openButton);
    const mobileNavigation = screen.getByRole("navigation", { name: "Mobile workspace" });
    expect(mobileNavigation).toBeDefined();
    expect(
      screen.getByRole("button", { name: "Close navigation" }).getAttribute("aria-expanded"),
    ).toBe("true");
    await waitFor(() =>
      expect(document.activeElement).toBe(
        within(mobileNavigation).getByRole("link", { name: "Dashboard" }),
      ),
    );

    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByRole("navigation", { name: "Mobile workspace" })).toBeNull();
    expect(document.activeElement).toBe(screen.getByRole("button", { name: "Open navigation" }));
  });

  test("marks the selected route after the pathname changes", () => {
    navigation.pathname = "/library";
    render(
      <AppShell userEmail="member@example.com">
        <p>Library</p>
      </AppShell>,
    );

    expect(screen.getByRole("link", { name: "Content Library" }).getAttribute("aria-current")).toBe(
      "page",
    );
  });

  test("provides reusable buttons, inputs, cards, status, and loading feedback", () => {
    render(
      <>
        <Button>Save draft</Button>
        <Input helpText="Use a permitted topic." id="topic" label="Topic" />
        <Card>
          <StatusBadge tone="success">Ready</StatusBadge>
        </Card>
        <LoadingState message="Preparing workspace..." />
      </>,
    );

    expect(screen.getByRole("button", { name: "Save draft" })).toBeDefined();
    expect(screen.getByLabelText("Topic")).toBeDefined();
    expect(screen.getByText("Use a permitted topic.")).toBeDefined();
    expect(screen.getByText("Ready")).toBeDefined();
    expect(screen.getByText("Preparing workspace...")).toBeDefined();
  });

  test("shows a safe error boundary and retries without exposing error details", () => {
    const retry = vi.fn();
    render(<WorkspaceError error={new Error("private technical detail")} retry={retry} />);

    expect(screen.getByRole("alert").textContent).not.toContain("private technical detail");
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(retry).toHaveBeenCalledOnce();
  });
});
