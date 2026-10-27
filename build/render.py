#!/usr/bin/env python3
"""
Renders every SVG in ../assets: one amber-phosphor CRT terminal session.

Text is outlined into vector paths, because GitHub serves repo SVGs under a CSP
that blocks embedded fonts. Edit the copy below, then rebuild:

    pip install fonttools
    python build/render.py

VT323 (SIL OFL) is fetched once from a pinned google/fonts commit into
build/.fonts/ and checked against its SHA-256 before use.
"""
import hashlib
import random
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"
CACHE = Path(__file__).resolve().parent / ".fonts"
FONT = ("VT323-Regular.ttf",
        "https://raw.githubusercontent.com/google/fonts/23e54b51ddffbc7713c583748e3bd86f62b1fa4a/ofl/vt323/VT323-Regular.ttf",
        "cf4de751ada78ceac033dbe16a687742939995b77bc2a052ae17a4957958594d")

# P3 amber phosphor on warm black
C = dict(
    screen="#130c05", edge="#3a2a12", faint="#2b1e0a", bar="#2a1d09",
    dim="#a87724", mid="#d49a35", amb="#ffb000", hi="#ffd88a", white="#fff4dc",
)

HOST = "bladekiller246"
WINDOWS = ["boot", "finger", "nmap", "msf", "log"]


# ── copy ────────────────────────────────────────────────────────────────────

BIOS = [  # label, value, status
    ("mount /dev/kjsce", "B.Tech IT · Honours in Cyber Security · class of 2028", "OK"),
    ("load modules", "machine-learning  offensive-security  honeypots  zk-identity", "OK"),
    ("link", "Mumbai, IN · 19.07°N 72.87°E", "UP"),
]
TAGLINE = "> machine learning x offensive security"
SUBLINE = "  agents that hunt auth bugs · honeypots that learn from attackers"

FINGER = [  # (left label, value), (right label, value)
    (("Login:", "mann"), ("Name:", "Mann Kuvadiya")),
    (("Directory:", "/home/mann"), ("Shell:", "/bin/bash")),
    (("Office:", "KJSCE, Somaiya Vidyavihar"), ("Location:", "Mumbai, IN")),
]
PROJECT = "Creep — an LLM agent that reads HAR + OpenAPI, infers the auth model, then breaks it."
PLAN = [
    "B.Tech IT, Honours in Cyber Security · K. J. Somaiya College of Engineering, Mumbai · '28",
    "I work where machine learning meets offensive security: agents that hunt auth bugs,",
    "honeypots that teach models how attackers behave, and vision models on the side.",
]

PORTS = [  # port, service, version (= the skills)
    ("22/tcp", "ssh", "Linux · Bash · Git · C/C++"),
    ("80/tcp", "http", "FastAPI · HTML/CSS/JS · React Native"),
    ("1883/tcp", "mqtt", "Raspberry Pi · IoT sensors · honeypots"),
    ("3306/tcp", "mysql", "SQL"),
    ("4444/tcp", "msf-handler", "Metasploit · Netcat · Nmap · Wireshark"),
    ("8080/tcp", "http-proxy", "Burp Suite · OWASP ZAP"),
    ("8545/tcp", "eth-rpc", "Solidity · circom · snarkjs"),
    ("8888/tcp", "jupyter", "Python · PyTorch · scikit-learn · OpenCV"),
    ("31337/tcp", "elite", "VAPT · OWASP Top 10 · OWASP LLM Top 10 · access control"),
]

