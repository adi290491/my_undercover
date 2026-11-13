import type { Step } from "./api";

// Every run ends with the agent's final message or an error, so a run whose
// last step is anything else is still going.
export function runEnded(steps: Step[] | undefined): boolean {
  const last = steps?.at(-1);
  return !last || last.kind === "message" || last.kind === "error";
}

export function runs(steps: Step[]): Step[][] {
  const byThread = new Map<string, Step[]>();
  for (const step of steps) {
    byThread.set(step.thread_id, [
      ...(byThread.get(step.thread_id) ?? []),
      step,
    ]);
  }
  return [...byThread.values()];
}
