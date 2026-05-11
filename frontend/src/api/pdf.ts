/**
 * PDF Report Exports — frontend API client.
 *
 * Backend endpoints (backend/app/routers/pdf_export.py):
 *   POST /build/{build_id}/pdf       → application/pdf bytes
 *   POST /builds/compare/pdf         → application/pdf bytes
 *
 * Returns a Blob (NOT JSON). Caller is responsible for triggering the
 * browser download (see ExportPdfButton.tsx for the canonical flow).
 *
 * Spec: docs/specs/feature-pdf-report-exports.md §4.
 */

import { formatErrorDetail } from "@/api/client";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export interface ExportBuildPdfOptions {
  studentName?: string | null;
}

export async function exportBuildPdf(
  buildId: string,
  opts: ExportBuildPdfOptions = {},
): Promise<Blob> {
  const res = await fetch(`${API_BASE}/build/${buildId}/pdf`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      student_name: opts.studentName ?? null,
    }),
  });
  if (!res.ok) {
    const parsed = await res.json().catch(() => ({}));
    throw new Error(formatErrorDetail(parsed, res.status));
  }
  return res.blob();
}

export interface ExportComparisonPdfOptions {
  studentName?: string | null;
}

export async function exportComparisonPdf(
  buildIds: string[],
  opts: ExportComparisonPdfOptions = {},
): Promise<Blob> {
  const res = await fetch(`${API_BASE}/builds/compare/pdf`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      build_ids: buildIds,
      student_name: opts.studentName ?? null,
    }),
  });
  if (!res.ok) {
    const parsed = await res.json().catch(() => ({}));
    throw new Error(formatErrorDetail(parsed, res.status));
  }
  return res.blob();
}

/**
 * Trigger a browser download for a PDF Blob.
 */
export function downloadBlobAs(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
