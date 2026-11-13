import type { Claim, Decision } from "./api";
import { money, outcomeLabel, time } from "./format";
import { Markdown } from "./Markdown";

function Paid({ claim }: Readonly<{ claim: Claim }>) {
  if (claim.payment) {
    return (
      <>
        <span className="num">{money(claim.payment.amount)}</span>,{" "}
        {time(claim.payment.paid_at)}
      </>
    );
  }
  if (claim.status === "awaiting_signoff")
    return <>Waiting for a handler's sign-off</>;
  return <>Not yet</>;
}

export function DecisionPanel({
  claim,
  decision,
}: Readonly<{ claim: Claim; decision: Decision }>) {
  const section = decision.policy_section;
  return (
    <section className="panel" aria-labelledby="decision">
      <h2 id="decision">The agent's decision</h2>
      <p className="outcome">
        <span>{outcomeLabel(decision.decision)}</span>
        {decision.decision === "approve" && (
          <span className="num">{money(decision.payout)}</span>
        )}
      </p>
      {claim.status === "awaiting_signoff" && (
        <p className="alert">
          <span className="alert-label">Needs sign-off</span> This payout of{" "}
          {money(decision.payout)} is over the approval limit. It is paid once a
          handler signs it off.
        </p>
      )}
      <p className="reason">{decision.reason}</p>
      <div className="section-quote">
        <h3>
          Section {section.number}, {section.title}
        </h3>
        <Markdown text={section.text} />
      </div>
      <dl className="details">
        <dt>Decided</dt>
        <dd>{time(decision.decided_at)}</dd>
        {decision.decision === "approve" && (
          <>
            <dt>Paid</dt>
            <dd>
              <Paid claim={claim} />
            </dd>
          </>
        )}
        {claim.sign_off && (
          <>
            <dt>Signed off</dt>
            <dd>
              {claim.sign_off.handler_name}, {time(claim.sign_off.signed_at)}
            </dd>
          </>
        )}
      </dl>
    </section>
  );
}
