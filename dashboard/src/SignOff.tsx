import { useState } from "react";
import { postJson, type Handler } from "./api";
import { money } from "./format";
import { useApi } from "./useApi";

export function SignOff({
  claimId,
  payout,
  onSigned,
}: Readonly<{ claimId: string; payout: number; onSigned: () => void }>) {
  const { data: handlers, error: loadError } = useApi<Handler[]>(
    "/api/handlers",
    0,
  );
  const [handlerId, setHandlerId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();

  const signOff = () => {
    setBusy(true);
    setError(undefined);
    postJson(`/api/claims/${claimId}/sign-off`, { handler_id: handlerId })
      .then(onSigned, (failure: unknown) => {
        setError(failure instanceof Error ? failure.message : String(failure));
      })
      .finally(() => {
        setBusy(false);
      });
  };

  return (
    <section className="panel" aria-labelledby="sign-off">
      <h2 id="sign-off">Sign off the payout</h2>
      <p>
        The agent approved {money(payout)}, which is over the approval limit.
        Signing it off pays it.
      </p>
      <div className="sign-off">
        <label htmlFor="handler">Handler</label>
        <select
          id="handler"
          value={handlerId}
          onChange={(event) => {
            setHandlerId(event.target.value);
          }}
        >
          <option value="">Choose a handler</option>
          {handlers
            ?.filter((handler) => handler.can_approve_over_limit)
            .map((handler) => (
              <option key={handler.handler_id} value={handler.handler_id}>
                {handler.name}, {handler.role}
              </option>
            ))}
        </select>
        <button
          type="button"
          className="primary"
          disabled={!handlerId || busy}
          onClick={signOff}
        >
          Sign off and pay {money(payout)}
        </button>
      </div>
      {(error ?? loadError) && <p className="alert">{error ?? loadError}</p>}
    </section>
  );
}
