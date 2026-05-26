import React, { useEffect, useRef, useState } from "react";
import { getTestRun } from "../api";

type Props = {
  c: Record<string, string>;
  runId: string;
  onClose: () => void;
};

export function RunConsolePanel(props: Props) {
  const { c, runId, onClose } = props;
  const [lines, setLines] = useState<string[]>([]);
  const [state, setState] = useState("running");
  const [returnCode, setReturnCode] = useState<number | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let closed = false;
    const es = new EventSource(`/api/runs/${encodeURIComponent(runId)}/stream`);
    es.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data) as { line?: string; done?: boolean; return_code?: number; state?: string };
        if (data.line) {
          setLines((prev) => [...prev, data.line as string]);
        }
        if (data.done) {
          setState(data.state ?? "done");
          setReturnCode(data.return_code ?? null);
          es.close();
        }
      } catch {
        // ignore malformed events
      }
    };
    es.onerror = () => {
      if (!closed) {
        void getTestRun(runId).then((r) => {
          setState(r.state);
          setReturnCode(r.return_code);
          setLines(r.lines ?? []);
        });
        es.close();
      }
    };
    return () => {
      closed = true;
      es.close();
    };
  }, [runId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines.length]);

  const passed = state === "done" && returnCode === 0;

  return (
    <div
      data-testid="elia-run-console"
      style={{
        border: `1px solid ${c.border}`,
        borderRadius: 12,
        padding: 14,
        background: c.inputBg,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <div style={{ fontWeight: 700 }}>
          Consola de ejecución — {passed ? "✓ Aprobado" : state === "running" ? "En curso…" : "✗ Fallido"}
        </div>
        <button type="button" onClick={onClose} style={{ border: "none", background: "transparent", color: c.primary, cursor: "pointer" }}>
          Cerrar
        </button>
      </div>
      <pre
        style={{
          margin: 0,
          maxHeight: "min(40vh, 320px)",
          overflow: "auto",
          fontSize: 12,
          lineHeight: 1.45,
          color: c.text,
          whiteSpace: "pre-wrap",
        }}
      >
        {lines.join("\n") || "Esperando salida…"}
      </pre>
      <div ref={bottomRef} />
    </div>
  );
}
