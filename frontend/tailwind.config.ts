import type { Config } from "tailwindcss";

/**
 * Brightpath Design System — Tailwind Configuration
 * Maps CSS custom properties from tokens.css into Tailwind utility classes.
 *
 * Usage examples:
 *   bg-bp-deep        → var(--color-bg-deep)
 *   text-bp-primary   → var(--color-text-primary)
 *   text-accent-thrive → var(--color-accent-thrive)
 *   font-display      → Fredoka
 *   rounded-xl        → 20px
 *   shadow-glow-thrive → glow shadow
 */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    container: {
      center: true,
      padding: {
        DEFAULT: "var(--layout-grid-gutter-mobile)",
        tablet: "var(--layout-grid-gutter-tablet)",
        desktop: "var(--layout-grid-gutter-desktop)",
      },
      screens: {
        tablet: "var(--layout-container-max-tablet)",
        desktop: "var(--layout-container-max-desktop)",
        wide: "var(--layout-container-max-wide)",
        ultra: "var(--layout-container-max-ultra)",
      },
    },
    extend: {
      colors: {
        bp: {
          void: "var(--color-bg-void)",
          deep: "var(--color-bg-deep)",
          mid: "var(--color-bg-mid)",
          surface: "var(--color-bg-surface)",
          raised: "var(--color-bg-raised)",
        },
        accent: {
          thrive: "var(--color-accent-thrive)",
          alert: "var(--color-accent-alert)",
          caution: "var(--color-accent-caution)",
          insight: "var(--color-accent-insight)",
          info: "var(--color-accent-info)",
          empathy: "var(--color-accent-empathy)",
        },
        stat: {
          ern: "var(--color-stat-ern)",
          roi: "var(--color-stat-roi)",
          res: "var(--color-stat-res)",
          grw: "var(--color-stat-grw)",
          hmn: "var(--color-stat-hmn)",
        },
        text: {
          primary: "var(--color-text-primary)",
          secondary: "var(--color-text-secondary)",
          muted: "var(--color-text-muted)",
          inverse: "var(--color-text-inverse)",
        },
        boss: {
          ai: "var(--color-boss-ai)",
          loans: "var(--color-boss-loans)",
          market: "var(--color-boss-market)",
          burnout: "var(--color-boss-burnout)",
          ceiling: "var(--color-boss-ceiling)",
        },
        border: {
          subtle: "var(--color-border-subtle)",
          DEFAULT: "var(--color-border-default)",
          strong: "var(--color-border-strong)",
        },
        state: {
          loading: "var(--color-state-loading)",
          success: "var(--color-state-success)",
          error: "var(--color-state-error)",
          disabled: "var(--color-state-disabled)",
          active: "var(--color-state-active)",
        },
        focus: {
          ring: "var(--color-focus-ring)",
        },
      },
      fontFamily: {
        display: ["Fredoka", "sans-serif"],
        body: ["Nunito", "sans-serif"],
        data: ["Space Mono", "monospace"],
      },
      fontSize: {
        "marketing-hero": ["6rem", { lineHeight: "1.05", letterSpacing: "-0.02em" }],
        "marketing-section": ["4rem", { lineHeight: "1.1", letterSpacing: "-0.015em" }],
        "hero-desktop": ["4rem", { lineHeight: "1.1" }],
        "hero-tablet": ["3.5rem", { lineHeight: "1.1" }],
        hero: ["3rem", { lineHeight: "1.1" }],
        title: ["2.5rem", { lineHeight: "1.2" }],
        display: ["2.25rem", { lineHeight: "1.15" }],
        heading: ["1.75rem", { lineHeight: "1.2" }],
        subheading: ["1.375rem", { lineHeight: "1.3" }],
        "body-lg": ["1.125rem", { lineHeight: "1.5" }],
        body: ["1rem", { lineHeight: "1.5" }],
        "body-sm": ["0.9375rem", { lineHeight: "1.5" }],
        cta: ["1.0625rem", { lineHeight: "1.4" }],
        small: ["0.875rem", { lineHeight: "1.4" }],
        micro: ["0.75rem", { lineHeight: "1.3" }],
        "stat-label": ["0.625rem", { lineHeight: "1.3" }],
        "data-lg": ["1.5rem", { lineHeight: "1.2" }],
        data: ["1rem", { lineHeight: "1.4" }],
        "data-sm": ["0.8125rem", { lineHeight: "1.3" }],
      },
      borderRadius: {
        sm: "6px",
        md: "10px",
        lg: "14px",
        xl: "20px",
        full: "9999px",
      },
      boxShadow: {
        sm: "var(--shadow-sm)",
        md: "var(--shadow-md)",
        lg: "var(--shadow-lg)",
        "glow-thrive": "var(--shadow-glow-thrive)",
        "glow-alert": "var(--shadow-glow-alert)",
        "glow-caution": "var(--shadow-glow-caution)",
        "glow-insight": "var(--shadow-glow-insight)",
        "glow-info": "var(--shadow-glow-info)",
        "glow-empathy": "var(--shadow-glow-empathy)",
      },
      spacing: {
        1: "4px",
        2: "8px",
        3: "12px",
        4: "16px",
        5: "20px",
        6: "24px",
        8: "32px",
        10: "40px",
        12: "48px",
        16: "64px",
        20: "80px",
      },
      screens: {
        mobile: "480px",
        tablet: "768px",
        desktop: "1200px",
        wide: "1440px",
        ultra: "1920px",
      },
      transitionDuration: {
        fast: "150ms",
        normal: "200ms",
        slow: "300ms",
      },
      gap: {
        "grid-mobile": "var(--layout-grid-gutter-mobile)",
        "grid-tablet": "var(--layout-grid-gutter-tablet)",
        "grid-desktop": "var(--layout-grid-gutter-desktop)",
      },
    },
  },
  plugins: [],
} satisfies Config;