MODULES = [  # file, module path, status, description, stack, public repo?
    ("mod-creep.svg", "auxiliary/scanner/http/creep", "ACTIVE",
     "LLM agent: reads HAR + OpenAPI, infers the auth model, then breaks it", "python · fastapi · llm apis", False),
    ("mod-honeypot.svg", "auxiliary/server/capture/medical_honeypot", "RESEARCH",
     "Raspberry Pi posing as a medical device; ML clusters whoever attacks it", "python · scikit-learn · raspberry pi", False),
    ("mod-dvwa.svg", "exploit/unix/webapp/dvwa_upload_rce", "WRITEUP",
     "VAPT proof of concept: unrestricted file upload escalated to RCE", "php", True),
    ("mod-privacylayer.svg", "auxiliary/admin/identity/privacylayer", "WIP",
     "Self-sovereign identity with zero-knowledge selective disclosure", "solidity · circom · react native", False),
    ("mod-datnet.svg", "post/vision/datnet", "RESEARCH",
     "Dual-axis transformer with channel + spatial attention for image restoration", "pytorch", True),
    ("mod-semicon.svg", "post/vision/semicon_ml", "SHIPPED",
     "NAFNet variant for KLA's hackathon: joint denoising + 2x super-resolution", "pytorch", True),
]

KEYS = [("key-linkedin.svg", "F1", "LINKEDIN"), ("key-portfolio.svg", "F2", "PORTFOLIO"), ("key-email.svg", "F3", "EMAIL")]

# 5×7 dot-matrix glyphs for the boot screen name
DOTS = {
    "M": "1...1 11.11 1.1.1 1.1.1 1...1 1...1 1...1",
    "A": ".111. 1...1 1...1 11111 1...1 1...1 1...1",
    "N": "1...1 11..1 1.1.1 1..11 1...1 1...1 1...1",
    "K": "1...1 1..1. 1.1.. 11... 1.1.. 1..1. 1...1",
    "U": "1...1 1...1 1...1 1...1 1...1 1...1 .111.",
    "V": "1...1 1...1 1...1 1...1 1...1 .1.1. ..1..",
    "D": "1111. 1...1 1...1 1...1 1...1 1...1 1111.",
    "I": ".111. ..1.. ..1.. ..1.. ..1.. ..1.. .111.",
    "Y": "1...1 1...1 .1.1. ..1.. ..1.. ..1.. ..1..",
}

CSS = """
@keyframes on{from{opacity:0}}
@keyframes blink{50%{opacity:0}}
@keyframes pulse{50%{opacity:.45}}
@keyframes px{0%{opacity:0}30%{opacity:1;fill:#fff4dc}100%{opacity:1}}
@keyframes pwr{0%{opacity:.9;transform:scaleY(.004)}22%{opacity:.75;transform:scaleY(1)}100%{opacity:0;transform:scaleY(1)}}
.k{animation:on .01s steps(1) backwards}
.ln{animation:on .18s ease-out backwards}
.px{animation:px .6s ease-out backwards}
.cur{animation:on .01s steps(1) backwards,blink 1.06s steps(1) infinite}
.pulse{animation:pulse 2.6s ease-in-out infinite}
.pwr{opacity:0;transform-box:fill-box;transform-origin:50% 50%;animation:pwr .7s ease-out both}
.roll{animation:roll 7s linear infinite}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
"""


# ── font & outlined text ────────────────────────────────────────────────────

def load_font():
    name, url, want = FONT
    path = CACHE / name
    if path.exists():
        data = path.read_bytes()
    else:
        print(f"  fetching {name}")
        with urllib.request.urlopen(url, timeout=120) as r:
            data = r.read()
    got = hashlib.sha256(data).hexdigest()
    if got != want:
        raise SystemExit(f"{name}: sha256 {got} does not match the pinned {want}; refusing to use it")
    CACHE.mkdir(exist_ok=True)
    path.write_bytes(data)
    return Font(TTFont(path))


class Font:
    def __init__(self, font):
        self.cmap = font.getBestCmap()
        self.glyphs = font.getGlyphSet()
        self.hmtx = font["hmtx"]

    def name(self, ch):
        g = self.cmap.get(ord(ch))
        if g is None:
            raise SystemExit(f"glyph missing from font: {ch!r} U+{ord(ch):04X}")
        return g

    def adv(self, ch):
        return self.hmtx[self.name(ch)][0]

    def path(self, ch):
        pen = SVGPathPen(self.glyphs)
        self.glyphs[self.name(ch)].draw(pen)
        return pen.getCommands()


def at(t):
    return f' style="animation-delay:{t:.2f}s"'


