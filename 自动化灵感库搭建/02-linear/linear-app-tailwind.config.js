/** @type {import('tailwindcss').Config} */
export default {
  theme: {
    extend: {
    colors: {
        primary: {
            '50': 'hsl(64, 89%, 97%)',
            '100': 'hsl(64, 89%, 94%)',
            '200': 'hsl(64, 89%, 86%)',
            '300': 'hsl(64, 89%, 76%)',
            '400': 'hsl(64, 89%, 64%)',
            '500': 'hsl(64, 89%, 50%)',
            '600': 'hsl(64, 89%, 40%)',
            '700': 'hsl(64, 89%, 32%)',
            '800': 'hsl(64, 89%, 24%)',
            '900': 'hsl(64, 89%, 16%)',
            '950': 'hsl(64, 89%, 10%)',
            DEFAULT: '#e4f222'
        },
        secondary: {
            '50': 'hsl(234, 56%, 97%)',
            '100': 'hsl(234, 56%, 94%)',
            '200': 'hsl(234, 56%, 86%)',
            '300': 'hsl(234, 56%, 76%)',
            '400': 'hsl(234, 56%, 64%)',
            '500': 'hsl(234, 56%, 50%)',
            '600': 'hsl(234, 56%, 40%)',
            '700': 'hsl(234, 56%, 32%)',
            '800': 'hsl(234, 56%, 24%)',
            '900': 'hsl(234, 56%, 16%)',
            '950': 'hsl(234, 56%, 10%)',
            DEFAULT: '#5e6ad2'
        },
        accent: {
            '50': 'hsl(121, 100%, 97%)',
            '100': 'hsl(121, 100%, 94%)',
            '200': 'hsl(121, 100%, 86%)',
            '300': 'hsl(121, 100%, 76%)',
            '400': 'hsl(121, 100%, 64%)',
            '500': 'hsl(121, 100%, 50%)',
            '600': 'hsl(121, 100%, 40%)',
            '700': 'hsl(121, 100%, 32%)',
            '800': 'hsl(121, 100%, 24%)',
            '900': 'hsl(121, 100%, 16%)',
            '950': 'hsl(121, 100%, 10%)',
            DEFAULT: '#00ff05'
        },
        'neutral-50': '#f7f8f8',
        'neutral-100': '#62666d',
        'neutral-200': '#d0d6e0',
        'neutral-300': '#e2e4e7',
        'neutral-400': '#8a8f98',
        'neutral-500': '#08090a',
        'neutral-600': '#23252a',
        'neutral-700': '#000000',
        'neutral-800': '#383b3f',
        'neutral-900': '#121414',
        background: '#08090a',
        foreground: '#f7f8f8'
    },
    fontFamily: {
        sans: [
            'Inter Variable',
            'sans-serif'
        ],
        body: [
            'Berkeley Mono',
            'sans-serif'
        ]
    },
    fontSize: {
        '11': [
            '11px',
            {
                lineHeight: '15.4px'
            }
        ],
        '12': [
            '12px',
            {
                lineHeight: '16.8px'
            }
        ],
        '13': [
            '13px',
            {
                lineHeight: '19.5px'
            }
        ],
        '14': [
            '14px',
            {
                lineHeight: '21px'
            }
        ],
        '15': [
            '15px',
            {
                lineHeight: '24px',
                letterSpacing: '-0.165px'
            }
        ],
        '16': [
            '16px',
            {
                lineHeight: 'normal'
            }
        ],
        '17': [
            '17px',
            {
                lineHeight: '27.2px'
            }
        ],
        '18': [
            '18px',
            {
                lineHeight: '28.8px',
                letterSpacing: '-0.165px'
            }
        ],
        '20': [
            '20px',
            {
                lineHeight: '26.6px',
                letterSpacing: '-0.24px'
            }
        ],
        '24': [
            '24px',
            {
                lineHeight: '31.92px',
                letterSpacing: '-0.288px'
            }
        ],
        '32': [
            '32px',
            {
                lineHeight: '36px',
                letterSpacing: '-0.704px'
            }
        ],
        '40': [
            '40px',
            {
                lineHeight: '44px',
                letterSpacing: '-0.88px'
            }
        ],
        '48': [
            '48px',
            {
                lineHeight: '48px',
                letterSpacing: '-1.056px'
            }
        ],
        '64': [
            '64px',
            {
                lineHeight: '64px',
                letterSpacing: '-1.408px'
            }
        ],
        '13.3333': [
            '13.3333px',
            {
                lineHeight: 'normal'
            }
        ]
    },
    spacing: {
        '0': '1px',
        '1': '39px',
        '2': '47px',
        '3': '51px',
        '4': '56px',
        '5': '69px',
        '6': '79px',
        '7': '91px',
        '8': '95px',
        '9': '99px',
        '10': '111px',
        '11': '123px',
        '12': '127px',
        '13': '131px',
        '14': '135px',
        '15': '152px',
        '16': '155px',
        '17': '159px',
        '18': '166px',
        '19': '199px',
        '20': '203px',
        '21': '212px',
        '22': '216px',
        '23': '220px',
        '24': '224px',
        '25': '282px',
        '26': '375px',
        '27': '385px',
        '28': '450px'
    },
    borderRadius: {
        xs: '1px',
        sm: '4px',
        md: '7px',
        lg: '16px',
        xl: '20px',
        full: '9999px'
    },
    boxShadow: {
        sm: 'rgba(0, 0, 0, 0.4) 0px 2px 4px 0px',
        xs: 'rgba(0, 0, 0, 0.03) 0px 1.2px 0px 0px',
        md: 'rgba(0, 0, 0, 0.2) 0px 0px 12px 0px inset',
        xl: 'rgba(8, 9, 10, 0.6) 0px 4px 32px 0px'
    },
    screens: {
        sm: '641px',
        md: '769px',
        lg: '1025px',
        xl: '1281px',
        '2xl': '1536px'
    },
    transitionDuration: {
        '100': '0.1s',
        '160': '0.16s',
        '200': '0.2s',
        '400': '0.4s'
    },
    transitionTimingFunction: {
        custom: 'cubic-bezier(0.25, 0.46, 0.45, 0.94)',
        default: 'ease'
    },
    container: {
        center: true,
        padding: '10px'
    },
    maxWidth: {
        container: '1364px'
    }
},
  },
};
