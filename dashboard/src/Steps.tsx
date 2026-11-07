import { type Step, useApi } from "./api";
import { clock } from "./format";

const KIND_LABELS: Record<Step["kind"], string> = {
  tool_call: "Called",
  tool_result: "Result",
  message: "Reply",
  error: "Stopped",
};

function StepItem({ step }: Readonly<{ step: Step }>) {
  if (step.kind !== "tool_result") {
    return (
      <li className={`step step-${step.kind}`}>
        <time className="mono muted">{clock(step.at)}</time>
        <span className="step-kind">{KIND_LABELS[step.kind]}</span>
        <span className={step.kind === "tool_call" ? "mono" : undefined}>
          {step.text}
        </span>
      </li>
    );
  }
  const [name = "", ...rest] = step.text.split(": ");
  const result = rest.join(": ");
  return (
    <li className="step step-tool_result">
      <time className="mono muted">{clock(step.at)}</time>
      <span className="step-kind">{KIND_LABELS[step.kind]}</span>
      <details>
        <summary>
          <span className="mono">{name}</span>{" "}
          <span className="muted">{result.slice(0, 80)}</span>
        </summary>
        <pre>{result}</pre>
      </details>
    </li>
  );
}

export function StepsPanel({
  claimId,
  version,
}: Readonly<{ claimId: string; version: number }>) {
  const { data: steps } = useApi<Step[]>(
    `/api/claims/${claimId}/steps`,
    version,
  );
  return (
    <section className="panel" aria-label="Agent steps">
      <h2>What the agent did</h2>
      {steps?.length === 0 && (
        <p className="muted">The agent has not worked on this claim yet.</p>
      )}
      <ol className="steps">
        {steps?.map((step) => (
          <StepItem key={step.step_id} step={step} />
        ))}
      </ol>
    </section>
  );
}
