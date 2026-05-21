export type LicenseDisplayBlock =
  | { kind: "title"; text: string }
  | { kind: "heading"; text: string }
  | { kind: "paragraph"; text: string }
  | { kind: "list"; items: string[] };

/** Convierte Licence.txt (saltos fijos) en bloques legibles para la UI. */
export function parseLicenseDisplayBlocks(raw: string): LicenseDisplayBlock[] {
  const normalized = (raw || "").replace(/\r\n/g, "\n").trim();
  if (!normalized) return [];

  const blocks: LicenseDisplayBlock[] = [];
  let prose: string[] = [];
  let listItems: string[] = [];
  let isFirstBlock = true;

  const flushProse = () => {
    if (!prose.length) return;
    const text = prose.join(" ").replace(/\s+/g, " ").trim();
    if (!text) {
      prose = [];
      return;
    }
    if (isFirstBlock) {
      blocks.push({ kind: "title", text });
      isFirstBlock = false;
    } else {
      blocks.push({ kind: "paragraph", text });
    }
    prose = [];
  };

  const flushList = () => {
    if (!listItems.length) return;
    blocks.push({ kind: "list", items: [...listItems] });
    listItems = [];
    isFirstBlock = false;
  };

  const lines = normalized.split("\n");
  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i];
    const trimmed = line.trim();

    if (!trimmed) {
      flushProse();
      flushList();
      continue;
    }

    if (trimmed.startsWith("-")) {
      flushProse();
      listItems.push(trimmed.replace(/^-\s*/, ""));
      isFirstBlock = false;
      continue;
    }

    if (listItems.length && /^\s+\S/.test(line)) {
      const last = listItems.pop() ?? "";
      listItems.push(`${last} ${trimmed}`);
      continue;
    }

    if (listItems.length) {
      flushList();
    }

    if (/:$/.test(trimmed) && trimmed.length <= 96 && !trimmed.startsWith("-")) {
      flushProse();
      blocks.push({ kind: "heading", text: trimmed.slice(0, -1) });
      isFirstBlock = false;
      continue;
    }

    prose.push(trimmed);
  }

  flushProse();
  flushList();
  return blocks;
}
