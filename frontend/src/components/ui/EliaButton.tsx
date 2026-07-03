import React, { forwardRef } from "react";

type Variant = "ghost" | "primary" | "danger" | "warn" | "tab";
type Size = "sm" | "md" | "icon";

function cx(...parts: Array<string | false | undefined | null>) {
  return parts.filter(Boolean).join(" ");
}

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: Size;
  active?: boolean;
};

export function EliaButton({
  variant = "ghost",
  size = "md",
  active = false,
  className,
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cx(
        "elia-btn",
        variant === "ghost" && "elia-btn--ghost",
        variant === "primary" && "elia-btn--primary",
        variant === "danger" && "elia-btn--danger",
        variant === "warn" && "elia-btn--warn",
        variant === "tab" && "elia-btn--tab",
        active && variant === "tab" && "is-active",
        size === "sm" && "elia-btn--sm",
        size === "icon" && "elia-btn--icon",
        className,
      )}
      {...props}
    />
  );
}

type LinkProps = React.AnchorHTMLAttributes<HTMLAnchorElement> & {
  variant?: "primary" | "ghost";
  size?: Size;
};

export function EliaLinkButton({ variant = "primary", size = "md", className, ...props }: LinkProps) {
  return (
    <a
      className={cx(
        "elia-btn",
        variant === "primary" && "elia-btn--primary",
        variant === "ghost" && "elia-btn--ghost",
        size === "sm" && "elia-btn--sm",
        className,
      )}
      {...props}
    />
  );
}

type ModalProps = {
  testId?: string;
  ariaLabel?: string;
  onClose: () => void;
  children: React.ReactNode;
  zIndex?: number;
  alignTop?: boolean;
};

export function EliaModalOverlay({ testId, ariaLabel, onClose, children, zIndex = 1100, alignTop }: ModalProps) {
  return (
    <div
      data-testid={testId}
      role="dialog"
      aria-modal="true"
      aria-label={ariaLabel}
      className={cx("elia-modal-overlay", alignTop && "elia-modal-overlay--top")}
      style={{ zIndex }}
      onClick={onClose}
    >
      {children}
    </div>
  );
}

type PanelProps = {
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
  testId?: string;
  onClick?: React.MouseEventHandler<HTMLDivElement>;
  wide?: boolean;
};

export const EliaModalPanel = forwardRef<HTMLDivElement, PanelProps>(function EliaModalPanel(
  { children, className, style, testId, onClick, wide },
  ref,
) {
  return (
    <div
      ref={ref}
      data-testid={testId}
      tabIndex={-1}
      className={cx("elia-modal-panel", wide && "elia-modal-panel--wide", className)}
      style={style}
      onClick={onClick}
    >
      {children}
    </div>
  );
});

export function EliaModalActions({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cx("elia-modal-actions", className)}>{children}</div>;
}

export function EliaModalHeader(props: { title: string; subtitle?: string; onClose?: () => void }) {
  const { title, subtitle, onClose } = props;
  return (
    <div className="elia-modal-header">
      <div style={{ flex: 1, minWidth: 0 }}>
        <div className="elia-modal-header__title">{title}</div>
        {subtitle ? <div className="elia-modal-header__subtitle">{subtitle}</div> : null}
      </div>
      {onClose ? (
        <EliaButton variant="ghost" size="sm" onClick={onClose} aria-label="Cerrar">
          Cerrar
        </EliaButton>
      ) : null}
    </div>
  );
}