class Svg:
    def __init__(self, font, w, h, label):
        self.font, self.w, self.h, self.label = font, w, h, label
        self.defs, self.glyphs, self.body, self.n = [], {}, [], 0

    def uid(self, prefix):
        self.n += 1
        return f"{prefix}{self.n}"

    def glyph(self, ch):
        gid = f"g{ord(ch):x}"
        if gid not in self.glyphs:
            self.glyphs[gid] = f'<path id="{gid}" d="{self.font.path(ch)}"/>'
        return gid

    def width(self, text, size):
        return sum(self.font.adv(c) for c in text) * size / 1000

    def text(self, x, y, text, size=21, fill="amb", anchor="start", t=None, cps=60, attrs=""):
        """Outlined text -> (svg, end x). t= types it in from t seconds at cps chars/s."""
        w = self.width(text, size)
        x -= {"start": 0, "middle": w / 2, "end": w}[anchor]
        uses, pos = [], 0
        for i, ch in enumerate(text):
            if ch != " ":
                anim = f' class="k"{at(t + i / cps)}' if t is not None else ""
                uses.append(f'<use href="#{self.glyph(ch)}" x="{pos}"{anim}/>')
            pos += self.font.adv(ch)
        k = size / 1000
        return (f'<g transform="translate({x:.1f} {y:.1f}) scale({k:.4f} {-k:.4f})" '
                f'fill="{C.get(fill, fill)}"{attrs}>{"".join(uses)}</g>'), x + w

    def runs(self, x, y, parts, size=21, t=None, cps=60):
        """Several colored runs on one line; typing carries on across runs."""
        out = []
        for txt, fill in parts:
            g, x = self.text(x, y, txt, size, fill, t=t, cps=cps)
            out.append(g)
            if t is not None:
                t += len(txt) / cps
        return "".join(out), x, t

    def save(self, name):
        label = escape(self.label, {'"': "&quot;"})
        css = CSS + f"@keyframes roll{{to{{transform:translateY({self.h + 140}px)}}}}"
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" '
               f'width="{self.w}" height="{self.h}" role="img" aria-label="{label}">'
               f"<title>{label}</title><style>{css}</style>"
               f'<defs>{"".join(self.defs)}{"".join(self.glyphs.values())}</defs>'
               f'{"".join(self.body)}</svg>')
        (OUT / name).write_text(svg, encoding="utf-8")
        print(f"  {name:24s} {len(svg) / 1024:6.1f} KB")


# ── shared pieces ───────────────────────────────────────────────────────────

FX = """<filter id="glow" x="-5%" y="-10%" width="110%" height="120%" color-interpolation-filters="sRGB">
<feGaussianBlur in="SourceGraphic" stdDeviation="1" result="a"/>
<feGaussianBlur in="SourceGraphic" stdDeviation="5" result="b"/>
<feColorMatrix in="b" values="1 0 0 0 0 0 1 0 0 0 0 0 1 0 0 0 0 0 .6 0" result="c"/>
<feMerge><feMergeNode in="c"/><feMergeNode in="a"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="1.5" fill="#000" fill-opacity=".3"/></pattern>
<radialGradient id="vig" r="75%"><stop offset=".6" stop-opacity="0"/><stop offset="1" stop-opacity=".5"/></radialGradient>
<radialGradient id="tube" cy="45%" r="75%"><stop offset="0" stop-color="#1e1407"/><stop offset="1" stop-color="#0d0803"/></radialGradient>
<linearGradient id="rollg" x2="0" y2="1"><stop offset="0" stop-color="#ffb000" stop-opacity="0"/>
<stop offset=".5" stop-color="#ffb000" stop-opacity=".05"/><stop offset="1" stop-color="#ffb000" stop-opacity="0"/></linearGradient>"""


