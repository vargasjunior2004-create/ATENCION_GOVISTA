/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f1faf4',
          100: '#dff2e5',
          200: '#c0e5cc',
          500: '#2e9e55',
          600: '#1f8a46',
          700: '#197037',
          800: '#145a2d',
          900: '#0f4a24',
        },
      },
    },
  },
  plugins: [],
};
