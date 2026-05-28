import React from "react";

export type SegmentedTabOption<T extends string> = {
  id: T;
  label: string;
  testId?: string;
};

type Props<T extends string> = {
  c: Record<string, string>;
  value: T;
  options: SegmentedTabOption<T>[];
  onChange: (id: T) => void;
  style?: React.CSSProperties;
};

export function SegmentedTabs<T extends string>(props: Props<T>) {
  const { c, value, options, onChange, style } = props;
  return (
    <div style={{ display: "flex", gap: 4, flexWrap: "wrap", ...style }}>
      {options.map(({ id, label, testId }) => {
        const active = value === id;
        return (
          <button
            key={id}
            type="button"
            data-testid={testId}
            onClick={() => onChange(id)}
            style={{
              padding: "7px 14px",
              borderRadius: 8,
              border: active ? `2px solid ${c.primary}` : `1px solid ${c.btnGhostBorder}`,
              background: active ? c.primary : c.btnGhostBg,
              color: active ? c.primaryFg : c.text,
              fontWeight: active ? 700 : 400,
              cursor: "pointer",
              fontSize: 13,
            }}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}
