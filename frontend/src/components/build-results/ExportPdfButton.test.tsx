/**
 * ExportPdfButton.test.tsx
 *
 * Spec: docs/specs/feature-pdf-report-exports.md §4 New Tests Required.
 *
 * Covers:
 *  - test_click_triggers_api_and_download — POST + URL.createObjectURL.
 *  - test_error_state_shown_on_api_failure — inline error toast.
 *  - The optional student-name input was removed per UX feedback —
 *    PDF exports always go out without a custom name.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

import { ExportPdfButton } from "./ExportPdfButton";

// Mock the @/api/pdf module so the click handler doesn't try to fetch.
const mockExportBuildPdf = vi.fn();
const mockDownloadBlobAs = vi.fn();
vi.mock("@/api/pdf", () => ({
  exportBuildPdf: (...args: unknown[]) => mockExportBuildPdf(...args),
  downloadBlobAs: (...args: unknown[]) => mockDownloadBlobAs(...args),
}));

beforeEach(() => {
  mockExportBuildPdf.mockReset();
  mockDownloadBlobAs.mockReset();
});

afterEach(() => {
  // Reset URL.createObjectURL mock between tests if it was stubbed.
  vi.restoreAllMocks();
});

describe("ExportPdfButton", () => {
  it("triggers exportBuildPdf and download on click (P1)", async () => {
    const fakeBlob = new Blob(["%PDF-1.4 ..."], { type: "application/pdf" });
    mockExportBuildPdf.mockResolvedValue(fakeBlob);

    render(
      <ExportPdfButton
        buildId="build-1"
        schoolName="Indiana University"
        programName="Mechanical Engineering"
      />,
    );

    fireEvent.click(screen.getByTestId("btn-export-pdf-build"));

    await waitFor(() => {
      expect(mockExportBuildPdf).toHaveBeenCalledTimes(1);
    });

    // The button no longer collects a student name; the API is called
    // with just the build_id.
    const [buildId] = mockExportBuildPdf.mock.calls[0]!;
    expect(buildId).toBe("build-1");

    // downloadBlobAs is called with the blob and a slugged filename.
    await waitFor(() => {
      expect(mockDownloadBlobAs).toHaveBeenCalledTimes(1);
    });
    const [calledBlob, filename] = mockDownloadBlobAs.mock.calls[0]!;
    expect(calledBlob).toBe(fakeBlob);
    expect(filename).toMatch(/^futureproof-/);
    expect(filename).toMatch(/\.pdf$/);
    expect(filename).toContain("indiana-university");
    expect(filename).toContain("mechanical-engineering");
  });

  it("does not render a student-name input", () => {
    render(
      <ExportPdfButton
        buildId="build-1"
        schoolName="Test U"
        programName="Test Program"
      />,
    );
    expect(
      screen.queryByTestId("input-export-student-name"),
    ).toBeNull();
  });

  it("shows an inline error alert on API failure (P1)", async () => {
    mockExportBuildPdf.mockRejectedValue(new Error("server returned 500"));

    render(
      <ExportPdfButton
        buildId="build-1"
        schoolName="Test U"
        programName="Test Program"
      />,
    );

    fireEvent.click(screen.getByTestId("btn-export-pdf-build"));

    // The error alert renders with role="alert".
    await waitFor(() => {
      expect(screen.getByTestId("alert-pdf-export-error")).toBeInTheDocument();
    });

    // Download was never invoked.
    expect(mockDownloadBlobAs).not.toHaveBeenCalled();
  });

  it("disables the button while the export is loading (saboteur)", async () => {
    // Defer resolution so we can observe the loading state.
    let resolve: (b: Blob) => void = () => {};
    const pending = new Promise<Blob>((r) => (resolve = r));
    mockExportBuildPdf.mockReturnValue(pending);

    render(
      <ExportPdfButton
        buildId="build-1"
        schoolName="Test U"
        programName="Test Program"
      />,
    );

    const btn = screen.getByTestId("btn-export-pdf-build") as HTMLButtonElement;
    fireEvent.click(btn);

    await waitFor(() => expect(btn.disabled).toBe(true));

    // Settle so the test can clean up.
    resolve(new Blob(["%PDF-1.4 ..."], { type: "application/pdf" }));
    await waitFor(() => expect(btn.disabled).toBe(false));
  });
});
