/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  safelist: ['bg-primary-dis', 'text-primary-foreground', 'animate-emojiFall'],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          'Pretendard',
          'system-ui',
          '-apple-system',
          'BlinkMacSystemFont',
          '"Segoe UI"',
          'sans-serif',
        ],
      },
      colors: {
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',

        card: 'hsl(var(--card))',
        'card-foreground': 'hsl(var(--card-foreground))',

        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',

        primary: 'hsl(var(--primary))',
        'primary-dis': 'hsl(var(--primary-dis))',
        'primary-foreground': 'hsl(var(--primary-foreground))',

        secondary: 'hsl(var(--secondary))',
        'secondary-foreground': 'hsl(var(--secondary-foreground))',

        muted: 'hsl(var(--muted))',
        'muted-foreground': 'hsl(var(--muted-foreground))',

        accent: 'hsl(var(--accent))',
        'accent-foreground': 'hsl(var(--accent-foreground))',

        destructive: 'hsl(var(--destructive))',
        'destructive-foreground': 'hsl(var(--destructive-foreground))',

        'sidebar-background': 'hsl(var(--sidebar-background))',
        'sidebar-foreground': 'hsl(var(--sidebar-foreground))',
        'sidebar-primary': 'hsl(var(--sidebar-primary))',
        'sidebar-primary-foreground': 'hsl(var(--sidebar-primary-foreground))',
        'sidebar-accent': 'hsl(var(--sidebar-accent))',
        'sidebar-accent-foreground': 'hsl(var(--sidebar-accent-foreground))',
        'sidebar-border': 'hsl(var(--sidebar-border))',
        'sidebar-ring': 'hsl(var(--sidebar-ring))',
      },
      borderRadius: {
        lg: 'var(--radius)',
      },

      //  keyframes 한 번만
      keyframes: {
        slotShow: {
          '0%': { opacity: '0', transform: 'scale(0.95)' },
          '2%': { opacity: '1', transform: 'scale(1)' },
          '16%': { opacity: '1', transform: 'scale(1)' },
          '20%': { opacity: '0', transform: 'scale(0.95)' },
          '100%': { opacity: '0' },
        },
        drawLoop: {
          '0%': { strokeDashoffset: '520' },
          '2%': { strokeDashoffset: '520' },
          '15%': { strokeDashoffset: '0' },
          '16.5%': { strokeDashoffset: '0' },
          '20%': { strokeDashoffset: '520' },
          '100%': { strokeDashoffset: '520' },
        },
        emojiFall: {
          '0%': { transform: 'translateY(-10%)', opacity: '1' },
          '100%': { transform: 'translateY(110vh)', opacity: '0' },
        },
      },

      //  animation 한 번만
      animation: {
        slot1: 'slotShow 10s ease-in-out 0s infinite both',
        slot2: 'slotShow 10s ease-in-out 2s infinite both',
        slot3: 'slotShow 10s ease-in-out 4s infinite both',
        slot4: 'slotShow 10s ease-in-out 6s infinite both',
        slot5: 'slotShow 10s ease-in-out 8s infinite both',

        draw1: 'drawLoop 10s ease-in-out 0s infinite both',
        draw2: 'drawLoop 10s ease-in-out 2s infinite both',
        draw3: 'drawLoop 10s ease-in-out 4s infinite both',
        draw4: 'drawLoop 10s ease-in-out 6s infinite both',
        draw5: 'drawLoop 10s ease-in-out 8s infinite both',
      },
    },
  },
  plugins: [],
}
