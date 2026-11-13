import { useCallback } from "react";
import type { Step } from "./api";
import { clock } from "./format";
import { runEnded, runs } from "./runs";
import { useApi } from "./useApi";

const LABELS = {
  tool_call: "Action",
  tool_result: "Result",
  refused: "Refused",
  message: "Agent",
  error: "Problem",
};

// The backend's refusals come back to the agent as a tool result that starts
// like "Refused (403): ...".
function look(step: Step): keyof typeof LABELS {
  if (step.kind === "tool_result" && step.text.startsWith("Refused (")) {
    return "refused";
  }
  return step.kind;
}

function StepRow({ step }: Readonly<{ step: Step }>) {
  const kind = look(step);
  return (
    <li className={`step ${kind}`}>
      <span className="step-time num">{clock(step.created_at)}</span>
      <span className="step-kind">{LABELS[kind]}</span>
      {kind === "tool_result" ? (
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
  claimInProgress,
}: Readonly<{ claimId: string; claimInProgress: boolean }>) {
  const refresh = useCallback(
    (steps: Step[] | undefined) =>
      claimInProgress || !runEnded(steps) ? 1000 : 0,
    [claimInProgress],
  );
  const { data: steps, error } = useApi<Step[]>(
    `/api/claims/${claimId}/steps`,
    refresh,
  );
  const working = claimInProgress || !runEnded(steps);
  return (
    <section className="panel" aria-labelledby="steps">
      <h2 id="steps">The agent's steps</h2>
      {working && (
        <p className="working">
          The agent is working on this claim. Its steps appear here as it goes.
        </p>
      )}
      {!steps && <p className="notice">{error ?? "Loading the steps"}</p>}
      {steps?.length === 0 && (
        <p className="notice">The agent hasn't worked on this claim yet.</p>
      )}
      {steps &&
        runs(steps).map((run, index) => (
          <div className="run" key={run[0]?.thread_id}>
            <h3>Run {index + 1}</h3>
            <ol className="steps" aria-live="polite">
              {run.map((step) => (
                <StepRow key={step.step_id} step={step} />
              ))}
            </ol>
          </div>
        ))}
    </section>
  );
}
