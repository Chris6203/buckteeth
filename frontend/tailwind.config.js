/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          900: "#0F111A",
          800: "#1A1A2E",
          700: "#16213E",
          600: "#0F3460",
        },
        cyan: {
          DEFAULT: "#00D4FF",
          50: "rgba(0, 212, 255, 0.05)",
          100: "rgba(0, 212, 255, 0.08)",
          200: "rgba(0, 212, 255, 0.15)",
          400: "#33DDFF",
          500: "#00D4FF",
          600: "#00B8DB",
        },
        lime: {
          DEFAULT: "#00FF88",
          100: "rgba(0, 255, 136, 0.1)",
          500: "#00FF88",
        },
      },
      fontFamily: {
        heading: ["Outfit", "sans-serif"],
        body: ["Inter", "sans-serif"],
      },
    },
  },
  plugins: [],
};
