import type { Config } from "tailwindcss";

// Tokens follow docs/design DESIGN.md ("Editorial Analytical").
const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        ink: "#172B3A", // primary ink: headings, primary buttons, key metrics
        charcoal: "#334155", // long-form reading copy
        muted: "#5E6A75", // secondary labels (AA on paper)
        slate: "#8A9BA8", // placeholders, neutral sentiment
        paper: "#FBF8F1", // page canvas
        sand: "#F3EFE6", // sidebar, inset fills
        ivory: "#FAF8F5", // elevated card surface
        sage: "#D9E5D5", // quiet highlight wash
        line: "#E2DCD0", // hairline borders
        "line-strong": "#DFD9CC",
        accent: "#4169E1", // restrained cobalt: actions, active indicators
        "accent-deep": "#2552CA", // cobalt text on light surfaces
        positive: "#3D7A5A",
        neutral: "#8A9BA8",
        negative: "#BA4A4A",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "Inter", "system-ui", "sans-serif"],
        serif: ["var(--font-newsreader)", "Newsreader", "Georgia", "serif"],
      },
      fontSize: {
        "display-lg": ["48px", { lineHeight: "56px", letterSpacing: "-0.02em" }],
        "display-md": ["36px", { lineHeight: "44px", letterSpacing: "-0.01em" }],
        "headline-lg": ["32px", { lineHeight: "40px", letterSpacing: "-0.015em" }],
        "headline-md": ["24px", { lineHeight: "32px", letterSpacing: "-0.01em" }],
        "headline-sm": ["20px", { lineHeight: "28px" }],
        "body-lg": ["18px", { lineHeight: "28px" }],
        quote: ["20px", { lineHeight: "30px", letterSpacing: "-0.01em" }],
        "label-md": ["12px", { lineHeight: "16px", letterSpacing: "0.04em" }],
        "label-sm": ["11px", { lineHeight: "14px", letterSpacing: "0.03em" }],
      },
      boxShadow: {
        flyout: "0 2px 8px rgba(23, 43, 58, 0.05)",
      },
      maxWidth: {
        content: "1320px",
      },
    },
  },
  plugins: [],
};

export default config;
