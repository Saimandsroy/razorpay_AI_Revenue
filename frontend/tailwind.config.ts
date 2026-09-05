import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        background: "#0a0c10",
        surface: "#111418",
        surfaceHover: "#161a1f",
        border: "#21262d",

        primary: "#e6edf3",
        secondary: "#848d97",
        tertiary: "#57606a",

        accent: {
          blue: "#2f81f7",
          bluebg: "rgba(47, 129, 247, 0.1)",
          green: "#3fb950",
          greenbg: "rgba(63, 185, 80, 0.1)",
          amber: "#d29922",
          amberbg: "rgba(210, 153, 34, 0.1)",
          red: "#f85149",
          redbg: "rgba(248, 81, 73, 0.1)"
        }
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      }
    },
  },
  plugins: [],
};

export default config;
