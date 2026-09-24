#!/usr/bin/env python3
"""
Renders every SVG in ../assets: the cyberpunk / Blade Runner art on this profile.

Text is converted to vector outlines, so the art renders the same everywhere
(GitHub serves repo SVGs under a CSP that blocks embedded fonts anyway).
Edit the copy in this file, then rebuild:

    pip install fonttools
    python build/render.py --mono "path/to/JetBrainsMono"

--mono is the folder holding JetBrainsMonoNLNerdFontMono-{Regular,Bold}.ttf
(nerdfonts.com -> JetBrainsMono). Chakra Petch and Noto Sans JP (both SIL OFL)
are fetched on first run from a pinned google/fonts commit into build/.fonts/
and checked against their SHA-256 before use.
"""
import argparse
import hashlib
import math
import random
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

from fontTools import subset
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"
CACHE = Path(__file__).resolve().parent / ".fonts"

GF = "https://raw.githubusercontent.com/google/fonts/23e54b51ddffbc7713c583748e3bd86f62b1fa4a/ofl/"
REMOTE = {
    "ChakraPetch-Bold.ttf": ("chakrapetch/ChakraPetch-Bold.ttf",
                             "65fbf76d95651697275e19db4d717c0e95a789ddd3476478b05292104db278a0"),
    "ChakraPetch-SemiBold.ttf": ("chakrapetch/ChakraPetch-SemiBold.ttf",
                                 "45264de3204ddbd5fb3e14a2402acd5c630d16650ae5fc221d2c52da46a6734b"),
    "ChakraPetch-Medium.ttf": ("chakrapetch/ChakraPetch-Medium.ttf",
                               "d480f4f97405fac3600652e2e14fd0b14339031c0af4da11582994878f04d919"),
    "NotoSansJP[wght].ttf": ("notosansjp/NotoSansJP%5Bwght%5D.ttf",
                             "c2f3b4d463500a2ddcd3849cded1fceeb9fd6d1c32e6cbecd568453ba50fc68f"),
}

# night city: near-black blues, neon cyan and magenta, 2077 yellow, 2049 amber
N = dict(
    void="#05050a", panel="#0a0a12", raised="#10101c", line="#1d1e30",
    dim="#5b5e7a", mid="#9598b3", text="#e8e8f2", white="#f6f6fc",
    cyan="#00e5ff", mag="#ff2a6d", yel="#fcee0a", amber="#ff9e3d", violet="#b8a2ff",
)

JP_TEXT = "機械学習セキュリティブレードランナー・"

BASE_CSS = """
@keyframes blink{50%{opacity:0}}
@keyframes twinkle{50%{opacity:.15}}
@keyframes flicker{0%,40%,44%,47%,77%,82%,100%{opacity:1}41%{opacity:.2}43%{opacity:.7}45%{opacity:.3}79%{opacity:.1}80%{opacity:.8}}
.blink{animation:blink 1.1s steps(1) infinite}
.twinkle{animation:twinkle 5s ease-in-out infinite}
.flicker{animation:flicker 5.5s linear infinite}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
"""


# ── fonts & outlined text ───────────────────────────────────────────────────

def fetch(name):
    """A pinned google/fonts file, verified by SHA-256 before it is trusted."""
    rel, want = REMOTE[name]
    path = CACHE / name
    if path.exists():
        data = path.read_bytes()
    else:
        print(f"  fetching {name}")
        with urllib.request.urlopen(GF + rel, timeout=120) as r:
            data = r.read()
    got = hashlib.sha256(data).hexdigest()
    if got != want:
        raise SystemExit(f"{name}: sha256 {got} does not match the pinned {want}; refusing to use it")
    if not path.exists():
        CACHE.mkdir(exist_ok=True)
        path.write_bytes(data)
    return path


class Font:
    def __init__(self, font):
        if font["head"].unitsPerEm != 1000:
            raise SystemExit("every face is assumed to be 1000 units per em")
        self.cmap = font.getBestCmap()
        self.glyphs = font.getGlyphSet()
        self.hmtx = font["hmtx"]
        self.cache = {}

    @classmethod
    def load(cls, path):
        return cls(TTFont(path))

    @classmethod
    def instance(cls, path, text, **axes):
        """Subset a variable font to `text` first, then pin its axes: much
        faster than instancing all of Noto Sans JP."""
        font = TTFont(path)
        sub = subset.Subsetter()
        sub.populate(text=text)
        sub.subset(font)
        return cls(instantiateVariableFont(font, axes))

    def glyph(self, ch):
        name = self.cmap.get(ord(ch))
        if name is None:
            raise SystemExit(f"glyph missing from font: {ch!r} U+{ord(ch):04X}")
        return name

    def adv(self, ch):
        return self.hmtx[self.glyph(ch)][0]

    def path(self, ch):
        if ch not in self.cache:
            pen = SVGPathPen(self.glyphs, ntos=lambda v: f"{v:.0f}" if v == int(v) else f"{v:.1f}")
            self.glyphs[self.glyph(ch)].draw(pen)
            self.cache[ch] = pen.getCommands()
        return self.cache[ch]


