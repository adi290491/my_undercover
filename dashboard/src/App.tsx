import { ClaimPage } from "./ClaimPage";
import { Instructions } from "./Instructions";
import { Queue } from "./Queue";
import { useRoute } from "./router";

export function App() {
  const route = useRoute();
  return (
    <>
      <header className="masthead">
        <a className="wordmark" href="#/">
          UnderCover <span className="tagline">Claims desk</span>
        </a>
        <nav aria-label="Main">
          <a
            href="#/"
            aria-current={route.page === "queue" ? "page" : undefined}
          >
            Queue
          </a>
          <a
            href="#/instructions"
            aria-current={route.page === "instructions" ? "page" : undefined}
          >
            Agent instructions
          </a>
        </nav>
      </header>
      <main>
        {route.page === "queue" && <Queue />}
        {route.page === "claim" && (
          <ClaimPage key={route.claimId} claimId={route.claimId} />
        )}
        {route.page === "instructions" && <Instructions />}
      </main>
    </>
  );
}
