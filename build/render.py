#!/usr/bin/env python3
"""
Renders every SVG in ../assets: the Hyprland-style art on this profile.

All text is converted to vector outlines from JetBrains Mono Nerd Font, so the
art renders identically whether or not a viewer has the font installed. Edit
the copy in this file, then rebuild:

    pip install fonttools
    python build/render.py --fonts "path/to/JetBrainsMono"

--fonts is the folder holding JetBrainsMonoNLNerdFontMono-{Regular,Bold,Italic}.ttf
(nerdfonts.com -> JetBrainsMono).
"""
import argparse
import math
import random
from pathlib import Path
from xml.sax.saxutils import escape

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"

# Catppuccin Mocha
C = dict(
    rosewater="#f5e0dc", flamingo="#f2cdcd", pink="#f5c2e7", mauve="#cba6f7",
    red="#f38ba8", maroon="#eba0ac", peach="#fab387", yellow="#f9e2af",
    green="#a6e3a1", teal="#94e2d5", sky="#89dceb", sapphire="#74c7ec",
    blue="#89b4fa", lavender="#b4befe", text="#cdd6f4", sub1="#bac2de",
    sub0="#a6adc8", ov2="#9399b2", ov1="#7f849c", ov0="#6c7086",
    s2="#585b70", s1="#45475a", s0="#313244", base="#1e1e2e",
    mantle="#181825", crust="#11111b",
)

ADV = 600  # every glyph in the Mono build is 600/1000 em wide
FACES = {"r": "Regular", "b": "Bold", "i": "Italic"}

BASE_CSS = """
@keyframes popin{from{opacity:0;transform:scale(.86)}}
@keyframes fadein{from{opacity:0}}
@keyframes slidedown{from{opacity:0;transform:translateY(-42px)}}
@keyframes blink{50%{opacity:0}}
@keyframes pulse{50%{opacity:.25}}
@keyframes draw{from{stroke-dashoffset:1}}
@keyframes eq{from{transform:scaleY(.18)}}
@keyframes swing{from{transform:scaleX(.45)}}
.pop{animation:popin .65s cubic-bezier(.05,.9,.1,1.05) both;transform-box:fill-box;transform-origin:center}
.fade{animation:fadein .35s ease-out both}
.slide{animation:slidedown .7s cubic-bezier(.05,.9,.1,1.05) both}
.blink{animation:blink 1.1s steps(1) infinite}
.pulse{animation:pulse 1.8s ease-in-out infinite}
.draw{stroke-dasharray:1;animation:draw 1.8s cubic-bezier(.45,0,.2,1) both}
.eq{transform-box:fill-box;transform-origin:50% 100%;animation:eq .8s ease-in-out infinite alternate}
.swing{transform-box:fill-box;transform-origin:0 50%;animation:swing 2.6s ease-in-out infinite alternate}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
"""


# ── glyph outlines ──────────────────────────────────────────────────────────

class Font:
    def __init__(self, path):
        f = TTFont(path)
        self.cmap = f.getBestCmap()
        self.glyphs = f.getGlyphSet()
        self.cache = {}

    def path(self, ch):
        if ch not in self.cache:
            name = self.cmap.get(ord(ch))
            if name is None:
                raise SystemExit(f"glyph missing from font: {ch!r} U+{ord(ch):04X}")
            pen = SVGPathPen(self.glyphs, ntos=lambda v: f"{v:.0f}" if v == int(v) else f"{v:.1f}")
            self.glyphs[name].draw(pen)
            self.cache[ch] = pen.getCommands()
        return self.cache[ch]


class Svg:
    def __init__(self, fonts, w, h, label):
        self.fonts, self.w, self.h, self.label = fonts, w, h, label
        self.defs, self.body, self.css = [], [], [BASE_CSS]
        self.glyph_ids = {}
        self.n = 0

    def id(self, prefix):
        self.n += 1
        return f"{prefix}{self.n}"

    def add(self, *parts):
        self.body.extend(parts)

    def gid(self, face, ch):
        key = (face, ch)
        if key not in self.glyph_ids:
            gid = f"g{face}{ord(ch):x}"
            self.defs.append(f'<path id="{gid}" d="{self.fonts[face].path(ch)}"/>')
            self.glyph_ids[key] = gid
        return self.glyph_ids[key]

    def text(self, x, y, runs, size=13, face="r", fill=C["text"], anchor="start",
             track=0.0, attrs=""):
        """Draw outlined monospace text; `runs` is a str or [(str, fill[, face])].
        Returns the drawn width in px."""
        if isinstance(runs, str):
            runs = [(runs, fill)]
        cols = sum(len(r[0]) for r in runs)
        step = ADV + track * 1000 / size
        width = cols * step * size / 1000 - track
        if anchor == "middle":
            x -= width / 2
        elif anchor == "end":
            x -= width
        k = size / 1000
        out = [f'<g transform="translate({x:.1f} {y:.1f}) scale({k:g} {-k:g})"{attrs}>']
        col = 0
        for run in runs:
            s, f = run[0], run[1] or fill
            fc = run[2] if len(run) > 2 else face
            uses = []
            for ch in s:
                if not ch.isspace():
                    uses.append(f'<use href="#{self.gid(fc, ch)}" x="{col * step:.0f}"/>')
                col += 1
            if uses:
                out.append(f'<g fill="{f}">{"".join(uses)}</g>')
        out.append("</g>")
        self.add("".join(out))
        return width

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
        print(f"  {name:22s} {len(svg) / 1024:6.1f} KB")


