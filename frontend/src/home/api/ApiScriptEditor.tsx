import React, { useMemo } from "react";
import CodeMirror from "@uiw/react-codemirror";
import { StreamLanguage } from "@codemirror/language";
import { javascript } from "@codemirror/legacy-modes/mode/javascript";
import { oneDark } from "@codemirror/theme-one-dark";
import { EditorView } from "@codemirror/view";

type Props = {
  value: string;
  onChange: (value: string) => void;
  dark?: boolean;
  readOnly?: boolean;
  minHeight?: string;
  placeholder?: string;
};

export function ApiScriptEditor(props: Props) {
  const { value, onChange, dark = false, readOnly = false, minHeight = "180px", placeholder } = props;

  const extensions = useMemo(
    () => [
      StreamLanguage.define(javascript),
      EditorView.lineWrapping,
      EditorView.theme({
        "&": { fontSize: "13px" },
        ".cm-scroller": { fontFamily: '"Cascadia Code", "Fira Code", Consolas, monospace' },
        ".cm-gutters": { border: "none" },
      }),
    ],
    [],
  );

  return (
    <div
      data-testid="elia-api-script-editor"
      style={{
        border: "1px solid var(--elia-editor-border, #e5e7eb)",
        borderRadius: 10,
        overflow: "hidden",
        background: dark ? "#1e1e1e" : "#ffffff",
        minHeight,
      }}
    >
      <CodeMirror
        value={value}
        height="100%"
        minHeight={minHeight}
        theme={dark ? oneDark : "light"}
        extensions={extensions}
        editable={!readOnly}
        placeholder={placeholder}
        basicSetup={{
          lineNumbers: true,
          foldGutter: true,
          highlightActiveLine: true,
          indentOnInput: true,
          bracketMatching: true,
        }}
        onChange={onChange}
      />
    </div>
  );
}
