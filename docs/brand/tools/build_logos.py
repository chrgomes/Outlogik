"""Builds every logo and symbol SVG. Run build_wordmark.py first (it writes word_path.txt).

Symbol geometry is in units of the ring radius; see ../README.md."""
import math
word=open('word_path.txt').read()
def pt(cx,cy,r,deg):
    t=math.radians(deg); return cx+r*math.cos(t), cy+r*math.sin(t)
def arc(cx,cy,r,a0,a1):
    x0,y0=pt(cx,cy,r,a0); x1,y1=pt(cx,cy,r,a1)
    large=1 if (a1-a0)%360>180 else 0
    return f"M{x0:.2f} {y0:.2f}A{r:.2f} {r:.2f} 0 {large} 1 {x1:.2f} {y1:.2f}"
STROKE=0.0717; DOT_R=0.19; DOT_DIST=0.977; DOT_ANGLE=-44.5
BIG=(51,296); SMALL=(-22,40)
def symbol(cx,cy,r,fill="currentColor"):
    sw=STROKE*r; dx,dy=pt(cx,cy,DOT_DIST*r,DOT_ANGLE)
    return (f'<g fill="none" stroke="{fill}" stroke-width="{sw:.2f}">'
            f'<path d="{arc(cx,cy,r,*BIG)}"/><path d="{arc(cx,cy,r,*SMALL)}"/></g>'
            f'<circle cx="{dx:.2f}" cy="{dy:.2f}" r="{DOT_R*r:.2f}" fill="{fill}"/>')
R=94.93; CX=98.3; CY=98.5; W,H=914,198
def lockup(fill):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="Outlogik">'
            f'<title>Outlogik</title>{symbol(CX,CY,R,fill)}<path fill="{fill}" d="{word}"/></svg>\n')
def symbol_svg(fill):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" role="img" aria-label="Outlogik">'
            f'<title>Outlogik</title>{symbol(50,50,42,fill)}</svg>\n')
files={
  'outlogik-logo.svg': lockup('currentColor'),
  'outlogik-logo-on-light.svg': lockup('#000000'),
  'outlogik-logo-on-dark.svg': lockup('#FFFFFF'),
  'outlogik-symbol.svg': symbol_svg('currentColor'),
  'outlogik-symbol-on-light.svg': symbol_svg('#000000'),
  'outlogik-symbol-on-dark.svg': symbol_svg('#FFFFFF'),
  'favicon.svg': ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
    '<style>.i{color:#000000}@media (prefers-color-scheme:dark){.i{color:#FFFFFF}}</style>'
    f'<g class="i">{symbol(50,50,42)}</g></svg>\n'),
}
for k,v in files.items(): open(k,'w').write(v)

# Small-size symbol (favicons, ≤ 32 px): same shape, heavier stroke and dot so it survives
# at 16 px. The gaps are widened a little so they stay open at the heavier weight.
def symbol_small(cx,cy,r,fill="currentColor"):
    sw=0.17*r; dx,dy=pt(cx,cy,DOT_DIST*r,DOT_ANGLE)
    return (f'<g fill="none" stroke="{fill}" stroke-width="{sw:.2f}">'
            f'<path d="{arc(cx,cy,r,56,291)}"/><path d="{arc(cx,cy,r,-17,35)}"/></g>'
            f'<circle cx="{dx:.2f}" cy="{dy:.2f}" r="{0.27*r:.2f}" fill="{fill}"/>')
small={
  'favicon.svg': ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
    '<style>.i{color:#000000}@media (prefers-color-scheme:dark){.i{color:#FFFFFF}}</style>'
    f'<g class="i">{symbol_small(50,50,38)}</g></svg>\n'),
  'outlogik-symbol-small.svg': ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" role="img" aria-label="Outlogik">'
    f'<title>Outlogik</title>{symbol_small(50,50,38)}</svg>\n'),
  'icon-tile.svg': ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
    f'<rect width="100" height="100" fill="#000000"/>{symbol(50,50,30,"#FFFFFF")}</svg>\n'),
}
for k,v in small.items(): open(k,'w').write(v)