def cw(size):
    return size * ADV / 1000


def mix(a, b, t):
    pa = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    pb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(pa, pb))


def ramp(stops, t):
    """Sample a multi-stop colour ramp at t in [0, 1]."""
    t = min(max(t, 0), 1) * (len(stops) - 1)
    i = min(int(t), len(stops) - 2)
    return mix(stops[i], stops[i + 1], t - i)


def wrap(text, cols):
    lines, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > cols:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}" if line else word
    return lines + [line]


# ── shared pieces ───────────────────────────────────────────────────────────

def defs_common(s):
    s.defs.append(
        '<linearGradient id="border" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{C["mauve"]}"/><stop offset=".5" stop-color="{C["blue"]}"/>'
        f'<stop offset="1" stop-color="{C["teal"]}"/>'
        '<animateTransform attributeName="gradientTransform" type="rotate" '
        'values="0 .5 .5;360 .5 .5" dur="7s" repeatCount="indefinite"/></linearGradient>'
        '<filter id="shadow" x="-20%" y="-20%" width="140%" height="150%">'
        '<feGaussianBlur stdDeviation="9"/></filter>'
        '<filter id="glow" x="-10%" y="-10%" width="120%" height="120%">'
        '<feGaussianBlur stdDeviation="5"/></filter>'
    )


class window:
    """A Hyprland window: rounded, borderless-titlebar, drop shadow, and the
    rotating gradient border when active. Content drawn inside is clipped."""

    def __init__(self, s, x, y, w, h, active=False, delay=0.0, r=12, opacity=.84, cls="pop", shadow=True):
        self.s, self.shadow = s, shadow
        self.args = (x, y, w, h, active, delay, r, opacity, cls)

    def __enter__(self):
        s = self.s
        x, y, w, h, active, delay, r, opacity, cls = self.args
        cid = s.id("clip")
        s.defs.append(f'<clipPath id="{cid}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}"/></clipPath>')
        s.add(f'<g class="{cls}" style="animation-delay:{delay}s">')
        if self.shadow:
            s.add(f'<rect x="{x + 4}" y="{y + 10}" width="{w - 8}" height="{h - 6}" rx="{r}" '
                  f'fill="#000" opacity=".55" filter="url(#shadow)"/>')
        s.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{C["base"]}" fill-opacity="{opacity}"/>')
        s.add(f'<g clip-path="url(#{cid})">')
        return self

    def __exit__(self, *exc):
        s = self.s
        x, y, w, h, active, delay, r, opacity, cls = self.args
        s.add("</g>")
        if active:
            s.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="none" '
                  f'stroke="url(#border)" stroke-width="3" opacity=".6" filter="url(#glow)"/>')
            s.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="none" '
                  f'stroke="url(#border)" stroke-width="2"/>')
        else:
            s.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="none" '
                  f'stroke="{C["s1"]}" stroke-width="1.5"/>')
        s.add("</g>")


def typed(s, x, y, runs, begin, size=13, per=.055):
    """Text that types itself out once, starting at `begin` seconds."""
    n = sum(len(r[0]) for r in runs)
    c = cw(size)
    dur = begin + n * per
    times = ["0"] + [f"{(begin + i * per) / dur:.4f}" for i in range(n + 1)]
    values = ["0"] + [f"{i * c:.1f}" for i in range(n + 1)]
    times[-1] = "1"
    cid = s.id("type")
    s.defs.append(
        f'<clipPath id="{cid}"><rect x="{x - 1}" y="{y - size * 1.1:.1f}" width="{n * c + 2:.1f}" '
        f'height="{size * 1.6:.1f}"><animate attributeName="width" values="{";".join(values)}" '
        f'keyTimes="{";".join(times)}" dur="{dur:.3f}s" calcMode="discrete" fill="freeze"/></rect></clipPath>'
    )
    s.add(f'<g clip-path="url(#{cid})">')
    s.text(x, y, runs, size=size)
    s.add("</g>")
    return n * c


def prompt(s, x, y, size=13):
    """starship-ish prompt: `~/bladekiller246 ❯ ` — returns its width."""
    return s.text(x, y, [("~/bladekiller246 ", C["blue"], "b"), ("❯ ", C["green"], "b")], size=size)


# ── hero: the desktop ───────────────────────────────────────────────────────

MK = [
    "███╗   ███╗██╗  ██╗",
    "████╗ ████║██║ ██╔╝",
    "██╔████╔██║█████╔╝ ",
    "██║╚██╔╝██║██╔═██╗ ",
    "██║ ╚═╝ ██║██║  ██╗",
    "╚═╝     ╚═╝╚═╝  ╚═╝",
]


def ansi_logo(s, x, y, rows, cellw, cellh, fill, shade):
    """The █ cells of a figlet drawn as geometry, over an extruded shadow in
    place of the box-drawing strokes, which blur to mush at README scale."""
    d = "".join(f"M{x + c * cellw:.1f} {y + r * cellh:.1f}h{cellw + .4:.1f}v{cellh + .4:.1f}h{-cellw - .4:.1f}z"
                for r, row in enumerate(rows) for c, ch in enumerate(row) if ch == "█")
    s.add(f'<path d="{d}" fill="{shade}" transform="translate({cellw * .45:.1f} {cellh * .3:.1f})"/>')
    s.add(f'<path d="{d}" fill="{fill}"/>')


