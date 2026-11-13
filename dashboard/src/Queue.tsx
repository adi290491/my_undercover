import { STATUSES, type ClaimSummary } from "./api";
import { date, label, money } from "./format";
import { links } from "./router";
import { StatusBadge } from "./StatusBadge";
import { useApi } from "./useApi";

export function Queue() {
  const { data: claims, error } = useApi<ClaimSummary[]>("/api/claims", 0);

  if (!claims) {
    return (
      <p className="notice">
        {error ? `The queue couldn't be loaded: ${error}` : "Loading the queue"}
      </p>
    );
  }

  return (
    <>
      <h1>Claims queue</h1>
      <section className="counts" aria-label="Claims by status">
        {STATUSES.map((status) => (
          <div className="panel count" key={status}>
            <StatusBadge status={status} />
            <span className="count-number num">
              {claims.filter((c) => c.status === status).length}
            </span>
          </div>
        ))}
      </section>
      <section className="panel table-panel">
        <table className="queue-table">
          <thead>
            <tr>
              <th scope="col">Claim</th>
              <th scope="col">Customer</th>
              <th scope="col">Type</th>
              <th scope="col" className="amount">
                Amount claimed
              </th>
              <th scope="col">Submitted</th>
              <th scope="col">Status</th>
            </tr>
          </thead>
          <tbody>
            {claims.map((claim) => (
              <tr key={claim.claim_id}>
                <td data-label="Claim">
                  <a className="num" href={links.claim(claim.claim_id)}>
                    {claim.claim_id}
                  </a>
                </td>
                <td data-label="Customer">{claim.customer_name}</td>
                <td data-label="Type">{label(claim.claim_type)}</td>
                <td data-label="Amount claimed" className="amount num">
                  {money(claim.amount_claimed)}
                </td>
                <td data-label="Submitted">{date(claim.submitted_on)}</td>
                <td data-label="Status">
                  <StatusBadge status={claim.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}
