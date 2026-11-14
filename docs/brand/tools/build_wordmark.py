"""Build the Outlogik wordmark from Albert Sans Regular (SIL OFL 1.1) as outlined SVG paths.

Usage: python build_wordmark.py albert-sans-latin-400-normal.woff2   (writes word_path.txt)
Needs: fonttools, brotli, uharfbuzz. The font file comes from the @fontsource/albert-sans npm package."""
import io, sys
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen

FONT = sys.argv[1]
TEXT = "Outlogik"
TRACKING = -0.005   # em; a hair tighter than default for display size

f = TTFont(FONT); upm = f['head'].unitsPerEm; cap = f['OS/2'].sCapHeight
buf = io.BytesIO(); f.flavor = None; f.save(buf); data = buf.getvalue()
hbfont = hb.Font(hb.Face(data))
b = hb.Buffer(); b.add_str(TEXT); b.guess_segment_properties()
hb.shape(hbfont, b, {"kern": True, "liga": False})
gs = f.getGlyphSet(); order = f.getGlyphOrder()

# Layout matches the original lockup: ring radius 94.93 centred at (98.3, 98.5),
# caps centred on the ring, 75-unit gap between symbol and wordmark.
R, CX, CY = 94.93, 98.3, 98.5
CAP_PX = 118.0
s = CAP_PX / cap
baseline = CY + CAP_PX / 2
gap_left = CX + R + 0.0717 * R / 2 + 75

pen = SVGPathPen(gs, ntos=lambda v: f"{v:.2f}".rstrip('0').rstrip('.'))
bp = BoundsPen(gs)
x = 0
first_lsb = None
for info, pos in zip(b.glyph_infos, b.glyph_positions):
    name = order[info.codepoint]
    if first_lsb is None:
        bb = BoundsPen(gs); gs[name].draw(bb); first_lsb = bb.bounds[0]
    t = (s, 0, 0, -s, gap_left + (x + pos.x_offset - first_lsb) * s, baseline - pos.y_offset * s)
    gs[name].draw(TransformPen(pen, t)); gs[name].draw(TransformPen(bp, t))
    x += pos.x_advance + TRACKING * upm
d = pen.getCommands()
xmin, ymin, xmax, ymax = bp.bounds
print(f"wordmark bounds x {xmin:.1f}-{xmax:.1f} y {ymin:.1f}-{ymax:.1f}", file=sys.stderr)
open('word_path.txt', 'w').write(d)
open('lockup_size.txt', 'w').write(f"{max(xmax, 197):.0f} {max(ymax, 197):.0f} {min(ymin,0):.1f}")
