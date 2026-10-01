"""GitHub profile README in the style of the landing page, with the profile-picture palette.

Run:  python build_profile.py   -> writes ./assets/p/*-{dark,light}.svg and ./README.md
Palette: warm near-black + parchment cream + wyvern rust + sky teal (sampled from the avatar).
Fonts (OFL): Space Grotesk, Inter, JetBrains Mono — subset per SVG and embedded.
"""
import base64
import html
import io
import math
import re
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent if HERE.name == "scripts" else HERE
SRC = HERE / "fonts" if (HERE / "fonts").exists() else ROOT / "src"
OUT = ROOT / "assets" / "p"

THEMES = {
    "dark": dict(
        bg="#15110F", panel="#1D1815", panel2="#241D19", line="#382C26", line2="#4A3B33",
        text="#F0E6D6", muted="#A89A8C", faint="#6F625A",
        acc="#E2673F", acc_ink="#1A0F0A", acc_dim="#7A3A26",
        teal="#79B4AE", teal_bg="#1C2826", acc_bg="#2B1A13",
        red="#E06C5A", dot="#FFF0DC", dot_op="0.05", glow="0.10", shadow="0.55",
        pipes="#4A3B33",
    ),
    "light": dict(
        bg="#F4ECDF", panel="#FCF7EF", panel2="#EFE5D5", line="#E0D3BF", line2="#D2C2AA",
        text="#2A1A12", muted="#6A574A", faint="#A08E7E",
        acc="#B5482B", acc_ink="#FFFFFF", acc_dim="#E8B8A6",
        teal="#2F6466", teal_bg="#E3EEEB", acc_bg="#F7E3D9",
        red="#B5482B", dot="#3C1E0A", dot_op="0.07", glow="0.14", shadow="0.18",
        pipes="#D2C2AA",
    ),
}

# ----------------------------------------------------------------------------- fonts

FONT_SRC = {
    "SG": ("SpaceGrotesk-var.woff2", 600),
    "SGB": ("SpaceGrotesk-var.woff2", 700),
    "IN": ("Inter-var.woff2", 400),
    "INB": ("Inter-var.woff2", 600),
    "JB": ("JetBrainsMono-var.woff2", 400),
    "JBB": ("JetBrainsMono-var.woff2", 600),
}
_inst = {}


def instanced(key):
    if key not in _inst:
        fn, w = FONT_SRC[key]
        f = instancer.instantiateVariableFont(TTFont(SRC / fn), {"wght": w})
        buf = io.BytesIO()
        f.save(buf)
        _inst[key] = buf.getvalue()
    return _inst[key]


def face(key, chars):
    f = TTFont(io.BytesIO(instanced(key)))
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern", "liga", "calt"]
    sub = subset.Subsetter(opts)
    sub.populate(text=chars)
    sub.subset(f)
    f.flavor = "woff2"
    buf = io.BytesIO()
    f.save(buf)
    return f"@font-face{{font-family:'{key}x';src:url(data:font/woff2;base64,{base64.b64encode(buf.getvalue()).decode()}) format('woff2');}}"


FALLBACK = {
    "SG": "'Space Grotesk','Segoe UI',Helvetica,Arial,sans-serif", "SGB": "'Space Grotesk','Segoe UI',Helvetica,Arial,sans-serif",
    "IN": "Inter,'Segoe UI',Helvetica,Arial,sans-serif", "INB": "Inter,'Segoe UI',Helvetica,Arial,sans-serif",
    "JB": "'JetBrains Mono',Consolas,monospace", "JBB": "'JetBrains Mono',Consolas,monospace",
}

# ----------------------------------------------------------------------------- svg builder


class Svg:
    def __init__(self, c, w, h, label):
        self.c, self.w, self.h, self.label = c, w, h, label
        self.parts, self.css = [], []
        self.used = {}  # font key -> chars

    def add(self, s):
        self.parts.append(s)
        return self

    def t(self, x, y, s, font="IN", size=15, fill=None, anchor="start", extra="", ls=None):
        """Text. `s` may contain <tspan> markup; chars are collected for subsetting."""
        fill = fill or self.c["text"]
        plain = re.sub(r"<[^>]+>", "", s)
        self.used.setdefault(font, set()).update(html.unescape(plain))
        for m in re.finditer(r'class="f-(\w+)"', s):  # fonts used inside tspans
            self.used.setdefault(m.group(1), set()).update(html.unescape(plain))
        lsp = f' letter-spacing="{ls}"' if ls is not None else ""
        self.parts.append(f'<text class="f-{font}" x="{x}" y="{y}" font-size="{size}" fill="{fill}" text-anchor="{anchor}"{lsp}{extra}>{s}</text>')
        return self

    def render(self):
        faces = "\n".join(face(k, "".join(sorted(v)) + " ") for k, v in self.used.items())
        cls = "\n".join(f".f-{k}{{font-family:'{k}x',{FALLBACK[k]};}}" for k in FONT_SRC)
        c = self.c
        css = f"""<style>
{faces}
{cls}
.flow{{fill:none;stroke:{c['teal']};stroke-width:1.5;stroke-dasharray:3 9;stroke-linecap:round;animation:flow 1.4s linear infinite;opacity:.9}}
.flow.acc{{stroke:{c['acc']};}} .flow.rev{{animation-direction:reverse;}}
.pulse{{animation:pulse 2s ease-out infinite;transform-box:fill-box;transform-origin:center;}}
.blink{{animation:blink 1.1s steps(1) infinite;}}
@keyframes flow{{to{{stroke-dashoffset:-24;}}}}
@keyframes pulse{{0%{{transform:scale(1);opacity:.8}}80%,100%{{transform:scale(2.8);opacity:0}}}}
@keyframes blink{{50%{{opacity:0;}}}}
{''.join(self.css)}
@media (prefers-reduced-motion: reduce){{*{{animation:none !important;}}}}
</style>"""
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="{self.w}" height="{self.h}" '
                f'role="img" aria-label="{html.escape(self.label)}">\n{css}\n' + "\n".join(self.parts) + "\n</svg>\n")


def esc(s):
    return html.escape(s, quote=False)


def wrap(text, width_px, size, k=0.52):
    max_chars = max(8, int(width_px / (size * k)))
    words, lines, cur = text.split(), [], ""
    for wd in words:
        if cur and len(cur) + 1 + len(wd) > max_chars:
            lines.append(cur)
            cur = wd
        else:
            cur = f"{cur} {wd}" if cur else wd
    if cur:
        lines.append(cur)
    return lines


def para(s, x, y, text, width, size=15, font="IN", fill=None, lh=1.5, k=0.52):
    lines = wrap(text, width, size, k)
    for i, ln in enumerate(lines):
        s.t(x, round(y + i * size * lh, 1), esc(ln), font, size, fill)
    return y + len(lines) * size * lh


def dots(s, pid, x, y, w, h, rx=10, step=16):
    c = s.c
    s.add(f'<defs><pattern id="{pid}" width="{step}" height="{step}" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="{c["dot"]}" fill-opacity="{c["dot_op"]}"/></pattern></defs>')
    s.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="url(#{pid})"/>')


def panel(s, x, y, w, h, rx=10, fill=None, stroke=None):
    c = s.c
    s.add(f'<rect x="{x+0.5}" y="{y+0.5}" width="{w-1}" height="{h-1}" rx="{rx}" fill="{fill or c["panel"]}" stroke="{stroke or c["line"]}"/>')