def screen(s, x, y, w, h, r, content, over=""):
    """Phosphor screen: tube, glowing content, scanlines, vignette, refresh bar."""
    cid = s.uid("clip")
    s.defs.append(f'<clipPath id="{cid}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}"/></clipPath>')
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="url(#tube)"/>'
            f'<g clip-path="url(#{cid})"><g filter="url(#glow)">{content}</g>{over}'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="url(#scan)"/>'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="url(#vig)"/>'
            f'<rect class="roll" x="{x}" y="{y - 140}" width="{w}" height="140" fill="url(#rollg)"/></g>')


def panel(s, content, active=None):
    """A full-bleed terminal panel, with a tmux status bar when active is set."""
    s.defs.append(FX)
    if active is not None:
        content += tmux(s, 1, s.h - 31, s.w - 2, active)
    s.body.append(screen(s, 1, 1, s.w - 2, s.h - 2, 16, content))
    s.body.append(f'<rect x="1" y="1" width="{s.w - 2}" height="{s.h - 2}" rx="16" fill="none" '
                  f'stroke="{C["edge"]}" stroke-width="1.5"/>')


def tmux(s, x, y, w, active):
    """tmux status line; the current window is shown in inverse video."""
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="30" fill="{C["bar"]}"/>']
    g, cx = s.text(x + 20, y + 21, "[bk246]", 18, "amb")
    out.append(g)
    cx += 14
    for i, name in enumerate(WINDOWS):
        label = f"{i}:{name}" + ("*" if i == active else "")
        if i == active:
            tw = s.width(label, 18)
            out.append(f'<rect x="{cx - 5:.1f}" y="{y + 5}" width="{tw + 10:.1f}" height="21" fill="{C["amb"]}"/>')
        g, cx = s.text(cx, y + 21, label, 18, "screen" if i == active else "mid")
        out.append(g)
        cx += 16
    out.append(s.text(x + w - 20, y + 21, f'"{HOST}"  mumbai, in', 18, "dim", "end")[0])
    return "".join(out)


def prompt(s, x, y, cmd="", size=21, t=None, cps=16):
    """guest@bladekiller246:~$ <cmd typed in from t>."""
    g1, cx, _ = s.runs(x, y, [(f"guest@{HOST}", "mid"), (":~$ ", "dim")], size)
    g2, cx, t2 = s.runs(cx, y, [(cmd, "hi")], size, t=t, cps=cps) if cmd else ("", cx, t)
    return g1 + g2, cx, t2


def cursor(x, y, t, size=21):
    return (f'<rect class="cur" x="{x + 2:.1f}" y="{y - size * .72:.1f}" width="{size * .45:.1f}" '
            f'height="{size * .86:.1f}" fill="{C["amb"]}" style="animation-delay:{t:.2f}s,{t:.2f}s"/>')


def line(content, t):
    return f'<g class="ln"{at(t)}>{content}</g>'


# ── sections ────────────────────────────────────────────────────────────────

