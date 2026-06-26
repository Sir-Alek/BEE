import React, { useMemo } from "react";

type Props = {
  text: string;
  maxHeight?: number;
};

function tryParseJson(text: string): unknown | null {
  const trimmed = text.trim();
  if (!trimmed.startsWith("{") && !trimmed.startsWith("[")) return null;
  try {
    return JSON.parse(trimmed);
  } catch {
    return null;
  }
}

function colorizeJson(json: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  const tokenRe =
    /("(?:\\.|[^"\\])*")(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?/g;
  let last = 0;
  let match: RegExpExecArray | null;
  let key = 0;
  while ((match = tokenRe.exec(json)) !== null) {
    if (match.index > last) {
      parts.push(json.slice(last, match.index));
    }
    const [raw, quoted, colon] = match;
    let color = "#0969da";
    if (quoted && colon) {
      color = "#8250df";
    } else if (quoted) {
      color = "#0a3069";
    } else if (raw === "true" || raw === "false") {
      color = "#0550ae";
    } else if (raw === "null") {
      color = "#6e7781";
    }
    parts.push(
      <span key={key++} style={{ color }}>
        {raw}
      </span>,
    );
    last = match.index + raw.length;
  }
  if (last < json.length) {
    parts.push(json.slice(last));
  }
  return parts;
}

export function JsonResponseView(props: Props) {
  const { text, maxHeight = 220 } = props;

  const display = useMemo(() => {
    const parsed = tryParseJson(text);
    if (parsed == null) return null;
    return JSON.stringify(parsed, null, 2);
  }, [text]);

  if (!display) {
    return (
      <pre
        style={{
          margin: 0,
          maxHeight,
          overflow: "auto",
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
          fontSize: 12,
          fontFamily: "monospace",
        }}
      >
        {text.slice(0, 8000) || "(sin cuerpo)"}
      </pre>
    );
  }

  return (
    <pre
      data-testid="elia-json-response-view"
      style={{
        margin: 0,
        maxHeight,
        overflow: "auto",
        whiteSpace: "pre-wrap",
        wordBreak: "break-word",
        fontSize: 12,
        fontFamily: "monospace",
        lineHeight: 1.45,
      }}
    >
      {colorizeJson(display)}
    </pre>
  );
}

export function isLikelyJsonBody(text: string): boolean {
  const trimmed = text.trim();
  return trimmed.startsWith("{") || trimmed.startsWith("[");
}
