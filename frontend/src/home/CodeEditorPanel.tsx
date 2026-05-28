import React, { useMemo } from "react";
import CodeMirror from "@uiw/react-codemirror";
import { autocompletion } from "@codemirror/autocomplete";
import { python } from "@codemirror/lang-python";
import { StreamLanguage } from "@codemirror/language";
import { gherkin } from "@codemirror/legacy-modes/mode/gherkin";
import { oneDark } from "@codemirror/theme-one-dark";
import { EditorView } from "@codemirror/view";
import { createEliaCompletionSource, ProjectAutocompleteContext } from "./editorAutocomplete";

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
  }, [filePath, completionContext]);

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
