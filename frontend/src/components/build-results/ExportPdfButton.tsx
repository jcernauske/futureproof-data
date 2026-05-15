/**
 * ExportPdfButton — single-build PDF export trigger on /my-build.
 *
 * Click flow:
 *   1. POST /build/{build_id}/pdf.
 *   2. Receive application/pdf bytes as a Blob.
 *   3. Trigger a browser download via URL.createObjectURL.
 *
 * On API error: show inline error toast ("Couldn't generate the PDF.
 * Try again."). No retry counter; the static-fallback path inside the
 * backend already handles Gemma failures, so a frontend-visible error
 * means a real transport problem worth surfacing.
 *
 * Spec: docs/specs/feature-pdf-report-exports.md §3 / §4.
 */

import { useState } from "react";

import { exportBuildPdf, downloadBlobAs } from "@/api/pdf";
import { useT } from "@/i18n/useT";
import { useProfileStore } from "@/store/profileStore";

interface ExportPdfButtonProps {
  buildId: string;
  schoolName: string;
  programName: string;
}

export function ExportPdfButton({
  buildId,
  schoolName,
  programName,
}: ExportPdfButtonProps) {
  const t = useT();
  const locale = useProfileStore((s) => s.locale);
  const [state, setState] = useState<"idle" | "loading" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleClick = async () => {
    if (state === "loading") return;
    setState("loading");
    setErrorMsg(null);
    try {
      const blob = await exportBuildPdf(buildId, { locale });
      const safe = (s: string) =>
        s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
      const today = new Date().toISOString().slice(0, 10).replace(/-/g, "");
      const filename = `futureproof-${safe(schoolName).slice(0, 32)}-${safe(programName).slice(0, 32)}-${today}.pdf`;
      downloadBlobAs(blob, filename);
      setState("idle");
    } catch (err) {
      console.warn("export pdf failed:", err);
      const detail = err instanceof Error ? err.message : "";
      setErrorMsg(detail || t("build.exportPdfError"));
      setState("error");
      // Auto-clear the error after 8s so the next click can be tried clean.
      setTimeout(() => {
        setState("idle");
        setErrorMsg(null);
      }, 8000);
    }
  };

  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        data-testid="btn-export-pdf-build"
        aria-label={t("build.exportPdfAriaLabel")}
        onClick={handleClick}
        disabled={state === "loading"}
        className="font-body text-accent-info hover:underline hover:brightness-125 transition-colors duration-150 bg-transparent border-none cursor-pointer disabled:opacity-60 disabled:cursor-wait"
        style={{ fontSize: 14 }}
      >
        {state === "loading"
          ? t("build.exportingPdf")
          : t("build.exportPdf")}
      </button>
      {state === "error" && (
        <span
          data-testid="alert-pdf-export-error"
          role="alert"
          className="font-body text-accent-warn"
          style={{ fontSize: 13, maxWidth: 480 }}
        >
          {errorMsg ?? t("build.exportPdfError")}
        </span>
      )}
    </div>
  );
}
