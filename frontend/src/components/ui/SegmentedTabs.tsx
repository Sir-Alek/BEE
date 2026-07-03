import React from "react";
import { EliaButton } from "./EliaButton";

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
          <EliaButton
            key={id}
            variant="tab"
            size="sm"
            active={active}
            data-testid={testId}
            onClick={() => onChange(id)}
          >
            {label}
          </EliaButton>
        );
      })}
    </div>
  );
}