class Svg:
    def __init__(self, fonts, w, h, label):
        self.fonts, self.w, self.h, self.label = fonts, w, h, label
        self.defs, self.body, self.css = [], [], [BASE_CSS]
        self.glyph_ids = set()
        self.n = 0

    def id(self, prefix):
        self.n += 1
        return f"{prefix}{self.n}"

    def add(self, *parts):
        self.body.extend(parts)

    def gid(self, face, ch):
        gid = f"g{face}-{ord(ch):x}"
        if gid not in self.glyph_ids:
            self.defs.append(f'<path id="{gid}" d="{self.fonts[face].path(ch)}"/>')
            self.glyph_ids.add(gid)
        return gid

    def _runs(self, runs, fill, face):
        if isinstance(runs, str):
            runs = [(runs, fill)]
        return [(r[0], r[1] or fill, r[2] if len(r) > 2 else face) for r in runs]

    def measure(self, runs, size=13, face="m", track=0.0):
        runs = self._runs(runs, None, face)
        n = sum(len(t) for t, _, _ in runs)
        return sum(self.fonts[f].adv(ch) for t, _, f in runs for ch in t) * size / 1000 + track * (n - 1)

    def text(self, x, y, runs, size=13, face="m", fill=N["text"], anchor="start", track=0.0, attrs=""):
        """Draw outlined text; `runs` is a str or [(str, fill[, face])].
        Returns the drawn width in px."""
        runs = self._runs(runs, fill, face)
        width = self.measure(runs, size, face, track)
        if anchor == "middle":
            x -= width / 2
        elif anchor == "end":
            x -= width
        k = size / 1000
        out = [f'<g transform="translate({x:.1f} {y:.1f}) scale({k:g} {-k:g})"{attrs}>']
        pos = 0.0
        for s, f, fc in runs:
            uses = []
            for ch in s:
                if not ch.isspace():
                    uses.append(f'<use href="#{self.gid(fc, ch)}" x="{pos:.0f}"/>')
                pos += self.fonts[fc].adv(ch) + track * 1000 / size
            if uses:
                out.append(f'<g fill="{f}">{"".join(uses)}</g>')
        out.append("</g>")
        self.add("".join(out))
        return width

    def vtext(self, cx, y, text, size, face, fill, step=1.08, attrs=""):
        """Vertical signage: one glyph per line, centred on cx."""
        self.add(f"<g{attrs}>")
        for i, ch in enumerate(text):
            self.text(cx, y + i * size * step, ch, size=size, face=face, fill=fill, anchor="middle")
        self.add("</g>")

    def save(self, name):
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
            f'viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{escape(self.label)}">'
            f"<title>{escape(self.label)}</title>"
            f'<style>{"".join(self.css).strip()}</style>'
            f'<defs>{"".join(self.defs)}</defs>'
            f'{"".join(self.body)}</svg>'
        )
        OUT.mkdir(exist_ok=True)
        (OUT / name).write_text(svg, encoding="utf-8")
        print(f"  {name:20s} {len(svg) / 1024:6.1f} KB")


# ── shared pieces ───────────────────────────────────────────────────────────

def chamfer(x, y, w, h, tl=0, tr=0, br=0, bl=0):
    """A rectangle with cut corners — the HUD panel shape."""
    return (f"M{x + tl} {y}H{x + w - tr}L{x + w} {y + tr}V{y + h - br}"
            f"L{x + w - br} {y + h}H{x + bl}L{x} {y + h - bl}V{y + tl}Z")


def panel(s, x, y, w, h, cut=18, accent=N["cyan"], accent2=N["mag"]):
    """Dark chamfered panel with neon ticks on the two cut corners."""
    s.add(f'<path d="{chamfer(x, y, w, h, tl=cut, br=cut)}" fill="{N["panel"]}" stroke="{N["line"]}" stroke-width="1.2"/>')
    s.add(f'<path d="M{x} {y + cut + 22}V{y + cut}L{x + cut} {y}H{x + cut + 60}" fill="none" stroke="{accent}" stroke-width="2"/>')
    s.add(f'<path d="M{x + w} {y + h - cut - 22}V{y + h - cut}L{x + w - cut} {y + h}H{x + w - cut - 60}" '
          f'fill="none" stroke="{accent2}" stroke-width="2"/>')


def section_label(s, x, y, num, title, size=13):
    w = s.text(x, y, f"// {num}", size=size, face="d", fill=N["mag"], track=1.5)
    return w + s.text(x + w + 12, y, title, size=size, face="ds", fill=N["text"], track=5) + 12


def glow_filter(s, fid, *devs):
    nodes = "".join(f'<feGaussianBlur in="SourceGraphic" stdDeviation="{d}" result="b{i}"/>' for i, d in enumerate(devs))
    merge = "".join(f'<feMergeNode in="b{i}"/>' for i in reversed(range(len(devs))))
    s.defs.append(f'<filter id="{fid}" x="-60%" y="-60%" width="220%" height="220%">{nodes}'
                  f'<feMerge>{merge}<feMergeNode in="SourceGraphic"/></feMerge></filter>')


# ── hero: the city ──────────────────────────────────────────────────────────

