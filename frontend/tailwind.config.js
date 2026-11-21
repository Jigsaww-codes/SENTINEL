/** Palette: deep navy command centre; red = high priority, amber = review, green = normal */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#070d1c',        // page background
        panel: '#0c1630',      // surfaces
        raised: '#12203f',     // elevated surfaces
        line: '#1f3158',       // borders
        mute: '#8a9bbf',       // secondary text
        high: '#f0455a',       // high-priority verification
        review: '#f5a524',     // review required
        ok: '#2fc58a',         // normal
        signal: '#4aa8ff',     // interactive / selection
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
}
