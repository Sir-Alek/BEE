import React from "react";

type Props = {
  c: Record<string, string>;
  title?: string;
  children: React.ReactNode;
  style?: React.CSSProperties;
};

export function SecondaryToolbar(props: Props) {
  const { title, children, style } = props;
  return (
    <div className="elia-toolbar" style={style}>
      {title ? <div className="elia-toolbar__title">{title}</div> : null}
      <div className="elia-toolbar__inner">{children}</div>
    </div>
  );
}

export function OutlinedButton(props: {
  c: Record<string, string>;
  children: React.ReactNode;
  disabled?: boolean;
  onClick?: () => void;
  testId?: string;
}) {
  const { children, disabled, onClick, testId } = props;
  return (
    <button
      type="button"
      data-testid={testId}
      disabled={disabled}
      onClick={onClick}
      className="elia-btn elia-btn--ghost elia-btn--sm"
    >
      {children}
    </button>
  );
}
