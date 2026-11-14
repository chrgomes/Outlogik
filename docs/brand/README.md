# Outlogik brand assets

The originals supplied on 2026-11-14 are in [`source/`](source/). Everything the app uses is
vector, in [`frontend/public/brand/`](../../frontend/public/brand/).

| File | Use |
|---|---|
| `outlogik-logo.svg` | Full logo in `currentColor`, for inline use where the theme sets the color |
| `outlogik-logo-on-light.svg` / `-on-dark.svg` | Full logo with fixed colors, for `<img>`, emails and documents |
| `outlogik-symbol.svg` (+ `-on-light` / `-on-dark`) | Symbol only, e.g. the collapsed sidebar (32 px and up) |
| `outlogik-symbol-small.svg` | Symbol for 16–24 px: heavier stroke and dot so it stays legible |
| `outlogik-icon-512.png` | Square app icon (symbol on dark tile) |
| `../favicon.svg`, `../favicon.ico`, `../apple-touch-icon.png` | Browser and home-screen icons |

## Colors

The logo is monochrome. Colors sampled from the supplied artwork:

| | Background | Logo |
|---|---|---|
| Light | `#FFFFFF` | `#050505` |
| Dark | `#121212` | `#E0DFDD` (a warm off-white, not pure white) |

## How the vectors were made

- **Symbol:** redrawn from measured geometry rather than traced, so curves are exact. With
  the ring radius as 1: stroke 0.072; the long arc runs clockwise from 51° to 296° and the
  short arc from −22° to 40° (0° = 3 o'clock); the dot (radius 0.19) sits on the ring at −44.5°.
- **Wordmark:** traced from the light-background original at 4× resolution.
- Rendered back over the original, the vector logo overlaps it by 97% (the differences are
  edge anti-aliasing).
- The small-size symbol is an optical adjustment for icons, not a different mark: stroke
  0.17, dot 0.27, gaps a few degrees wider.

## Usage

- Keep clear space around the logo of at least the dot's diameter.
- Use the full logo from 96 px wide; below that use the symbol. Below 24 px use the small-size symbol.
- Don't recolor the logo outside the two theme colors, or add effects.
- The wordmark's typeface isn't identified yet. If you have the font file or its name, add it
  here so UI headings can match it.
