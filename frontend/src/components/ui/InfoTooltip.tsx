import React, { useId, useState } from "react";

type Props = {
  c: Record<string, string>;
  text: React.ReactNode;
  label?: string;
};

export function InfoTooltip(props: Props) {
  const { c, text, label = "Más información" } = props;
  const [open, setOpen] = useState(false);
  const tipId = useId();

  return (
    <span
      style={{ position: "relative", display: "inline-flex", alignItems: "center", marginLeft: 6 }}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      <button
        type="button"
        aria-label={label}
        aria-describedby={open ? tipId : undefined}
        onClick={() => setOpen((v) => !v)}
        style={{
          width: 18,
          height: 18,
          borderRadius: "50%",
          border: `1px solid ${c.inputBorder}`,
          background: c.neutralBg,
          color: c.muted,
          fontSize: 11,
          lineHeight: 1,
          cursor: "help",
          padding: 0,
          flexShrink: 0,
        }}
      >
        i
      </button>
      {open ? (
        <span
          id={tipId}
          role="tooltip"
          style={{
            position: "absolute",
            left: "50%",
            bottom: "calc(100% + 8px)",
            transform: "translateX(-50%)",
            zIndex: 50,
            minWidth: 220,
            maxWidth: 320,
            padding: "10px 12px",
            borderRadius: 10,
            border: `1px solid ${c.border}`,
            background: c.surface,
            color: c.text,
            fontSize: 12,
            lineHeight: 1.45,
            boxShadow: c.shadow,
            fontWeight: 400,
            whiteSpace: "normal",
          }}
        >
          {text}
        </span>
      ) : null}
    </span>
  );
}
