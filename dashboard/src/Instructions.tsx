import { useApi } from "./api";

export function Instructions() {
  const { data, error } = useApi<{ instructions: string }>("/api/instructions");
  if (error) return <p role="alert">{error}</p>;
  if (!data) return <p>Loading the instructions</p>;

  return (
    <>
      <h1>Agent instructions</h1>
      <p className="muted">
        What the UnderCover Agent is told before each claim. Read only.
      </p>
      <pre className="panel instructions">{data.instructions}</pre>
    </>
  );
}
