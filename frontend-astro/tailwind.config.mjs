/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './src/**/*.{astro,html,js,jsx,md,mdx,svelte,ts,tsx,vue}',
  ],
  theme: {
    extend: {
      colors: {
        ash: {
          50: '#f5f5f7',
          100: '#e6e6eb',
          200: '#c8c8d4',
          300: '#a3a3b5',
          400: '#7a7a90',
          500: '#5a5a6e',
          600: '#454556',
          700: '#333342',
          800: '#22222d',
          900: '#16161d',
          950: '#0c0c12',
        },
        y2k: {
          blue: '#00a8e8',
          cyan: '#5ce1e6',
          electric: '#0088ff',
          ice: '#b8e6ff',
        },
        soft: {
          pink: '#e8a0bf',
          rose: '#d484a8',
          blush: '#f5c9dc',
          lavender: '#9d8ec7',
          lilac: '#c4b8e8',
          mint: '#9dd9c7',
          sage: '#a8c4a2',
        },
        ink: {
          DEFAULT: '#0c0c12',
          card: 'rgba(22, 22, 29, 0.72)',
          glass: 'rgba(18, 18, 24, 0.60)',
          blur: 'rgba(12, 12, 18, 0.85)',
        },
        fog: {
          DEFAULT: 'rgba(200, 200, 215, 0.08)',
          dense: 'rgba(200, 200, 215, 0.15)',
        },
        positive: '#6ee7d0',
        negative: '#e8a0bf',
      },
      fontFamily: {
        display: ['"Bodoni Moda"', '"Cormorant Garamond"', '"Noto Serif SC"', 'Georgia', 'serif'],
        sans: ['"Inter"', '"Noto Sans SC"', 'system-ui', 'sans-serif'],
        mono: ['"Space Mono"', '"JetBrains Mono"', 'monospace'],
      },
      animation: {
        'fade-in': 'fadeIn 0.8s cubic-bezier(0.22, 1, 0.36, 1) forwards',
        'slide-up': 'slideUp 0.8s cubic-bezier(0.22, 1, 0.36, 1) forwards',
        'pulse-slow': 'pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'grain': 'grain 8s steps(10) infinite',
        'float': 'float 7s ease-in-out infinite',
        'drift': 'drift 12s ease-in-out infinite',
        'shimmer': 'shimmer 3s ease-in-out infinite',
        'foam-rise': 'foamRise 1.2s cubic-bezier(0.22, 1, 0.36, 1) forwards',
        'fog-roll': 'fogRoll 1.5s cubic-bezier(0.22, 1, 0.36, 1) forwards',
        'crow-fly': 'crowFly 1s cubic-bezier(0.22, 1, 0.36, 1) forwards',
        'pixel-dissolve': 'pixelDissolve 0.6s cubic-bezier(0.22, 1, 0.36, 1) forwards',
        'ink-spread': 'inkSpread 0.5s cubic-bezier(0.22, 1, 0.36, 1) forwards',
        'bubble': 'bubble 4s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(28px)' },
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
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        drift: {
          '0%, 100%': { transform: 'translate(0, 0)' },
          '50%': { transform: 'translate(8px, -6px)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        foamRise: {
          '0%': { opacity: '0', transform: 'translateY(8px) scale(0.9)' },
          '30%': { opacity: '0.6', transform: 'translateY(-4px) scale(1.05)' },
          '100%': { opacity: '0', transform: 'translateY(-24px) scale(1.2)' },
        },
        fogRoll: {
          '0%': { opacity: '0', transform: 'translateY(20%)' },
          '40%': { opacity: '1' },
          '100%': { opacity: '0', transform: 'translateY(-20%)' },
        },
        crowFly: {
          '0%': { opacity: '1', transform: 'translate(0, 0) scale(1)' },
          '100%': { opacity: '0', transform: 'translate(60px, -40px) scale(0.6)' },
        },
        pixelDissolve: {
          '0%': { opacity: '0.8', filter: 'blur(0px)' },
          '50%': { opacity: '0.4', filter: 'blur(2px)' },
          '100%': { opacity: '0', filter: 'blur(4px)' },
        },
        inkSpread: {
          '0%': { opacity: '0.6', transform: 'scale(0.8)' },
          '100%': { opacity: '0', transform: 'scale(2.5)' },
        },
        bubble: {
          '0%, 100%': { transform: 'translateY(0) scale(1)', opacity: '0.3' },
          '50%': { transform: 'translateY(-20px) scale(1.1)', opacity: '0.6' },
        },
      },
      backgroundImage: {
        'noise': "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.5'/%3E%3C/svg%3E\")",
        'scanlines': "linear-gradient(to bottom, rgba(255,255,255,0.03) 1px, transparent 1px)",
        'pixel-grid': "linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px)",
      },
      boxShadow: {
        'soft': '0 2px 20px -4px rgba(0, 0, 0, 0.25)',
        'glow-blue': '0 0 40px -10px rgba(0, 168, 232, 0.25)',
        'glow-pink': '0 0 40px -10px rgba(232, 160, 191, 0.25)',
        'glow-lavender': '0 0 40px -10px rgba(157, 142, 199, 0.25)',
        'glass': '0 8px 32px -8px rgba(0,0,0,0.35), inset 0 1px 1px rgba(255,255,255,0.06)',
        'glass-lg': '0 24px 64px -24px rgba(0,0,0,0.45), inset 0 1px 1px rgba(255,255,255,0.08)',
      },
      transitionTimingFunction: {
        'editorial': 'cubic-bezier(0.22, 1, 0.36, 1)',
        'apple': 'cubic-bezier(0.25, 0.1, 0.25, 1)',
      },
    },
  },
  plugins: [],
}
