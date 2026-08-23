/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        mono: ['JetBrains Mono', 'Menlo', 'Monaco', 'Courier New', 'monospace'],
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      colors: {
        slate: {
          850: '#151f32',
          900: '#0f172a',
          950: '#080d1a',
        },
        finance: {
          accent: '#2563eb',
          accentLight: '#3b82f6',
          matched: '#059669',
          matchedBg: '#ecfdf5',
          exception: '#dc2626',
          exceptionBg: '#fef2f2',
          pending: '#d97706',
          pendingBg: '#fffbeb',
          escalated: '#7c3aed',
          escalatedBg: '#f5f3ff',
        }
      }
    },
  },
  plugins: [],
}