FASTFETCH = [
    ("OS", "B.Tech IT · class of '28"),
    ("Host", "KJSCE, Somaiya Vidyavihar"),
    ("Kernel", "Honours in Cyber Security"),
    ("Uptime", "on GitHub since 2021"),
    ("Packages", "pytorch, scikit-learn"),
    ("Shell", "python · c · c++ · bash"),
    ("WM", "Hyprland (in spirit)"),
    ("CPU", "LLM agents · vision models"),
    ("GPU", "image restoration"),
    ("Locale", "Mumbai, IN"),
]

PLAN = [
    ("»", "building Creep: an LLM agent that reads HAR + OpenAPI,"),
    (" ", "infers the auth model, then tries to break it"),
    ("»", "honeypotting medical-device services on a Raspberry Pi,"),
    (" ", "then classifying who knocks with ML (paper in progress)"),
    ("»", "asking which attention axis noise, blur & rain need"),
]

K, P, S, T, O, Y_, G, R_ = C["mauve"], C["ov2"], C["lavender"], C["text"], C["sky"], C["yellow"], C["green"], C["red"]
NVIM = [
    [("from", K), (" dataclasses ", T), ("import", K), (" dataclass", Y_)],
    [],
    [("@dataclass", C["peach"])],
    [("class", K), (" ", T), ("Mann", Y_), (":", P)],
    [("    based ", S), ("=", O), (" ", T), ('"Mumbai, IN"', G)],
    [("    stack ", S), ("=", O), (" ", T), ("[", P), ('"torch"', G), (", ", P), ('"sklearn"', G), (", ", P), ('"fastapi"', G), ("]", P)],
    [("    hunts ", S), ("=", O), (" ", T), ("[", P), ('"idor"', G), (", ", P), ('"bola"', G), (", ", P), ('"broken authz"', G), ("]", P)],
    [],
    [("    ", T), ("def", K), (" ", T), ("now", C["blue"]), ("(", P), ("self", R_, "i"), (") ", P), ("->", O), (" ", T), ("str", Y_), (":", P)],
    [("        ", T), ("return", K), (" ", T), ('"creep"', G), ("  ", T), ("# llm vs access control", C["ov1"], "i")],
]


