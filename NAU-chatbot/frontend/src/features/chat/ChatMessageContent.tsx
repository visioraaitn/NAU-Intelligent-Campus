import type { ReactNode } from "react";

type ContentBlock =
  | { type: "heading"; content: string }
  | { type: "paragraph"; lines: string[] }
  | { type: "list"; ordered: boolean; items: string[] };

const urlPattern = /(https?:\/\/[^\s<]+)/g;
const trailingUrlPunctuation = /[),.;!?]+$/;

function linkedText(value: string): ReactNode[] {
  return value.split(urlPattern).flatMap((part, index) => {
    if (!part.match(/^https?:\/\//)) return part;
    const trailing = part.match(trailingUrlPunctuation)?.[0] ?? "";
    const href = trailing ? part.slice(0, -trailing.length) : part;
    return [
      <a href={href} key={`${href}-${index}`} target="_blank" rel="noreferrer">
        {href}
      </a>,
      trailing,
    ];
  });
}

function parseContent(content: string): ContentBlock[] {
  const blocks: ContentBlock[] = [];
  let paragraph: string[] = [];
  let list: Extract<ContentBlock, { type: "list" }> | null = null;

  const flushParagraph = () => {
    if (paragraph.length) blocks.push({ type: "paragraph", lines: paragraph });
    paragraph = [];
  };
  const flushList = () => {
    if (list) blocks.push(list);
    list = null;
  };

  content.split(/\r?\n/).forEach((rawLine) => {
    const line = rawLine.trim();
    if (!line) {
      flushParagraph();
      flushList();
      return;
    }

    const heading = line.match(/^#{1,3}\s+(.+)$/);
    if (heading) {
      flushParagraph();
      flushList();
      blocks.push({ type: "heading", content: heading[1] ?? line });
      return;
    }

    const unorderedItem = line.match(/^[-*•]\s+(.+)$/);
    const orderedItem = line.match(/^\d+[.)]\s+(.+)$/);
    const item = unorderedItem?.[1] ?? orderedItem?.[1];
    if (item) {
      flushParagraph();
      const ordered = Boolean(orderedItem);
      if (!list || list.ordered !== ordered) {
        flushList();
        list = { type: "list", ordered, items: [] };
      }
      list.items.push(item);
      return;
    }

    flushList();
    paragraph.push(line);
  });

  flushParagraph();
  flushList();
  return blocks;
}

export function ChatMessageContent({ content }: { content: string }) {
  return (
    <div className="message-text">
      {parseContent(content).map((block, index) => {
        if (block.type === "heading") {
          return <h3 key={`heading-${index}`}>{linkedText(block.content)}</h3>;
        }
        if (block.type === "list") {
          const List = block.ordered ? "ol" : "ul";
          return (
            <List key={`list-${index}`}>
              {block.items.map((item, itemIndex) => (
                <li key={`${item}-${itemIndex}`}>{linkedText(item)}</li>
              ))}
            </List>
          );
        }
        return (
          <p key={`paragraph-${index}`}>
            {block.lines.map((line, lineIndex) => (
              <span key={`${line}-${lineIndex}`}>
                {linkedText(line)}
                {lineIndex < block.lines.length - 1 && <br />}
              </span>
            ))}
          </p>
        );
      })}
    </div>
  );
}
