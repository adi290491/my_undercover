import { useState } from "react";
import { postJson } from "./api";

export function RunButton({
  claimId,
  onStarted,
}: Readonly<{ claimId: string; onStarted: () => void }>) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();

  const start = () => {
    setBusy(true);
    setError(undefined);
    postJson(`/api/claims/${claimId}/run`, {})
      .then(onStarted, (failure: unknown) => {
        setError(failure instanceof Error ? failure.message : String(failure));
      })
      .finally(() => {
        setBusy(false);
      });
  };

  return (
    <div className="run-agent">
      <button type="button" className="primary" disabled={busy} onClick={start}>
        {busy ? "Starting the agent" : "Run the agent"}
      </button>
      {error && <p className="alert">{error}</p>}
    </div>
  );
}
