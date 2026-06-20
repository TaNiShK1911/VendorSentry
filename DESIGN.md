---
name: Institutional Excellence
colors:
  surface: '#f9f9f9'
  surface-dim: '#dadada'
  surface-bright: '#f9f9f9'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f3f3f4'
  surface-container: '#eeeeee'
  surface-container-high: '#e8e8e8'
  surface-container-highest: '#e2e2e2'
  on-surface: '#1a1c1c'
  on-surface-variant: '#5d403b'
  inverse-surface: '#2f3131'
  inverse-on-surface: '#f0f1f1'
  outline: '#916f6a'
  outline-variant: '#e6bdb7'
  surface-tint: '#be0a0a'
  primary: '#bb0507'
  on-primary: '#ffffff'
  primary-container: '#e02b20'
  on-primary-container: '#fffcff'
  inverse-primary: '#ffb4a9'
  secondary: '#5e5e5e'
  on-secondary: '#ffffff'
  secondary-container: '#e2e2e2'
  on-secondary-container: '#646464'
  tertiary: '#00609d'
  on-tertiary: '#ffffff'
  tertiary-container: '#0079c5'
  on-tertiary-container: '#fefcff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ffdad5'
  primary-fixed-dim: '#ffb4a9'
  on-primary-fixed: '#410000'
  on-primary-fixed-variant: '#930003'
  secondary-fixed: '#e2e2e2'
  secondary-fixed-dim: '#c6c6c6'
  on-secondary-fixed: '#1b1b1b'
  on-secondary-fixed-variant: '#474747'
  tertiary-fixed: '#d0e4ff'
  tertiary-fixed-dim: '#9ccaff'
  on-tertiary-fixed: '#001d35'
  on-tertiary-fixed-variant: '#00497a'
  background: '#f9f9f9'
  on-background: '#1a1c1c'
  surface-variant: '#e2e2e2'
  surface-muted: '#F4F4F4'
  border-subtle: '#BDBDBD'
  data-neutral: '#666666'
typography:
  headline-xl:
    fontFamily: Montserrat
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Montserrat
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Montserrat
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-lg:
    fontFamily: Source Sans 3
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Source Sans 3
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-md:
    fontFamily: Source Sans 3
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
  label-sm:
    fontFamily: Source Sans 3
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
  headline-lg-mobile:
    fontFamily: Montserrat
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 34px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 8px
  gutter: 24px
  margin-desktop: 64px
  margin-mobile: 16px
  container-max: 1280px
---

## Brand & Style
The design system is rooted in the principles of mathematical precision, structural integrity, and institutional trust. It is designed for a global financial audience that demands clarity, reliability, and professional rigor. 

The aesthetic is **Corporate / Modern**, characterized by a high-contrast palette and a rigid adherence to geometric alignment. Drawing inspiration from the brand's iconic square motif, the UI utilizes a "modular block" philosophy where information is organized into clear, distinct zones. This approach creates a sense of stability and transparency, essential for high-stakes financial services. The visual narrative avoids unnecessary ornamentation, favoring bold strokes and purposeful whitespace to drive focus toward data and decision-making.

## Colors
The color strategy is built upon a commanding triad of Red, Black, and White. This high-contrast palette ensures immediate brand recognition and establishes a clear visual hierarchy.

- **Primary Red:** Used strategically for primary actions, critical alerts, and brand accents. It represents energy and leadership.
- **Secondary Black:** Used for typography, structural borders, and the "lower half" of modular motifs, grounding the design with authority.
- **Neutrals:** A pure white base is supplemented by light grays for background layering and subtle borders, maintaining a clean, "paper-like" institutional feel.

Color application must follow a disciplined ratio: heavy use of white space, punctuated by black structural elements, with red reserved for the most important interactive focal points.

## Typography
The typographic system utilizes two distinct sans-serif families to balance brand character with functional legibility.

**Montserrat** is the display face. Its geometric construction mirrors the square motif of the brand. It should be used for headlines and prominent titles, typically in bold weights to convey strength and confidence.

**Source Sans 3** is the workhorse typeface. It provides exceptional clarity for body copy, data tables, and complex financial forms. It feels professional and unobtrusive, allowing the user to process information without friction.

Key principles:
- Use **All-Caps** for labels and utility links to reinforce the architectural feel.
- Maintain generous line heights in body text to ensure readability of dense financial disclosures.
- Headlines should utilize tight letter-spacing for a modern, impactful look.

## Layout & Spacing
This design system employs a **Fixed Grid** model for desktop to maintain a sense of structured permanence. The layout is governed by a strict 8px base unit, ensuring all components and containers align perfectly to a mathematical rhythm.

- **Desktop:** A 12-column grid with 24px gutters. Content is centered within a 1280px container.
- **Tablet:** An 8-column grid with 20px gutters and 32px side margins.
- **Mobile:** A 4-column fluid grid with 16px margins.

The "Square Motif" should be reflected in the layout through the use of 1:1 aspect ratio containers for icons or decorative brand elements, and through the intentional use of thick horizontal dividers that separate major content sections, echoing the bar in the brand logo.

## Elevation & Depth
In keeping with a professional financial aesthetic, the design system avoids heavy shadows or skeuomorphic depth. Instead, it utilizes **Tonal Layers** and **Bold Borders** to establish hierarchy.

- **Level 0 (Base):** Pure white background.
- **Level 1 (Containers):** Subtle light-gray surfaces (`#F4F4F4`) or thin 1px black borders are used to define cards and sections.
- **Active State:** A slight "lift" is achieved using a very tight, low-opacity neutral shadow (4px blur, 10% opacity) or a 2px red accent border on the left or bottom edge.

The goal is an "architectural" depth—stacking flat planes rather than floating elements. This reinforces the feeling of a solid, grounded platform.

## Shapes
The shape language is predominantly **geometric and rectilinear**. While the core logo is a perfect square with sharp 90-degree angles, the UI adopts a "Soft" (0.25rem) corner radius for interactive components to provide a subtle modern refinement and improve touch-target perception.

- **Buttons & Inputs:** Consistent 4px (Soft) radius.
- **Cards:** Sharp corners (0px) are preferred for large layout containers to maintain the institutional "block" aesthetic, while smaller nested components can use the 4px radius.
- **Icons:** Must be contained within square bounding boxes to maintain visual alignment with the brand motif.

## Components

### Buttons
- **Primary:** Solid Red background with White text. Sharp or slightly rounded (4px) rectangular shape.
- **Secondary:** Solid Black background with White text.
- **Tertiary/Ghost:** 1px Black or Red border with matching text. No background fill until hover.

### Input Fields
Inputs are rectangular with a 1px border (`#BDBDBD`). Upon focus, the border shifts to Black or Red with a 2px thickness. Labels are always positioned above the field in uppercase Source Sans 3.

### Cards
Cards are flat containers. Use a 1px `#BDBDBD` border for standard information and a thicker 4px Red top-border for "Featured" or "Action Required" states.

### Chips & Tags
Small, rectangular tags with no roundedness or 2px radius. Use light gray backgrounds for neutral data and primary red for "New" or "Urgent" status indicators.

### The Square Motif Accent
Incorporate a decorative "SG Square" (a square split horizontally into red and black) as a bullet point in lists or as a corner accent in primary cards to reinforce brand identity throughout the journey.