def pill(s, x, y, text, color, bg_op=0.1, font="JB", size=11.5, pad=11, h=24):
    w = len(text) * size * 0.6 + pad * 2
    s.add(f'<rect x="{x}" y="{y}" width="{w:.0f}" height="{h}" rx="{h/2}" fill="{color}" fill-opacity="{bg_op}" stroke="{color}" stroke-opacity="0.4"/>')
    s.t(round(x + w / 2, 1), y + h / 2 + size * 0.36, esc(text), font, size, color, "middle")
    return w


def button(s, x, y, text, primary, size=13):
    c = s.c
    w = len(text) * size * 0.6 + 36
    if primary:
        s.add(f'<rect x="{x}" y="{y}" width="{w:.0f}" height="42" rx="3" fill="{c["acc"]}"/>')
        s.t(round(x + w / 2, 1), y + 26, esc(text), "JBB", size, c["acc_ink"], "middle")
    else:
        s.add(f'<rect x="{x+0.5}" y="{y+0.5}" width="{w-1:.0f}" height="41" rx="3" fill="{c["panel"]}" stroke="{c["line2"]}"/>')
        s.t(round(x + w / 2, 1), y + 26, esc(text), "JB", size, c["text"], "middle")
    return w


# ----------------------------------------------------------------------------- hero

