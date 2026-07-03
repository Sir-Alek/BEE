import React, { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { LoadingStatusRow } from "./LoadingStatusRow";
import { EliaButton, EliaModalOverlay, EliaModalPanel } from "./ui";

type Props = {
  c: Record<string, string>;
  title: string;
  subtitle?: React.ReactNode;
  content: string;
  loading?: boolean;
  error?: string | null;
  onClose: () => void;
  testId?: string;
};

export function MarkdownGuideModal(props: Props) {
  const { c, title, subtitle, content, loading, error, onClose, testId = "elia-markdown-guide-modal" } = props;
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const t = window.setTimeout(() => {
      panelRef.current?.focus({ preventScroll: true });
    }, 0);
    return () => {
      document.body.style.overflow = prevOverflow;
      window.clearTimeout(t);
    };
  }, []);

  const modal = (
    <EliaModalOverlay testId={testId} ariaLabel={title} onClose={onClose} zIndex={10050}>
      <EliaModalPanel
        ref={panelRef}
        wide
        className="elia-modal-panel--guide"
        onClick={(e) => e.stopPropagation()}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 12,
            padding: "16px 20px",
            borderBottom: `1px solid ${c.border}`,
          }}
        >
          <div>
            <div style={{ fontWeight: 800, fontSize: 16, color: c.text }}>{title}</div>
            {subtitle ? (
              <div style={{ fontSize: 12, color: c.muted, marginTop: 4 }}>{subtitle}</div>
            ) : null}
          </div>
          <EliaButton variant="ghost" size="sm" onClick={onClose}>
            Cerrar
          </EliaButton>
        </div>
        <div className="elia-modal-body" style={{ flex: 1, overflow: "auto", padding: "16px 20px 20px" }}>
          {loading ? (
            <LoadingStatusRow c={c} text="Cargando guía…" loading testId={`${testId}-loading`} />
          ) : error ? (
            <div style={{ fontSize: 13, color: "#c0392b" }}>{error}</div>
          ) : (
            <pre
              style={{
                margin: 0,
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
                fontSize: 13,
                lineHeight: 1.55,
                fontFamily: '"Segoe UI", system-ui, sans-serif',
                color: c.text,
              }}
            >
              {content}
            </pre>
          )}
        </div>
      </EliaModalPanel>
    </EliaModalOverlay>
  );

  return createPortal(modal, document.body);
}
