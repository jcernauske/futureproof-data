/**
 * Mock wrapped handler for VITE_USE_MOCK_API=true.
 *
 * Frontend development without Playwright installed. Mock frames are
 * inline SVG data URIs that render placeholder rectangles labeled with
 * the frame name, using the Brightpath color scheme. The in-app viewer
 * composition (tap zones, progress dots, action bar) is fully
 * testable against these placeholders.
 */

import type { RenderResponse, WrappedResponse } from "@/api/wrapped";

const FRAME_LABELS = [
  "Identity",
  "Pentagon",
  "Boss Gauntlet",
  "Standout",
  "Biggest Risk",
  "Your Turn",
];

const FRAME_COLORS = [
  "#7DD4A3", // thrive
  "#B8A9E8", // insight
  "#F2D477", // caution
  "#7BB8E0", // info
  "#F4A97E", // alert
  "#E88BA9", // empathy
];

function placeholderSvg(label: string, accent: string, index: number): string {
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920" viewBox="0 0 1080 1920">
      <defs>
        <radialGradient id="g${index}" cx="50%" cy="35%" r="60%">
          <stop offset="0%" stop-color="${accent}" stop-opacity="0.25"/>
          <stop offset="100%" stop-color="${accent}" stop-opacity="0"/>
        </radialGradient>
      </defs>
      <rect width="1080" height="1920" fill="#1B1D30"/>
      <rect width="1080" height="1920" fill="url(#g${index})"/>
      <text x="540" y="160" text-anchor="middle"
            font-family="'Space Mono', monospace" font-size="20"
            letter-spacing="6" fill="#8A8595">FUTUREPROOF · MOCK</text>
      <text x="540" y="920" text-anchor="middle"
            font-family="'Fredoka', sans-serif" font-weight="700"
            font-size="110" fill="${accent}">${label}</text>
      <text x="540" y="1000" text-anchor="middle"
            font-family="'Nunito', sans-serif" font-size="34"
            fill="#C4BFB0">Frame ${index + 1} of 6</text>
      <text x="540" y="1830" text-anchor="middle"
            font-family="'Nunito', sans-serif" font-size="22"
            fill="#8A8595">Mock — install Playwright to see real frames</text>
    </svg>
  `;
  const encoded = typeof window === "undefined"
    ? Buffer.from(svg).toString("base64")
    : btoa(unescape(encodeURIComponent(svg)));
  return `data:image/svg+xml;base64,${encoded}`;
}

export async function mockRenderWrapped(): Promise<RenderResponse> {
  await new Promise((r) => setTimeout(r, 300));
  return { status: "ok", frame_count: 6 };
}

export async function mockGetWrapped(
  _buildId: string,
): Promise<WrappedResponse> {
  await new Promise((r) => setTimeout(r, 150));
  return {
    frames: FRAME_LABELS.map((label, i) => ({
      index: i,
      url: placeholderSvg(label, FRAME_COLORS[i] ?? "#7DD4A3", i),
    })),
  };
}
