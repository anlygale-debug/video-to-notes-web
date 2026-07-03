// React Theme — extracted from https://vercel.com
// Compatible with: Chakra UI, Stitches, Vanilla Extract, or any CSS-in-JS

/**
 * TypeScript type definition for this theme:
 *
 * interface Theme {
 *   colors: {
    primary: string;
    background: string;
    foreground: string;
    neutral50: string;
    neutral100: string;
    neutral200: string;
    neutral300: string;
    neutral400: string;
    neutral500: string;
    neutral600: string;
    neutral700: string;
    neutral800: string;
    neutral900: string;
 *   };
 *   fonts: {
    body: string;
    mono: string;
 *   };
 *   fontSizes: {
    '8': string;
    '12': string;
    '13': string;
    '14': string;
    '16': string;
    '20': string;
    '22': string;
    '24': string;
    '30': string;
    '56': string;
    '64': string;
 *   };
 *   space: {
    '1': string;
    '32': string;
    '40': string;
    '64': string;
    '80': string;
    '208': string;
    '256': string;
    '276': string;
 *   };
 *   radii: {
    xs: string;
    md: string;
    lg: string;
 *   };
 *   shadows: {
    sm: string;
 *   };
 *   states: {
 *     hover: { opacity: number };
 *     focus: { opacity: number };
 *     active: { opacity: number };
 *     disabled: { opacity: number };
 *   };
 * }
 */

export const theme = {
  "colors": {
    "primary": "#0070f3",
    "background": "#fafafa",
    "foreground": "#171717",
    "neutral50": "#ebebeb",
    "neutral100": "#171717",
    "neutral200": "#4d4d4d",
    "neutral300": "#666666",
    "neutral400": "#ffffff",
    "neutral500": "#8f8f8f",
    "neutral600": "#a8a8a8",
    "neutral700": "#000000",
    "neutral800": "#7d7d7d",
    "neutral900": "#383838"
  },
  "fonts": {
    "body": "'GeistSans', sans-serif",
    "mono": "'Geist Mono', monospace"
  },
  "fontSizes": {
    "8": "8px",
    "12": "12px",
    "13": "13px",
    "14": "14px",
    "16": "16px",
    "20": "20px",
    "22": "22px",
    "24": "24px",
    "30": "30px",
    "56": "56px",
    "64": "64px"
  },
  "space": {
    "1": "1px",
    "32": "32px",
    "40": "40px",
    "64": "64px",
    "80": "80px",
    "208": "208px",
    "256": "256px",
    "276": "276px"
  },
  "radii": {
    "xs": "2px",
    "md": "6px",
    "lg": "12px"
  },
  "shadows": {
    "sm": "rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0.08) 0px 0px 0px 1px, rgba(0, 0, 0, 0.02) 0px 1px 1px 0px, rgba(0, 0, 0, 0.04) 0px 4px 8px 0px, rgb(250, 250, 250) 0px 0px 0px 1px, rgb(255, 255, 255) 0px 0px 0px 1px"
  },
  "states": {
    "hover": {
      "opacity": 0.08
    },
    "focus": {
      "opacity": 0.12
    },
    "active": {
      "opacity": 0.16
    },
    "disabled": {
      "opacity": 0.38
    }
  }
};

// MUI v5 theme
export const muiTheme = {
  "palette": {
    "primary": {
      "main": "#0070f3",
      "light": "hsl(212, 100%, 63%)",
      "dark": "hsl(212, 100%, 33%)"
    },
    "background": {
      "default": "#fafafa",
      "paper": "#f4f4f4"
    },
    "text": {
      "primary": "#171717",
      "secondary": "#0072f5"
    }
  },
  "typography": {
    "h1": {
      "fontSize": "56px",
      "fontWeight": "450",
      "lineHeight": "56px"
    },
    "h2": {
      "fontSize": "24px",
      "fontWeight": "400",
      "lineHeight": "32px"
    },
    "h3": {
      "fontSize": "20px",
      "fontWeight": "400",
      "lineHeight": "28px"
    }
  },
  "shape": {
    "borderRadius": 6
  },
  "shadows": [
    "rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgb(255, 255, 255) 0px 0px 0px 2px, rgb(0, 114, 245) 0px 0px 0px 4px",
    "rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0.08) 0px 1px 0px 0px",
    "rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0.04) 0px 2px 2px 0px, rgba(0, 0, 0, 0.04) 0px 8px 16px -4px",
    "rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0.1) 0px 1px 0px 0px",
    "rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgb(235, 235, 235) 0px 0px 0px 1px"
  ]
};

export default theme;
