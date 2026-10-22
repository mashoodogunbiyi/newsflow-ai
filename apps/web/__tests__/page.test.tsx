import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import Home from "@/app/page";

describe("NewsFlow AI homepage", () => {
  test("renders the primary heading and fixture-mode status", () => {
    render(<Home />);

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "Turn careful reporting into confident LinkedIn content.",
      }),
    ).toBeDefined();
    expect(screen.getAllByText(/fixture mode/i)).toHaveLength(2);
  });
});