def hero(c, tabs=("home", "systems", "ps", "homelab", "ai", "quests", "contact")):
    w, h = 1000, 500
    s = Svg(c, w, h, "Tomás Caporaso — Backend systems, built to be understood. Available for part-time / async roles.")
    s.add(f'<defs><radialGradient id="hg" cx="0.92" cy="0.05" r="0.6"><stop offset="0" stop-color="{c["acc"]}" stop-opacity="{c["glow"]}"/><stop offset="1" stop-color="{c["acc"]}" stop-opacity="0"/></radialGradient>'
          f'<linearGradient id="ul" x1="0" x2="1"><stop offset="0" stop-color="{c["acc"]}"/><stop offset="1" stop-color="{c["teal"]}"/></linearGradient>'
          f'<radialGradient id="hm" cx="0.3" cy="0.45" r="0.6"><stop offset="0.3" stop-color="#fff"/><stop offset="1" stop-color="#000"/></radialGradient>'
          f'<mask id="hmask"><rect width="{w}" height="{h}" fill="url(#hm)"/></mask></defs>')
    s.add(f'<rect width="{w}" height="{h}" rx="12" fill="{c["bg"]}"/>')
    s.add(f'<g mask="url(#hmask)">')
    dots(s, "hd", 0, 0, w, h, 12, 22)
    s.add("</g>")
    s.add(f'<rect width="{w}" height="{h}" rx="12" fill="url(#hg)"/>')
    s.add(f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="12" fill="none" stroke="{c["line"]}"/>')

    # waybar
    s.add(f'<path d="M12 0.5 H{w-12} A11.5 11.5 0 0 1 {w-.5} 12 V46 H.5 V12 A11.5 11.5 0 0 1 12 .5Z" fill="{c["panel"]}"/>')
    s.add(f'<line x1="0" y1="46" x2="{w}" y2="46" stroke="{c["line"]}"/>')
    s.t(26, 28, f'<tspan fill="{c["teal"]}">~</tspan> tomas<tspan fill="{c["acc"]}">.</tspan>caporaso', "JBB", 13)
    x = 200
    for i, name in enumerate(tabs):
        lab = f"{i+1} {name}"
        ww = len(lab) * 7.2 + 16
        if i == 0:
            s.add(f'<rect x="{x}" y="12" width="{ww:.0f}" height="22" rx="3" fill="{c["acc"]}"/>')
            s.t(round(x + ww / 2, 1), 27, lab, "JBB", 12, c["acc_ink"], "middle")
        else:
            s.t(round(x + ww / 2, 1), 27, f'<tspan fill="{c["faint"]}">{i+1}</tspan> {name}', "JB", 12, c["muted"], "middle")
        x += ww + 4
    rx = w - 18
    for mod in ["BA · UTC-3", "mate ●●●○", "ts ▲ up"]:
        ww = len(mod) * 7.2 + 18
        rx -= ww
        s.add(f'<rect x="{rx:.0f}" y="11" width="{ww:.0f}" height="24" rx="3" fill="{c["panel2"]}" stroke="{c["line"]}"/>')
        col = c["teal"] if "up" in mod else (c["acc"] if "mate" in mod else c["muted"])
        s.t(round(rx + ww / 2, 1), 27.5, esc(mod), "JB", 12, col, "middle")
        rx -= 6

    # left column
    lx = 44
    s.add(f'<rect x="{lx}" y="84" width="330" height="28" rx="14" fill="{c["teal"]}" fill-opacity="0.08" stroke="{c["teal"]}" stroke-opacity="0.35"/>')
    s.add(f'<circle class="pulse" cx="{lx+16}" cy="98" r="3.5" fill="{c["teal"]}"/><circle cx="{lx+16}" cy="98" r="3.5" fill="{c["teal"]}"/>')
    s.t(lx + 30, 102.5, "available for part-time / async roles", "JB", 12.5, c["teal"])
    s.t(lx - 3, 178, "Backend systems,", "SG", 54, c["text"], ls=-1.6)
    s.t(lx - 3, 238, "built to be", "SG", 54, c["acc"], ls=-1.6)
    s.add(f'<rect x="{lx}" y="249" height="5" rx="2.5" width="0" fill="url(#ul)"><animate attributeName="width" from="0" to="272" begin="0.5s" dur="0.9s" fill="freeze" calcMode="spline" keySplines=".2 .8 .2 1"/></rect>')
    s.t(lx - 3, 304, "understood.", "SG", 54, c["text"], ls=-1.6)
    s.t(lx, 348, f'I design <tspan class="f-INB" fill="{c["text"]}">event-driven backends</tspan> and <tspan class="f-INB" fill="{c["text"]}">multi-agent</tspan>', "IN", 17, c["muted"])
    s.t(lx, 374, f'<tspan class="f-INB" fill="{c["text"]}">systems</tspan>: clean boundaries, explicit contracts, and', "IN", 17, c["muted"])
    s.t(lx, 400, "infrastructure I run myself end to end.", "IN", 17, c["muted"])
    bx = lx
    bx += button(s, bx, 428, "masega360.github.io ↗", True) + 10
    button(s, bx, 428, "Résumé.pdf", False)

    # terminal
    tx, ty, tw, th = 560, 92, 396, 330
    s.add(f'<rect x="{tx+8}" y="{ty+16}" width="{tw}" height="{th}" rx="8" fill="#000" opacity="{c["shadow"]}" filter="url(#blur)"/>')
    s.add(f'<defs><filter id="blur" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="14"/></filter></defs>')
    panel(s, tx, ty, tw, th, 8)
    s.add(f'<path d="M{tx+8} {ty+.5} H{tx+tw-8} A7.5 7.5 0 0 1 {tx+tw-.5} {ty+8} V{ty+34} H{tx+.5} V{ty+8} A7.5 7.5 0 0 1 {tx+8} {ty+.5}Z" fill="{c["panel2"]}"/>')
    s.add(f'<line x1="{tx}" y1="{ty+34}" x2="{tx+tw}" y2="{ty+34}" stroke="{c["line"]}"/>')
    for i, col in enumerate(["#E06C5A", "#E2A13F", c["teal"]]):
        s.add(f'<circle cx="{tx+18+i*16}" cy="{ty+17}" r="5" fill="{col}"/>')
    s.t(tx + tw / 2 + 20, ty + 21.5, "tomas@masega360: ~", "JB", 11.5, c["muted"], "middle")
    lines = [
        ("cmd", f'<tspan fill="{c["teal"]}">$</tspan> cat status.json'),
        ("out", f'<tspan fill="{c["faint"]}">{{</tspan>'),
        ("out", f'  <tspan fill="{c["muted"]}">"role"</tspan>: <tspan fill="{c["acc"]}">["backend", "applied_ai"]</tspan>,'),
        ("out", f'  <tspan fill="{c["muted"]}">"langs"</tspan>: <tspan fill="{c["acc"]}">["Go", "Rust", "C", "Kotlin"]</tspan>,'),
        ("out", f'  <tspan fill="{c["muted"]}">"infra"</tspan>: <tspan fill="{c["acc"]}">["Linux", "Docker", "Tailscale"]</tspan>,'),
        ("out", f'  <tspan fill="{c["muted"]}">"tz"</tspan>: <tspan fill="{c["acc"]}">"UTC-3 (Buenos Aires)"</tspan>,'),
        ("out", f'  <tspan fill="{c["muted"]}">"availability"</tspan>: <tspan fill="{c["acc"]}">"part-time / async"</tspan>'),
        ("out", f'<tspan fill="{c["faint"]}">}}</tspan>'),
    ]
    y, t = ty + 68, 0.4
    clips = []
    for i, (kind, txt) in enumerate(lines):
        plain = html.unescape(re.sub(r"<[^>]+>", "", txt))
        n = len(plain)
        dur = 0.045 * n if kind == "cmd" else 0.06
        clips.append(f'<clipPath id="tl{i}"><rect x="{tx+14}" y="{y-16}" height="24" width="0"><animate attributeName="width" from="0" to="{n*7.6+10:.0f}" begin="{t:.2f}s" dur="{dur:.2f}s" fill="freeze"/></rect></clipPath>')
        s.t(tx + 20, y, txt, "JB", 12.5, c["text"], extra=f' clip-path="url(#tl{i})" xml:space="preserve"')
        t += dur + (0.3 if kind == "cmd" else 0.08)
        y += 29
    s.add("<defs>" + "".join(clips) + "</defs>")
    s.add(f'<g opacity="0"><animate attributeName="opacity" to="1" begin="{t:.2f}s" dur="0.01s" fill="freeze"/>')
    s.t(tx + 20, y, "$", "JB", 12.5, c["teal"])
    s.add(f'<rect class="blink" x="{tx+34}" y="{y-12}" width="8" height="15" fill="{c["acc"]}"/></g>')
    return s.render()


# ----------------------------------------------------------------------------- section header

def header(c, l1, l2, note):
    w, h = 1000, 150
    s = Svg(c, w, h, f"{l1} {l2}")
    s.t(-2, 70, esc(l1), "SG", 44, c["text"], ls=-1.3)
    if l2:
        s.t(-2, 122, esc(l2), "SG", 44, c["acc"], ls=-1.3)
    if note:
        para(s, 620, 74, note, 370, 15.5, "IN", c["muted"])
    s.add(f'<line x1="0" y1="{h-1}" x2="{w}" y2="{h-1}" stroke="{c["line"]}"/>')
    s.add(f'<line x1="0" y1="{h-1}" x2="0" y2="{h-1}" stroke="{c["acc"]}" stroke-width="2"><animate attributeName="x2" from="0" to="140" begin="0.2s" dur="0.8s" fill="freeze"/></line>')
    return s.render()


# ----------------------------------------------------------------------------- diagrams (shared with the landing)

def node_css(c):
    return f"""
.n rect{{fill:{c['panel']};stroke:{c['line2']};}} .n text{{font-family:'JBx',{FALLBACK['JB']};font-size:11px;fill:{c['text']};text-anchor:middle;}}
.n .sub{{fill:{c['muted']};font-size:9.5px;}}
.n.core rect{{fill:{c['teal_bg']};stroke:{c['teal']};}} .n.core text{{fill:{c['teal']};font-family:'JBBx',{FALLBACK['JB']};}}
.n.gate rect{{fill:{c['acc_bg']};stroke:{c['acc']};}} .n.gate text{{fill:{c['acc']};font-family:'JBBx',{FALLBACK['JB']};}}
.e{{fill:none;stroke:{c['line2']};stroke-width:1.2;}}
.lbl{{font-family:'JBx',{FALLBACK['JB']};font-size:9.5px;fill:{c['faint']};}}
"""


VECFIN = """
<path class="e" d="M92 22 C130 22 132 108 166 108"/><path class="e" d="M92 66 C130 66 132 112 166 112"/><path class="e" d="M92 110 C130 110 132 116 166 116"/>
<path class="e" d="M92 154 C130 154 132 120 166 120"/><path class="e" d="M92 198 C130 198 132 124 166 124"/>
<path class="flow" d="M92 22 C130 22 132 108 166 108"/><path class="flow" d="M92 66 C130 66 132 112 166 112" style="animation-delay:-.3s"/>
<path class="flow" d="M92 110 C130 110 132 116 166 116" style="animation-delay:-.6s"/><path class="flow" d="M92 154 C130 154 132 120 166 120" style="animation-delay:-.9s"/>
<path class="flow" d="M92 198 C130 198 132 124 166 124" style="animation-delay:-1.2s"/>
<path class="e" d="M266 110 C284 110 282 42 300 42"/><path class="e" d="M266 116 L300 116"/><path class="e" d="M266 122 C284 122 282 190 300 190"/>
<path class="flow acc" d="M266 110 C284 110 282 42 300 42"/><path class="flow acc" d="M266 116 L300 116" style="animation-delay:-.5s"/><path class="flow acc" d="M266 122 C284 122 282 190 300 190" style="animation-delay:-1s"/>
<path class="e" d="M216 136 L216 186"/><path class="flow rev" d="M216 136 L216 186"/>
<g class="n"><rect x="2" y="10" width="90" height="24" rx="3"/><text x="47" y="26">Binance</text></g>
<g class="n"><rect x="2" y="54" width="90" height="24" rx="3"/><text x="47" y="70">Kraken</text></g>
<g class="n"><rect x="2" y="98" width="90" height="24" rx="3"/><text x="47" y="114">IOL</text></g>
<g class="n"><rect x="2" y="142" width="90" height="24" rx="3"/><text x="47" y="158">Yahoo Fin.</text></g>
<g class="n"><rect x="2" y="186" width="90" height="24" rx="3"/><text x="47" y="202">MercadoPago</text></g>
<g class="n core"><rect x="166" y="94" width="100" height="42" rx="4"/><text x="216" y="113">Go API</text><text class="sub" x="216" y="127">REST · JWT</text></g>
<g class="n"><rect x="176" y="186" width="80" height="26" rx="3"/><text x="216" y="203">Expo app</text></g>
<g class="n"><rect x="300" y="30" width="98" height="24" rx="3"/><text x="349" y="46">PostgreSQL</text></g>
<g class="n"><rect x="300" y="104" width="98" height="24" rx="3"/><text x="349" y="120">Bedrock/Gemini</text></g>
<g class="n"><rect x="300" y="178" width="98" height="24" rx="3"/><text x="349" y="194">alert worker</text></g>
"""

ANIMA = """
<line x1="10" y1="118" x2="390" y2="118" stroke="{teal}" stroke-width="2"/>
<circle r="3.5" fill="{acc}"><animateMotion dur="3.2s" repeatCount="indefinite" path="M10 118 L390 118"/></circle>
<circle r="3.5" fill="{acc}" opacity=".6"><animateMotion dur="3.2s" begin="-1.6s" repeatCount="indefinite" path="M390 118 L10 118"/></circle>
<text class="lbl" x="84" y="110">async bus · redis</text><text class="lbl" x="316" y="110" text-anchor="end">+5 modules</text>
<path class="e" d="M72 66 L72 118"/><path class="flow" d="M72 66 L72 118"/>
<path class="e" d="M200 66 L200 118"/><path class="flow rev" d="M200 66 L200 118"/>
<path class="e" d="M328 66 L328 118"/><path class="flow" d="M328 66 L328 118" style="animation-delay:-.7s"/>
<path class="e" d="M72 118 L72 170"/><path class="flow rev" d="M72 118 L72 170"/>
<path class="e" d="M200 118 L200 170"/><path class="flow acc" d="M200 118 L200 170"/>
<path class="e" d="M328 118 L328 170"/>
<path class="e" d="M246 191 L282 191"/><path class="flow acc" d="M246 191 L282 191"/>
<g class="n"><rect x="26" y="26" width="92" height="40" rx="3"/><text x="72" y="44">Sensus</text><text class="sub" x="72" y="57">perception</text></g>
<g class="n core"><rect x="154" y="26" width="92" height="40" rx="3"/><text x="200" y="44">Anima</text><text class="sub" x="200" y="57">orchestrator</text></g>
<g class="n"><rect x="282" y="26" width="92" height="40" rx="3"/><text x="328" y="44">Cogito</text><text class="sub" x="328" y="57">reasoning</text></g>
<g class="n"><rect x="26" y="170" width="92" height="40" rx="3"/><text x="72" y="188">Biblios</text><text class="sub" x="72" y="201">memory</text></g>
<g class="n gate"><rect x="154" y="170" width="92" height="40" rx="3"/><text x="200" y="188">Custos</text><text class="sub" x="200" y="201">risk gate</text></g>
<g class="n"><rect x="282" y="170" width="92" height="40" rx="3"/><text x="328" y="188">Notus</text><text class="sub" x="328" y="201">action</text></g>
"""

DIAGRAM_CHARS = "BinanceKrakenIOLYahooFin.MercadoPagoGoAPIRESTJWTExpoappPostgreSQLBedrock/Geminialertworker·" \
                "asyncbusredis+5modulesSensusperceptionAnimaorchestratorCogitoreasoningBibliosmemoryCustosriskgateNotusaction "


def case(c, *, num, tag, title, badge, private, pitch, spec, foot_l, foot_r, diagram, caption):
    w, h = 1000, 520
    s = Svg(c, w, h, f"Case file {num}: {title}. {pitch}")
    s.css.append(node_css(c))
    s.used.setdefault("JB", set()).update(DIAGRAM_CHARS)
    s.used.setdefault("JBB", set()).update(DIAGRAM_CHARS)
    # outlined number
    s.t(w + 6, 200, num, "SGB", 230, "none", "end", extra=f' stroke="{c["line2"]}" stroke-width="1.5"')
    s.t(0, 36, f'CASE FILE <tspan fill="{c["acc"]}">/ {esc(tag.upper())}</tspan>', "JB", 12, c["faint"], ls=1.2)
    s.t(-3, 108, esc(title), "SGB", 70, c["text"], ls=-2.6)
    tw = len(title) * 70 * 0.56
    pill(s, tw + 18, 74, badge, c["acc"] if private else c["teal"])
    para(s, 0, 150, pitch, 640, 18.5, "IN", c["muted"], 1.45)
    # spec table
    sy, sw = 214, 410
    rows = []
    for k, v in spec:
        lines = wrap(v, sw - 140, 14.5, k=0.58)
        rows.append((k, lines, 22 + len(lines) * 21))
    sh = sum(r[2] for r in rows) + 50
    panel(s, 0, sy, sw, sh, 10)
    y = sy
    for i, (k, lines, rh) in enumerate(rows):
        if i:
            s.add(f'<line x1="0" y1="{y}" x2="{sw}" y2="{y}" stroke="{c["line"]}"/>')
        s.t(20, y + 27, k.upper(), "JB", 11, c["faint"], ls=0.8)
        for j, ln in enumerate(lines):
            s.t(120, y + 28 + j * 21, esc(ln), "IN", 14.5, c["text"])
        y += rh
    s.add(f'<path d="M.5 {y} H{sw-.5} V{y+40} A9.5 9.5 0 0 1 {sw-10} {y+49.5} H10 A9.5 9.5 0 0 1 .5 {y+40}Z" fill="{c["panel2"]}" stroke="{c["line"]}"/>')
    s.t(20, y + 30, esc(foot_l), "JBB", 13, c["acc"])
    s.t(sw - 20, y + 30, esc(foot_r), "JB", 11, c["faint"], "end")
    # diagram
    dx, dw = sw + 24, w - sw - 24
    dh = max(sh, 290)
    panel(s, dx, sy, dw, dh, 10, c["panel2"])
    dots(s, f"dd{num}", dx, sy, dw, dh, 10)
    sc = min(1.27, (dh - 58) / 236)
    gx = dx + (dw - 400 * sc) / 2
    gy = sy + (dh - 30 - 236 * sc) / 2 + 2
    s.add(f'<g transform="translate({gx:.1f} {gy:.1f}) scale({sc:.3f})">{diagram.format(**c)}</g>')
    s.t(dx + dw / 2, sy + dh - 14, esc(caption), "JB", 11, c["faint"], "middle")
    s.h = sy + max(sh, dh) + 6
    return s.render()


# ----------------------------------------------------------------------------- htop

PROCS = [
    ("1337", "Go", "#00ADD8", "R", "21.4", "ai-gateway", "", "One endpoint, many GPUs: Ollama load balancer with queue, health checks and retries."),
    ("2077", "Python", "#5A8FC2", "R", "18.9", "job-hunter-ai", "[private]", "Local agent that hunts jobs and drafts the application."),
    ("3141", "Vue/Py", "#41B883", "R", "9.7", "the-stalker", "", "ESP32 cameras over MQTT, Rekognition / YOLOv8 inference, relays from a web UI."),
    ("4004", "Go", "#00ADD8", "R", "14.2", "latebra", "[private]", "Builds a real-time contextual data lake from your digital life."),
    ("5150", "Python", "#5A8FC2", "R", "11.8", "opticx", "[private]", "Reactive vision-AI pipeline library for AWS."),
    ("6502", "Kotlin", "#A97BFF", "S", "0.3", "KorusLedger", "", "Event-driven finance backend. Sleeping while it gets rewritten in Go."),
]


def htop(c):
    w = 1000
    row_h = 46
    top = 128
    h = top + 30 + len(PROCS) * row_h + 34
    s = Svg(c, w, h, "Process list of projects: " + ", ".join(p[5] for p in PROCS))
    panel(s, 0, 0, w, h, 10)
    # meters
    for i, (lab, pct, col, val) in enumerate([("CPU", 0.62, c["teal"], "62%"), ("Mem", 0.71, c["teal"], "curiosity"), ("Mate", 0.38, c["acc"], "refill soon")]):
        y = 34 + i * 26
        s.t(24, y, lab, "JB", 13, c["teal"])
        s.t(70, y, "[", "JB", 13, c["faint"])
        bw = 330
        n = 44
        s.t(80, y, "|" * n, "JB", 13, c["pipes"], extra=' textLength="%d" lengthAdjust="spacingAndGlyphs"' % bw)
        s.add(f'<clipPath id="m{i}"><rect x="80" y="{y-14}" height="20" width="0"><animate attributeName="width" from="0" to="{bw*pct:.0f}" begin="{0.2+i*0.15:.2f}s" dur="1s" fill="freeze"/></rect></clipPath>')
        s.t(80, y, "|" * n, "JB", 13, col, extra=f' textLength="{bw}" lengthAdjust="spacingAndGlyphs" clip-path="url(#m{i})"')
        s.t(80 + bw + 4, y, "]", "JB", 13, c["faint"])
        s.t(80 + bw + 104, y, esc(val), "JB", 13, c["muted"], "end")
    ix = 560
    s.t(ix, 34, f'Tasks: <tspan class="f-JBB" fill="{c["text"]}">8</tspan>, <tspan class="f-JBB" fill="{c["text"]}">3</tspan> private; <tspan class="f-JBB" fill="{c["teal"]}">5 running</tspan>', "JB", 13, c["muted"])
    s.t(ix, 60, f'Load average: <tspan class="f-JBB" fill="{c["text"]}">0.62 0.58 0.55</tspan>', "JB", 13, c["muted"])
    s.t(ix, 86, f'Uptime: <tspan class="f-JBB" fill="{c["text"]}">3rd year</tspan> @ Universidad Austral', "JB", 13, c["muted"])
    # header row
    s.add(f'<rect x="0" y="{top}" width="{w}" height="28" fill="{c["teal"]}"/>')
    cols = [(20, "PID"), (90, "LANG"), (190, "S"), (270, "CPU%"), (300, "COMMAND")]
    for x, lab in cols:
        s.t(x, top + 19, lab, "JBB", 12, c["acc_ink"] if c is THEMES["dark"] else "#FFFFFF", "end" if lab == "CPU%" else "start")
    y = top + 28
    for i, (pid, lang, lc, st, cpu, name, priv, desc) in enumerate(PROCS):
        if i:
            s.add(f'<line x1="0" y1="{y}" x2="{w}" y2="{y}" stroke="{c["line"]}"/>')
        by = y + 29
        s.t(20, by, pid, "JB", 13, c["faint"])
        s.add(f'<circle cx="94" cy="{by-4.5}" r="4" fill="{lc}"/>')
        s.t(104, by, lang, "JB", 13, c["muted"])
        s.t(190, by, st, "JBB", 13, c["teal"] if st == "R" else c["muted"])
        s.t(270, by, cpu, "JB", 13, c["text"], "end")
        nx = 300
        s.t(nx, by, esc(name), "JBB", 13.5, c["text"])
        nx += len(name) * 8.1 + 8
        if priv:
            s.t(nx, by, priv, "JB", 11, c["acc"])
            nx += len(priv) * 6.6 + 8
        s.t(nx, by, esc(desc), "IN", 13.5, c["muted"])
        y += row_h
    # function keys
    s.add(f'<path d="M.5 {y} H{w-.5} V{h-10} A9.5 9.5 0 0 1 {w-10} {h-.5} H10 A9.5 9.5 0 0 1 .5 {h-10}Z" fill="{c["panel2"]}" stroke="{c["line"]}"/>')
    fx = 0
    for k, lab in [("F1", "GitHub"), ("F2", "LinkedIn"), ("F3", "Résumé"), ("F4", "Homelab"), ("F5", "AI"), ("F9", "Hire"), ("F10", "Quit")]:
        s.t(fx + 12, y + 22, k, "JB", 12, c["text"])
        kx = fx + 12 + len(k) * 7.2 + 4
        lw = len(lab) * 7.2 + 18
        s.add(f'<rect x="{kx:.0f}" y="{y+5}" width="{lw:.0f}" height="24" fill="{c["teal"]}" fill-opacity="0.22"/>')
        s.t(round(kx + 6, 1), y + 22, esc(lab), "JB", 12, c["text"])
        fx = kx + lw
    return s.render()


# ----------------------------------------------------------------------------- homelab

def homelab(c):
    w, h = 1000, 420
    s = Svg(c, w, h, "Homelab: a workstation sends requests through a Tailscale mesh to a Raspberry Pi 5 running ai-gateway, which picks between two GPU boxes running Ollama.")
    s.css.append(node_css(c))
    y = para(s, 0, 30, "The best way to understand distributed systems is to be the on-call for one. My projects run on a small fleet at home, stitched together with Tailscale and driven from a Hyprland terminal.", 360, 16.5, "IN", c["muted"], 1.55)
    y = para(s, 0, y + 16, "Requests land on a Raspberry Pi 5 running ai-gateway, which picks whichever GPU box is free. Everything else lives in Docker.", 360, 16.5, "IN", c["muted"], 1.55)
    y += 20
    for node, role in [("pi5", "ai-gateway · :3000"), ("laptop-3090", "ollama · gpu"), ("pc-backup", "ollama · fallback"), ("docker-host", "portainer · mqtt")]:
        s.t(0, y, node, "JBB", 13, c["text"])
        s.t(180, y, role, "JB", 12.5, c["muted"], "middle" if False else "start")
        s.t(360, y, "● up", "JB", 12.5, c["teal"], "end")
        s.add(f'<line x1="0" y1="{y+12}" x2="360" y2="{y+12}" stroke="{c["line2"]}" stroke-dasharray="3 4"/>')
        y += 34
    mx, my, mw, mh = 400, 0, 600, 410
    panel(s, mx, my, mw, mh, 12, c["panel2"])
    dots(s, "ld", mx, my, mw, mh, 12)
    sc = 1.08
    g = f"""
<ellipse cx="260" cy="180" rx="236" ry="158" fill="none" stroke="{c['line2']}" stroke-dasharray="2 6"/>
<text class="lbl" x="260" y="16" text-anchor="middle">tailnet · 100.x.y.z</text>
<path class="e" d="M150 96 C200 96 210 170 228 170"/><path class="flow acc" d="M150 96 C200 96 210 170 228 170"/>
<path class="e" d="M330 170 C360 170 360 96 390 96"/><path class="flow" d="M330 170 C360 170 360 96 390 96"/>
<path class="e" d="M330 186 C360 186 360 264 390 264"/><path class="flow" d="M330 186 C360 186 360 264 390 264" style="animation-delay:-.7s"/>
<path class="e" d="M150 264 L228 264"/><path class="flow rev" d="M150 264 L228 264"/>
<g class="n"><rect x="40" y="72" width="110" height="48" rx="4"/><text x="95" y="93">workstation</text><text class="sub" x="95" y="108">hyprland · zsh</text></g>
<g class="n core"><rect x="228" y="152" width="102" height="52" rx="5"/><text x="279" y="174">pi5</text><text class="sub" x="279" y="190">ai-gateway</text></g>
<g class="n"><rect x="390" y="72" width="104" height="48" rx="4"/><text x="442" y="93">laptop-3090</text><text class="sub" x="442" y="108">ollama · prio 1</text></g>
<g class="n"><rect x="390" y="240" width="104" height="48" rx="4"/><text x="442" y="261">pc-backup</text><text class="sub" x="442" y="276">ollama · prio 2</text></g>
<g class="n"><rect x="40" y="240" width="110" height="48" rx="4"/><text x="95" y="261">esp32 cams</text><text class="sub" x="95" y="276">mqtt publish</text></g>
<g class="n gate"><rect x="228" y="240" width="102" height="48" rx="4"/><text x="279" y="261">docker-host</text><text class="sub" x="279" y="276">portainer</text></g>
<text class="lbl" x="178" y="128">POST /api/generate</text>
<text class="lbl" x="352" y="140" text-anchor="middle">least load</text>
<text class="lbl" x="189" y="256" text-anchor="middle">jpeg frames</text>
<text class="lbl" x="260" y="338" text-anchor="middle">fig.3 — requests hit the Pi, the Pi picks a GPU</text>
"""
    s.used.setdefault("JB", set()).update(re.sub(r"<[^>]+>", "", g))
    s.used.setdefault("JBB", set()).update("pi5ai-gatewaydocker-host")
    s.add(f'<g transform="translate({mx + (mw - 520*sc)/2:.1f} {my+14}) scale({sc})">{g}</g>')
    return s.render()


# ----------------------------------------------------------------------------- applied AI

LAYERS = [
    ("pixels", "structured events", "Perception", [
        "Reactive frame pipelines with quality gates that drop blurry, dark and duplicate frames before inference",
        "YOLO, DeepFace, InsightFace locally; Rekognition and SageMaker endpoints in the cloud",
        "120 fps ball tracking with background subtraction and camera calibration"], "opticx · golf-sim-vision · the-stalker"),
    ("requests", "tokens", "Serving", [
        "Inference gateway over Ollama nodes: priority + load routing, bounded queue, health checks, retries",
        "One OpenAI-compatible surface so every project is model-agnostic",
        "Cross-provider fallback (Bedrock / Gemini) when a cloud model degrades"], "ai-gateway · VecFin"),
    ("goals", "tool calls", "Agents", [
        "Tool loops with function calling: the model picks the next step from persistent state",
        "Semantic classification instead of keyword matching; structured outputs validated before use",
        "Side effects behind dry-run by default: the agent drafts, a human approves"], "job-hunter-ai · latebra"),
    ("intent", "approved action", "Memory & oversight", [
        "Episodic, semantic and procedural memory, with temperature deciding what gets consolidated",
        "A risk gate classifies every action SAFE / REVERSIBLE / IRREVERSIBLE / FORBIDDEN",
        "Small specialized models with explicit I/O contracts over one large general one"], "anima"),
]


def ai_layers(c):
    w = 1000
    s = Svg(c, w, 10, "Applied AI across four layers: perception, serving, agents, memory and oversight.")
    # thesis
    s.add(f'<rect x="0" y="6" width="3" height="96" fill="{c["acc"]}"/>')
    s.t(24, 36, "The model is the easy part.", "SG", 25, c["text"], ls=-0.4)
    para(s, 24, 68, "What decides whether an AI system works is everything around it: what it's allowed to see, where it runs, which tools it can call, what it remembers, and who checks it before it acts.", 900, 18, "SG", c["muted"], 1.4, k=0.5)
    top = 140
    colw = w / 4
    heights = []
    blocks = []
    for io_in, io_out, title, items, src in LAYERS:
        lines = [wrap(it, colw - 52, 13.5) for it in items]
        heights.append(96 + sum(len(l) * 19.5 + 12 for l in lines) + 56)
        blocks.append(lines)
    lh = max(heights)
    panel(s, 0, top, w, lh, 10)
    for i, ((io_in, io_out, title, items, src), lines) in enumerate(zip(LAYERS, blocks)):
        x = i * colw
        if i:
            s.add(f'<line x1="{x}" y1="{top}" x2="{x}" y2="{top+lh}" stroke="{c["line"]}"/>')
            s.add(f'<circle cx="{x}" cy="{top+32}" r="9" fill="{c["panel"]}" stroke="{c["line"]}"/>')
            s.t(x, top + 36, "→", "JB", 10, c["acc"], "middle")
        s.t(x + 22, top + 34, f'IN <tspan fill="{c["teal"]}">{io_in.upper()}</tspan> · OUT <tspan fill="{c["teal"]}">{io_out.upper()}</tspan>', "JB", 10, c["faint"], ls=0.5)
        s.t(x + 22, top + 68, esc(title), "SG", 20, c["text"])
        y = top + 100
        for ln in lines:
            s.add(f'<rect x="{x+22}" y="{y-9}" width="5" height="5" fill="{c["acc"]}"/>')
            for j, l in enumerate(ln):
                s.t(x + 36, round(y + j * 19.5, 1), esc(l), "IN", 13.5, c["text"])
            y += len(ln) * 19.5 + 12
        for j, ln in enumerate(wrap(src, colw - 40, 10.5, k=0.6)):
            s.t(x + 22, top + lh - 30 + j * 15, esc(ln), "JB", 10.5, c["muted"])
    s.h = top + lh + 4
    return s.render()


def ai_figs(c):
    w, h = 1000, 470
    s = Svg(c, w, h, "Figure 4: memory temperature over time. Figure 5: frames filtered by cheap quality gates before inference.")
    fw = 488
    # ---- fig 4
    panel(s, 0, 0, fw, h, 10)
    s.t(22, 32, f'fig.4 <tspan fill="{c["acc"]}">/ anima · biblios</tspan>', "JB", 11, c["faint"])
    s.t(22, 60, "Memory temperature", "SG", 19, c["text"])
    para(s, 22, 86, "Access warms a memory with diminishing returns; idle time cools it exponentially. Cold memories get consolidated into semantic knowledge.", fw - 44, 13.5, "IN", c["muted"], 1.45)
    cx, cy, cw, ch = 22, 140, fw - 44, 200
    panel(s, cx, cy, cw, ch, 8, c["panel2"])
    X0, X1, Y0, Y1 = cx + 34, cx + cw - 14, cy + ch - 24, cy + 16
    for v, lab in ((1, "1.0"), (0.5, "0.5"), (0, "0")):
        yy = Y0 - v * (Y0 - Y1)
        s.add(f'<line x1="{X0}" y1="{yy}" x2="{X1}" y2="{yy}" stroke="{c["line"]}"/>')
        s.t(X0 - 8, yy + 3.5, lab, "JB", 10, c["faint"], "end")
    theta = 0.18
    ty = Y0 - theta * (Y0 - Y1)
    s.add(f'<line x1="{X0}" y1="{ty}" x2="{X1}" y2="{ty}" stroke="{c["teal"]}" stroke-dasharray="4 4"/>')
    s.t(X1, ty - 6, "θ = 0.18 · consolidate", "JB", 10, c["teal"], "end")
    # simulate the curve
    T, n, pts, acc, cons = 0.0, 0, [], [], []
    accesses = {0, 9, 17, 24, 46, 158, 166}
    steps = 200
    for i in range(steps):
        if i == 158:
            T, n = 0.0, 0  # consolidated: a new episode starts
        if i in accesses:
            n += 1
            T = min(1, T + 0.42 / (1 + math.log(1 + n)))
            acc.append(i)
        T *= math.exp(-0.019)
        if T < theta and not cons and i < 158:
            cons.append(i)
        pts.append(T)
    xs = lambda i: X0 + i / (steps - 1) * (X1 - X0)
    ys = lambda v: Y0 - v * (Y0 - Y1)
    d = " ".join(("M" if i == 0 else "L") + f"{xs(i):.1f} {ys(v):.1f}" for i, v in enumerate(pts))
    s.add(f'<defs><linearGradient id="mg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{c["acc"]}" stop-opacity=".25"/><stop offset="1" stop-color="{c["acc"]}" stop-opacity="0"/></linearGradient>'
          f'<clipPath id="reveal"><rect x="{X0}" y="{Y1-4}" height="{Y0-Y1+14}" width="0"><animate attributeName="width" values="0;{X1-X0};{X1-X0}" keyTimes="0;0.75;1" dur="9s" repeatCount="indefinite"/></rect></clipPath></defs>')
    s.add(f'<g clip-path="url(#reveal)">')
    s.add(f'<path d="{d} L{xs(steps-1):.1f} {Y0} L{X0} {Y0}Z" fill="url(#mg)"/>')
    s.add(f'<path d="{d}" fill="none" stroke="{c["acc"]}" stroke-width="2" stroke-linejoin="round"/>')
    for i in acc:
        s.add(f'<circle cx="{xs(i):.1f}" cy="{Y0+8}" r="2.6" fill="{c["teal"]}"/>')
    for i in cons:
        s.add(f'<line x1="{xs(i):.1f}" y1="{Y1}" x2="{xs(i):.1f}" y2="{Y0}" stroke="{c["teal"]}"/>')
        s.t(round(xs(i) + 5, 1), Y1 + 12, "consolidated", "JB", 9.5, c["teal"])
    s.add("</g>")
    ey = cy + ch + 30
    for ln in [f'access : <tspan class="f-JBB" fill="{c["text"]}">T</tspan> <tspan fill="{c["acc"]}">←</tspan> min(1, T + k / (1 + ln(1 + n)))',
               f'idle   : <tspan class="f-JBB" fill="{c["text"]}">T</tspan> <tspan fill="{c["acc"]}">←</tspan> T · e^(−λ·Δt)',
               f'cold   : T &lt; θ <tspan fill="{c["acc"]}">⇒</tspan> cluster → Cogito → semantic item']:
        s.t(22, ey, ln, "JB", 11.5, c["muted"], extra=' xml:space="preserve"')
        ey += 22

    # ---- fig 5
    ox = fw + 24
    panel(s, ox, 0, fw, h, 10)
    s.t(ox + 22, 32, f'fig.5 <tspan fill="{c["acc"]}">/ opticx</tspan>', "JB", 11, c["faint"])
    s.t(ox + 22, 60, "Pay for inference only when it's worth it", "SG", 19, c["text"])
    para(s, ox + 22, 86, "Frames arrive faster than the model should run. Cheap checks reject what isn't worth a forward pass; only survivors reach the model.", fw - 44, 13.5, "IN", c["muted"], 1.45)
    lx, ly, lw, lh = ox + 22, 140, fw - 44, 200
    panel(s, lx, ly, lw, lh, 8, c["panel2"])
    gates = [("stream", "~4 fps", "120 in"), ("throttle", "≤ 3 fps", "−31"), ("blur", "lapVar≥100", "−22"),
             ("light", "lum ≥ 30", "−9"), ("dedupe", "Δ ≥ 10", "−11"), ("model", "yolo", "47 ✓")]
    gw = lw / 6
    for i, (name, rule, cnt) in enumerate(gates):
        gx = lx + i * gw
        if i:
            s.add(f'<line x1="{gx:.1f}" y1="{ly}" x2="{gx:.1f}" y2="{ly+lh}" stroke="{c["line2"]}" stroke-dasharray="3 4"/>')
        if name == "model":
            s.add(f'<rect x="{gx:.1f}" y="{ly+.5}" width="{gw-.5:.1f}" height="{lh-1}" rx="0" fill="{c["teal"]}" fill-opacity="0.08"/>')
        s.t(round(gx + gw / 2, 1), ly + 20, name, "JBB", 10.5, c["teal"] if name == "model" else c["text"], "middle")
        s.t(round(gx + gw / 2, 1), ly + 35, esc(rule), "JB", 8.5, c["faint"], "middle")
        col = c["muted"] if i == 0 else (c["teal"] if name == "model" else c["red"])
        s.t(round(gx + gw / 2, 1), ly + lh - 12, esc(cnt), "JB", 10.5, col, "middle")
    # animated frames: each chip has a fate (gate index where it is dropped, 5 = reaches the model)
    fates = [5, 1, 2, 5, 3, 4, 5, 2]
    period = 8.0
    chip_w = gw - 10
    for k, fate in enumerate(fates):
        name = f"ch{k}"
        frames = []
        hops = fate
        # timeline (fractions of the period): spawn, hop to each gate, settle, fall/fade
        t0 = 0.0
        frames.append(f"0%{{transform:translate(0px,0px);opacity:1}}")
        for hop in range(1, hops + 1):
            pct = t0 + hop * 7
            frames.append(f"{pct}%{{transform:translate({hop*gw:.1f}px,0px);opacity:1}}")
        end = t0 + hops * 7
        if fate == 5:
            frames.append(f"{end+8}%{{transform:translate({hops*gw:.1f}px,0px);opacity:1}}")
            frames.append(f"{end+12}%{{transform:translate({hops*gw:.1f}px,0px);opacity:0}}")
        else:
            frames.append(f"{end+4}%{{transform:translate({hops*gw:.1f}px,0px) ;opacity:1}}")
            frames.append(f"{end+10}%{{transform:translate({hops*gw:.1f}px,40px) rotate(-10deg);opacity:0}}")
        frames.append("100%{opacity:0}")
        s.css.append(f"@keyframes {name}{{{''.join(frames)}}}"
                     f".{name}{{animation:{name} {period}s linear infinite;animation-delay:{-k*period/len(fates):.2f}s;transform-box:view-box;}}")
        bad = {1: "throttled", 2: "lapVar 61", 3: "lum 18", 4: "Δ 4"}.get(fate)
        stroke = c["teal"] if fate == 5 else c["line2"]
        s.add(f'<g class="{name}"><rect x="{lx+5:.1f}" y="{ly+70}" width="{chip_w:.1f}" height="50" rx="4" fill="{c["panel"]}" stroke="{stroke}"/>')
        txts = ["lapVar 142", "lum 88", "Δ 23"] if fate == 5 else (["throttled", "lum 91", "Δ 17"] if fate == 1 else
               [bad if fate == 2 else "lapVar 156", bad if fate == 3 else "lum 77", bad if fate == 4 else "Δ 21"])
        for j, tx in enumerate(txts):
            col = c["red"] if (tx == bad) else c["muted"]
            s.t(lx + 11, ly + 87 + j * 13, esc(tx), "JB", 9, col)
        s.add("</g>")
    ey = ly + lh + 30
    s.t(ox + 22, ey, f'frames <tspan fill="{c["acc"]}">|</tspan> throttle(333ms) <tspan fill="{c["acc"]}">|</tspan> gate(blur, lum, Δ) <tspan fill="{c["acc"]}">|</tspan> infer', "JB", 11.5, c["muted"])
    s.t(ox + 22, ey + 22, f'<tspan fill="{c["acc"]}">→</tspan> Ok[VisionResult] <tspan fill="{c["acc"]}">|</tspan> Err', "JB", 11.5, c["muted"])
    s.t(ox + 22, ey + 52, f'inference skipped on <tspan class="f-JBB" fill="{c["teal"]}">~60%</tspan> of frames', "JB", 12, c["text"])
    return s.render()


# ----------------------------------------------------------------------------- side quests

QUESTS = [
    ("computer vision", "◯ ⟶", "Golf sim vision", "A PS3 Eye at 120 fps tracking golf balls: ball speed and launch angle.", "Python · OpenCV", "+120 fps", -2.0, "https://github.com/Masega360/golf-sim-vision"),
    ("3d printing", "⊏⊐", "Gripper", "Modular printable holders with dovetail joints, plus a web configurator for the STL.", "OpenSCAD · three.js", "+3 layers", 1.5, "https://github.com/Masega360/gripper"),
    ("game modding", "▓▒░", "LoadingPlus", "An Oxygen Not Included mod that overhauls the loading experience.", "C# · private", "+morale", -1.0, "mailto:tomascaporaso@gmail.com?subject=LoadingPlus"),
    ("tabletop", "d20", "D&D Combat Helper", "An initiative and combat tracker so the DM stops doing math on a napkin.", "JavaScript", "+1 initiative", 2.0, "https://github.com/Masega360/DnD-Combat-Helper"),
]


def quest_card(c, kind, glyph, title, desc, stack, xp, rot):
    w, h = 250, 300
    s = Svg(c, w, h, f"Side quest: {title}. {desc}")
    cx, cy = w / 2, h / 2
    s.add(f'<g transform="rotate({rot} {cx} {cy})">')
    s.add(f'<rect x="20" y="30" width="{w-40}" height="{h-56}" rx="6" fill="#000" opacity="{float(c["shadow"])*0.5}" transform="translate(3 6)"/>')
    panel(s, 18, 28, w - 36, h - 56, 6)
    s.add(f'<rect x="{cx-38}" y="16" width="76" height="22" fill="{c["acc"]}" fill-opacity="0.32" transform="rotate(-3 {cx} 27)"/>')
    s.t(36, 66, f"QUEST · {kind.upper()}", "JB", 9.5, c["faint"], ls=0.8)
    s.t(36, 104, esc(glyph), "JBB", 26, c["acc"])
    s.t(36, 140, esc(title), "SG", 17.5, c["text"])
    para(s, 36, 166, desc, w - 76, 13, "IN", c["muted"], 1.45)
    s.t(36, h - 46, esc(stack), "JB", 10, c["faint"])
    s.t(w - 36, h - 46, esc(xp), "JB", 10, c["teal"], "end")
    s.add("</g>")
    return s.render()


# ----------------------------------------------------------------------------- contact

def contact(c):
    w, h = 1000, 330
    s = Svg(c, w, h, "Let's talk backend. Part-time and async-friendly. Email tomascaporaso@gmail.com")
    s.add(f'<defs><radialGradient id="cg" cx="0.95" cy="1" r="0.6"><stop offset="0" stop-color="{c["acc"]}" stop-opacity="{c["glow"]}"/><stop offset="1" stop-color="{c["acc"]}" stop-opacity="0"/></radialGradient></defs>')
    panel(s, 0, 0, w, h, 14)
    s.add(f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="14" fill="url(#cg)"/>')
    s.t(48, 112, "Let’s talk", "SGB", 76, c["text"], ls=-3)
    s.t(48, 190, "backend.", "SGB", 76, c["acc"], ls=-3)
    s.t(50, 234, "Part-time and async-friendly. UTC-3, comfortable overlapping with US hours.", "IN", 17, c["muted"])
    x = 50
    x += button(s, x, 256, "tomascaporaso@gmail.com →", True) + 10
    x += button(s, x, 256, "LinkedIn ↗", False) + 10
    button(s, x, 256, "Résumé.pdf", False)
    return s.render()


# ----------------------------------------------------------------------------- README

def pic(name, alt, width="100%"):
    return (f'<picture><source media="(prefers-color-scheme: dark)" srcset="assets/p/{name}-dark.svg">'
            f'<source media="(prefers-color-scheme: light)" srcset="assets/p/{name}-light.svg">'
            f'<img alt="{html.escape(alt)}" src="assets/p/{name}-dark.svg" width="{width}"></picture>')


def link(href, inner):
    return f'<a href="{href}">{inner}</a>'


def readme():
    quests = "\n".join(f'  {link(q[7], pic("quest-" + str(i), "Side quest: " + q[2], "24%"))}' for i, q in enumerate(QUESTS))
    return f"""{link("https://masega360.github.io", pic("hero", "Tomás Caporaso — Backend systems, built to be understood."))}

<p align="center">
  <a href="https://masega360.github.io"><b>masega360.github.io</b></a> &nbsp;·&nbsp;
  <a href="https://www.linkedin.com/in/tomas-martin-caporaso-5761572a8">LinkedIn</a> &nbsp;·&nbsp;
  <a href="https://masega360.github.io/Tomas_Caporaso_Resume.pdf">Résumé</a> &nbsp;·&nbsp;
  <a href="mailto:tomascaporaso@gmail.com">tomascaporaso@gmail.com</a>
</p>

<br>

{pic("h-systems", "Two systems, drawn out.")}

{link("https://github.com/Masega360/VecFin", pic("case-vecfin", "Case file 01: VecFin"))}

{link("mailto:tomascaporaso@gmail.com?subject=Anima%20repo%20access", pic("case-anima", "Case file 02: Anima"))}

<br>

{pic("h-ps", "Everything else that's running.")}

{link("https://github.com/Masega360?tab=repositories", pic("htop", "Process list of my other projects"))}

<br>

{pic("h-lab", "I run my own stuff.")}

{pic("homelab", "Homelab map over Tailscale")}

<br>

{pic("h-ai", "Applied AI, end to end.")}

{pic("ai-layers", "Applied AI across perception, serving, agents, memory and oversight")}

{pic("ai-figs", "Memory temperature and inference gating figures")}

<br>

{pic("h-quests", "Side quests.")}

<p align="center">
{quests}
</p>

<br>

{link("mailto:tomascaporaso@gmail.com", pic("contact", "Let's talk backend — tomascaporaso@gmail.com"))}
"""


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    total = 0
    for theme, c in THEMES.items():
        files = {
            "hero": hero(c),
            "h-systems": header(c, "Two systems,", "drawn out.", "These two show the range: money in motion, and agents that have to ask before they act."),
            "case-vecfin": case(c, num="01", tag="fintech", title="VecFin", badge="public repo", private=False,
                                pitch="Your whole net worth in one place: a Go backend that pulls wallets, banks and crypto brokers into one picture, with an AI that explains it back to you.",
                                spec=[("sources", "Binance, Kraken, IOL, MercadoPago, Yahoo Finance, live"),
                                      ("ai", "Chat assistant with dual-provider fallback, Bedrock / Gemini"),
                                      ("extras", "Communities, price-alert worker, PDF fiscal reports, JWT + Google OAuth"),
                                      ("stack", "Go · PostgreSQL · React Native (Expo) · Docker")],
                                foot_l="→ read the source", foot_r="Masega360/VecFin", diagram=VECFIN, caption="fig.1 — data in, decisions out"),
            "case-anima": case(c, num="02", tag="ai oversight", title="Anima", badge="private · on request", private=True,
                               pitch="A multi-agent system where nothing acts without asking first: eleven modules on an async bus, and a risk gate between thinking and doing.",
                               spec=[("gate", "Every action is classified SAFE / REVERSIBLE / IRREVERSIBLE / FORBIDDEN before it runs"),
                                     ("memory", "Episodic → semantic → procedural, consolidated by temperature"),
                                     ("models", "Local inference: Llama 3.1, Qwen 2.5 via Ollama"),
                                     ("stack", "Python asyncio · Redis · Qdrant · FastAPI + WebSocket")],
                               foot_l="→ request access", foot_r="private repo", diagram=ANIMA, caption="fig.2 — nothing executes without passing Custos"),
            "h-ps": header(c, "Everything else", "that's running.", "The private ones are real too; ask and I'll walk you through them."),
            "htop": htop(c),
            "h-lab": header(c, "I run my", "own stuff.", ""),
            "homelab": homelab(c),
            "h-ai": header(c, "Applied AI,", "end to end.", "From pixels to permission: perception pipelines, model serving, tool-using agents, and the memory and guardrails around them."),
            "ai-layers": ai_layers(c),
            "ai-figs": ai_figs(c),
            "h-quests": header(c, "Side quests.", "", "Not everything has to be a backend. Some things just have to exist."),
            "contact": contact(c),
        }
        for i, q in enumerate(QUESTS):
            files[f"quest-{i}"] = quest_card(c, *q[:7])
        for name, body in files.items():
            p = OUT / f"{name}-{theme}.svg"
            p.write_text(body, encoding="utf-8")
            total += p.stat().st_size
    (ROOT / "README.md").write_text(readme(), encoding="utf-8")
    print(f"wrote {len(files)*2} svgs ({total/1024:.0f} KB) + README.md")


if __name__ == "__main__":
    main()
