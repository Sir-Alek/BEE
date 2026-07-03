import React from "react";
import { EliaLinkButton } from "./ui";

type Props = {
  email: string;
  jobId?: string;
  c: Record<string, string>;
};

export function SupportContactLink(props: Props) {
  const { email, jobId } = props;
  const trimmed = email.trim();
  if (!trimmed) return null;

  const subject = jobId
    ? `ELIA — Reporte de error (job ${jobId.slice(0, 8)})`
    : "ELIA — Reporte de error";
  const body =
    "Describe el problema y adjunta el reporte de error descargado desde ELIA.\n\n" +
    (jobId ? `Job ID: ${jobId}\n` : "");

  const href = `mailto:${trimmed}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;

  return (
    <EliaLinkButton data-testid="elia-support-contact-job" href={href} variant="ghost">
      Reportar o contactar a soporte →
    </EliaLinkButton>
  );
}
