import React from "react";
import { EliaButton, EliaModalActions, EliaModalOverlay, EliaModalPanel } from "./ui";

type Props = {
  c: Record<string, string>;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  destructive?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
};

export function ConfirmModal(props: Props) {
  const {
    title,
    message,
    confirmLabel = "Confirmar",
    cancelLabel = "Cancelar",
    destructive = false,
    onConfirm,
    onCancel,
  } = props;

  return (
    <EliaModalOverlay testId="elia-confirm-modal" ariaLabel={title} onClose={onCancel} zIndex={1100}>
      <EliaModalPanel onClick={(e) => e.stopPropagation()}>
        <div className="elia-modal-header__title" style={{ marginBottom: 10 }}>
          {title}
        </div>
        <div className="elia-modal-body-text">{message}</div>
        <EliaModalActions>
          <EliaButton variant="ghost" size="sm" onClick={onCancel}>
            {cancelLabel}
          </EliaButton>
          <EliaButton variant={destructive ? "danger" : "primary"} size="sm" onClick={onConfirm}>
            {confirmLabel}
          </EliaButton>
        </EliaModalActions>
      </EliaModalPanel>
    </EliaModalOverlay>
  );
}
