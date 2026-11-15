# Outlogik brand assets

Everything the app and the marketing site use is vector, in [`frontend/brand/assets/`](../../frontend/brand/assets/) (logos in `logo/`, favicons and home-screen icons in `icons/`). Both sites serve the logos at `/brand/…` and the icons at the site root.
The first concept artwork (2026-11-14) is kept in [`source/`](source/) for reference only. Its
wordmark is **not** used: it closely resembled Logitech's.

| File | Use |
|---|---|
| `outlogik-logo.svg` | Full logo in `currentColor`, for inline use where the theme sets the color |
| `outlogik-logo-on-light.svg` / `-on-dark.svg` | Full logo with fixed colors, for `<img>`, emails and documents |
| `outlogik-symbol.svg` (+ `-on-light` / `-on-dark`) | Symbol only, e.g. the collapsed sidebar (32 px and up) |
| `outlogik-symbol-small.svg` | Symbol for 16–24 px: heavier stroke and dot so it stays legible |
| `icons/favicon.svg`, `icons/favicon.ico`, `icons/apple-touch-icon.png`, `icons/outlogik-icon-512.png` | Browser and home-screen icons |

## Colors

The brand is monochrome. These are the marketing website spec's colours (§2), defined once in
[`frontend/brand/scss/_palette.scss`](../../frontend/brand/scss/_palette.scss) and used by both sites.

| Name | Value | Used for |
|---|---|---|
| Black | `#000000` | Logo on light, primary buttons, headings |
| White | `#FFFFFF` | Backgrounds, logo on dark |
| Dark charcoal | `#171717` | Body text; dark-mode surfaces |
| Dark grey | `#333333` | Secondary text; dark-mode borders |
| Medium grey | `#737373` | Muted text (4.7:1 on white) |
| Light grey | `#E5E5E5` | Borders, dividers |
| Off-white | `#FAFAFA` | Alternate backgrounds, sidebar |

Status colours (success, warning, danger) appear only for status, always with a label or icon.

## How the vectors were made

- **Symbol:** redrawn from measured geometry rather than traced, so curves are exact. With
  the ring radius as 1: stroke 0.072; the long arc runs clockwise from 51° to 296° and the
  short arc from −22° to 40° (0° = 3 o'clock); the dot (radius 0.19) sits on the ring at −44.5°.
- **Wordmark:** "Outlogik" set in **Albert Sans Regular** (SIL Open Font License 1.1) with
  the font's own kerning and tracking −0.005 em, then converted to outlines, so the logo
  files need no font. Cap height is 0.62× the ring diameter, centred on the ring; the gap
  between symbol and wordmark is 0.79× the ring radius.
- Chosen to stay clearly apart from Logitech's wordmark: grotesque rather than geometric
  letters, and a single-storey "g" with a straight stem and short flat tail.
- Rebuild with [`tools/build_wordmark.py`](tools/build_wordmark.py), then
  [`tools/build_logos.py`](tools/build_logos.py).
- The small-size symbol is an optical adjustment for icons, not a different mark: stroke
  0.17, dot 0.27, gaps a few degrees wider.

## Usage

- Keep clear space around the logo of at least the dot's diameter.
- Use the full logo from 96 px wide; below that use the symbol. Below 24 px use the small-size symbol.
- Don't recolor the logo outside the two theme colors, or add effects.
- Never retype the wordmark in live text; always use the SVG.

## Typeface

**Albert Sans** (SIL OFL 1.1) is the brand typeface, for the wordmark and the app UI. The app
bundles the font files and serves them itself (step 7). It must never load fonts, or anything
else, from Google Fonts or another third-party CDN.