HERO_CSS = """
@keyframes rainA{to{transform:translate(26.4px,150px)}}
@keyframes rainB{to{transform:translate(17.6px,100px)}}
@keyframes fly{to{transform:translateX(-1240px)}}
@keyframes flare{0%,100%{transform:scale(1,1);opacity:.95}18%{transform:scale(.8,1.3);opacity:1}37%{transform:scale(1.1,.85);opacity:.8}
 61%{transform:scale(.9,1.2);opacity:1}83%{transform:scale(1.05,.9);opacity:.85}}
@keyframes gc{0%,87%,100%{transform:translate(0,0)}88%{transform:translate(-5px,1px)}90%{transform:translate(4px,-1px)}92%{transform:translate(-3px,0)}94%{transform:translate(1px,1px)}}
@keyframes gm{0%,87%,100%{transform:translate(0,0)}88%{transform:translate(5px,-1px)}90%{transform:translate(-4px,1px)}92%{transform:translate(3px,0)}94%{transform:translate(-1px,-1px)}}
@keyframes slice{0%,88%,93%,100%{opacity:0;transform:translateX(0)}89%{opacity:1;transform:translateX(16px)}91%{opacity:1;transform:translateX(-11px)}}
.rainA{animation:rainA .55s linear infinite}
.rainB{animation:rainB .8s linear infinite}
.fly{animation:fly 28s linear infinite}
.flare{transform-box:fill-box;transform-origin:50% 100%;animation:flare 2.6s ease-in-out infinite}
.gc{animation:gc 6s steps(1) infinite}
.gm{animation:gm 6s steps(1) infinite}
.slice{animation:slice 6s steps(1) infinite}
"""

SKEW = math.tan(math.radians(10))  # rain falls 10° off vertical


def skyline(rnd, x0, x1, base, height, wmin, wmax, gap=(1, 8)):
    """Boxes (x, y, w, h) marching left to right; `height(x)` picks the range."""
    boxes, x = [], x0
    while x < x1:
        w = rnd.uniform(wmin, wmax)
        lo, hi = height(x)
        h = rnd.uniform(lo, hi)
        boxes.append((x, base - h, w, h))
        x += w + rnd.uniform(*gap)
    return boxes


def draw_buildings(s, rnd, boxes, base, fill, antenna_light=False):
    d, beacons = [], []
    for x, y, w, h in boxes:
        d.append(f"M{x:.1f} {y:.1f}h{w:.1f}V{base}h{-w:.1f}Z")
        if rnd.random() < .45 and w > 22:  # setback on the roof
            rw, rh = w * rnd.uniform(.35, .6), rnd.uniform(8, 22)
            rx = x + rnd.uniform(0, w - rw)
            d.append(f"M{rx:.1f} {y - rh:.1f}h{rw:.1f}v{rh + 1:.1f}h{-rw:.1f}Z")
            y -= rh
        if rnd.random() < .3:  # antenna
            ax, ah = x + rnd.uniform(.2, .8) * w, rnd.uniform(10, 26)
            d.append(f"M{ax:.1f} {y - ah:.1f}h1.4V{y + 1:.1f}h-1.4Z")
            if antenna_light:
                beacons.append((ax + .7, y - ah))
    s.add(f'<path d="{"".join(d)}" fill="{fill}"/>')
    for bx, by in beacons:
        s.add(f'<circle class="blink" style="animation-duration:{rnd.uniform(1.6, 3.2):.1f}s" '
              f'cx="{bx:.1f}" cy="{by:.1f}" r="1.4" fill="{N["mag"]}"/>')


def draw_lights(s, rnd, boxes, density, palette, twinkle=.06):
    """Lit windows, batched into one path per colour so the file stays small."""
    static = {}
    for x, y, w, h in boxes:
        for wy in range(int(y + 6), int(y + h - 4), 7):
            for wx in range(int(x + 4), int(x + w - 4), 6):
                if rnd.random() >= density:
                    continue
                col, op = rnd.choice(palette)
                if rnd.random() < twinkle:
                    s.add(f'<rect class="twinkle" style="animation-duration:{rnd.uniform(3, 9):.1f}s;'
                          f'animation-delay:-{rnd.uniform(0, 9):.1f}s" x="{wx}" y="{wy}" width="2.4" height="3.2" '
                          f'fill="{col}" opacity="{op}"/>')
                else:
                    static.setdefault((col, op), []).append(f"M{wx} {wy}h2.4v3.2h-2.4z")
    for (col, op), d in static.items():
        s.add(f'<path d="{"".join(d)}" fill="{col}" opacity="{op}"/>')


def rain(s, pid, rnd, tile, n, lmin, lmax, color, op, width, cls, W, H):
    """Vertical streaks in a pattern skewed 10°; moving the layer by one skewed
    tile loops seamlessly."""
    d = []
    for _ in range(n):
        x, y, L = rnd.uniform(0, tile), rnd.uniform(0, tile), rnd.uniform(lmin, lmax)
        for oy in (0, -tile):  # wrap streaks that run off the bottom edge
            d.append(f"M{x:.1f} {y + oy:.1f}v{L:.1f}")
    s.defs.append(f'<pattern id="{pid}" width="{tile}" height="{tile}" patternUnits="userSpaceOnUse" '
                  f'patternTransform="skewX(10)"><path d="{"".join(d)}" stroke="{color}" stroke-opacity="{op}" '
                  f'stroke-width="{width}" stroke-linecap="round"/></pattern>')
    s.add(f'<rect class="{cls}" x="-120" y="{-tile - 10}" width="{W + 240}" height="{H + tile + 20}" fill="url(#{pid})"/>')


