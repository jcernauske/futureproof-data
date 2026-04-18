import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { PageContainer } from "./PageContainer";

describe("PageContainer", () => {
  it("renders children inside a grid container by default", () => {
    render(
      <PageContainer>
        <div data-testid="child">hello</div>
      </PageContainer>,
    );
    const root = screen.getByTestId("page-container");
    expect(root.className).toContain("container");
    expect(root.className).toContain("mx-auto");
    expect(root.className).toContain("grid-cols-12");
    expect(screen.getByTestId("child")).toBeInTheDocument();
  });

  it("wraps children in a col-span-8 col-start-3 cell when variant=centered", () => {
    render(
      <PageContainer variant="centered">
        <div data-testid="child">content</div>
      </PageContainer>,
    );
    const root = screen.getByTestId("page-container");
    expect(root.className).toContain("grid-cols-12");
    const child = screen.getByTestId("child");
    const parentCell = child.parentElement!;
    expect(parentCell.className).toContain("col-span-12");
    expect(parentCell.className).toContain("desktop:col-span-8");
    expect(parentCell.className).toContain("desktop:col-start-3");
  });

  it("renders without grid classes when variant=bleed", () => {
    render(
      <PageContainer variant="bleed">
        <div>bleed child</div>
      </PageContainer>,
    );
    const root = screen.getByTestId("page-container");
    expect(root.className).toContain("container");
    expect(root.className).not.toContain("grid-cols-12");
  });

  it("forwards className and testId", () => {
    render(
      <PageContainer className="pt-14" testId="custom-id">
        <div>x</div>
      </PageContainer>,
    );
    const root = screen.getByTestId("custom-id");
    expect(root.className).toContain("pt-14");
  });
});
