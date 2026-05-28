import React from "react";
import { InfoTooltip } from "./InfoTooltip";

type Props = {
  c: Record<string, string>;
  children: React.ReactNode;
  tooltip?: React.ReactNode;
  htmlFor?: string;
  style?: React.CSSProperties;
};

export function FieldLabel(props: Props) {
  const { c, children, tooltip, htmlFor, style } = props;
  return (
    <label
      htmlFor={htmlFor}
      style={{
        display: "flex",
        alignItems: "center",
        fontSize: 12,
        fontWeight: 600,
        color: c.text,
        marginBottom: 6,
        ...style,
      }}
    >
      <span>{children}</span>
      {tooltip ? <InfoTooltip c={c} text={tooltip} /> : null}
    </label>
  );
}
