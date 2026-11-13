import type { Step, StepKind } from "./api";
import { clock } from "./format";
import { useApi } from "./useApi";

const KINDS: Record<StepKind, string> = {
  tool_call: "Action",
  tool_result: "Result",
  message: "Agent",
  error: "Problem",
};

function runs(steps: Step[]): Step[][] {
  const byThread = new Map<string, Step[]>();
  for (const step of steps) {
    byThread.set(step.thread_id, [
      ...(byThread.get(step.thread_id) ?? []),
      step,
    ]);
  }
  return [...byThread.values()];
}

function StepRow({ step }: Readonly<{ step: Step }>) {
  return (
    <li className={`step ${step.kind}`}>
      <span className="step-time num">{clock(step.created_at)}</span>
      <span className="step-kind">{KINDS[step.kind]}</span>
      {step.kind === "tool_result" ? (
        <details className="step-text">
          <summary>Show the result</summary>
          <pre>{step.text}</pre>
        </details>
      ) : (
        <p className="step-text">{step.text}</p>
      )}
    </li>
  );
}

export function Steps({
  claimId,
  refreshMs,
}: Readonly<{ claimId: string; refreshMs: number }>) {
  const { data: steps, error } = useApi<Step[]>(
    `/api/claims/${claimId}/steps`,
    refreshMs,
  );
  return (
    <section className="panel" aria-labelledby="steps">
      <h2 id="steps">The agent's steps</h2>
      {!steps && <p className="notice">{error ?? "Loading the steps"}</p>}
      {steps?.length === 0 && (
        <p className="notice">The agent hasn't worked on this claim yet.</p>
      )}
      {steps &&
        runs(steps).map((run, index) => (
          <div className="run" key={run[0]?.thread_id}>
            <h3>Run {index + 1}</h3>
            <ol className="steps">
              {run.map((step) => (
                <StepRow key={step.step_id} step={step} />
              ))}
            </ol>
          </div>
        ))}
    </section>
  );
}
