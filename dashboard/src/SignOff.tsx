import { useState } from "react";
import { type Claim, type Handler, post, useApi } from "./api";
import { money } from "./format";

export function SignOffPanel({
  claim,
  onSigned,
}: Readonly<{ claim: Claim; onSigned: () => void }>) {
  const { data: handlers } = useApi<Handler[]>("/api/handlers");
  const [handlerId, setHandlerId] = useState("");
  const [problem, setProblem] = useState("");

  const signOff = () => {
    post(`/api/claims/${claim.claim_id}/sign-off`, {
      handler_id: handlerId,
    }).then(onSigned, (failure: unknown) => {
      setProblem(String(failure));
    });
  };

  return (
    <section className="panel" aria-label="Sign-off">
      <h2>Waiting for sign-off</h2>
      <p>
        The payout of {money(claim.decision?.payout ?? 0)} is over the $1,000.00
        limit, so it is paid only when a handler signs off.
      </p>
      <div className="sign-off">
        <label>
          Handler{" "}
          <select
            value={handlerId}
            onChange={(event) => {
              setHandlerId(event.target.value);
            }}
          >
            <option value="">Choose a handler</option>
            {handlers?.map((handler) => (
              <option key={handler.handler_id} value={handler.handler_id}>
                {handler.name}
              </option>
            ))}
          </select>
        </label>
        <button type="button" disabled={!handlerId} onClick={signOff}>
          Sign off and pay
        </button>
      </div>
      {problem && <p role="alert">{problem}</p>}
    </section>
  );
}
