import type { PastClaim, Policy } from "./api";
import { addOn, date, dateRange, label, money } from "./format";
import { useApi } from "./useApi";

export function PolicyPanel({ policyId }: Readonly<{ policyId: string }>) {
  const { data: policy, error } = useApi<Policy>(
    `/api/policies/${policyId}`,
    0,
  );
  return (
    <section className="panel" aria-labelledby="policy">
      <h2 id="policy">Policy</h2>
      {policy ? (
        <dl className="details">
          <dt>Policy</dt>
          <dd className="num">{policy.policy_id}</dd>
          <dt>Plan</dt>
          <dd>{label(policy.plan)}</dd>
          <dt>Add-ons</dt>
          <dd>{policy.add_ons.map(addOn).join(", ") || "None"}</dd>
          <dt>Bought</dt>
          <dd>
            {date(policy.purchased_on)}, through {policy.sold_through}
          </dd>
          <dt>Trip</dt>
          <dd>
            {policy.trip.destination},{" "}
            {dateRange(policy.trip.departs_on, policy.trip.returns_on)}
          </dd>
          <dt>Trip cost</dt>
          <dd className="num">{money(policy.trip.trip_cost)}</dd>
          <dt>Travelers</dt>
          <dd>{policy.travelers.join(", ")}</dd>
        </dl>
      ) : (
        <p className="notice">{error ?? "Loading the policy"}</p>
      )}
    </section>
  );
}

export function HistoryPanel({ customerId }: Readonly<{ customerId: string }>) {
  const { data: history, error } = useApi<PastClaim[]>(
    `/api/customers/${customerId}/claims`,
    0,
  );
  return (
    <section className="panel" aria-labelledby="history">
      <h2 id="history">Claim history</h2>
      {history ? (
        <PastClaims history={history} />
      ) : (
        <p className="notice">{error ?? "Loading the claim history"}</p>
      )}
    </section>
  );
}

function PastClaims({ history }: Readonly<{ history: PastClaim[] }>) {
  if (history.length === 0) return <p className="notice">No earlier claims.</p>;
  return (
    <ul className="history">
      {history.map((past) => (
        <li key={past.claim_id}>
          <p className="history-heading">
            <span className="num">{past.claim_id}</span>
            <span>{label(past.claim_type)}</span>
          </p>
          <p>{past.summary}</p>
          <p className="notice">
            Filed {date(past.filed_on)}. {label(past.outcome)}
            {past.amount_paid > 0 && `, ${money(past.amount_paid)} paid`}.
          </p>
        </li>
      ))}
    </ul>
  );
}
