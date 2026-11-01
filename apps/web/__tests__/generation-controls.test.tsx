import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { GenerationControls } from "@/components/generation/generation-controls";

const navigation = vi.hoisted(() => ({ refresh: vi.fn(), replace: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => navigation,
}));

const articleId = "10000000-0000-4000-8000-000000000003";
const generationResponse = {
  generation_id: "20000000-0000-4000-8000-000000000004",
  article_id: articleId,
  draft: "A synthetic LinkedIn draft for human review.",
  tone: "professional",
  length: "medium",
  source_title: "Synthetic technology update",
  source_name: "NewsFlow AI synthetic fixture",
  source_url: "https://example.invalid/newsflow-ai/fixture-technology-001",
  source_attribution: "Source: NewsFlow AI synthetic fixture - not live news",
  status: "draft",
  review_required: true,
  grounding_status: "passed_automated_checks",
  validation_warnings: [],
  grounding_policy_version: "grounding_v1",
  created_at: "2026-11-01T09:00:00Z",
};

function renderAvailableControls() {
  return render(
    <GenerationControls articleId={articleId} availabilityStatus="available" generationAllowed />,
  );
}

describe("LinkedIn generation controls", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    navigation.refresh.mockReset();
    navigation.replace.mockReset();
    document.cookie = "newsflow_csrf=csrf-test-token; path=/";
  });

  afterEach(() => {
    cleanup();
    document.cookie = "newsflow_csrf=; Max-Age=0; path=/";
    vi.unstubAllGlobals();
  });

  test("selects the supported professional and medium defaults", () => {
    renderAvailableControls();

    expect((screen.getByRole("radio", { name: /professional/i }) as HTMLInputElement).checked).toBe(
      true,
    );
    expect((screen.getByRole("radio", { name: /medium/i }) as HTMLInputElement).checked).toBe(true);
    expect(screen.getAllByRole("radio")).toHaveLength(6);
    expect(screen.getByRole("button", { name: "Generate LinkedIn draft" })).toBeDefined();
  });

  test("submits the selected article, tone, length, CSRF proof, and idempotency key", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ ...generationResponse, tone: "analytical", length: "long" }), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      }),
    );
    renderAvailableControls();

    fireEvent.click(screen.getByRole("radio", { name: /analytical/i }));
    fireEvent.click(screen.getByRole("radio", { name: /long/i }));
    fireEvent.click(screen.getByRole("button", { name: "Generate LinkedIn draft" }));

    expect(await screen.findByText("Your private draft has been generated.")).toBeDefined();
    expect(fetch).toHaveBeenCalledOnce();
    const [, options] = vi.mocked(fetch).mock.calls[0] ?? [];
    expect(options).toEqual(
      expect.objectContaining({
        method: "POST",
        credentials: "same-origin",
        body: JSON.stringify({ article_id: articleId, tone: "analytical", length: "long" }),
      }),
    );
    expect(new Headers(options?.headers).get("x-csrf-token")).toBe("csrf-test-token");
    expect(new Headers(options?.headers).get("idempotency-key")).toMatch(/^generation:/);
    expect(screen.getByText(/nothing has been published to LinkedIn/i)).toBeDefined();
    await waitFor(() =>
      expect(document.activeElement?.textContent).toContain(
        "Your private draft has been generated.",
      ),
    );
  });

  test("prevents duplicate submissions while a request is active", async () => {
    vi.mocked(fetch).mockImplementationOnce(() => new Promise(() => undefined));
    renderAvailableControls();

    const button = screen.getByRole("button", { name: "Generate LinkedIn draft" });
    fireEvent.click(button);
    fireEvent.submit(button.closest("form") as HTMLFormElement);

    expect(await screen.findByRole("button", { name: "Generating draft..." })).toHaveProperty(
      "disabled",
      true,
    );
    expect(fetch).toHaveBeenCalledOnce();
    expect(
      screen.getByText("Your LinkedIn draft generation request is being processed."),
    ).toBeDefined();
  });

  test("keeps generation disabled without an article or with a restricted article", () => {
    const { rerender } = render(
      <GenerationControls
        articleId={null}
        availabilityStatus="missing"
        generationAllowed={false}
      />,
    );

    expect(screen.getByText(/choose an article from the authorised catalogue/i)).toBeDefined();
    expect(screen.getByRole("button", { name: "Generate LinkedIn draft" })).toHaveProperty(
      "disabled",
      true,
    );

    rerender(
      <GenerationControls
        articleId={articleId}
        availabilityStatus="restricted"
        generationAllowed={false}
      />,
    );
    expect(screen.getByText(/source permissions do not allow AI generation/i)).toBeDefined();
    expect(fetch).not.toHaveBeenCalled();
  });

  test("returns the user to login when authentication cannot be confirmed", async () => {
    document.cookie = "newsflow_csrf=; Max-Age=0; path=/";
    renderAvailableControls();

    fireEvent.click(screen.getByRole("button", { name: "Generate LinkedIn draft" }));

    await waitFor(() =>
      expect(navigation.replace).toHaveBeenCalledWith("/login?reason=session_expired"),
    );
    expect(navigation.refresh).toHaveBeenCalledOnce();
    expect(fetch).not.toHaveBeenCalled();
  });

  test("returns the user to login when FastAPI rejects stale CSRF proof", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          error: {
            code: "csrf_validation_failed",
            message: "CSRF validation failed.",
          },
        }),
        { status: 403, headers: { "Content-Type": "application/json" } },
      ),
    );
    renderAvailableControls();

    fireEvent.click(screen.getByRole("button", { name: "Generate LinkedIn draft" }));

    await waitFor(() =>
      expect(navigation.replace).toHaveBeenCalledWith("/login?reason=session_expired"),
    );
    expect(navigation.refresh).toHaveBeenCalledOnce();
  });

  test("explains a usage limit and temporarily disables another request", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          error: {
            code: "generation_limit_exceeded",
            message: "Your daily generation allowance has been reached.",
          },
        }),
        {
          status: 429,
          headers: { "Content-Type": "application/json", "Retry-After": "30" },
        },
      ),
    );
    renderAvailableControls();

    fireEvent.click(screen.getByRole("button", { name: "Generate LinkedIn draft" }));

    expect(
      await screen.findByText("Your daily generation allowance has been reached."),
    ).toBeDefined();
    expect(screen.getByRole("button", { name: "Try again in 30s" })).toHaveProperty(
      "disabled",
      true,
    );
  });

  test("rejects a successful response that does not match the selected request", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          ...generationResponse,
          article_id: "30000000-0000-4000-8000-000000000005",
        }),
        { status: 201, headers: { "Content-Type": "application/json" } },
      ),
    );
    renderAvailableControls();

    fireEvent.click(screen.getByRole("button", { name: "Generate LinkedIn draft" }));

    expect(
      await screen.findByText(
        "The generated draft response could not be verified. Please try again.",
      ),
    ).toBeDefined();
    expect(screen.queryByText("Your private draft has been generated.")).toBeNull();
  });

  test("shows a provider timeout as a retryable failure", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          error: {
            code: "openai_timeout",
            message: "The AI provider took too long to respond.",
          },
        }),
        { status: 504, headers: { "Content-Type": "application/json" } },
      ),
    );
    renderAvailableControls();

    fireEvent.click(screen.getByRole("button", { name: "Generate LinkedIn draft" }));

    expect(await screen.findByText("The AI provider took too long to respond.")).toBeDefined();
    expect(screen.getByRole("button", { name: "Try again" })).toBeDefined();
  });

  test("uses native, labelled controls that remain operable without a pointer", () => {
    renderAvailableControls();

    const conversational = screen.getByRole("radio", { name: /conversational/i });
    conversational.focus();
    fireEvent.click(conversational);

    expect(document.activeElement).toBe(conversational);
    expect((conversational as HTMLInputElement).checked).toBe(true);
    expect(screen.getByRole("group", { name: "Writing tone" })).toBeDefined();
    expect(screen.getByRole("group", { name: "Post length" })).toBeDefined();
  });
});