def hero(font):
    W, H = 960, 560
    sx, sy, sw, sh = 34, 32, 892, 428
    s = Svg(font, W, H, "A retro amber CRT terminal boots up: BIOS lines mount B.Tech IT, Honours in Cyber Security, "
                        "class of 2028, load machine-learning and offensive-security modules, link up from Mumbai. "
                        "The name Mann Kuvadiya lights up on a dot-matrix, then: machine learning × offensive security. "
                        "Agents that hunt auth bugs, honeypots that learn from attackers.")
    s.defs.append(FX)
    s.defs.append('<linearGradient id="bez" x2="0" y2="1"><stop offset="0" stop-color="#2e2b27"/>'
                  '<stop offset="1" stop-color="#191715"/></linearGradient>'
                  '<radialGradient id="knob" cx="40%" cy="35%"><stop offset="0" stop-color="#4a453e"/>'
                  '<stop offset="1" stop-color="#1c1a17"/></radialGradient>'
                  '<radialGradient id="glare" cx="30%" cy="10%" r="60%"><stop offset="0" stop-color="#fff" stop-opacity=".07"/>'
                  '<stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>'
                  '<filter id="led" x="-200%" y="-200%" width="500%" height="500%"><feGaussianBlur stdDeviation="4"/></filter>')

    # bezel
    s.body.append(f'<rect width="{W}" height="{H}" rx="30" fill="url(#bez)"/>'
                  f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="29" fill="none" stroke="#ffffff" stroke-opacity=".07"/>'
                  f'<rect x="{sx - 10}" y="{sy - 10}" width="{sw + 20}" height="{sh + 20}" rx="28" fill="#050302" '
                  f'stroke="#000" stroke-opacity=".6" stroke-width="2"/>')

    x0, c = 68, []
    t0 = .8
    # BIOS
    c.append(line(s.runs(x0, 74, [("BK-246 BIOS v3.0", "mid"), ("  ·  P3 amber phosphor  ·  80x25", "dim")], 19)[0]
                  + s.text(sx + sw - 34, 74, f"(c) 2026 {HOST}", 19, "dim", "end")[0], t0))
    for i, (label, value, status) in enumerate(BIOS):
        y, t = 102 + i * 24, t0 + .3 * (i + 1)
        g, ex = s.text(x0, y, label, 19, "mid")
        dots1 = "." * int((222 - ex) / 7.6)
        g += s.text(ex + 6, y, dots1, 19, "faint")[0]
        g2, vx = s.text(236, y, value, 19, "amb")
        right = sx + sw - 34
        st = f"[ {status} ]"
        stw = s.width(st, 19)
        dots2 = "." * max(0, int((right - stw - vx - 16) / 7.6))
        g += g2 + s.text(vx + 8, y, dots2, 19, "faint")[0]
        c.append(line(g, t) + line(s.text(right, y, st, 19, "hi", "end")[0], t + .18))
    c.append(line(s.text(x0, 174, "starting session for guest ...", 19, "dim")[0], t0 + 1.35))

    # dot-matrix name
    rnd = random.Random(246)
    p, dot, top, col, tn = 10.5, 8.4, 200, 0, 2.25
    unlit, lit = [], []
    for ch in "MANN KUVADIYA":
        if ch == " ":
            col += 4
            continue
        for r, row in enumerate(DOTS[ch].split()):
            for cc, bit in enumerate(row):
                x, y = x0 + (col + cc) * p, top + r * p
                if bit == "1":
                    d = tn + (col + cc) / 75 * .8 + rnd.random() * .25
                    lit.append(f'<rect class="px" x="{x:.1f}" y="{y:.1f}" width="{dot}" height="{dot}" rx="1.2"{at(d)}/>')
                else:
                    unlit.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{dot}" height="{dot}" rx="1.2"/>')
        col += 6
    c.append(f'<g fill="{C["faint"]}" opacity=".7">{"".join(unlit)}</g><g fill="{C["amb"]}">{"".join(lit)}</g>')

    # tagline, subline, prompt
    tt = 3.35
    c.append(s.text(x0, 324, TAGLINE, 30, "hi", t=tt, cps=34)[0])
    tt += len(TAGLINE) / 34 + .25
    c.append(line(s.text(x0, 358, SUBLINE, 20, "mid")[0], tt))
    g, cx, _ = prompt(s, x0, 404)
    c.append(line(g, tt + .45) + cursor(cx, 404, tt + .45))
    c.append(line(tmux(s, sx, sy + sh - 30, sw, 0), t0))

    over = (f'<rect x="{sx}" y="{sy}" width="{sw}" height="{sh}" fill="url(#glare)"/>'
            f'<rect class="pwr" x="{sx}" y="{sy}" width="{sw}" height="{sh}" fill="{C["hi"]}"/>')
    s.body.append(screen(s, sx, sy, sw, sh, 22, "".join(c), over))

    # bottom strip: badge, vents, power LED, knobs
    by = 514
    g, ex = s.text(46, by + 8, "BK-246", 26, "#6e665b")
    s.body.append(g + s.text(ex + 14, by + 7, "AMBER PHOSPHOR TERMINAL", 16, "#5c554b")[0])
    s.body.append("".join(f'<rect x="{430 + i * 16}" y="{by - 12}" width="5" height="24" rx="2.5" fill="#0f0e0c"/>'
                          for i in range(7)))
    s.body.append(f'<circle cx="796" cy="{by}" r="9" fill="{C["amb"]}" opacity=".55" filter="url(#led)"/>'
                  f'<circle cx="796" cy="{by}" r="4.5" fill="{C["hi"]}"/>')
    s.body.append(s.text(812, by + 6, "PWR", 15, "#6e665b")[0])
    for kx in (872, 914):
        s.body.append(f'<circle cx="{kx}" cy="{by}" r="14" fill="url(#knob)" stroke="#0c0b0a" stroke-width="2"/>'
                      f'<line x1="{kx}" y1="{by - 11}" x2="{kx}" y2="{by - 5}" stroke="#8a8174" stroke-width="2" stroke-linecap="round"/>')
    s.save("boot.svg")


