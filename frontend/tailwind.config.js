/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        arcus: { bg: '#0a0e1a', card: '#111827', border: '#1f2937', accent: '#38bdf8' },
      },
    },
  },
  plugins: [],
}
