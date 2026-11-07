import { useState } from "react";
import {
  type Claim,
  type ClaimHistory,
  type Policy,
  post,
  useApi,
} from "./api";
import {
  ClaimStory,
  DecisionPanel,
  HistoryPanel,
  PolicyPanel,
} from "./ClaimParts";
import { money, words } from "./format";
import { StatusBadge } from "./StatusBadge";

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
  const [version, setVersion] = useState(0);
  const [problem, setProblem] = useState("");
  const { data: claim, error } = useApi<Claim>(
    `/api/claims/${claimId}`,
    version,
  );
  if (error) return <p role="alert">{error}</p>;
  if (!claim) return <p>Loading {claimId}</p>;

  const runAgent = () => {
    setProblem("");
    post(`/api/claims/${claimId}/run`).then(
      () => {
        setVersion((v) => v + 1);
      },
      (failure: unknown) => {
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
          <button type="button" onClick={runAgent}>
            Run the agent
          </button>
        )}
      </header>
      {problem && <p role="alert">{problem}</p>}
      <div className="columns">
        <div className="stack">
          <ClaimStory claim={claim} />
        </div>
        <div className="stack">
          <DecisionPanel claim={claim} />
          <Related claim={claim} />
        </div>
      </div>
    </>
  );
}
