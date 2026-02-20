import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Therapeutic color palette
        primary: {
          50: "#fef7f5",
          100: "#fdeee9",
          200: "#fad9cf",
          300: "#f5b8a5",
          400: "#ed8f73",
          500: "#da7756", // Main brand color
          600: "#c45d3d",
          700: "#a34931",
          800: "#863e2c",
          900: "#6f3729",
        },
        // Calm, healing tones
        healing: {
          sage: "#9CAF88",
          lavender: "#B8A9C9",
          sky: "#87CEEB",
          sand: "#E6D5B8",
          cream: "#FFF8F0",
        },
        // UI colors
        surface: {
          DEFAULT: "#FFFFFF",
          secondary: "#F8F9FA",
          tertiary: "#F1F3F5",
        },
        text: {
          primary: "#1A1A2E",
          secondary: "#4A4A68",
          muted: "#8B8BA7",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        display: ["Cal Sans", "Inter", "system-ui", "sans-serif"],
      },
      borderRadius: {
        "4xl": "2rem",
      },
      animation: {
        "fade-in": "fadeIn 0.3s ease-in-out",
        "slide-up": "slideUp 0.4s ease-out",
        "pulse-soft": "pulseSoft 2s ease-in-out infinite",
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
      },
    },
  },
  plugins: [],
};

export default config;
