/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './src/**/*.{astro,html,js,jsx,md,mdx,svelte,ts,tsx,vue}',
  ],
  theme: {
    extend: {
      colors: {
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
        display: ['"Cormorant Garamond"', '"Noto Serif SC"', 'Georgia', 'serif'],
        serif: ['"Noto Serif SC"', 'Georgia', 'serif'],
        sans: ['"Inter"', '"Noto Sans SC"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      animation: {
        'fade-in': 'fadeIn 0.7s ease-out forwards',
        'slide-up': 'slideUp 0.6s ease-out forwards',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'grain': 'grain 8s steps(10) infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(18px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        grain: {
          '0%, 100%': { transform: 'translate(0, 0)' },
          '10%': { transform: 'translate(-5%, -10%)' },
          '20%': { transform: 'translate(-15%, 5%)' },
          '30%': { transform: 'translate(7%, -25%)' },
          '40%': { transform: 'translate(-5%, 25%)' },
          '50%': { transform: 'translate(-15%, 10%)' },
          '60%': { transform: 'translate(15%, 0%)' },
          '70%': { transform: 'translate(0%, 15%)' },
          '80%': { transform: 'translate(3%, 35%)' },
          '90%': { transform: 'translate(-10%, 10%)' },
        },
      },
      backgroundImage: {
        'marble': "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='marble'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.012' numOctaves='5' seed='7'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3CfeComponentTransfer%3E%3CfeFuncR type='linear' slope='0.15' intercept='0.92'/%3E%3CfeFuncG type='linear' slope='0.15' intercept='0.91'/%3E%3CfeFuncB type='linear' slope='0.15' intercept='0.89'/%3E%3C/feComponentTransfer%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23marble)'/%3E%3C/svg%3E\")",
      },
      boxShadow: {
        'soft': '0 2px 20px -4px rgba(0, 0, 0, 0.04)',
        'glow': '0 0 40px -10px rgba(107, 123, 95, 0.15)',
        'glass': 'inset 0 1px 1px rgba(255,255,255,0.65), inset 0 -1px 1px rgba(44,42,38,0.03), 0 1px 2px rgba(44,42,38,0.02), 0 16px 48px -16px rgba(44,42,38,0.10)',
        'glass-lg': 'inset 0 1px 1px rgba(255,255,255,0.7), inset 0 -1px 1px rgba(44,42,38,0.03), 0 1px 2px rgba(44,42,38,0.02), 0 24px 64px -20px rgba(44,42,38,0.14)',
      },
    },
  },
  plugins: [],
}
