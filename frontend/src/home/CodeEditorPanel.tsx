import React, { useMemo } from "react";
import CodeMirror from "@uiw/react-codemirror";
import { autocompletion } from "@codemirror/autocomplete";
import { python } from "@codemirror/lang-python";
import { StreamLanguage } from "@codemirror/language";
import { gherkin } from "@codemirror/legacy-modes/mode/gherkin";
import { oneDark } from "@codemirror/theme-one-dark";
import { EditorView, hoverTooltip } from "@codemirror/view";
import { createEliaCompletionSource, ProjectAutocompleteContext } from "./editorAutocomplete";
import { catalogByName } from "./pageFunctionsCatalog";

type Props = {
  value: string;
  filePath: string;
  dark: boolean;
  readOnly?: boolean;
  minHeight?: string;
  completionContext?: ProjectAutocompleteContext;
  onChange: (value: string) => void;
  onSave?: () => void;
  toolbar?: React.ReactNode;
};

function languageExtension(path: string) {
  const lower = path.toLowerCase();
  if (lower.endsWith(".py")) return python();
  if (lower.endsWith(".feature")) return StreamLanguage.define(gherkin);
  return [];
}

const pageFunctionHover = hoverTooltip((view, pos) => {
  const { from, to } = view.state.doc.lineAt(pos);
  const line = view.state.doc.sliceString(from, to);
  const offset = pos - from;
  const before = line.slice(0, offset);
  const wordMatch = before.match(/([A-Za-z_][A-Za-z0-9_]*)$/);
  if (!wordMatch) return null;
  const name = wordMatch[1];
  const meta = catalogByName(name);
  if (!meta) return null;
  const start = offset - name.length;
  return {
    pos: from + start,
    end: from + offset,
    above: true,
    create() {
      const dom = document.createElement("div");
      dom.style.maxWidth = "420px";
      dom.style.padding = "8px 10px";
      dom.style.fontSize = "12px";
      dom.style.lineHeight = "1.45";
      dom.innerHTML = `<strong>${meta.name}</strong><br/><code style="font-size:11px">${meta.signature}</code><br/><span>${meta.summary}</span>`;
      return { dom };
    },
  };
});

export function CodeEditorPanel(props: Props) {
  const {
    value,
    filePath,
    dark,
    readOnly = false,
    minHeight = "min(52vh, 520px)",
    completionContext,
    onChange,
    onSave,
    toolbar,
  } = props;

  const isPython = filePath.toLowerCase().endsWith(".py");

  const extensions = useMemo(() => {
    const base = [
      languageExtension(filePath),
      EditorView.lineWrapping,
      EditorView.theme({
        "&": { fontSize: "13px" },
        ".cm-scroller": { fontFamily: '"Cascadia Code", "Fira Code", Consolas, monospace' },
        ".cm-gutters": { border: "none" },
      }),
    ];
    if (isPython) {
      base.push(pageFunctionHover);
    }
    if (completionContext && filePath) {
      base.push(
        autocompletion({
          activateOnTyping: true,
          maxRenderedOptions: 24,
          override: [createEliaCompletionSource(completionContext, filePath)],
        }),
      );
    }
    return base;
  }, [filePath, completionContext, isPython]);

  return (
    <div
      data-testid="elia-code-editor"
      style={{
        border: "1px solid var(--elia-editor-border, #e5e7eb)",
        borderRadius: 10,
        overflow: "hidden",
        background: dark ? "#1e1e1e" : "#ffffff",
        display: "flex",
        flexDirection: "column",
        minHeight,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 8,
          padding: "6px 10px",
          borderBottom: "1px solid var(--elia-editor-border, #e5e7eb)",
          background: dark ? "#252526" : "#f3f4f6",
          fontSize: 12,
        }}
      >
        <span style={{ color: dark ? "#d4d4d4" : "#374151", overflow: "hidden", textOverflow: "ellipsis" }}>
          {filePath || "Sin archivo seleccionado"}
        </span>
        <div style={{ display: "flex", gap: 6, alignItems: "center", flexShrink: 0 }}>{toolbar}</div>
      </div>
      <CodeMirror
        value={value}
        height="100%"
        minHeight={minHeight}
        theme={dark ? oneDark : "light"}
        extensions={extensions}
        editable={!readOnly}
        basicSetup={{
          lineNumbers: true,
          foldGutter: true,
          highlightActiveLine: true,
          indentOnInput: true,
          bracketMatching: true,
          autocompletion: false,
        }}
        onChange={onChange}
        onKeyDown={(ev) => {
          if ((ev.ctrlKey || ev.metaKey) && ev.key === "s") {
            ev.preventDefault();
            onSave?.();
          }
        }}
      />
    </div>
  );
}
