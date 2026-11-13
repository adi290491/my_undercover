import { Queue } from "./Queue";
import { links, useRoute, type Route } from "./router";

function Page({ route }: Readonly<{ route: Route }>) {
  if (route.page === "queue") return <Queue />;
  return (
    <p className="notice">
      There's no page here. <a href={links.queue}>Back to the queue</a>
    </p>
  );
}

export function App() {
  const route = useRoute();
  return (
    <div className="page">
      <header className="masthead">
        <div>
          <a className="brand-name" href={links.queue}>
            UnderCover
          </a>
          <p className="tagline">Travel claims, handled straight through</p>
        </div>
        <nav aria-label="Main">
          <a
            href={links.queue}
            aria-current={route.page === "queue" ? "page" : undefined}
          >
            Queue
          </a>
          <a
            href={links.instructions}
            aria-current={route.page === "instructions" ? "page" : undefined}
          >
            Instructions
          </a>
        </nav>
      </header>
      <main>
        <Page route={route} />
      </main>
    </div>
  );
}
