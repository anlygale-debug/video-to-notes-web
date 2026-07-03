/** @type {import('tailwindcss').Config} */
export default {
  theme: {
    extend: {
    colors: {
        primary: {
            '50': 'hsl(212, 100%, 97%)',
            '100': 'hsl(212, 100%, 94%)',
            '200': 'hsl(212, 100%, 86%)',
            '300': 'hsl(212, 100%, 76%)',
            '400': 'hsl(212, 100%, 64%)',
            '500': 'hsl(212, 100%, 50%)',
            '600': 'hsl(212, 100%, 40%)',
            '700': 'hsl(212, 100%, 32%)',
            '800': 'hsl(212, 100%, 24%)',
            '900': 'hsl(212, 100%, 16%)',
            '950': 'hsl(212, 100%, 10%)',
            DEFAULT: '#0070f3'
        },
        'neutral-50': '#ebebeb',
        'neutral-100': '#171717',
        'neutral-200': '#4d4d4d',
        'neutral-300': '#666666',
        'neutral-400': '#ffffff',
        'neutral-500': '#8f8f8f',
        'neutral-600': '#a8a8a8',
        'neutral-700': '#000000',
        'neutral-800': '#7d7d7d',
        'neutral-900': '#383838',
        background: '#fafafa',
        foreground: '#171717'
    },
    fontFamily: {
        sans: [
            'GeistSans',
            'sans-serif'
        ],
        mono: [
            'Geist Mono',
            'sans-serif'
        ]
    },
    fontSize: {
        '8': [
            '8px',
            {
                lineHeight: '8px'
            }
        ],
        '12': [
            '12px',
            {
                lineHeight: '16px',
                letterSpacing: '0.6px'
            }
        ],
        '13': [
            '13px',
            {
                lineHeight: '13px',
                letterSpacing: '-0.13px'
            }
        ],
        '14': [
            '14px',
            {
                lineHeight: '20px'
            }
        ],
        '16': [
            '16px',
            {
                lineHeight: '24px'
            }
        ],
        '20': [
            '20px',
            {
                lineHeight: '28px'
            }
        ],
        '22': [
            '22px',
            {
                lineHeight: '28px',
                letterSpacing: '-0.66px'
            }
        ],
        '24': [
            '24px',
            {
                lineHeight: '32px'
            }
        ],
        '30': [
            '30px',
            {
                lineHeight: '33px',
                letterSpacing: '-1.5px'
            }
        ],
        '56': [
            '56px',
            {
                lineHeight: '56px',
                letterSpacing: '-3.36px'
            }
        ],
        '64': [
            '64px',
            {
                lineHeight: '64px',
                letterSpacing: '-3.84px'
            }
        ]
    },
    spacing: {
        '8': '32px',
        '10': '40px',
        '16': '64px',
        '20': '80px',
        '52': '208px',
        '64': '256px',
        '69': '276px',
        '1px': '1px'
    },
    borderRadius: {
        xs: '2px',
        md: '6px',
        lg: '12px'
    },
    boxShadow: {
        sm: 'rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0.08) 0px 0px 0px 1px, rgba(0, 0, 0, 0.02) 0px 1px 1px 0px, rgba(0, 0, 0, 0.04) 0px 4px 8px 0px, rgb(250, 250, 250) 0px 0px 0px 1px, rgb(255, 255, 255) 0px 0px 0px 1px'
    },
    screens: {
        sm: '470px',
        md: '769px',
        lg: '1036px',
        '1151px': '1151px',
        '1200px': '1200px',
        '2300px': '2300px'
    },
    transitionDuration: {
        '100': '0.1s',
        '150': '0.15s',
        '200': '0.2s',
        '250': '0.25s',
        '300': '0.3s',
        '400': '0.4s',
        '500': '0.5s',
        '700': '0.7s',
        '1000': '1s',
        '1200': '1.2s'
    },
    transitionTimingFunction: {
        custom: 'cubic-bezier(0.3, 0.57, 0.07, 0.95)',
        linear: 'linear'
    },
    container: {
        center: true,
        padding: '0px'
    },
    maxWidth: {
        container: '1280px'
    }
},
  },
};
