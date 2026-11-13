import type { Text } from "./api";
import { Markdown } from "./Markdown";
import { useApi } from "./useApi";

export function Instructions() {
  const { data, error } = useApi<Text>("/api/instructions", 0);
  return (
    <>
      <h1>The agent's instructions</h1>
      <p className="notice">
        Read only. The agent reads these at the start of every claim.
      </p>
      <article className="panel prose">
        {data ? (
          <Markdown text={data.text} />
        ) : (
          <p className="notice">{error ?? "Loading the instructions"}</p>
        )}
      </article>
    </>
  );
}