def keycap(font, name, legend, label):
    W, H = 260, 68
    s = Svg(font, W, H, label.title())
    s.defs.append(FX.split("</filter>")[0] + "</filter>")
    s.defs.append('<linearGradient id="cap" x2="0" y2="1"><stop offset="0" stop-color="#34302a"/>'
                  '<stop offset="1" stop-color="#211e1a"/></linearGradient>')
    s.body.append(f'<rect x="1" y="5" width="{W - 2}" height="{H - 6}" rx="11" fill="#0d0c0a"/>'
                  f'<rect x="1" y="1" width="{W - 2}" height="{H - 8}" rx="11" fill="url(#cap)" stroke="#45403a"/>'
                  f'<rect x="7" y="5" width="{W - 14}" height="{H - 20}" rx="8" fill="#ffffff" fill-opacity=".03"/>')
    g = s.text(18, 24, legend, 16, "dim")[0]
    g += s.text(18, 49, label, 28, "amb")[0]
    ax, ay = W - 38, 22  # ↗ arrow
    g += (f'<path d="M{ax} {ay + 16}L{ax + 16} {ay}M{ax + 5} {ay}H{ax + 16}V{ay + 11}" fill="none" '
          f'stroke="{C["amb"]}" stroke-width="2.2" stroke-linecap="square"/>')
    s.body.append(f'<g filter="url(#glow)">{g}</g>')
    s.save(name)


def finger(font):
    W, H = 960, 380
    s = Svg(font, W, H, "$ finger mann. Login: mann. Name: Mann Kuvadiya. Office: KJSCE, Somaiya Vidyavihar. "
                        "Location: Mumbai, IN. On GitHub since 25 March 2021. Project: " + PROJECT + " Plan: " + " ".join(PLAN))
    x0, x2, lh = 40, 376, 27
    c, (g, cx, t) = [], prompt(s, x0, 46, "finger mann", t=.4)
    c.append(g)
    t += .3
    y = 46
    for left, right in FINGER:
        y += lh
        g = s.runs(x0, y, [(left[0] + " ", "dim"), (left[1], "hi")])[0]
        g += s.runs(x2, y, [(right[0] + " ", "dim"), (right[1], "hi")])[0]
        c.append(line(g, t))
        t += .06
    y += lh
    c.append(line(s.runs(x0, y, [("On since ", "dim"), ("Thu Mar 25 2021", "amb"), (" on github", "dim")])[0], t))
    y += lh
    c.append(line(s.text(x0, y, "No mail.", 21, "dim")[0], t + .06))
    y += lh
    c.append(line(s.runs(x0, y, [("Project: ", "dim"), (PROJECT, "amb")])[0], t + .12))
    y += lh
    c.append(line(s.text(x0, y, "Plan:", 21, "dim")[0], t + .18))
    for i, txt in enumerate(PLAN):
        y += lh
        c.append(line(s.text(x0 + 2 * 8.4, y, txt, 21, "hi" if i == 0 else "mid")[0], t + .24 + i * .06))
    panel(s, "".join(c), active=1)
    s.save("finger.svg")


