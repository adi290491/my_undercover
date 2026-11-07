import { useState } from "react";
import {
  type Claim,
  type ClaimHistory,
  type Policy,
  post,
  useApi,
  useInterval,
  useVersion,
} from "./api";
import {
  ClaimStory,
  DecisionPanel,
  HistoryPanel,
  PolicyPanel,
} from "./ClaimParts";
import { money, words } from "./format";
import { SignOffPanel } from "./SignOff";
import { StatusBadge } from "./StatusBadge";
import { StepsPanel } from "./Steps";

function Related({ claim }: Readonly<{ claim: Claim }>) {
  const policy = useApi<Policy>(`/api/policies/${claim.policy_id}`);
  const history = useApi<ClaimHistory>(
    `/api/customers/${claim.customer_id}/claims`,
  );
  return (
    <>
      {policy.data && <PolicyPanel policy={policy.data} />}
      {history.data && <HistoryPanel history={history.data} />}
    </>
  );
}

export function ClaimPage({ claimId }: Readonly<{ claimId: string }>) {
  const [version, bump] = useVersion();
  const [problem, setProblem] = useState("");
  // The thread of a run we asked for: until the claim shows it, the run has
  // not started. Empty while the request is on its way.
  const [launched, setLaunched] = useState<string>();
  const { data: claim, error } = useApi<Claim>(
    `/api/claims/${claimId}`,
    version,
  );
  const live = claim?.status === "waiting" || claim?.status === "in_progress";
  useInterval(bump, live ? 1000 : null);
  if (error) return <p role="alert">{error}</p>;
  if (!claim) return <p>Loading {claimId}</p>;

  const starting = launched !== undefined && claim.thread_id !== launched;
  const runAgent = () => {
    setProblem("");
    setLaunched("");
    post<{ thread_id: string }>(`/api/claims/${claimId}/run`).then(
      (run) => {
        setLaunched(run.thread_id);
        bump();
      },
      (failure: unknown) => {
        setLaunched(undefined);
        setProblem(String(failure));
      },
    );
  };

  return (
    <>
      <a href="#/">Back to the queue</a>
      <header className="claim-header">
        <div>
          <h1>
            <span className="mono">{claim.claim_id}</span> {claim.customer_name}
          </h1>
          <p className="muted">
            {words(claim.claim_type)}, {money(claim.amount_claimed)} claimed
          </p>
        </div>
        <StatusBadge status={claim.status} />
        {claim.status === "waiting" && (
          <button type="button" onClick={runAgent} disabled={starting}>
            {starting ? "Starting the agent" : "Run the agent"}
          </button>
        )}
      </header>
      {problem && <p role="alert">{problem}</p>}
      <div className="columns">
        <div className="stack">
          <ClaimStory claim={claim} />
        </div>
        <div className="stack">
          {claim.status === "awaiting_signoff" && (
            <SignOffPanel claim={claim} onSigned={bump} />
          )}
          <DecisionPanel claim={claim} />
          <StepsPanel claimId={claimId} version={version} />
          <Related claim={claim} />
        </div>
      </div>
    </>
  );
}
