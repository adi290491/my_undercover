import type { Claim } from "./api";
import { ClaimRecords } from "./ClaimRecords";
import { date, label, money } from "./format";
import { HistoryPanel, PolicyPanel } from "./PolicyPanel";
import { links } from "./router";
import { StatusBadge } from "./StatusBadge";
import { useApi } from "./useApi";

export function ClaimPage({ claimId }: Readonly<{ claimId: string }>) {
  const { data: claim, error } = useApi<Claim>(`/api/claims/${claimId}`, 0);

  if (!claim) {
    return (
      <p className="notice">
        {error ?? "Loading the claim"}{" "}
        {error && <a href={links.queue}>Back to the queue</a>}
      </p>
    );
  }

  return (
    <>
      <a className="back" href={links.queue}>
        Back to the queue
      </a>
      <div className="claim-title">
        <h1>{claim.claim_id}</h1>
        <StatusBadge status={claim.status} />
      </div>
      <p className="claim-subtitle">
        {label(claim.claim_type)} for {claim.customer_name}
      </p>
      <dl className="panel facts">
        <div>
          <dt>Amount claimed</dt>
          <dd className="num">{money(claim.amount_claimed)}</dd>
        </div>
        <div>
          <dt>Submitted</dt>
          <dd>{date(claim.submitted_on)}</dd>
        </div>
        <div>
          <dt>Incident</dt>
          <dd>
            {date(claim.incident_date)}, {claim.incident_location}
          </dd>
        </div>
      </dl>
      <div className="claim-layout">
        <div className="stack">
          <ClaimRecords claim={claim} />
        </div>
        <aside className="stack">
          <PolicyPanel policyId={claim.policy_id} />
          <HistoryPanel customerId={claim.customer_id} />
        </aside>
      </div>
    </>
  );
}
