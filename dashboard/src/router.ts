import { useSyncExternalStore } from "react";

export type Route =
  | { page: "queue" }
  | { page: "claim"; claimId: string }
  | { page: "instructions" }
  | { page: "missing" };

export function parse(hash: string): Route {
  const path = hash.replace(/^#/, "") || "/";
  if (path === "/") return { page: "queue" };
  if (path === "/instructions") return { page: "instructions" };
  const claim = /^\/claims\/([\w-]+)$/.exec(path);
  if (claim?.[1]) return { page: "claim", claimId: claim[1] };
  return { page: "missing" };
}

function subscribe(onChange: () => void): () => void {
  window.addEventListener("hashchange", onChange);
  return () => {
    window.removeEventListener("hashchange", onChange);
  };
}

export function useRoute(): Route {
  return parse(useSyncExternalStore(subscribe, () => window.location.hash));
}

export const links = {
  queue: "#/",
  claim: (claimId: string) => `#/claims/${claimId}`,
  instructions: "#/instructions",
};
