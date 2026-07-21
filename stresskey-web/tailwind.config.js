/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sora: ['"Sora"', '"Helvetica Neue"', "Helvetica", "Arial", "sans-serif"],
      },
      colors: {
        void: {
          950: "#020207",
          900: "#06060f",
          800: "#0b0b1a",
          700: "#11132a",
        },
        glow: {
          calm:     "#34e7b8",
          happy:    "#ffd166",
          neutral:  "#7eb6ff",
          stressed: "#ff6b6b",
          angry:    "#ff8c4b",
          coral:    "#fb7c5c",
        },
      },
      backdropBlur: {
        xs: "4px",
        "2xl": "40px",
        "3xl": "56px",
      },
      keyframes: {
        breathe: {
          "0%, 100%": { transform: "scale(1)", opacity: "0.55" },
          "50%":      { transform: "scale(1.12)", opacity: "0.85" },
        },
        "breathe-slow": {
          "0%, 100%": { transform: "scale(1)", opacity: "0.4" },
          "50%":      { transform: "scale(1.06)", opacity: "0.65" },
        },
        "rise-in": {
          "0%":   { opacity: "0", transform: "translateY(18px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "drift": {
          "0%, 100%": { transform: "translate(0, 0)" },
          "50%":      { transform: "translate(2%, -3%)" },
        },
      },
      animation: {
        breathe: "breathe 6s ease-in-out infinite",
        "breathe-slow": "breathe-slow 9s ease-in-out infinite",
        "rise-in": "rise-in 0.8s cubic-bezier(0.22,1,0.36,1) both",
        "drift": "drift 18s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

