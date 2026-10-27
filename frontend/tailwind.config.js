/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#F6F7F9",
        surface: "#FFFFFF",
        ink: "#202939",
        muted: "#667085",
        border: "#E4E7EC",
        primary: "#2457C5",
        success: "#1E7A4C",
        warning: "#B7791F",
        danger: "#B42318",
      },
      fontFamily: {
        sans: ["system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
      },
    },
  },
  plugins: [],
};
