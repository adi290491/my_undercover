export type Block =
  | { kind: "heading"; level: number; text: string }
  | { kind: "p"; text: string }
  | { kind: "ul" | "ol"; items: string[] };

function listItem(line: string): { kind: "ul" | "ol"; text: string } | null {
  const bullet = /^- (.*)$/.exec(line);
  if (bullet?.[1] !== undefined) return { kind: "ul", text: bullet[1] };
  const numbered = /^\d+\. (.*)$/.exec(line);
  if (numbered?.[1] !== undefined) return { kind: "ol", text: numbered[1] };
  return null;
}

export function blocks(source: string): Block[] {
  const result: Block[] = [];
  let open: Block | undefined;
  for (const line of source.split("\n").map((l) => l.trim())) {
    const heading = /^(#{1,3}) (.*)$/.exec(line);
    const item = listItem(line);
    if (!line || heading) {
      open = undefined;
      if (heading?.[1] && heading[2]) {
        result.push({
          kind: "heading",
          level: heading[1].length,
          text: heading[2],
        });
      }
    } else if (item) {
      if (open?.kind === item.kind) open.items.push(item.text);
      else {
        open = { kind: item.kind, items: [item.text] };
        result.push(open);
      }
    } else if (open?.kind === "p") {
      open.text += ` ${line}`;
    } else {
      open = { kind: "p", text: line };
      result.push(open);
    }
  }
  return result;
}

export interface Span {
  kind: "text" | "strong" | "code";
  text: string;
}

export function spans(text: string): Span[] {
  return text
    .split(/(\*\*[^*]+\*\*|`[^`]+`)/)
    .filter(Boolean)
    .map((part) => {
      if (part.startsWith("**"))
        return { kind: "strong", text: part.slice(2, -2) };
      if (part.startsWith("`"))
        return { kind: "code", text: part.slice(1, -1) };
      return { kind: "text", text: part };
    });
}
