/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // 侘寂 / 幽玄色调
        ink: {
          50: '#f7f6f4',
          100: '#eeedea',
          200: '#dddad4',
          300: '#c4bfb6',
          400: '#a69f93',
          500: '#8a8276',
          600: '#6e665c',
          700: '#5a534b',
          800: '#4a453f',
          900: '#3d3935',
          950: '#1a1917',
        },
        washi: {
          DEFAULT: '#f5f3ef',
          dark: '#ebe7e0',
        },
        sumi: '#2c2a26',
        moss: '#6b7b5f',
        rust: '#9c6b4f',
        stone: '#8c8a84',
        mist: '#b8b5ad',
      },
      fontFamily: {
        serif: ['"Noto Serif SC"', 'Georgia', 'serif'],
        sans: ['"Inter"', '"Noto Sans SC"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      animation: {
        'fade-in': 'fadeIn 0.6s ease-out',
        'slide-up': 'slideUp 0.5s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      boxShadow: {
        'soft': '0 2px 20px -4px rgba(0, 0, 0, 0.04)',
        'glow': '0 0 40px -10px rgba(107, 123, 95, 0.15)',
      },
    },
  },
  plugins: [],
}