def hero(fonts):
    W, H = 1000, 440
    rnd = random.Random(2019)
    s = Svg(fonts, W, H, "A neon city at night in the rain: Mann Kuvadiya, machine learning × security, Mumbai. "
                         "Kanji and katakana neon signs read 'machine learning' and 'security'.")
    s.css.append(HERO_CSS)
    frame = chamfer(0, 0, W, H, tl=28, br=28)
    s.defs.append(
        f'<clipPath id="frame"><path d="{frame}"/></clipPath>'
        '<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#04040b"/><stop offset=".36" stop-color="#0c0820"/>'
        '<stop offset=".6" stop-color="#231040"/><stop offset=".74" stop-color="#4b1646"/>'
        '<stop offset=".84" stop-color="#7a2440"/><stop offset="1" stop-color="#1a0812"/></linearGradient>'
        f'<radialGradient id="haze"><stop offset="0" stop-color="{N["amber"]}" stop-opacity=".42"/>'
        f'<stop offset="1" stop-color="{N["amber"]}" stop-opacity="0"/></radialGradient>'
        f'<radialGradient id="haze2"><stop offset="0" stop-color="{N["mag"]}" stop-opacity=".25"/>'
        f'<stop offset="1" stop-color="{N["mag"]}" stop-opacity="0"/></radialGradient>'
        '<linearGradient id="pyr" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3c1b44"/>'
        '<stop offset="1" stop-color="#1b0c28"/></linearGradient>'
        '<radialGradient id="flame" cy=".7"><stop offset="0" stop-color="#fff3c4"/>'
        f'<stop offset=".35" stop-color="{N["amber"]}"/><stop offset="1" stop-color="#ff4d1a" stop-opacity="0"/></radialGradient>'
        f'<radialGradient id="flarehalo"><stop offset="0" stop-color="{N["amber"]}" stop-opacity=".35"/>'
        f'<stop offset="1" stop-color="{N["amber"]}" stop-opacity="0"/></radialGradient>'
        '<linearGradient id="fog" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#05050a" stop-opacity="0"/>'
        '<stop offset="1" stop-color="#05050a" stop-opacity=".85"/></linearGradient>'
        '<linearGradient id="farfog" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#4b1646" stop-opacity="0"/>'
        '<stop offset="1" stop-color="#4b1646" stop-opacity=".45"/></linearGradient>'
        '<linearGradient id="trail" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity=".7"/>'
        '<stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        '<pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="1.2" fill="#000"/></pattern>'
        '<radialGradient id="vignette" r=".75"><stop offset=".55" stop-color="#000" stop-opacity="0"/>'
        '<stop offset="1" stop-color="#000" stop-opacity=".7"/></radialGradient>'
    )
    glow_filter(s, "neon", 2, 7)
    glow_filter(s, "soft", 9)
    s.defs.append('<filter id="blur" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="3"/></filter>')

    s.add('<g clip-path="url(#frame)">')
    s.add(f'<rect width="{W}" height="{H}" fill="url(#sky)"/>')
    s.add('<ellipse cx="760" cy="340" rx="420" ry="170" fill="url(#haze)"/>')
    s.add('<ellipse cx="180" cy="370" rx="320" ry="120" fill="url(#haze2)"/>')

    # far: a pyramid arcology, gas flares, hazy blocks
    s.add('<path d="M800 200L960 350H640Z" fill="url(#pyr)"/>')
    pyr = []
    for r in range(9):
        y = 214 + r * 14
        half = (y - 200) * 160 / 150
        for x in range(int(800 - half + 4), int(800 + half - 3), 6):
            if rnd.random() < .38:
                pyr.append(f"M{x} {y}h2v1.6h-2z")
    s.add(f'<path d="{"".join(pyr)}" fill="{N["amber"]}" opacity=".55"/>')
    far = skyline(rnd, -10, W + 10, H, lambda x: (95, 145) if x < 560 else (115, 185), 22, 58)
    draw_buildings(s, rnd, far, H, "#1c0d2b")
    for fx, top, dur in ((590, 262, 2.3), (962, 246, 3.1)):
        s.add(f'<rect x="{fx - 3}" y="{top}" width="6" height="{H - top}" fill="#170a22"/>')
        s.add(f'<circle cx="{fx}" cy="{top - 10}" r="46" fill="url(#flarehalo)"/>')
        s.add(f'<ellipse class="flare" style="animation-duration:{dur}s" cx="{fx}" cy="{top - 14}" rx="7" ry="16" '
              f'fill="url(#flame)" filter="url(#blur)"/>')
    s.add(f'<rect y="240" width="{W}" height="{H - 240}" fill="url(#farfog)"/>')

    # mid
    mid = skyline(rnd, -10, W + 10, H, lambda x: (55, 105) if x < 560 else (85, 150), 18, 46)
    draw_buildings(s, rnd, mid, H, "#0e0718", antenna_light=True)
    draw_lights(s, rnd, mid, .09, [("#ffb867", .55), ("#ffb867", .35), ("#6ff0ff", .45)])

    # near, with two towers carrying the neon
    near = skyline(rnd, -10, W + 10, H, lambda x: (28, 70) if x < 560 else (45, 110), 26, 70, gap=(0, 4))
    towers = [(612, 236, 74, H - 236), (866, 210, 80, H - 210)]
    draw_buildings(s, rnd, near, H, "#060509")
    s.add("".join(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#060509"/>' for x, y, w, h in towers))
    draw_lights(s, rnd, near + towers, .045, [("#ffb867", .5), ("#6ff0ff", .5), ("#ff5c8a", .45)])
    for (x, y, w, h), text, col, flick in ((towers[0], "機械学習", N["cyan"], False),
                                           (towers[1], "セキュリティ", N["mag"], True)):
        size = 21
        sw, sh = 36, len(text) * size * 1.08 + 18
        sx, sy = x + (w - sw) / 2, y + 22
        s.add(f'<g{" class=" + chr(34) + "flicker" + chr(34) if flick else ""}>')
        s.add(f'<rect x="{sx:.1f}" y="{sy}" width="{sw}" height="{sh:.1f}" fill="#0b0610" stroke="{col}" '
              f'stroke-opacity=".7" filter="url(#neon)"/>')
        s.vtext(x + w / 2, sy + 9 + size * .86, text, size, "jp", col, attrs=' filter="url(#neon)"')
        s.add("</g>")
    s.add(f'<rect y="300" width="{W}" height="{H - 300}" fill="url(#fog)"/>')

    # a spinner crossing the sky
    s.add(f'<g class="fly"><g transform="translate({W + 80} 84)">'
          '<path d="M6 0H70" stroke="url(#trail)" stroke-width="1.3"/>'
          f'<ellipse rx="8" ry="2.6" fill="#0d0d16" stroke="{N["mid"]}" stroke-opacity=".5" stroke-width=".6"/>'
          '<circle cx="-7" cy="0" r="1.8" fill="#fff" filter="url(#neon)"/>'
          f'<circle class="blink" cx="5" cy="-1.5" r="1.3" fill="{N["mag"]}"/></g></g>')

    rain(s, "rainB", rnd, 100, 9, 6, 14, "#9fe8ff", .16, .7, "rainB", W, H)

    # identity
    x0, ny = 56, 176
    s.text(x0, 98, [("// ", N["mag"]), ("SYS.ID — BLADEKILLER246", N["mid"])], size=11.5, track=2.5)
    name, nsize = "MANN KUVADIYA", 62
    nw = s.measure(name, nsize, "d", 2)
    if nw > 560:
        raise SystemExit(f"hero name is {nw:.0f}px wide; the sky holds 560")
    s.add('<g opacity=".45" filter="url(#soft)">')
    s.text(x0, ny, name, size=nsize, face="d", fill=N["cyan"], track=2)
    s.add("</g>")
    s.add('<g class="gc" opacity=".9">')
    s.text(x0 - 2.5, ny, name, size=nsize, face="d", fill=N["cyan"], track=2)
    s.add('</g><g class="gm" opacity=".9">')
    s.text(x0 + 2.5, ny, name, size=nsize, face="d", fill=N["mag"], track=2)
    s.add("</g>")
    s.text(x0, ny, name, size=nsize, face="d", fill=N["white"], track=2)
    s.defs.append(f'<clipPath id="band"><rect x="{x0 - 30}" y="{ny - 32}" width="{nw + 60:.0f}" height="10"/></clipPath>')
    s.add('<g clip-path="url(#band)"><g class="slice">')
    s.text(x0, ny, name, size=nsize, face="d", fill=N["cyan"], track=2)
    s.add("</g></g>")
    s.text(x0, ny + 40, "MACHINE LEARNING × SECURITY", size=16, face="ds", fill=N["cyan"], track=6)
    s.text(x0, ny + 68, [("MUMBAI, IN", N["text"]), ("   N 19.07°  E 72.87°", N["dim"])], size=12, track=2)

    rain(s, "rainA", rnd, 150, 7, 12, 26, "#c4f3ff", .24, 1, "rainA", W, H)

    # HUD
    c, L = 16, 26
    hud = [f"M{c} {c + L}V{c}H{c + L}", f"M{W - c - L} {c}H{W - c}V{c + L}",
           f"M{c} {H - c - L}V{H - c}H{c + L}", f"M{W - c - L} {H - c}H{W - c}V{H - c - L}"]
    s.add(f'<path d="{"".join(hud)}" fill="none" stroke="{N["cyan"]}" stroke-opacity=".6" stroke-width="1.5"/>')
    w = s.text(W - 44, 46, "2077", size=11.5, fill=N["dim"], anchor="end", track=2)
    s.text(W - 44 - w - 10, 46, "ブレードランナー", size=12, face="jp", fill=N["mag"], anchor="end", track=1)
    s.add(f'<circle class="blink" cx="{c + 26}" cy="{H - 42}" r="3" fill="{N["cyan"]}"/>')
    s.text(c + 36, H - 38, "SIGNAL · ONLINE", size=11, fill=N["mid"], track=2.5)

    s.add(f'<rect width="{W}" height="{H}" fill="url(#scan)" opacity=".14"/>')
    s.add(f'<rect width="{W}" height="{H}" fill="url(#vignette)"/>')
    s.add("</g>")
    s.add(f'<path d="{frame}" fill="none" stroke="{N["cyan"]}" stroke-opacity=".35" stroke-width="1.5"/>')
    s.save("hero.svg")


# ── dossier ─────────────────────────────────────────────────────────────────

DOSSIER = [
    ("SUBJECT", [("MANN KUVADIYA", N["white"], "d")]),
    ("ALIAS", [("BLADERUNNER2077", N["mag"])]),
    ("CLASS", [("B.TECH IT · HONOURS IN CYBER SECURITY · '28", None)]),
    ("ORIGIN", [("KJSCE, SOMAIYA VIDYAVIHAR · MUMBAI", None)]),
    ("FUNCTION", [("MACHINE LEARNING × OFFENSIVE SECURITY", N["cyan"])]),
    ("INCEPT", [("2021.03.25", None), ("   joined github", N["dim"], "m")]),
    ("STATUS", [("ACTIVE — BUILDING CREEP", N["yel"])]),
]


def dossier(fonts):
    W, H = 1000, 300
    rnd = random.Random(1982)
    s = Svg(fonts, W, H, "Dossier. Subject: Mann Kuvadiya, alias Bladerunner2077. B.Tech IT with Honours in Cyber "
                         "Security, class of 2028, KJSCE, Somaiya Vidyavihar, Mumbai. Function: machine learning × "
                         "offensive security. Status: active, building Creep.")
    s.css.append("@keyframes sweep{from{transform:translateY(0)}to{transform:translateY(150px)}}"
                 "@keyframes dilate{50%{transform:scale(1.18)}}"
                 ".sweep{animation:sweep 2.8s ease-in-out infinite alternate}"
                 ".dilate{transform-box:fill-box;transform-origin:center;animation:dilate 4s ease-in-out infinite}")
    glow_filter(s, "neon", 2, 5)
    panel(s, 8, 8, W - 16, H - 16)
    section_label(s, 36, 44, "01", "DOSSIER")
    s.text(W - 40, 44, "REF · BK-246", size=11, fill=N["dim"], anchor="end", track=2.5)
    s.add(f'<path d="M36 60H{W - 40}" stroke="{N["line"]}"/>')

    # iris scan
    ex, ey = 150, 172
    bx, by, bw, bh = 40, 78, 220, 190
    br = [f"M{bx} {by + 16}V{by}H{bx + 16}", f"M{bx + bw - 16} {by}H{bx + bw}V{by + 16}",
          f"M{bx} {by + bh - 16}V{by + bh}H{bx + 16}", f"M{bx + bw - 16} {by + bh}H{bx + bw}V{by + bh - 16}"]
    s.add(f'<path d="{"".join(br)}" fill="none" stroke="{N["cyan"]}" stroke-opacity=".6" stroke-width="1.5"/>')
    s.defs.append(
        f'<clipPath id="lid"><path d="M{ex - 74} {ey}Q{ex} {ey - 62} {ex + 74} {ey}Q{ex} {ey + 62} {ex - 74} {ey}Z"/></clipPath>'
        '<radialGradient id="iris"><stop offset="0" stop-color="#1a0b05"/><stop offset=".42" stop-color="#6e2c0c"/>'
        f'<stop offset=".72" stop-color="{N["amber"]}"/><stop offset=".9" stop-color="#ffd28a"/>'
        '<stop offset="1" stop-color="#3a1a0a"/></radialGradient>'
    )
    for r, dash, op in ((60, "2 5", .35), (72, "", .18)):
        s.add(f'<circle cx="{ex}" cy="{ey}" r="{r}" fill="none" stroke="{N["cyan"]}" stroke-opacity="{op}"'
              f'{" stroke-dasharray=" + chr(34) + dash + chr(34) if dash else ""}/>')
    s.add(f'<path d="M{ex - 96} {ey}H{ex - 80}M{ex + 80} {ey}H{ex + 96}M{ex} {ey - 92}V{ey - 76}M{ex} {ey + 76}V{ey + 92}" '
          f'stroke="{N["cyan"]}" stroke-opacity=".5"/>')
    s.add(f'<path d="M{ex - 74} {ey}Q{ex} {ey - 62} {ex + 74} {ey}Q{ex} {ey + 62} {ex - 74} {ey}Z" fill="#07070e"/>')
    s.add('<g clip-path="url(#lid)">')
    s.add(f'<circle cx="{ex}" cy="{ey}" r="38" fill="url(#iris)"/>')
    fibres = "".join(
        f"M{ex + 16 * math.cos(a):.1f} {ey + 16 * math.sin(a):.1f}L{ex + 36 * math.cos(a):.1f} {ey + 36 * math.sin(a):.1f}"
        for a in (i * math.tau / 40 + rnd.uniform(-.05, .05) for i in range(40)))
    s.add(f'<path d="{fibres}" stroke="#ffd08a" stroke-opacity=".28" stroke-width=".8"/>')
    s.add(f'<circle class="dilate" cx="{ex}" cy="{ey}" r="13" fill="#020203"/>')
    s.add(f'<ellipse cx="{ex + 11}" cy="{ey - 12}" rx="5" ry="3.5" fill="#fff" opacity=".85"/>')
    s.add(f'<circle cx="{ex - 14}" cy="{ey + 10}" r="1.6" fill="{N["cyan"]}" opacity=".8"/>')
    s.add("</g>")
    s.add(f'<path d="M{ex - 74} {ey}Q{ex} {ey - 62} {ex + 74} {ey}Q{ex} {ey + 62} {ex - 74} {ey}Z" fill="none" '
          f'stroke="{N["cyan"]}" stroke-opacity=".55" stroke-width="1.2"/>')
    s.add(f'<g class="sweep"><rect x="{bx + 8}" y="{by + 12}" width="{bw - 16}" height="1.6" fill="{N["cyan"]}" '
          f'filter="url(#neon)" opacity=".85"/></g>')
    s.text(bx + bw / 2, by + bh + 1, [("IRIS SCAN  ", N["mid"]), ("✓ MATCH", N["cyan"], "mb")], size=10.5,
           anchor="middle", track=2)

    # fields
    lx, vx = 300, 420
    for i, (label, runs) in enumerate(DOSSIER):
        y = 96 + i * 28
        s.text(lx, y, label, size=11, fill=N["dim"], track=2.5)
        if label == "STATUS":
            s.add(f'<circle class="blink" cx="{vx + 4}" cy="{y - 4.5}" r="3.5" fill="{N["yel"]}"/>')
            s.text(vx + 16, y, runs, size=15, face="dm", fill=N["text"], track=1.5)
        else:
            w = s.text(vx, y, runs, size=15, face="dm", fill=N["text"], track=1.5)
            if vx + w > 920:
                raise SystemExit(f"dossier {label} runs to x={vx + w:.0f}; the panel holds 920")

    # barcode down the right edge
    bars, y = [], 80
    while y < 262:
        h = rnd.choice((1, 1, 2, 3))
        bars.append(f"M944 {y}h24v{h}h-24z")
        y += h + rnd.choice((1, 2, 2, 3))
    s.add(f'<path d="{"".join(bars)}" fill="{N["dim"]}" opacity=".5"/>')
    s.save("dossier.svg")


# ── case files ──────────────────────────────────────────────────────────────

CASES = [
    dict(file="case-creep.svg", title="CREEP", status="ACTIVE", color="cyan", live=True, link=False,
         desc="LLM agent that reads HAR + OpenAPI, infers the auth model, then breaks it",
         tech="python · fastapi · llm apis"),
    dict(file="case-honeypot.svg", title="MED-DEVICE HONEYPOT", status="RESEARCH", color="amber", live=False, link=False,
         desc="Raspberry Pi posing as medical devices; ML clusters whoever attacks it",
         tech="python · scikit-learn · rpi"),
    dict(file="case-datnet.svg", title="DATNET", status="RESEARCH", color="amber", live=False, link=True,
         desc="Dual-axis transformer: channel + spatial attention for image restoration",
         tech="pytorch · transformers"),
    dict(file="case-semicon.svg", title="SEMICON-ML", status="SHIPPED", color="yel", live=False, link=True,
         desc="NAFNet variant for KLA's hackathon: joint denoise + 2× super-resolution",
         tech="pytorch · nafnet"),
    dict(file="case-privacylayer.svg", title="PRIVACYLAYER", status="DEMOED", color="mag", live=False, link=False,
         desc="Self-sovereign identity with zero-knowledge selective disclosure",
         tech="solidity · circom · react native"),
    dict(file="case-dvwa.svg", title="UPLOAD → RCE", status="WRITEUP", color="violet", live=False, link=True,
         desc="VAPT proof of concept: an unrestricted file upload escalated to RCE",
         tech="php · vapt · owasp"),
]


def case(fonts, i, c):
    W, H = 1000, 78
    acc = N[c["color"]]
    s = Svg(fonts, W, H, f'Case {i:02d}: {c["title"]} — {c["desc"]}. Status: {c["status"].lower()}.')
    shape = chamfer(4, 4, W - 8, H - 8, br=16)
    s.defs.append(f'<clipPath id="row"><path d="{shape}"/></clipPath>')
    s.add(f'<path d="{shape}" fill="{N["panel"]}" stroke="{N["line"]}" stroke-width="1.2"/>')
    s.add(f'<g clip-path="url(#row)"><rect x="4" y="4" width="3" height="{H - 8}" fill="{acc}"/></g>')
    s.text(28, 50, f"{i:02d}", size=26, face="d", fill="#2c2e48", track=1)
    s.text(84, 34, c["title"], size=19, face="d", fill=N["white"], track=2.5)
    dw = s.text(84, 58, c["desc"], size=12.5, fill=N["mid"])
    tw = s.measure(c["tech"], 11, "m", .5)
    if 84 + dw > 916 - tw - 24:
        raise SystemExit(f'{c["title"]}: description collides with the tech line')
    s.text(916, 58, c["tech"], size=11, fill=N["dim"], anchor="end", track=.5)
    sw = s.text(916, 34, c["status"], size=12, face="ds", fill=acc, anchor="end", track=3)
    s.add(f'<circle{" class=" + chr(34) + "blink" + chr(34) if c["live"] else ""} cx="{916 - sw - 12:.1f}" cy="29.5" '
          f'r="3.2" fill="{acc}"/>')
    s.add(f'<path d="M934 18V60" stroke="{N["line"]}"/>')
    if c["link"]:
        s.text(962, 47, "↗", size=20, face="mb", fill=N["cyan"], anchor="middle")
    else:
        s.text(962, 46, "", size=15, fill=N["dim"], anchor="middle")
    s.save(c["file"])


# ── headers, loadout, buttons, footer ───────────────────────────────────────

HEADERS = [
    ("head-cases.svg", "02", "CASE FILES", f"{len(CASES):02d} RECORDS"),
    ("head-activity.svg", "04", "ACTIVITY", "LIVE FEED"),
]


def header(fonts, name, num, title, note):
    W, H = 1000, 48
    s = Svg(fonts, W, H, title.title())
    s.defs.append(f'<linearGradient id="rule" x1="0" x2="1"><stop offset="0" stop-color="{N["cyan"]}" stop-opacity=".7"/>'
                  f'<stop offset="1" stop-color="{N["cyan"]}" stop-opacity="0"/></linearGradient>')
    s.add(f'<path d="{chamfer(4, 6, W - 8, 36, tl=12)}" fill="{N["panel"]}" stroke="{N["line"]}" stroke-width="1.2"/>')
    w = section_label(s, 28, 29, num, title)
    nw = s.measure(note, 11, "m", 2.5)
    s.add(f'<rect x="{28 + w + 10:.0f}" y="23" width="{W - 60 - w - nw - 34:.0f}" height="1.5" fill="url(#rule)"/>')
    s.text(W - 28, 28.5, note, size=11, fill=N["dim"], anchor="end", track=2.5)
    s.save(name)


LOADOUT = [
    ("BUILD", ["PYTHON", "PYTORCH", "SCIKIT-LEARN", "OPENCV", "FASTAPI", "SQL", "SOLIDITY"]),
    ("BREAK", ["VAPT", "OWASP TOP 10", "OWASP LLM TOP 10", "ACCESS CONTROL", "HONEYPOTS"]),
    ("RUN", ["LINUX", "GIT", "RASPBERRY PI", "C / C++", "BASH"]),
]


def loadout(fonts):
    W, H = 1000, 196
    s = Svg(fonts, W, H, "Loadout. " + " ".join(f'{k.title()}: {", ".join(v)}.' for k, v in LOADOUT))
    panel(s, 8, 8, W - 16, H - 16)
    section_label(s, 36, 44, "03", "LOADOUT")
    s.add(f'<path d="M36 60H{W - 40}" stroke="{N["line"]}"/>')
    for r, (label, items) in enumerate(LOADOUT):
        y = 100 + r * 34
        s.text(36, y, label, size=11, fill=[N["cyan"], N["mag"], N["yel"]][r], track=3)
        x = 130
        for j, item in enumerate(items):
            if j:
                s.add(f'<path d="M{x + 11} {y - 9}l4 4-4 4-4-4z" fill="{N["mag"]}" opacity=".8"/>')
                x += 22
            x += s.text(x, y, item, size=15, face="dm", fill=N["text"], track=2)
        if x > W - 40:
            raise SystemExit(f"loadout row {label} runs to x={x:.0f}")
    s.save("loadout.svg")


BUTTONS = [
    ("btn-linkedin.svg", "", "LINKEDIN", "cyan"),
    ("btn-portfolio.svg", "\U000f0379", "PORTFOLIO", "mag"),
    ("btn-email.svg", "\U000f01ee", "EMAIL", "amber"),
]


def button(fonts, name, icon, label, color):
    acc = N[color]
    s0 = Svg(fonts, 1, 1, "")
    lw = s0.measure(label, 14, "ds", 3)
    W, H = round(58 + lw + 24), 44
    s = Svg(fonts, W, H, label.title())
    s.add(f'<path d="{chamfer(1, 1, W - 2, H - 2, tl=11, br=11)}" fill="{N["panel"]}" stroke="{acc}" '
          f'stroke-opacity=".8" stroke-width="1.4"/>')
    s.add(f'<path d="M34 12V32" stroke="{acc}" stroke-opacity=".35"/>')
    s.text(19, 28, icon, size=15, fill=acc, anchor="middle")
    s.text(46, 27.5, label, size=14, face="ds", fill=N["white"], track=3)
    s.save(name)


def footer(fonts):
    W, H = 1000, 130
    rnd = random.Random(2049)
    s = Svg(fonts, W, H, "End of transmission")
    s.css.append(HERO_CSS)
    shape = chamfer(4, 4, W - 8, H - 8, tl=16, br=16)
    s.defs.append(f'<clipPath id="f"><path d="{shape}"/></clipPath>'
                  '<linearGradient id="dusk" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#07060e"/>'
                  '<stop offset="1" stop-color="#2a0f30"/></linearGradient>')
    s.add(f'<path d="{shape}" fill="url(#dusk)"/>')
    s.add('<g clip-path="url(#f)">')
    city = skyline(rnd, -10, W + 10, H, lambda x: (14, 44), 16, 44, gap=(0, 5))
    draw_buildings(s, rnd, city, H, "#050409", antenna_light=True)
    draw_lights(s, rnd, city, .07, [("#ffb867", .5), ("#6ff0ff", .45)], twinkle=.1)
    rain(s, "rainA", rnd, 150, 6, 10, 22, "#c4f3ff", .22, 1, "rainA", W, H)
    w = s.text(W / 2 - 8, 56, "// END OF TRANSMISSION", size=14, face="ds", fill=N["mid"], anchor="middle", track=7)
    s.add(f'<rect class="blink" x="{W / 2 - 8 + w / 2 + 8:.1f}" y="43" width="9" height="15" fill="{N["cyan"]}"/>')
    s.add("</g>")
    s.add(f'<path d="{shape}" fill="none" stroke="{N["line"]}" stroke-width="1.2"/>')
    s.save("footer.svg")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mono", required=True, type=Path, help="folder with JetBrainsMonoNLNerdFontMono-*.ttf")
    args = ap.parse_args()
    fonts = {
        "m": Font.load(args.mono / "JetBrainsMonoNLNerdFontMono-Regular.ttf"),
        "mb": Font.load(args.mono / "JetBrainsMonoNLNerdFontMono-Bold.ttf"),
        "d": Font.load(fetch("ChakraPetch-Bold.ttf")),
        "ds": Font.load(fetch("ChakraPetch-SemiBold.ttf")),
        "dm": Font.load(fetch("ChakraPetch-Medium.ttf")),
        "jp": Font.instance(fetch("NotoSansJP[wght].ttf"), JP_TEXT, wght=700),
    }
    print(f"rendering into {OUT}")
    hero(fonts)
    dossier(fonts)
    for i, c in enumerate(CASES, 1):
        case(fonts, i, c)
    for h in HEADERS:
        header(fonts, *h)
    loadout(fonts)
    for b in BUTTONS:
        button(fonts, *b)
    footer(fonts)


if __name__ == "__main__":
    main()
