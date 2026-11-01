import {
  act,
  cleanup,
  fireEvent,
  render,
  renderHook,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import { GenerationStatus } from "@/components/generation/generation-status";
import { useGeneration, useTextGeneration } from "@/hooks/use-generation";
import { useImageGeneration } from "@/hooks/use-image-generation";
import type {
  GenerationFailure,
  GenerationOperationResult,
  GenerationState,
} from "@/types/generation-state";

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolver) => {
    resolve = resolver;
  });
  return { promise, resolve };
}

const retryableTimeout: GenerationFailure = {
  category: "timeout",
  message: "The AI provider took too long to respond. Please try again deliberately.",
  retryAfterSeconds: null,
  retryable: true,
};

describe("reusable generation state system", () => {
  afterEach(() => cleanup());

  test("moves from idle through submitting and processing to completed", async () => {
    const operation = deferred<GenerationOperationResult<string>>();
    const execute = vi.fn(() => operation.promise);
    const { result } = renderHook(() => useTextGeneration(execute));

    expect(result.current.state.phase).toBe("idle");

    let run!: ReturnType<typeof result.current.start>;
    act(() => {
      run = result.current.start("draft request");
    });
    expect(result.current.state.phase).toBe("submitting");
    await waitFor(() => expect(result.current.state.phase).toBe("processing"));

    await act(async () => {
      operation.resolve({ data: "private draft", status: "success" });
      await run;
    });
    expect(result.current.state.phase).toBe("completed");
    expect(result.current.state.result).toBe("private draft");
  });

  test("creates a safe failed state when an operation throws a network error", async () => {
    const execute = vi.fn(async () => {
      throw new Error("private network details");
    });
    const { result } = renderHook(() => useTextGeneration(execute));

    await act(async () => {
      await result.current.start("draft request");
    });

    expect(result.current.state.phase).toBe("failed");
    expect(result.current.state.error?.category).toBe("network");
    expect(result.current.state.error?.message).not.toContain("private network details");
  });

  test("allows one deliberate retry after a retryable timeout", async () => {
    const execute = vi
      .fn()
      .mockResolvedValueOnce({ error: retryableTimeout, status: "error" })
      .mockResolvedValueOnce({ data: "retried draft", status: "success" });
    const { result } = renderHook(() => useTextGeneration<string, string>(execute));

    await act(async () => {
      await result.current.start("draft request");
    });
    expect(result.current.state.phase).toBe("failed");

    await act(async () => {
      await result.current.retry();
    });
    expect(result.current.state.phase).toBe("completed");
    expect(result.current.state.result).toBe("retried draft");
    expect(execute).toHaveBeenCalledTimes(2);
  });

  test("prevents a second request while generation is active", async () => {
    const operation = deferred<GenerationOperationResult<string>>();
    const execute = vi.fn(() => operation.promise);
    const { result } = renderHook(() => useTextGeneration(execute));

    let firstRun!: ReturnType<typeof result.current.start>;
    act(() => {
      firstRun = result.current.start("first");
    });
    const duplicate = await result.current.start("duplicate");

    expect(duplicate).toEqual({ accepted: false });
    expect(execute).toHaveBeenCalledTimes(1);

    await act(async () => {
      operation.resolve({ data: "first result", status: "success" });
      await firstRun;
    });
  });

  test("does not let an older response replace a newer result", async () => {
    const first = deferred<GenerationOperationResult<string>>();
    const second = deferred<GenerationOperationResult<string>>();
    const execute = vi.fn((input: string) => (input === "first" ? first.promise : second.promise));
    const { result } = renderHook(() => useTextGeneration(execute));

    let firstRun!: ReturnType<typeof result.current.start>;
    act(() => {
      firstRun = result.current.start("first");
    });
    await waitFor(() => expect(result.current.state.phase).toBe("processing"));

    act(() => result.current.reset());
    let secondRun!: ReturnType<typeof result.current.start>;
    act(() => {
      secondRun = result.current.start("second");
    });
    await waitFor(() => expect(result.current.state.phase).toBe("processing"));

    await act(async () => {
      second.resolve({ data: "newer result", status: "success" });
      await secondRun;
    });
    expect(result.current.state.result).toBe("newer result");

    await act(async () => {
      first.resolve({ data: "older result", status: "success" });
      await firstRun;
    });
    expect(result.current.state.phase).toBe("completed");
    expect(result.current.state.result).toBe("newer result");
  });

  test("supports image-specific processing and completion feedback", async () => {
    const operation = deferred<GenerationOperationResult<string>>();
    const execute = vi.fn(() => operation.promise);

    function ImageHarness() {
      const generation = useImageGeneration<string, string>(execute);
      return (
        <>
          <button onClick={() => void generation.start("image request")} type="button">
            Create image
          </button>
          <GenerationStatus state={generation.state} />
        </>
      );
    }

    render(<ImageHarness />);
    expect(screen.getByText("Ready to create an illustration.")).toBeDefined();
    fireEvent.click(screen.getByRole("button", { name: "Create image" }));
    expect(await screen.findByText("Creating your illustration...")).toBeDefined();

    await act(async () => {
      operation.resolve({ data: "private image", status: "success" });
    });
    expect(await screen.findByText("Your private illustration is ready for review.")).toBeDefined();
  });

  test("presents usage limits without enabling an early retry", () => {
    const state: GenerationState<never> = {
      error: {
        category: "usage_limit",
        message: "Your daily generation allowance has been reached.",
        retryAfterSeconds: 30,
        retryable: true,
      },
      failedAt: Date.now(),
      kind: "text",
      phase: "failed",
      requestId: "text:1",
      result: null,
    };

    render(<GenerationStatus onRetry={vi.fn()} retrySeconds={30} state={state} />);

    expect(screen.getByRole("alert")).toBeDefined();
    expect(screen.getByText("Your daily generation allowance has been reached.")).toBeDefined();
    expect(screen.getByRole("button", { name: "Try again in 30s" })).toHaveProperty(
      "disabled",
      true,
    );
  });

  test("announces processing politely and failures assertively", () => {
    const processing: GenerationState<string> = {
      error: null,
      kind: "text",
      phase: "processing",
      requestId: "text:1",
      result: null,
      startedAt: Date.now(),
    };
    const { rerender } = render(<GenerationStatus state={processing} />);
    expect(screen.getByRole("status").getAttribute("aria-live")).toBe("polite");

    rerender(
      <GenerationStatus
        state={{
          error: retryableTimeout,
          failedAt: Date.now(),
          kind: "text",
          phase: "failed",
          requestId: "text:1",
          result: null,
        }}
      />,
    );
    expect(screen.getByRole("alert").getAttribute("aria-live")).toBe("assertive");
  });

  test("does not expose a cancellation action for synchronous backend requests", () => {
    const execute = vi.fn(async () => ({ data: "result", status: "success" as const }));
    const { result } = renderHook(() => useGeneration({ execute, kind: "text" }));

    expect("cancel" in result.current).toBe(false);
  });
});
