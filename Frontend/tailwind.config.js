/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg:        '#08080A',   // app background
        surface:   '#0D0D10',   // cards / panels
        surface2:  '#111116',   // nested boxes, table stripes
        border:    '#1E1E24',   // all 1px borders
        border2:   '#2A2A32',   // hover / focus borders
        text:      '#F4F4F5',   // primary text
        muted:     '#8A8A94',   // secondary text, labels
        dim:       '#5A5A64',   // tertiary / footnotes

        accent:    '#FF2D78',   // AIFlow pink — primary action, active nav, key numbers
        accentDim: '#B01F55',
        accentBg:  'rgba(255,45,120,0.08)',

        // pathway / status colors — used for badges, bars, chart series
        deterministic: '#22C55E',  // green
        cache:         '#A855F7',  // purple
        retrieval:     '#6366F1',  // indigo
        smallModel:    '#FF2D78',  // pink
        largeModel:    '#F59E0B',  // amber
        escalated:     '#EF4444',  // red
        ok:            '#22C55E',
        warn:          '#F59E0B',
        danger:        '#EF4444',
      },
      fontFamily: {
        sans: ['Sora', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      animation: {
        'pulse-subtle': 'pulseSubtle 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.15s ease-out forwards',
        'slide-up': 'slideUp 0.25s ease-out forwards',
      },
      keyframes: {
        pulseSubtle: {
          '0%, 100%': { opacity: '1', transform: 'scale(1)' },
          '50%': { opacity: '0.4', transform: 'scale(0.95)' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      }
    },
  },
  plugins: [],
}