def nmap(font):
    W, H = 960, 574
    s = Svg(font, W, H, "$ nmap -sV -p- mann. Open ports, one per skill: " +
            "; ".join(f"{p} {svc}: {v}" for p, svc, v in PORTS) + ".")
    x0, lh, cw = 40, 26, 8.4
    cols = [0, 11, 18, 32]
    c, (g, cx, t) = [], prompt(s, x0, 46, "nmap -sV -p- mann", t=.4)
    c.append(g)
    t += .35
    head = [("Starting Nmap 7.95 ( https://nmap.org )", "dim"), ("Nmap scan report for mann (19.07.72.87)", "mid"),
            ("Host is up (0.0028s latency).", "dim"), ("Not shown: 65526 closed tcp ports (reset)", "dim")]
    y = 46
    for txt, fill in head:
        y += lh
        c.append(line(s.text(x0, y, txt, 21, fill)[0], t))
        t += .12
    y += lh * 2
    c.append(line("".join(s.text(x0 + col * cw, y, h, 21, "dim")[0]
                          for col, h in zip(cols, ["PORT", "STATE", "SERVICE", "VERSION"])), t))
    for port, svc, ver in PORTS:
        y += lh
        t += .14
        g = "".join(s.text(x0 + col * cw, y, txt, 21, fill)[0]
                    for col, txt, fill in zip(cols, [port, "open", svc, ver], ["hi", "amb", "mid", "hi"]))
        c.append(line(g, t))
    y += lh * 2
    c.append(line(s.runs(x0, y, [("Service Info: ", "dim"), ("OS: Linux; CPE: cpe:/a:kjsce:btech_it_hons_cyber_security:2028", "mid")])[0], t + .3))
    y += lh
    c.append(line(s.text(x0, y, "Nmap done: 1 IP address (1 host up) scanned since 2021", 21, "amb")[0], t + .45))
    panel(s, "".join(c), active=2)
    s.save("nmap.svg")


def msf_head(font):
    W, H = 960, 262
    s = Svg(font, W, H, "$ msfconsole -q. msf6 > search author:bladekiller246. Matching modules:")
    x0 = 40
    c, (g, cx, t) = [], prompt(s, x0, 46, "msfconsole -q", t=.4)
    c.append(g)
    t += .5
    g, ex = s.text(x0, 74, "msf6", 21, "hi")
    g += f'<rect x="{x0}" y="78" width="{ex - x0:.1f}" height="1.6" fill="{C["hi"]}"/>'
    g2, cx, t2 = s.runs(ex, 74, [(" > ", "hi"), ("search author:bladekiller246", "hi")], t=t, cps=16)
    c.append(line(g, t - .1) + g2)
    t = t2 + .3
    c.append(line(s.text(x0, 128, "Matching Modules", 21, "amb")[0] + s.text(x0, 152, "================", 21, "amb")[0], t))
    hdr = [(40, "#", "start"), (84, "Name", "start"), (640, "Status", "start"), (W - 40, "Link", "end")]
    g = "".join(s.text(x, 206, h, 21, "dim", a)[0] + s.text(x, 230, "-" * len(h), 21, "dim", a)[0] for x, h, a in hdr)
    c.append(line(g, t + .1))
    panel(s, "".join(c))
    s.save("msf-head.svg")


def module(font, i, file, path, status, desc, stack, public):
    W, H = 960, 92
    s = Svg(font, W, H, f"Module {i}: {path}. Status: {status.lower()}. {desc}. Stack: {stack}. "
                        + ("Opens the repository." if public else "Private repository."))
    head, _, leaf = path.rpartition("/")
    c = [s.text(40, 41, str(i), 26, "hi")[0], s.runs(84, 40, [(head + "/", "mid"), (leaf, "hi")], 23)[0]]
    tw = s.width(status, 18)
    if status == "ACTIVE":
        c.append(f'<g class="pulse"><rect x="640" y="22" width="{tw + 16:.1f}" height="24" rx="3" fill="{C["amb"]}"/>'
                 + s.text(648, 40, status, 18, "screen")[0] + "</g>")
    else:
        c.append(f'<rect x="640.6" y="22.6" width="{tw + 15:.1f}" height="23" rx="3" fill="none" stroke="{C["amb"]}" stroke-width="1.2"/>'
                 + s.text(648, 40, status, 18, "amb")[0])
    rx = W - 40
    if public:
        c.append(f'<path d="M{rx - 12} 40L{rx} 28M{rx - 8} 28H{rx}V36" fill="none" stroke="{C["hi"]}" '
                 f'stroke-width="2" stroke-linecap="square"/>' + s.text(rx - 20, 40, "open", 19, "hi", "end")[0])
    else:
        lx = rx - 11
        c.append(f'<g fill="none" stroke="{C["dim"]}" stroke-width="1.8"><rect x="{lx}" y="30" width="11" height="9" rx="1.5"/>'
                 f'<path d="M{lx + 2.5} 30V27a3 3 0 0 1 6 0V30"/></g>' + s.text(rx - 19, 40, "private", 19, "dim", "end")[0])
    c.append(s.text(84, 70, desc, 19, "mid")[0] + s.text(rx, 70, stack, 18, "dim", "end")[0])
    panel(s, "".join(c))
    s.save(file)


