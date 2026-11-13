import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { Instructions } from "../../dashboard/src/Instructions";
import { blocks, spans } from "../../dashboard/src/prose";
import { Refusal, stubApi } from "./testing";

const text = `# How the agent works

You are the agent.
You read claims.

## 1. Read

- the **claim**
- the \`policy\`

1. Start here.
2. Then here.
`;

it("shows the instructions, read only", async () => {
  stubApi({ "/api/instructions": { text } });
  const { container } = render(<Instructions />);
  expect(
    await screen.findByRole("heading", { name: "How the agent works" }),
  ).toBeDefined();
  expect(screen.getByRole("heading", { name: "1. Read" })).toBeDefined();
  expect(screen.getByText("You are the agent. You read claims.")).toBeDefined();
  expect(screen.getByText("claim").tagName).toBe("STRONG");
  expect(screen.getByText("policy").tagName).toBe("CODE");
  expect(screen.getAllByRole("list")).toHaveLength(2);
  expect(screen.getByText(/Read only/)).toBeDefined();
  expect(
    container.querySelector("input, textarea, [contenteditable], button"),
  ).toBeNull();
});

it("says when the instructions can't be loaded", async () => {
  stubApi({ "/api/instructions": new Refusal(500, "The file is missing.") });
  render(<Instructions />);
  expect(await screen.findByText("The file is missing.")).toBeDefined();
});

it("splits markdown into blocks and spans", () => {
  expect(blocks(text).map((b) => b.kind)).toEqual([
    "heading",
    "p",
    "heading",
    "ul",
    "ol",
  ]);
  expect(blocks("- one\n- two\n\nAfter")).toEqual([
    { kind: "ul", items: ["one", "two"] },
    { kind: "p", text: "After" },
  ]);
  expect(spans("a **b** `c`")).toEqual([
    { kind: "text", text: "a " },
    { kind: "strong", text: "b" },
    { kind: "text", text: " " },
    { kind: "code", text: "c" },
  ]);
});
