/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        surface: '#0f1117',
        card: '#16181d',
        border: '#23262d',
        accent: '#f59e0b',
        'accent-muted': '#92400e',
        'text-primary': '#f1f5f9',
        'text-secondary': '#94a3b8',
        'text-muted': '#475569',
      },
      fontFamily: {
        sans: [
          'Inter',
          'ui-sans-serif',
          'system-ui',
          '-apple-system',
          'sans-serif',
        ],
        mono: ['JetBrains Mono', 'Fira Code', 'ui-monospace', 'monospace'],
      },
      borderColor: {
        DEFAULT: '#23262d',
      },
      ringColor: {
        DEFAULT: '#f59e0b',
      },
    },
  },
  plugins: [],
}