def hero(fonts):
    W, H = 1000, 600
    s = Svg(fonts, W, H, "A Hyprland desktop: fastfetch for Mann Kuvadiya, nvim editing mann.py, and a btop-style training monitor")
    defs_common(s)
    # wallpaper: deep mocha with soft colour fields bleeding through the glass
    s.defs.append(
        f'<clipPath id="screen"><rect width="{W}" height="{H}" rx="18"/></clipPath>'
        f'<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{C["base"]}"/>'
        f'<stop offset="1" stop-color="{C["crust"]}"/></linearGradient>'
        '<filter id="grain"><feTurbulence type="fractalNoise" baseFrequency=".85" numOctaves="2" stitchTiles="stitch"/>'
        '<feColorMatrix values="0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 .6 0"/></filter>'
        f'<linearGradient id="logo" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{C["mauve"]}"/>'
        f'<stop offset=".55" stop-color="{C["blue"]}"/><stop offset="1" stop-color="{C["teal"]}"/></linearGradient>'
    )
    blobs = [(150, 520, 300, C["mauve"], .55), (860, 120, 320, C["blue"], .45),
             (640, 600, 230, C["pink"], .35), (40, 40, 200, C["teal"], .30), (980, 560, 200, C["mauve"], .35)]
    for i, (cx, cy, r, col, op) in enumerate(blobs):
        s.defs.append(f'<radialGradient id="blob{i}"><stop offset="0" stop-color="{col}" stop-opacity="{op}"/>'
                      f'<stop offset="1" stop-color="{col}" stop-opacity="0"/></radialGradient>')
    s.add('<g clip-path="url(#screen)">')
    s.add(f'<rect width="{W}" height="{H}" fill="url(#sky)"/>')
    for i, (cx, cy, r, *_rest) in enumerate(blobs):
        s.add(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#blob{i})"/>')
    s.add(f'<rect width="{W}" height="{H}" filter="url(#grain)" opacity=".05"/>')

    waybar(s, W)

    # ── window A: fastfetch (active) ──
    ax, ay, aw, ah = 12, 56, 540, 532
    with window(s, ax, ay, aw, ah, active=True, delay=.05):
        px = ax + 22
        w = prompt(s, px, ay + 36)
        typed(s, px + w, ay + 36, [("fastfetch", T)], begin=.75)
        out = 1.35
        s.add(f'<g class="fade" style="animation-delay:{out}s">')
        ansi_logo(s, px + 2, ay + 58, MK, 9, 19, "url(#logo)", C["s2"])
        s.text(px + 2, ay + 58 + 6 * 19 + 26, "BLADERUNNER", size=11, face="b", fill=C["ov1"], track=4.5)
        s.text(px + 2, ay + 58 + 6 * 19 + 44, "2077", size=11, face="b", fill=C["s2"], track=4.5)
        ix = px + 19 * 9 + 26
        iy = ay + 72
        s.text(ix, iy, [("mann", C["mauve"], "b"), ("@", C["ov2"], "b"), ("bladerunner2077", C["blue"], "b")])
        s.text(ix, iy + 19, "─" * 20, fill=C["s2"])
        keys = [C["mauve"], C["lavender"], C["blue"], C["sapphire"], C["teal"]]
        for i, (k, v) in enumerate(FASTFETCH):
            s.text(ix, iy + 19 * (i + 2), [(f"{k:<9}", ramp(keys, i / (len(FASTFETCH) - 1)), "b"), (v, C["text"])])
        py = iy + 19 * 12 + 2
        for i, col in enumerate(["red", "peach", "yellow", "green", "teal", "blue", "mauve", "pink"]):
            s.add(f'<rect x="{ix + i * 29}" y="{py}" width="23" height="13" rx="3.5" fill="{C[col]}"/>')
        s.add("</g>")

        y2 = ay + 346
        s.add(f'<g class="fade" style="animation-delay:{out + .25}s">')
        w = prompt(s, px, y2)
        s.add("</g>")
        typed(s, px + w, y2, [("cat .plan", T)], begin=out + .45)
        s.add(f'<g class="fade" style="animation-delay:{out + .45 + 9 * .055 + .1:.2f}s">')
        for i, (mark, line) in enumerate(PLAN):
            s.text(px, y2 + 26 + i * 20, [(mark + " ", C["peach"], "b"), (line, C["sub1"])])
        s.add("</g>")
        y3 = y2 + 26 + len(PLAN) * 20 + 22
        s.add(f'<g class="fade" style="animation-delay:{out + 1.2:.2f}s">')
        w = prompt(s, px, y3)
        s.add(f'<rect class="blink" x="{px + w:.1f}" y="{y3 - 12}" width="{cw(13):.1f}" height="16" fill="{C["rosewater"]}"/>')
        s.add("</g>")

    # ── window B: nvim ──
    bx, by, bw, bh = 562, 56, 426, 262
    with window(s, bx, by, bw, bh, delay=.18):
        s.add(f'<g class="fade" style="animation-delay:.5s">')
        s.text(bx + 16, by + 24, [(" ", C["yellow"]), ("mann.py", C["text"], "b")], size=12)
        s.text(bx + bw - 16, by + 24, "~/bladekiller246", size=12, fill=C["ov0"], anchor="end")
        s.add(f'<path d="M{bx} {by + 36}H{bx + bw}" stroke="{C["s0"]}"/>')
        gx, cx0, top = bx + 12, bx + 12 + cw(13) * 4, by + 58
        cur = len(NVIM) - 1
        s.add(f'<rect x="{bx}" y="{top + cur * 18 - 13}" width="{bw}" height="18" fill="{C["s0"]}" fill-opacity=".55"/>')
        for i, runs in enumerate(NVIM):
            y = top + i * 18
            n = abs(cur - i) if i != cur else i + 1
            s.text(gx + cw(13) * 2, y, str(n), fill=C["lavender"] if i == cur else C["s2"],
                   face="b" if i == cur else "r", anchor="end")
            if runs:
                s.text(cx0, y, runs)
        # block cursor on the `c` of "creep"
        ccol = 8 + len("return") + 2
        s.add(f'<g class="blink"><rect x="{cx0 + ccol * cw(13):.1f}" y="{top + cur * 18 - 13}" width="{cw(13):.1f}" '
              f'height="18" fill="{C["rosewater"]}"/>')
        s.text(cx0 + ccol * cw(13), top + cur * 18, "c", fill=C["crust"])
        s.add("</g>")
        # lualine
        ly = by + bh - 32
        s.add(f'<rect x="{bx + 8}" y="{ly}" width="{bw - 16}" height="22" rx="11" fill="{C["mantle"]}"/>')
        s.add(f'<rect x="{bx + 8}" y="{ly}" width="74" height="22" rx="11" fill="{C["blue"]}"/>')
        s.text(bx + 45, ly + 15.5, "NORMAL", size=11.5, face="b", fill=C["crust"], anchor="middle")
        s.text(bx + 92, ly + 15.5, [(" main", C["mauve"]), ("  mann.py", C["sub1"])], size=11.5)
        s.add(f'<rect x="{bx + bw - 8 - 64}" y="{ly}" width="64" height="22" rx="11" fill="{C["blue"]}"/>')
        s.text(bx + bw - 8 - 32, ly + 15.5, f"{cur + 1}:17", size=11.5, face="b", fill=C["crust"], anchor="middle")
        s.text(bx + bw - 8 - 74, ly + 15.5, "utf-8  python", size=11.5, fill=C["ov1"], anchor="end")
        s.add("</g>")

    # ── window C: btop-ish training monitor ──
    btop(s, 562, 328, 426, 260, delay=.31)

    s.add("</g>")
    s.add(f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="18" fill="none" stroke="{C["s0"]}"/>')
    s.save("hero.svg")


def waybar(s, W):
    y, h = 12, 34
    base = y + 22
    isl = f'fill="{C["crust"]}" fill-opacity=".8" stroke="{C["s0"]}"'
    s.add('<g class="slide">')
    # left: hyprland logo + workspaces + focused window
    title = "fastfetch"
    s.add(f'<rect x="12" y="{y}" width="{round(172 + cw(12) * len(title) + 16)}" height="{h}" rx="11" {isl}/>')
    s.text(28, base + 1, "", size=17, fill=C["blue"])
    wx = 58
    s.add(f'<rect x="{wx}" y="{y + 12}" width="28" height="10" rx="5" fill="url(#border)"/>')
    wx += 42
    for occupied in (True, True, False, False):
        s.add(f'<circle cx="{wx}" cy="{y + 17}" r="4.5" fill="{C["ov1"] if occupied else C["s1"]}"/>')
        wx += 18
    s.text(172, base, title, size=12, fill=C["ov1"])
    # centre: who
    cx = W / 2
    s.add(f'<rect x="{cx - 150}" y="{y}" width="300" height="{h}" rx="11" {isl}/>')
    s.text(cx - 134, base, [("Mann Kuvadiya", C["text"], "b"), (" · ", C["ov0"]), ("ML × Security", C["mauve"])], size=12.5)
    ex = cx + 102
    for i, (dur, col) in enumerate(zip((.62, .9, .5, .78, .66), (C["mauve"], C["lavender"], C["blue"], C["sapphire"], C["teal"]))):
        s.add(f'<rect class="eq" style="animation-duration:{dur}s;animation-delay:-{i * .17:.2f}s" '
              f'x="{ex + i * 7}" y="{y + 9}" width="4" height="16" rx="2" fill="{col}"/>')
    # right: status modules
    mods = [("\U000f034e", "mumbai", C["peach"]), ("\U000f0474", "kjsce '28", C["green"])]
    iw = 16 + sum(cw(12.5) * (len(t) + 2) + 16 for _, t, _ in mods) + cw(14) + 16
    rx = W - 12 - iw
    s.add(f'<rect x="{rx:.1f}" y="{y}" width="{iw:.1f}" height="{h}" rx="11" {isl}/>')
    x = rx + 16
    for icon, label, col in mods:
        x += s.text(x, base, [(icon + " ", col), (label, C["sub1"])], size=12.5) + 16
    s.text(W - 12 - 16, base + 1, "", size=14, fill=C["red"], anchor="end")
    s.add("</g>")


def titled_box(s, x, y, w, h, title, color, r=8):
    """btop box: rounded frame with the title cut into the top border."""
    tw = len(title) * cw(12) + 12
    tx = x + 14
    d = (f"M{tx},{y}H{x + r}A{r},{r} 0 0 0 {x},{y + r}V{y + h - r}A{r},{r} 0 0 0 {x + r},{y + h}"
         f"H{x + w - r}A{r},{r} 0 0 0 {x + w},{y + h - r}V{y + r}A{r},{r} 0 0 0 {x + w - r},{y}H{tx + tw}")
    s.add(f'<path d="{d}" fill="none" stroke="{color}" stroke-opacity=".55" stroke-width="1.2"/>')
    s.text(tx + 6, y + 4.5, title, size=12, face="b", fill=color)


def btop(s, x, y, w, h, delay):
    rnd = random.Random(2077)
    with window(s, x, y, w, h, delay=delay):
        gx, gy, gw, gh = x + 12, y + 16, w - 24, 122
        titled_box(s, gx, gy, gw, gh, "¹datnet/train", C["mauve"])
        s.text(gx + gw - 14, gy + 22, [("● ", C["pink"]), ("loss  ", C["sub0"]), ("● ", C["teal"]), ("psnr", C["sub0"])],
               size=11, anchor="end")
        # plot area
        px0, px1, py0, py1 = gx + 14, gx + gw - 14, gy + 32, gy + gh - 10
        for i in range(4):
            yy = py0 + (py1 - py0) * i / 3
            s.add(f'<path d="M{px0} {yy:.1f}H{px1}" stroke="{C["s0"]}" stroke-dasharray="2 4"/>')
        n = 72
        loss, psnr = [], []
        for i in range(n):
            t = i / (n - 1)
            loss.append(.9 * math.exp(-3.4 * t) + .1 + rnd.uniform(-1, 1) * .05 * (1 - .6 * t))
            psnr.append(.12 + .72 * (1 - math.exp(-2.8 * t)) + rnd.uniform(-1, 1) * .025)

        def pts(vals):
            return [(px0 + (px1 - px0) * i / (n - 1), py1 - (py1 - py0) * min(max(v, 0), 1)) for i, v in enumerate(vals)]

        lp, pp = pts(loss), pts(psnr)
        line = lambda p: "M" + "L".join(f"{a:.1f} {b:.1f}" for a, b in p)
        s.defs.append(f'<linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{C["pink"]}" '
                      f'stop-opacity=".35"/><stop offset="1" stop-color="{C["pink"]}" stop-opacity="0"/></linearGradient>')
        s.add(f'<path class="fade" style="animation-delay:{delay + 1.6}s;animation-duration:.8s" '
              f'd="{line(lp)}L{px1} {py1}L{px0} {py1}Z" fill="url(#area)"/>')
        s.add(f'<path class="draw" style="animation-delay:{delay + .5}s" pathLength="1" d="{line(lp)}" fill="none" '
              f'stroke="{C["pink"]}" stroke-width="1.8" stroke-linejoin="round"/>')
        s.add(f'<path class="draw" style="animation-delay:{delay + .8}s" pathLength="1" d="{line(pp)}" fill="none" '
              f'stroke="{C["teal"]}" stroke-width="1.8" stroke-linejoin="round"/>')
        s.add(f'<circle class="pulse" cx="{pp[-1][0]:.1f}" cy="{pp[-1][1]:.1f}" r="3.2" fill="{C["teal"]}"/>')

        # proc table
        ty = gy + gh + 14
        titled_box(s, gx, ty, gw, h - (ty - y) - 12, "²proc", C["blue"])
        s.add(f'<g class="fade" style="animation-delay:{delay + .6}s">')
        c = cw(12.5)
        s.text(gx + 14, ty + 24, [("pid   ", C["ov1"], "b"), ("program", C["ov1"], "b")], size=12.5)
        s.text(gx + gw - 14, ty + 24, "load", size=12.5, face="b", fill=C["ov1"], anchor="end")
        procs = [("2077", "python train.py", 1.0, 3.1), ("1337", "uvicorn creep.api", .72, 2.3),
                 ("4040", "honeypot.service", .55, 2.8)]
        bx0 = gx + 14 + c * 24
        bw = gx + gw - 14 - bx0
        for i, (pid, prog, load, dur) in enumerate(procs):
            yy = ty + 44 + i * 19
            s.text(gx + 14, yy, [(f"{pid}  ", C["peach"]), (prog, C["text"])], size=12.5)
            s.add(f'<rect x="{bx0:.1f}" y="{yy - 9}" width="{bw:.1f}" height="8" rx="4" fill="{C["s0"]}"/>')
            s.add(f'<rect class="swing" style="animation-duration:{dur}s;animation-delay:-{i * .9:.1f}s" '
                  f'x="{bx0:.1f}" y="{yy - 9}" width="{bw * load:.1f}" height="8" rx="4" fill="url(#bar)"/>')
        s.defs.append(f'<linearGradient id="bar"><stop offset="0" stop-color="{C["teal"]}"/>'
                      f'<stop offset=".6" stop-color="{C["blue"]}"/><stop offset="1" stop-color="{C["mauve"]}"/></linearGradient>')
        s.add("</g>")


# ── link buttons ────────────────────────────────────────────────────────────

BUTTONS = [
    ("btn-linkedin.svg", "", "linkedin", C["blue"], "LinkedIn"),
    ("btn-portfolio.svg", "\U000f0379", "portfolio", C["mauve"], "Portfolio"),
    ("btn-email.svg", "\U000f01ee", "email", C["peach"], "Email"),
]


def button(fonts, name, icon, label, color, alt):
    size = 14
    w = round(24 + cw(size) * (len(label) + 2) + 26)
    h = 44
    s = Svg(fonts, w, h, alt)
    s.defs.append(f'<linearGradient id="edge" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{color}"/>'
                  f'<stop offset="1" stop-color="{C["s1"]}"/></linearGradient>')
    s.add(f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="{(h - 2) / 2}" fill="{C["crust"]}" stroke="url(#edge)" stroke-width="1.5"/>')
    s.add(f'<circle cx="24" cy="{h / 2}" r="13" fill="{color}" fill-opacity=".16"/>')
    s.text(24, h / 2 + 5, icon, size=size, fill=color, anchor="middle")
    s.text(46, h / 2 + 5, label, size=size, face="b", fill=C["text"])
    s.save(name)


# ── section headers ─────────────────────────────────────────────────────────

HEADERS = [
    ("head-projects.svg", "1", "~/projects", C["mauve"]),
    ("head-stack.svg", "2", "~/stack", C["blue"]),
    ("head-activity.svg", "3", "~/activity", C["teal"]),
]


def header(fonts, name, num, label, color):
    W, H = 1000, 50
    s = Svg(fonts, W, H, label.replace("~/", "").capitalize())
    pw = round(48 + cw(15) * len(label) + 20)
    s.defs.append(f'<linearGradient id="rule" x1="0" x2="1"><stop offset="0" stop-color="{color}" stop-opacity=".9"/>'
                  f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></linearGradient>')
    s.add(f'<rect x="1" y="6" width="{pw}" height="38" rx="12" fill="{C["crust"]}" stroke="{C["s1"]}"/>')
    s.add(f'<rect x="7" y="12" width="26" height="26" rx="8" fill="{color}"/>')
    s.text(20, 30, num, size=14, face="b", fill=C["crust"], anchor="middle")
    s.text(44, 30.5, label, size=15, face="b", fill=C["text"])
    s.add(f'<rect x="{pw + 14}" y="24" width="{W - pw - 16}" height="2" rx="1" fill="url(#rule)"/>')
    s.save(name)


# ── project cards ───────────────────────────────────────────────────────────

CARDS = [
    dict(file="card-creep.svg", icon="\U000f11ea", color="mauve", title="Creep",
         sub="llm-driven access-control testing",
         status=("building", "green", True), link=None,
         desc="An LLM agent that reads HAR traffic and OpenAPI specs, infers the app's intended "
              "authorisation model, then plans multi-step requests to break it. Trained ML swaps "
              "in wherever it measurably beats the LLM.",
         tags=["python", "fastapi", "llm apis", "scikit-learn"]),
    dict(file="card-honeypot.svg", icon="\U000f0fa1", color="peach", title="Med-Device Honeypot",
         sub="raspberry pi honeypot × ml",
         status=("paper wip", "peach", True), link=None,
         desc="A Raspberry Pi posing as medical-device network services. Raw attack logs become a "
              "modelling-ready store joined with public threat intel, and an ML stage classifies "
              "and clusters who knocks.",
         tags=["python", "scikit-learn", "raspberry pi", "linux"]),
    dict(file="card-datnet.svg", icon="\U000f02f9", color="blue", title="DATNet",
         sub="dual-axis transformer · restoration",
         status=("research", "peach", False), link="repo",
         desc="Channel-axis (MDTA) and spatial-axis (shifted-window) attention in one block, with a "
              "learned gate that sets the balance per degradation. An ablation-first PyTorch study "
              "of what noise, blur and rain actually need.",
         tags=["pytorch", "transformers", "opencv"]),
    dict(file="card-semicon.svg", icon="\U000f061a", color="teal", title="SemiCon-ML",
         sub="kla ps-01 · joint denoise + 2× sr",
         status=("hackathon", "blue", False), link="repo",
         desc="NAFNet-derived model for the SemiCon AI Hackathon. Takes 128×128 images hit by "
              "speckle, Gaussian noise and 2× downsampling in random order, and restores a clean "
              "256×256 in a single pass.",
         tags=["pytorch", "nafnet", "super-resolution"]),
    dict(file="card-privacylayer.svg", icon="\U000f0237", color="green", title="PrivacyLayer",
         sub="self-sovereign identity · zk",
         status=("demo day", "lavender", False), link=None,
         desc="W3C DIDs and verifiable credentials with zero-knowledge selective disclosure of "
              "single attributes. On-chain DID registry, enclave-bound key custody. Presented at "
              "the KLEOS 4.0 demo day.",
         tags=["solidity", "circom", "snarkjs", "react native"]),
    dict(file="card-dvwa.svg", icon="\U000f068c", color="red", title="Upload → RCE",
         sub="vapt finding · proof of concept",
         status=("writeup", "red", False), link="repo",
         desc="A VAPT assessment finding written up as a proof of concept: how an unrestricted "
              "file upload in DVWA escalates to remote code execution.",
         tags=["php", "vapt", "owasp"]),
]


def card(fonts, c):
    W, H = 480, 250
    acc = C[c["color"]]
    s = Svg(fonts, W, H, f'{c["title"]}: {c["sub"]}')
    s.defs.append(
        f'<linearGradient id="edge" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{acc}"/>'
        f'<stop offset=".45" stop-color="{C["s1"]}"/><stop offset="1" stop-color="{C["s0"]}"/></linearGradient>'
        f'<radialGradient id="halo" cx="1" cy="0" r="1"><stop offset="0" stop-color="{acc}" stop-opacity=".22"/>'
        f'<stop offset=".6" stop-color="{acc}" stop-opacity="0"/></radialGradient>'
        f'<clipPath id="card"><rect x="6" y="6" width="{W - 12}" height="{H - 12}" rx="14"/></clipPath>'
    )
    s.add(f'<rect x="6" y="6" width="{W - 12}" height="{H - 12}" rx="14" fill="{C["base"]}"/>')
    s.add(f'<g clip-path="url(#card)"><rect x="6" y="6" width="{W - 12}" height="{H - 12}" fill="url(#halo)"/></g>')
    s.add(f'<rect x="6" y="6" width="{W - 12}" height="{H - 12}" rx="14" fill="none" stroke="url(#edge)" stroke-width="1.6"/>')
    # icon tile, title
    s.add(f'<rect x="26" y="26" width="44" height="44" rx="12" fill="{acc}" fill-opacity=".14" stroke="{acc}" stroke-opacity=".4"/>')
    s.text(48, 56, c["icon"], size=24, fill=acc, anchor="middle")
    s.text(84, 47, c["title"], size=19, face="b", fill=C["text"])
    s.text(84, 66, c["sub"], size=12, fill=C["sub0"])
    # status chip
    label, scol, live = c["status"]
    sw = cw(11.5) * len(label) + 34
    sx = W - 26 - sw
    s.add(f'<rect x="{sx:.1f}" y="30" width="{sw:.1f}" height="24" rx="12" fill="{C[scol]}" fill-opacity=".12" '
          f'stroke="{C[scol]}" stroke-opacity=".35"/>')
    pulse = ' class="pulse"' if live else ""
    s.add(f'<circle{pulse} cx="{sx + 14:.1f}" cy="42" r="3.5" fill="{C[scol]}"/>')
    s.text(sx + 24, 46, label, size=11.5, face="b", fill=C[scol])
    # description
    lines = wrap(c["desc"], 54)
    if len(lines) > 4:
        raise SystemExit(f'{c["title"]}: description wraps to {len(lines)} lines; the card holds 4')
    for i, line in enumerate(lines):
        s.text(26, 104 + i * 20, line, size=13, fill=C["sub1"])
    # tags + link hint
    x = 26
    for t in c["tags"]:
        tw = cw(11.5) * len(t) + 18
        s.add(f'<rect x="{x:.1f}" y="200" width="{tw:.1f}" height="24" rx="8" fill="{C["s0"]}"/>')
        s.text(x + 9, 216, t, size=11.5, fill=acc)
        x += tw + 7
    if c["link"]:
        s.text(W - 26, 216, [(" ", C["sub0"]), ("repo ↗", C["text"], "b")], size=12, anchor="end")
    else:
        s.text(W - 26, 216, [(" ", C["ov0"]), ("private", C["ov1"])], size=12, anchor="end")
    s.save(c["file"])


# ── stack ───────────────────────────────────────────────────────────────────

STACK = [
    ("ml", "mauve", [("pytorch", ""), ("scikit-learn", ""), ("numpy", ""), ("pandas", ""), ("opencv", ""), ("matplotlib", "")]),
    ("llm", "pink", [("llm apis", ""), ("agent flows", ""), ("structured output", ""), ("prompt-injection handling", "")]),
    ("security", "red", [("vapt", ""), ("owasp top 10", ""), ("owasp llm top 10", ""), ("honeypots", ""), ("did / vc · zk", "")]),
    ("backend", "peach", [("fastapi", "\U000f109b"), ("rest", ""), ("sql", "\U000f01bc"), ("sql server", ""), ("openapi · har", "")]),
    ("lang", "green", [("python", ""), ("c", "\U000f0671"), ("c++", "\U000f0672"), ("javascript", "\U000f031e"),
                       ("solidity", "\U000f086a"), ("bash", "")]),
    ("tools", "blue", [("git", ""), ("linux", "\U000f033d"), ("raspberry pi", "\U000f043f"), ("github", "")]),
]


def stack(fonts):
    W = 1000
    row = 40
    H = 74 + row * len(STACK) + 20
    s = Svg(fonts, W, H, "Stack: " + "; ".join(f'{g}: {", ".join(t for t, _ in items)}' for g, _, items in STACK))
    defs_common(s)
    with window(s, 8, 8, W - 16, H - 20, active=True, opacity=1, cls="fade", shadow=False):
        w = prompt(s, 32, 44, size=14)
        s.text(32 + w, 44, "eza --icons ~/stack", size=14)
        for i, (group, col, items) in enumerate(STACK):
            y = 88 + i * row
            acc = C[col]
            s.text(34, y, [(" ", acc), (group, acc, "b")], size=14)
            x = 176
            for label, icon in items:
                text = f"{icon} {label}" if icon else label
                tw = cw(12.5) * len(text) + 22
                s.add(f'<rect x="{x:.1f}" y="{y - 18}" width="{tw:.1f}" height="27" rx="9" fill="{C["s0"]}" '
                      f'fill-opacity=".7" stroke="{acc}" stroke-opacity=".22"/>')
                runs = [(icon + " ", acc), (label, C["text"])] if icon else [(label, C["text"])]
                s.text(x + 11, y, runs, size=12.5)
                x += tw + 8
    s.save("stack.svg")


# ── footer: cava ────────────────────────────────────────────────────────────

def footer(fonts):
    W, H = 1000, 110
    s = Svg(fonts, W, H, "An audio visualiser signing off: thanks for stopping by")
    rnd = random.Random(246)
    s.defs.append(
        f'<linearGradient id="cava" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="{C["teal"]}"/>'
        f'<stop offset=".5" stop-color="{C["blue"]}"/><stop offset="1" stop-color="{C["mauve"]}"/></linearGradient>'
        '<linearGradient id="fade" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
        '<stop offset=".18" stop-color="#fff"/><stop offset=".82" stop-color="#fff"/>'
        '<stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        f'<mask id="edges"><rect width="{W}" height="{H}" fill="url(#fade)"/></mask>'
    )
    n, gap = 60, 4
    bw = (W - gap * (n - 1)) / n
    s.add('<g mask="url(#edges)">')
    for i in range(n):
        t = i / (n - 1)
        env = .35 + .65 * math.sin(math.pi * t) ** 1.4
        hgt = 10 + 58 * env * rnd.uniform(.55, 1)
        s.add(f'<rect class="eq" style="animation-duration:{rnd.uniform(.45, 1.1):.2f}s;animation-delay:-{rnd.uniform(0, 1):.2f}s" '
              f'x="{i * (bw + gap):.1f}" y="{72 - hgt:.1f}" width="{bw:.1f}" height="{hgt:.1f}" rx="2.5" fill="url(#cava)"/>')
    s.add("</g>")
    s.text(W / 2, 100, [("❯ ", C["green"], "b"), ("thanks for stopping by", C["ov1"]), ("  ·  ", C["s2"]),
                        ("hyprctl dispatch exit", C["ov1"], "i")], size=13, anchor="middle")
    s.save("footer.svg")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fonts", required=True, type=Path, help="folder with JetBrainsMonoNLNerdFontMono-*.ttf")
    args = ap.parse_args()
    fonts = {k: Font(args.fonts / f"JetBrainsMonoNLNerdFontMono-{v}.ttf") for k, v in FACES.items()}
    print(f"rendering into {OUT}")
    hero(fonts)
    stack(fonts)
    footer(fonts)
    for b in BUTTONS:
        button(fonts, *b)
    for h in HEADERS:
        header(fonts, *h)
    for c in CARDS:
        card(fonts, c)


if __name__ == "__main__":
    main()
