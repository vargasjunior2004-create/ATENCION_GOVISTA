/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eefbf3',
          100: '#d6f5e1',
          200: '#b0eac7',
          300: '#7ddaA6',
          400: '#43c47f',
          500: '#1faa62',
          600: '#12894d',
          700: '#0f6e3f',
          800: '#105834',
          900: '#0e482c',
          950: '#062917',
        },
        vista: {
          dark: '#0a1f14',
          sidebar: '#0d2b1b',
          accent: '#00d67b',
          glow: '#00ff8c',
          muted: '#1a3d2a',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        display: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        'card': '0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.03)',
        'card-hover': '0 4px 16px rgba(0,0,0,0.08), 0 1px 4px rgba(0,0,0,0.04)',
        'glow': '0 0 20px rgba(0,214,123,0.15)',
      },
    },
  },
  plugins: [],
};
