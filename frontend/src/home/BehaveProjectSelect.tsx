import React, { useEffect } from "react";

type Props = {
  c: Record<string, string>;
  value: string;
  onChange: (project: string) => void;
  projects: string[];
  platform: string;
  placeholder?: string;
};

export function BehaveProjectSelect(props: Props) {
  const {
    c,
    value,
    onChange,
    projects,
    platform,
    placeholder = "Selecciona proyecto Behave",
  } = props;

  useEffect(() => {
    if (!value.trim() && projects.length > 0) {
      onChange(projects[0]);
    }
  }, [projects, value, onChange]);

  const options = [...new Set([...(value.trim() ? [value.trim()] : []), ...projects])];

  return (
    <select
      data-testid={`elia-behave-project-select-${platform}`}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      style={{
        flex: "1 1 220px",
        minWidth: 180,
        padding: "8px 10px",
        borderRadius: 8,
        border: `1px solid ${c.inputBorder}`,
        background: c.inputBg,
        color: c.text,
        fontSize: 14,
      }}
    >
      <option value="">
        {projects.length === 0 ? `Sin proyectos en behave/${platform}` : placeholder}
      </option>
      {options.map((p) => (
        <option key={p} value={p}>
          {p}
        </option>
      ))}
    </select>
  );
}
