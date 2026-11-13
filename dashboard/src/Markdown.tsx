import { blocks, spans, type Block } from "./prose";

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

export function Markdown({ text }: Readonly<{ text: string }>) {
  return blocks(text).map((block, index) => (
    <Section key={`${String(index)}-${block.kind}`} block={block} />
  ));
}
