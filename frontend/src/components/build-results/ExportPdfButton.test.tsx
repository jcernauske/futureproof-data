/**
 * ExportPdfButton.test.tsx
 *
 * Spec: docs/specs/feature-pdf-report-exports.md §4 New Tests Required.
 *
 * Covers:
 *  - test_click_triggers_api_and_download — POST + URL.createObjectURL.
 *  - test_optional_name_field_prefills_from_profile — defaultStudentName.
 *  - test_error_state_shown_on_api_failure — inline error toast.
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
        defaultStudentName=""
        schoolName="Indiana University"
        programName="Mechanical Engineering"
      />,
    );

    fireEvent.click(screen.getByTestId("btn-export-pdf-build"));

    await waitFor(() => {
      expect(mockExportBuildPdf).toHaveBeenCalledTimes(1);
    });

    // First arg is the build_id; second is options.
    const [buildId, opts] = mockExportBuildPdf.mock.calls[0]!;
    expect(buildId).toBe("build-1");
    expect(opts).toEqual({ studentName: null });

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

  it("prefills the optional name input from defaultStudentName (P1)", () => {
    render(
      <ExportPdfButton
        buildId="build-1"
        defaultStudentName="Rowan"
        schoolName="Test U"
        programName="Test Program"
      />,
    );

    const input = screen.getByTestId(
      "input-export-student-name",
    ) as HTMLInputElement;
    expect(input.value).toBe("Rowan");
  });

  it("sends the typed student name to the API (P1)", async () => {
    const fakeBlob = new Blob(["%PDF-1.4 ..."], { type: "application/pdf" });
    mockExportBuildPdf.mockResolvedValue(fakeBlob);

    render(
      <ExportPdfButton
        buildId="build-1"
        defaultStudentName="Rowan"
        schoolName="Test U"
        programName="Test Program"
      />,
    );

    // Edit the value before clicking.
    const input = screen.getByTestId(
      "input-export-student-name",
    ) as HTMLInputElement;
    fireEvent.change(input, { target: { value: "Sam" } });

    fireEvent.click(screen.getByTestId("btn-export-pdf-build"));

    await waitFor(() => {
      expect(mockExportBuildPdf).toHaveBeenCalledTimes(1);
    });
    const [, opts] = mockExportBuildPdf.mock.calls[0]!;
    expect(opts).toEqual({ studentName: "Sam" });
  });

  it("sends null when the name input is empty/whitespace (P1)", async () => {
    const fakeBlob = new Blob(["%PDF-1.4 ..."], { type: "application/pdf" });
    mockExportBuildPdf.mockResolvedValue(fakeBlob);

    render(
      <ExportPdfButton
        buildId="build-1"
        defaultStudentName="   "
        schoolName="Test U"
        programName="Test Program"
      />,
    );

    fireEvent.click(screen.getByTestId("btn-export-pdf-build"));

    await waitFor(() => {
      expect(mockExportBuildPdf).toHaveBeenCalledTimes(1);
    });
    const [, opts] = mockExportBuildPdf.mock.calls[0]!;
    // Whitespace-only is normalized to null per ExportPdfButton.tsx.
    expect(opts).toEqual({ studentName: null });
  });

  it("shows an inline error alert on API failure (P1)", async () => {
    mockExportBuildPdf.mockRejectedValue(new Error("server returned 500"));

    render(
      <ExportPdfButton
        buildId="build-1"
        defaultStudentName=""
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
        defaultStudentName=""
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
