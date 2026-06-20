/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive) / <alpha-value>)",
          foreground: "hsl(var(--destructive-foreground) / <alpha-value>)",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        sidebar: {
          DEFAULT: "hsl(var(--sidebar-background))",
          foreground: "hsl(var(--sidebar-foreground))",
          primary: "hsl(var(--sidebar-primary))",
          "primary-foreground": "hsl(var(--sidebar-primary-foreground))",
          accent: "hsl(var(--sidebar-accent))",
          "accent-foreground": "hsl(var(--sidebar-accent-foreground))",
          border: "hsl(var(--sidebar-border))",
          ring: "hsl(var(--sidebar-ring))",
        },
        // SG custom colors (Institutional Excellence)
        sg: {
          surface: 'var(--sg-surface)',
          'surface-dim': 'var(--sg-surface-dim)',
          'surface-muted': 'var(--sg-surface-muted)',
          primary: 'var(--sg-primary)',
          'primary-hover': 'var(--sg-primary-hover)',
          secondary: 'var(--sg-secondary)',
          text: {
            primary: 'var(--sg-text-primary)',
            secondary: 'var(--sg-text-secondary)',
            inverse: 'var(--sg-text-inverse)',
          },
          border: {
            DEFAULT: 'var(--sg-border)',
            subtle: 'var(--sg-border-subtle)',
            focus: 'var(--sg-border-focus)',
          },
          error: 'var(--sg-error)',
          risk: {
            red: '#bb0507',
            'red-bg': 'var(--sg-risk-red-bg)',
            yellow: '#E8A838',
            'yellow-bg': 'var(--sg-risk-yellow-bg)',
            green: '#1DB954',
            'green-bg': 'var(--sg-risk-green-bg)',
            clear: '#00D4AA',
            'clear-bg': 'var(--sg-risk-clear-bg)',
          },
        },
      },
      fontFamily: {
        sans: ['Source Sans 3', 'system-ui', 'sans-serif'],
        display: ['Montserrat', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      borderRadius: {
        xl: "calc(var(--radius) + 4px)",
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
        xs: "calc(var(--radius) - 6px)",
        card: '0px',
        button: '4px',
        input: '4px',
        chip: '2px',
      },
      boxShadow: {
        xs: "0 1px 2px 0 rgb(0 0 0 / 0.05)",
        card: '0 1px 3px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.06)',
        elevated: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
        lift: '0 4px 12px rgba(0, 0, 0, 0.1)',
      },
      spacing: {
        'sidebar': '240px',
        'topbar': '56px',
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
        "caret-blink": {
          "0%,70%,100%": { opacity: "1" },
          "20%,50%": { opacity: "0" },
        },
        "pulse-scale": {
          "0%, 100%": { transform: "scale(1)", opacity: "1" },
          "50%": { transform: "scale(1.4)", opacity: "0.7" },
        },
        "spin-slow": {
          "0%": { transform: "rotate(0deg)" },
          "100%": { transform: "rotate(360deg)" },
        },
        "shimmer": {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        "fade-in-up": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "typing": {
          from: { width: "0" },
          to: { width: "100%" },
        },
        "blink": {
          "from, to": { borderColor: "transparent" },
          "50%": { borderColor: "rgba(255, 255, 255, 0.4)" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "caret-blink": "caret-blink 1.25s ease-out infinite",
        "pulse-scale": "pulse-scale 2s ease-in-out infinite",
        "spin-slow": "spin-slow 0.8s linear infinite",
        "shimmer": "shimmer 1.5s ease-in-out infinite",
        "fade-in-up": "fade-in-up 0.3s ease forwards",
        "typing": "typing 0.1s steps(1, end)",
        "blink": "blink 0.8s step-end infinite",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}