def msf_tail(font):
    W, H = 960, 150
    s = Svg(font, W, H, "Interact with a module by name or index; click one above to open its repository.")
    x0 = 40
    c = [s.runs(x0, 40, [("Interact with a module by name or index. For example ", "dim"), ("info 4", "mid"),
                         (", ", "dim"), ("use 4", "mid")], 21)[0],
         s.text(x0, 66, "(or just click one above: public modules open their repo)", 21, "dim")[0]]
    g, ex = s.text(x0, 100, "msf6", 21, "hi")
    g += f'<rect x="{x0}" y="104" width="{ex - x0:.1f}" height="1.6" fill="{C["hi"]}"/>'
    g2, cx = s.text(ex, 100, " > ", 21, "hi")
    c.append(g + g2 + cursor(cx, 100, 0))
    panel(s, "".join(c), active=3)
    s.save("msf-tail.svg")


def log_head(font):
    W, H = 960, 100
    s = Svg(font, W, H, "$ watch -n 43200 snake ~/contributions: the contribution graph, redrawn twice a day.")
    c, (g, cx, t) = [], prompt(s, 40, 44, "watch -n 43200 snake ~/contributions", t=.4, cps=22)
    c.append(g)
    c.append(line(s.text(40, 72, "Every 43200.0s: snake ~/contributions", 21, "dim")[0]
                  + s.text(W - 40, 72, f"{HOST}: redrawn twice a day", 21, "dim", "end")[0], t + .3))
    panel(s, "".join(c))
    s.save("log-head.svg")


def footer(font):
    W, H = 960, 168
    s = Svg(font, W, H, "$ exit. [exited]. Connection to bladekiller246 closed. The CRT powers down to a single glowing line.")
    c, (g, cx, t) = [], prompt(s, 40, 44, "exit", t=.4)
    c.append(g)
    c.append(line(s.text(40, 70, "[exited]", 21, "dim")[0], t + .3))
    c.append(line(s.text(40, 96, f"Connection to {HOST} closed.", 21, "mid")[0], t + .45))
    c.append(line(s.text(W - 40, 96, "thanks for scanning.", 21, "amb", "end")[0], t + .6))
    cx, cy = W / 2, 132
    c.append(f'<g class="pulse"><rect x="{cx - 220}" y="{cy - .8}" width="440" height="1.6" fill="{C["amb"]}" opacity=".45"/>'
             f'<rect x="{cx - 70}" y="{cy - 1}" width="140" height="2" fill="{C["hi"]}" opacity=".8"/>'
             f'<circle cx="{cx}" cy="{cy}" r="3" fill="{C["white"]}"/></g>')
    panel(s, "".join(c))
    s.save("footer.svg")


def main():
    font = load_font()
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("*.svg"):
        old.unlink()
    hero(font)
    for k in KEYS:
        keycap(font, *k)
    finger(font)
    nmap(font)
    msf_head(font)
    for i, m in enumerate(MODULES):
        module(font, i, *m)
    msf_tail(font)
    log_head(font)
    footer(font)


if __name__ == "__main__":
    main()
