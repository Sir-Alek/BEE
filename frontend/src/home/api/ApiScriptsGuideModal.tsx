import React from "react";
import { MarkdownGuideModal } from "../../components/MarkdownGuideModal";

type Props = {
  c: Record<string, string>;
  title: string;
  content: string;
  loading?: boolean;
  error?: string | null;
  onClose: () => void;
};

export function ApiScriptsGuideModal(props: Props) {
  const { c, title, content, loading, error, onClose } = props;

  return (
    <MarkdownGuideModal
      c={c}
      title={title}
      subtitle={
        <>
          Referencia de <code style={{ fontSize: 11 }}>pm.*</code> en pre-request y post-request
        </>
      }
      content={content}
      loading={loading}
      error={error}
      onClose={onClose}
      testId="elia-api-scripts-guide-modal"
    />
  );
}
