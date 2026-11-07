import type { Claim, ClaimHistory, Policy } from "./api";
import { date, money, when, words } from "./format";

export function DecisionPanel({ claim }: Readonly<{ claim: Claim }>) {
  const { decision, payment, sign_off } = claim;
  if (!decision) {
    return (
      <section className="panel" aria-label="Decision">
        <h2>Decision</h2>
        <p className="muted">The agent has not decided this claim yet.</p>
      </section>
    );
  }
  return (
    <section className="panel" aria-label="Decision">
      <h2>Decision</h2>
      <p className="decision-line">
        <span className={`badge decision-${decision.decision}`}>
          {words(decision.decision)}
        </span>
        <span className="mono payout">{money(decision.payout)}</span>
      </p>
      <p>{decision.reason}</p>
      <p className="muted">{decision.policy_section}</p>
      {payment && (
        <p>
          Paid <span className="mono">{money(payment.amount)}</span> on{" "}
          {when(payment.paid_at)}
        </p>
      )}
      {sign_off && <p>Signed off by {sign_off.handler_name}</p>}
    </section>
  );
}

export function ClaimStory({ claim }: Readonly<{ claim: Claim }>) {
  return (
    <>
      <section className="panel" aria-label="Story">
        <h2>The customer&apos;s story</h2>
        <p>{claim.story}</p>
        <p className="muted">
          {claim.incident_location}, {date(claim.incident_date)}. Submitted{" "}
          {date(claim.submitted_on)}.
        </p>
      </section>
      <section className="panel" aria-label="Items">
        <h2>Items claimed</h2>
        <table>
          <tbody>
            {claim.items.map((item) => (
              <tr key={item.description}>
                <td>{item.description}</td>
                <td className="muted">{words(item.category)}</td>
                <td className="mono amount">{money(item.amount)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <th scope="row" colSpan={2}>
                Total claimed
              </th>
              <td className="mono amount">{money(claim.amount_claimed)}</td>
            </tr>
          </tfoot>
        </table>
      </section>
      <section className="panel" aria-label="Documents">
        <h2>Documents</h2>
        {claim.documents.map((document) => (
          <article key={document.name} className="document">
            <h3>
              {document.name}{" "}
              <span className="muted">{words(document.type)}</span>
            </h3>
            <p>{document.content}</p>
          </article>
        ))}
      </section>
    </>
  );
}

export function PolicyPanel({ policy }: Readonly<{ policy: Policy }>) {
  return (
    <section className="panel" aria-label="Policy">
      <h2>
        Policy <span className="mono">{policy.policy_id}</span>
      </h2>
      <dl>
        <dt>Plan</dt>
        <dd>{words(policy.plan)}</dd>
        <dt>Add-ons</dt>
        <dd>{policy.add_ons.map(words).join(", ") || "None"}</dd>
        <dt>Bought</dt>
        <dd>
          {date(policy.purchased_on)} through {policy.sold_through}
        </dd>
        <dt>Trip</dt>
        <dd>
          {policy.trip.destination}, {date(policy.trip.departs_on)} to{" "}
          {date(policy.trip.returns_on)}
        </dd>
        <dt>Trip cost</dt>
        <dd className="mono">{money(policy.trip.trip_cost)}</dd>
        <dt>Travelers</dt>
        <dd>{policy.travelers.join(", ")}</dd>
      </dl>
    </section>
  );
}

export function HistoryPanel({ history }: Readonly<{ history: ClaimHistory }>) {
  return (
    <section className="panel" aria-label="Claim history">
      <h2>Claim history</h2>
      <p className="muted">Customer since {date(history.customer_since)}</p>
      {history.previous_claims.length === 0 && <p>No earlier claims.</p>}
      <ul className="history">
        {history.previous_claims.map((past) => (
          <li key={past.claim_id}>
            <span className="mono">{past.claim_id}</span>, {date(past.filed_on)}
            , {words(past.claim_type)}: {past.summary}.{" "}
            <span className="muted">
              {words(past.outcome)}, paid {money(past.amount_paid)}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
