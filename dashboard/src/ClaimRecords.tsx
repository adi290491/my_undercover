import type { Claim } from "./api";
import { label, money } from "./format";

export function ClaimRecords({ claim }: Readonly<{ claim: Claim }>) {
  return (
    <>
      <section className="panel" aria-labelledby="story">
        <h2 id="story">The customer's story</h2>
        <p className="summary">{claim.summary}</p>
        <p className="story">{claim.story}</p>
      </section>
      <section className="panel" aria-labelledby="items">
        <h2 id="items">Items claimed</h2>
        <table className="items">
          <thead>
            <tr>
              <th scope="col">Item</th>
              <th scope="col">Category</th>
              <th scope="col" className="amount">
                Amount
              </th>
            </tr>
          </thead>
          <tbody>
            {claim.items.map((item) => (
              <tr key={item.description}>
                <td>{item.description}</td>
                <td>{label(item.category)}</td>
                <td className="amount num">{money(item.amount)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <th scope="row" colSpan={2}>
                Total claimed
              </th>
              <td className="amount num">{money(claim.amount_claimed)}</td>
            </tr>
          </tfoot>
        </table>
      </section>
      <section className="panel" aria-labelledby="documents">
        <h2 id="documents">Documents</h2>
        <ul className="documents">
          {claim.documents.map((document) => (
            <li key={document.name}>
              <h3>{document.name}</h3>
              <p className="document-type">{label(document.type)}</p>
              <p>{document.content}</p>
            </li>
          ))}
        </ul>
      </section>
    </>
  );
}
