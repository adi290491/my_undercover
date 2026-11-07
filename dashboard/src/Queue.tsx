import { type ClaimSummary, useApi } from "./api";
import { date, money, STATUS_LABELS, STATUSES, words } from "./format";
import { StatusBadge } from "./StatusBadge";

export function Queue() {
  const { data: claims, error } = useApi<ClaimSummary[]>("/api/claims");
  if (error) return <p role="alert">{error}</p>;
  if (!claims) return <p>Loading the queue</p>;

  return (
    <>
      <h1>Claims queue</h1>
      <ul className="counts" aria-label="Claims by status">
        {STATUSES.map((status) => (
          <li key={status} className={`count status-${status}`}>
            <span className="number">
              {claims.filter((claim) => claim.status === status).length}
            </span>
            <span>{STATUS_LABELS[status]}</span>
          </li>
        ))}
      </ul>
      <ul className="panel claims" aria-label="Claims">
        {claims.map((claim) => (
          <li key={claim.claim_id}>
            <a className="claim-row" href={`#/claims/${claim.claim_id}`}>
              <span className="mono">{claim.claim_id}</span>
              <span className="who">
                <strong>{claim.customer_name}</strong>
                <span className="muted">{claim.summary}</span>
              </span>
              <span>{words(claim.claim_type)}</span>
              <span className="muted">{date(claim.submitted_on)}</span>
              <span className="mono amount">{money(claim.amount_claimed)}</span>
              <StatusBadge status={claim.status} />
            </a>
          </li>
        ))}
      </ul>
    </>
  );
}
