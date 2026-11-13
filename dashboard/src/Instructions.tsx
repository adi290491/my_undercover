import type { Text } from "./api";
import { blocks, spans, type Block } from "./markdown";
import { useApi } from "./useApi";

function Inline({ text }: Readonly<{ text: string }>) {
  return spans(text).map((span, index) => {
    const key = `${String(index)}-${span.text}`;
    if (span.kind === "strong") return <strong key={key}>{span.text}</strong>;
    if (span.kind === "code") return <code key={key}>{span.text}</code>;
    return <span key={key}>{span.text}</span>;
  });
}

function Section({ block }: Readonly<{ block: Block }>) {
  if (block.kind === "heading") {
    const Heading = block.level === 1 ? "h2" : "h3";
    return (
      <Heading>
        <Inline text={block.text} />
      </Heading>
    );
  }
  if (block.kind === "p") {
    return (
      <p>
        <Inline text={block.text} />
      </p>
    );
  }
  const List = block.kind;
  return (
    <List>
      {block.items.map((item) => (
        <li key={item}>
          <Inline text={item} />
        </li>
      ))}
    </List>
  );
}

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
          blocks(data.text).map((block, index) => (
            <Section key={`${String(index)}-${block.kind}`} block={block} />
          ))
        ) : (
          <p className="notice">{error ?? "Loading the instructions"}</p>
        )}
      </article>
    </>
  );
}
