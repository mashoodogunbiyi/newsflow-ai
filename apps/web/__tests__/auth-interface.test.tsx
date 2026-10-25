import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { CredentialsForm } from "@/components/auth/credentials-form";
import { LogoutButton } from "@/components/auth/logout-button";

const navigation = vi.hoisted(() => ({
  refresh: vi.fn(),
  replace: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => navigation,
}));

function enterCredentials(email: string, password: string) {
  fireEvent.change(screen.getByLabelText("Email address"), {
    target: { value: email },
  });
  fireEvent.change(screen.getByLabelText("Password"), {
    target: { value: password },
  });
}

describe("frontend authentication interface", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    navigation.refresh.mockReset();
    navigation.replace.mockReset();
  });

  afterEach(() => {
    cleanup();
    document.cookie = "newsflow_csrf=; Max-Age=0; path=/";
    vi.unstubAllGlobals();
  });

  test("registers a valid account through the same-origin gateway", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          id: "9bb4cb73-dd34-4883-b823-2b67aa6a9128",
          email: "new.user@example.com",
          message: "Account created successfully",
        }),
        { status: 201, headers: { "Content-Type": "application/json" } },
      ),
    );
    render(<CredentialsForm mode="register" />);

    enterCredentials("New.User@example.com", "Secure-Test-Password-42!");
    fireEvent.click(screen.getByRole("button", { name: "Create account" }));

    expect(await screen.findByRole("heading", { name: "Your account is ready." })).toBeDefined();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/auth/register",
      expect.objectContaining({
        method: "POST",
        credentials: "same-origin",
        body: JSON.stringify({
          email: "new.user@example.com",
          password: "Secure-Test-Password-42!",
        }),
      }),
    );
  });

  test("reports accessible client-side registration errors before sending data", async () => {
    const fetchMock = vi.mocked(fetch);
    render(<CredentialsForm mode="register" />);

    enterCredentials("not-an-email", "weak");
    fireEvent.click(screen.getByRole("button", { name: "Create account" }));

    expect(await screen.findByText("Enter a valid email address.")).toBeDefined();
    expect(screen.getByLabelText("Email address").getAttribute("aria-invalid")).toBe("true");
    expect(screen.getByText(/your password still needs/i)).toBeDefined();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  test("logs in and replaces the current route with the dashboard", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ message: "Login successful" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    render(<CredentialsForm mode="login" />);

    enterCredentials("member@example.com", "Secure-Test-Password-42!");
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => expect(navigation.replace).toHaveBeenCalledWith("/dashboard"));
    expect(navigation.refresh).toHaveBeenCalledOnce();
  });

  test("displays a safe backend error for invalid credentials", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          error: {
            code: "invalid_credentials",
            message: "Email or password is incorrect.",
          },
        }),
        { status: 401, headers: { "Content-Type": "application/json" } },
      ),
    );
    render(<CredentialsForm mode="login" />);

    enterCredentials("member@example.com", "Incorrect-Password-42!");
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect((await screen.findByRole("alert")).textContent).toContain(
      "Email or password is incorrect.",
    );
    expect(navigation.replace).not.toHaveBeenCalled();
  });

  test("shows a processing state while login is pending", async () => {
    vi.mocked(fetch).mockImplementationOnce(() => new Promise(() => undefined));
    render(<CredentialsForm mode="login" />);

    enterCredentials("member@example.com", "Secure-Test-Password-42!");
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(
      (await screen.findByRole("button", { name: "Signing in..." })) as HTMLButtonElement,
    ).toHaveProperty("disabled", true);
    expect(screen.getByText("Your authentication request is being processed.")).toBeDefined();
  });

  test("logs out using the readable CSRF cookie", async () => {
    document.cookie = "newsflow_csrf=csrf-test-token; path=/";
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));
    render(<LogoutButton />);

    fireEvent.click(screen.getByRole("button", { name: "Log out" }));

    await waitFor(() =>
      expect(navigation.replace).toHaveBeenCalledWith("/login?reason=logged_out"),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/auth/logout",
      expect.objectContaining({
        method: "POST",
        credentials: "same-origin",
        headers: { "X-CSRF-Token": "csrf-test-token" },
      }),
    );
  });
});
