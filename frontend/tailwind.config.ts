import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/\\[locale\\]/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Sage green primary palette
        primary: {
          50: "#f6f7f6",
          100: "#e3e7e3",
          200: "#c7d0c7",
          300: "#a3b2a3",
          400: "#7d917d",
          500: "#627862", // Main brand color
          600: "#4d5f4d",
          700: "#404d40",
          800: "#363f36",
          900: "#2e352e",
          950: "#171c17",
        },
        // Earthy accent colors
        healing: {
          sage: "#627862",
          lavender: "#a17d66",
          sky: "#bc7a5c",
          sand: "#e9dcc8",
          cream: "#fdfcfa",
        },
        // Warm cream surfaces
        surface: {
          DEFAULT: "#fdfcfa",
          secondary: "#f9f6f0",
          tertiary: "#f3ece0",
        },
        // Earthy text colors
        text: {
          primary: "#2e352e",
          secondary: "#533f38",
          muted: "#6c5b45",
        },
        // Extended palettes
        cream: {
          50: "#fdfcfa",
          100: "#f9f6f0",
          200: "#f3ece0",
          300: "#e9dcc8",
          400: "#dcc8a8",
          500: "#cfb48d",
        },
        earth: {
          400: "#b29581",
          500: "#a17d66",
          600: "#946c5a",
          700: "#7b594c",
          800: "#654a42",
        },
        terra: {
          400: "#cb9379",
          500: "#bc7a5c",
          600: "#ae6850",
          700: "#915544",
          800: "#77483c",
        },
        // CSS variable-based colors (shadcn/ui)
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
      },
      fontFamily: {
        sans: ["Source Sans 3", "Inter", "system-ui", "sans-serif"],
        display: ["Playfair Display", "Cal Sans", "Georgia", "serif"],
      },
      borderRadius: {
        "4xl": "2rem",
        soft: "0.625rem",
        softer: "1rem",
      },
      boxShadow: {
        soft: "0 2px 8px -2px rgba(46, 53, 46, 0.08), 0 4px 16px -4px rgba(46, 53, 46, 0.12)",
        "soft-lg": "0 4px 12px -4px rgba(46, 53, 46, 0.1), 0 8px 24px -8px rgba(46, 53, 46, 0.15)",
        "inner-soft": "inset 0 2px 4px 0 rgba(46, 53, 46, 0.05)",
      },
      animation: {
        "fade-in": "fadeIn 0.3s ease-in-out",
        "slide-up": "slideUp 0.4s ease-out",
        "pulse-soft": "pulseSoft 2s ease-in-out infinite",
        "writing": "writing 1.5s ease-in-out infinite",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { transform: "translateY(10px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
        pulseSoft: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.7" },
        },
        writing: {
          "0%, 100%": { transform: "rotate(-5deg) translateY(0)" },
          "25%": { transform: "rotate(0deg) translateY(-2px)" },
          "50%": { transform: "rotate(5deg) translateY(0)" },
          "75%": { transform: "rotate(0deg) translateY(2px)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
