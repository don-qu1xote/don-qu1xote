import base64
import io
import math
import random
import sys
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"
FONTS = Path(sys.argv[1] if len(sys.argv) > 1 else "node_modules/@fontsource")

FACES = {
    "head": ("unbounded", 700),
    "mono": ("jetbrains-mono", 400),
    "monob": ("jetbrains-mono", 700),
}

THEMES = {
    "dark": dict(
        panel="#0f131a",
        panel2="#141922",
        border="#252c37",
        text="#e9e7e2",
        dim="#8d96a3",
        faint="#4a5361",
        accent="#ffb454",
        accent2="#ffcf8a",
        edge="#2a323e",
        node="#3b4554",
        dots="#1c222c",
        face_l="#0b0e13",
        face_r="#11151c",
        halo="0.10",
    ),
    "light": dict(
        panel="#fbfaf7",
        panel2="#f3f1ec",
        border="#dedad2",
        text="#1d2026",
        dim="#5d6470",
        faint="#a3a9b2",
        accent="#c25e00",
        accent2="#e07b12",
        edge="#d9d5cc",
        node="#b9b4aa",
        dots="#ebe7df",
        face_l="#e6e2d9",
        face_r="#efebe3",
        halo="0.10",
    ),
}

MONO_ADV = 0.6
GAP = 9


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Fonts:
    def __init__(self):
        self.files = {}
        for key, (family, weight) in FACES.items():
            parts = []
            for script in ("latin", "cyrillic"):
                path = FONTS / family / "files" / f"{family}-{script}-{weight}-normal.woff2"
                data = path.read_bytes()
                font = TTFont(io.BytesIO(data))
                parts.append((data, font))
            self.files[key] = parts

    def width(self, key, text, size):
        total = 0
        for ch in text:
            for _, font in self.files[key]:
                cmap = font.getBestCmap()
                if ord(ch) in cmap:
                    total += font["hmtx"][cmap[ord(ch)]][0]
                    break
        return total / 1000 * size

    def css(self, used):
        rules = []
        for key, text in used.items():
            chars = set(text) | {" "}
            for data, font in self.files[key]:
                cmap = font.getBestCmap()
                codes = sorted(ord(c) for c in chars if ord(c) in cmap)
                if not codes:
                    continue
                opts = subset.Options()
                opts.flavor = "woff2"
                opts.layout_features = ["kern", "liga", "calt"]
                opts.name_IDs = []
                sub = subset.Subsetter(opts)
                sub.populate(unicodes=codes)
                f = TTFont(io.BytesIO(data))
                sub.subset(f)
                buf = io.BytesIO()
                f.flavor = "woff2"
                f.save(buf)
                b64 = base64.b64encode(buf.getvalue()).decode()
                ranges = ",".join(f"U+{c:04X}" for c in codes)
                rules.append(
                    f"@font-face{{font-family:'{key}';src:url(data:font/woff2;base64,{b64}) format('woff2');unicode-range:{ranges};}}"
                )
        return "\n".join(rules)


F = None


class Svg:
    def __init__(self, w, h, title, left=0, right=0):
        self.w, self.h, self.title = w, h, title
        self.left, self.right = left, right
        self.body = []
        self.defs = []
        self.style = []
        self.used = {}

    def text(self, x, y, s, font="mono", size=14, fill="#000", anchor="start", spacing=0, opacity=None, cls=None):
        self.used[font] = self.used.get(font, "") + s
        attrs = f'x="{x:.1f}" y="{y:.1f}" font-family="{font}" font-size="{size}" fill="{fill}"'
        if anchor != "start":
            attrs += f' text-anchor="{anchor}"'
        if spacing:
            attrs += f' letter-spacing="{spacing}"'
        if opacity is not None:
            attrs += f' opacity="{opacity}"'
        if cls:
            attrs += f' class="{cls}"'
        self.body.append(f"<text {attrs}>{esc(s)}</text>")

    def raw(self, s):
        self.body.append(s)

    def render(self):
        full = self.w + self.left + self.right
        head = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{full}" height="{self.h}" '
            f'viewBox="{-self.left} 0 {full} {self.h}" role="img" aria-label="{esc(self.title)}">'
        )
        out = [head, f"<title>{esc(self.title)}</title>"]
        css = F.css(self.used)
        out.append("<style>" + css + "\n" + "\n".join(self.style) + "</style>")
        if self.defs:
            out.append("<defs>" + "".join(self.defs) + "</defs>")
        out += self.body
        out.append("</svg>")
        return "\n".join(out)


def panel(svg, t, x=0.5, y=0.5, w=None, h=None, r=16, fill=None):
    w = w if w is not None else svg.w - 1
    h = h if h is not None else svg.h - 1
    svg.raw(
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill or t["panel"]}" stroke="{t["border"]}"/>'
    )


def arrow(svg, x, y, color, size=14):
    s = size
    svg.raw(
        f'<g fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        f'<path d="M{x} {y + s} L{x + s} {y}"/><path d="M{x + s * 0.3} {y} H{x + s} V{y + s * 0.7}"/></g>'
    )


def mono_w(s, size):
    return len(s) * MONO_ADV * size


def graph_nodes():
    rnd = random.Random(21)
    cols, rows = 6, 5
    x0, x1, y0, y1 = 628, 948, 62, 318
    nodes = []
    for r in range(rows):
        for c in range(cols):
            if rnd.random() < 0.22:
                continue
            x = x0 + (x1 - x0) * c / (cols - 1) + rnd.uniform(-20, 20)
            y = y0 + (y1 - y0) * r / (rows - 1) + rnd.uniform(-16, 16)
            nodes.append((x, y))
    edges = set()
    for i, a in enumerate(nodes):
        near = sorted(range(len(nodes)), key=lambda j: math.dist(a, nodes[j]))[1:4]
        for j in near:
            if math.dist(a, nodes[j]) < 112:
                edges.add(tuple(sorted((i, j))))
    return nodes, sorted(edges)


def shortest(nodes, edges, s, e):
    adj = {i: [] for i in range(len(nodes))}
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    prev = {s: None}
    queue = [s]
    for v in queue:
        for u in sorted(adj[v], key=lambda u: math.dist(nodes[u], nodes[e])):
            if u not in prev:
                prev[u] = v
                queue.append(u)
    path, v = [], e
    while v is not None:
        path.append(v)
        v = prev.get(v)
    return path[::-1]


def header(t):
    svg = Svg(1000, 380, "Арман Секенов, C++ разработчик из Казани")
    svg.defs.append(
        f'<pattern id="dots" width="18" height="18" patternUnits="userSpaceOnUse"><circle cx="1.5" cy="1.5" r="1.3" fill="{t["dots"]}"/></pattern>'
        '<linearGradient id="fade" x1="0" x2="1"><stop offset="0.35" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff"/></linearGradient>'
        '<mask id="m"><rect width="1000" height="380" fill="url(#fade)"/></mask>'
        '<clipPath id="clip"><rect x="0.5" y="0.5" width="999" height="379" rx="18"/></clipPath>'
    )
    panel(svg, t, r=18)
    svg.raw('<g clip-path="url(#clip)">')
    svg.raw('<rect width="1000" height="380" fill="url(#dots)" mask="url(#m)"/>')
    svg.defs.append(
        f'<radialGradient id="halo"><stop offset="0" stop-color="{t["accent"]}" stop-opacity="{t["halo"]}"/><stop offset="1" stop-color="{t["accent"]}" stop-opacity="0"/></radialGradient>'
        '<filter id="hg" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="4"/></filter>'
    )
    svg.raw('<ellipse cx="800" cy="200" rx="260" ry="190" fill="url(#halo)"/>')

    nodes, edges = graph_nodes()
    s = min(range(len(nodes)), key=lambda i: nodes[i][0] * 0.6 - nodes[i][1])
    e = max(range(len(nodes)), key=lambda i: nodes[i][0] * 0.6 - nodes[i][1])
    path = shortest(nodes, edges, s, e)

    for a, b in edges:
        (x1, y1), (x2, y2) = nodes[a], nodes[b]
        svg.raw(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{t["edge"]}" stroke-width="1.3"/>')

    T = 7.0
    step = 0.55
    start = 0.6
    hold = 0.8 * T
    out_end = 0.9 * T

    def pct(sec):
        return f"{sec / T * 100:.2f}%"

    for k in range(len(path) - 1):
        (x1, y1), (x2, y2) = nodes[path[k]], nodes[path[k + 1]]
        L = math.dist((x1, y1), (x2, y2))
        a = start + k * step
        b = a + step
        svg.style.append(
            f"@keyframes e{k}{{0%{{stroke-dashoffset:{L:.1f};opacity:1}}{pct(a)}{{stroke-dashoffset:{L:.1f}}}"
            f"{pct(b)}{{stroke-dashoffset:0}}{pct(hold)}{{stroke-dashoffset:0;opacity:1}}"
            f"{pct(out_end)}{{stroke-dashoffset:0;opacity:0}}100%{{stroke-dashoffset:{L:.1f};opacity:0}}}}"
            f".e{k}{{stroke-dasharray:{L:.1f};animation:e{k} {T}s linear infinite}}"
        )
        svg.raw(
            f'<line class="e{k}" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{t["accent"]}" stroke-width="6" stroke-linecap="round" opacity=".55" filter="url(#hg)"/>'
            f'<line class="e{k}" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{t["accent"]}" stroke-width="2.4" stroke-linecap="round"/>'
        )

    on_path = {v: i for i, v in enumerate(path)}
    for i, (x, y) in enumerate(nodes):
        if i in on_path:
            continue
        svg.raw(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{t["node"]}"/>')

    for idx, v in enumerate(path):
        x, y = nodes[v]
        lit = start - 0.15 if idx == 0 else start + idx * step
        end = idx in (0, len(path) - 1)
        r = 7 if end else 5.5
        svg.style.append(
            f"@keyframes n{idx}{{0%{{fill:{t['node']};transform:scale(1)}}{pct(lit)}{{fill:{t['node']};transform:scale(1)}}"
            f"{pct(lit + 0.12)}{{fill:{t['accent']};transform:scale(1.35)}}{pct(lit + 0.35)}{{fill:{t['accent']};transform:scale(1)}}"
            f"{pct(hold)}{{fill:{t['accent']}}}{pct(out_end)}{{fill:{t['node']}}}100%{{fill:{t['node']}}}}}"
            f".n{idx}{{transform-box:fill-box;transform-origin:center;animation:n{idx} {T}s ease-out infinite}}"
        )
        if end:
            svg.raw(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="12" fill="none" stroke="{t["accent"]}" stroke-opacity="0.45" stroke-width="1.2"/>')
        svg.raw(f'<circle class="n{idx}" cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{t["node"]}"/>')

    sx, sy = nodes[path[0]]
    ex, ey = nodes[path[-1]]
    svg.text(sx - 2, sy + 30, "A", "monob", 12, t["dim"], anchor="middle")
    svg.text(ex + 22, ey + 4, "B", "monob", 12, t["dim"])

    svg.style.append(
        "@media (prefers-reduced-motion: reduce){line,circle{animation:none!important;stroke-dashoffset:0!important}}"
    )
    svg.raw("</g>")

    x = 64
    svg.text(x, 76, "КАЗАНЬ / C++ / БЭКЕНД", "mono", 13, t["accent"], spacing=2.5)
    svg.text(x - 3, 150, "Арман", "head", 62, t["text"])
    svg.text(x - 3, 220, "Секенов", "head", 62, t["text"])
    svg.text(x, 264, "Пишу на C++ и больше всего люблю продуктовые задачи.", "mono", 15.5, t["text"])
    facts = [
        "две стажировки в Яндексе: инфраструктура и Доставка",
        "прикладная математика в КГЭУ, выпускник Школы 21",
        "веду клуб по алгоритмам и преподаю в колледже",
    ]
    for i, f in enumerate(facts):
        y = 302 + i * 26
        svg.raw(f'<rect x="{x}" y="{y - 9}" width="7" height="7" rx="1.5" fill="{t["accent"]}"/>')
        svg.text(x + 20, y, f, "mono", 14.5, t["dim"])
    return svg


def label(t, s):
    svg = Svg(1000, 78, s)
    y = 50
    svg.text(4, y, "//", "monob", 14, t["accent"])
    svg.text(32, y, s.upper(), "mono", 14, t["text"], spacing=3)
    w = 32 + mono_w(s, 14) + len(s) * 3 + 18
    svg.raw(f'<line x1="{w:.0f}" y1="{y - 4.5}" x2="1000" y2="{y - 4.5}" stroke="{t["border"]}"/>')
    return svg


def status(svg, t, x, y, text, live):
    color = t["accent"] if live else t["faint"]
    w = mono_w(text, 11.5) + len(text) * 2 + 40
    svg.raw(f'<rect x="{x}" y="{y - 19}" width="{w:.0f}" height="28" rx="14" fill="{t["panel"]}" stroke="{t["border"]}"/>')
    if live:
        svg.style.append("@keyframes pulse{0%,100%{opacity:.15}50%{opacity:.7}}.pulse{animation:pulse 2.4s ease-in-out infinite}")
        svg.raw(f'<circle class="pulse" cx="{x + 16}" cy="{y - 5}" r="7" fill="{color}"/>')
    svg.raw(f'<circle cx="{x + 16}" cy="{y - 5}" r="3.5" fill="{color}"/>')
    svg.text(x + 28, y, text.upper(), "mono", 11.5, t["dim"], spacing=2)


def cover_base(svg, t, x, y, w, h, uid, fade="down"):
    coords = 'x1="0" y1="0" x2="0" y2="1"' if fade == "down" else 'x1="1" y1="0" x2="0" y2="0"'
    svg.defs.append(
        f'<pattern id="d{uid}" width="16" height="16" patternUnits="userSpaceOnUse"><circle cx="1.5" cy="1.5" r="1.2" fill="{t["dots"]}"/></pattern>'
        f'<linearGradient id="g{uid}" {coords}><stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        f'<mask id="k{uid}"><rect x="{x}" y="{y}" width="{w}" height="{h}" fill="url(#g{uid})"/></mask>'
        f'<radialGradient id="r{uid}"><stop offset="0" stop-color="{t["accent"]}" stop-opacity="{t["halo"]}"/><stop offset="1" stop-color="{t["accent"]}" stop-opacity="0"/></radialGradient>'
    )
    svg.raw(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="url(#d{uid})" mask="url(#k{uid})"/>')


def glow_filter(svg, uid, dev=4):
    svg.defs.append(
        f'<filter id="{uid}" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="{dev}"/></filter>'
    )


def cover_sixfeat(svg, t):
    cover_base(svg, t, 0, 0, 500, 170, "sf")
    glow_filter(svg, "sfg", 5)
    cx, cy = 250, 88
    svg.raw(f'<ellipse cx="{cx}" cy="{cy}" rx="170" ry="70" fill="url(#rsf)"/>')
    rnd = random.Random(6)
    a1 = [i * math.tau / 6 for i in range(6)]
    ring1 = [(cx + 74 * math.cos(a), cy + 34 * math.sin(a)) for a in a1]
    a2 = []
    for k in range(6):
        for d in (-0.32, 0.32):
            a2.append(a1[k] + d + rnd.uniform(-0.06, 0.06))
    ring2 = [(cx + 172 * math.cos(a), cy + 60 * math.sin(a)) for a in a2]
    T = 6.0
    phases = [(0.3, ring1), (1.0, ring2)]

    def kf(name, at):
        a = at / T * 100
        svg.style.append(
            f"@keyframes {name}{{0%,{a:.1f}%{{opacity:0}}{a + 8:.1f}%,82%{{opacity:1}}94%,100%{{opacity:0}}}}"
            f".{name}{{animation:{name} {T}s ease-out infinite}}"
        )

    kf("sa", 0.3)
    kf("sb", 1.0)
    kf("sc", 1.7)
    svg.raw('<g class="sa">')
    for x, y in ring1:
        svg.raw(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="{t["edge"]}" stroke-width="1.3"/>')
    svg.raw("</g>")
    svg.raw('<g class="sb">')
    for i, (x, y) in enumerate(ring2):
        px, py = ring1[i // 2]
        svg.raw(f'<line x1="{px:.1f}" y1="{py:.1f}" x2="{x:.1f}" y2="{y:.1f}" stroke="{t["edge"]}" stroke-width="1.1"/>')
    for i, (x, y) in enumerate(ring2):
        svg.raw(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{3 + (i % 3)}" fill="{t["node"]}"/>')
    svg.raw("</g>")
    svg.raw('<g class="sa">')
    for x, y in ring1:
        svg.raw(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{t["node"]}"/>')
    svg.raw("</g>")
    end = ring2[1]
    mid = ring1[0]
    path = f"M{cx} {cy} L{mid[0]:.1f} {mid[1]:.1f} L{end[0]:.1f} {end[1]:.1f}"
    svg.raw(f'<g class="sc"><path d="{path}" fill="none" stroke="{t["accent"]}" stroke-width="5" opacity=".5" filter="url(#sfg)"/>')
    svg.raw(f'<path d="{path}" fill="none" stroke="{t["accent"]}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>')
    for x, y in (mid, end):
        svg.raw(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.5" fill="{t["accent"]}"/>')
    svg.raw("</g>")
    svg.raw(f'<circle cx="{cx}" cy="{cy}" r="16" fill="{t["accent"]}" opacity=".35" filter="url(#sfg)"/>')
    svg.raw(f'<circle cx="{cx}" cy="{cy}" r="8" fill="{t["accent"]}"/>')


def cover_morph(svg, t):
    cover_base(svg, t, 0, 0, 500, 170, "mo")
    glow_filter(svg, "mog", 6)
    svg.raw(f'<ellipse cx="250" cy="86" rx="190" ry="64" fill="url(#rmo)"/>')
    rnd = random.Random(3)
    n = 44
    x0, x1, base = 52, 448, 88
    step = (x1 - x0) / (n - 1)
    svg.defs.append(
        f'<linearGradient id="bar" x1="0" x2="1"><stop offset="0" stop-color="{t["node"]}"/>'
        f'<stop offset="0.5" stop-color="{t["accent"]}"/><stop offset="1" stop-color="{t["node"]}"/></linearGradient>'
    )
    bars = []
    for i in range(n):
        x = x0 + i * step
        env = math.sin(math.pi * i / (n - 1)) ** 0.8
        h = 10 + 52 * env * rnd.uniform(0.45, 1.0)
        d = rnd.uniform(0.9, 1.7)
        lo = rnd.uniform(0.25, 0.55)
        delay = -rnd.uniform(0, 2)
        svg.style.append(
            f"@keyframes b{i}{{0%,100%{{transform:scaleY(1)}}50%{{transform:scaleY({lo:.2f})}}}}"
            f".b{i}{{transform-box:fill-box;transform-origin:center;animation:b{i} {d:.2f}s ease-in-out {delay:.2f}s infinite}}"
        )
        bars.append(f'<rect class="b{i}" x="{x - 2.5:.1f}" y="{base - h / 2:.1f}" width="5" height="{h:.1f}" rx="2.5"/>')
    svg.raw(f'<g fill="url(#bar)" opacity=".45" filter="url(#mog)">' + "".join(bars) + "</g>")
    svg.raw(f'<g fill="url(#bar)">' + "".join(bars) + "</g>")
    y = 150
    svg.raw(f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="{t["edge"]}" stroke-width="3" stroke-linecap="round"/>')
    L = x1 - x0
    svg.style.append(
        f"@keyframes prog{{0%{{stroke-dashoffset:{L}}}100%{{stroke-dashoffset:0}}}}"
        f".prog{{stroke-dasharray:{L};animation:prog 24s linear infinite}}"
        f"@keyframes head{{0%{{transform:translateX(0)}}100%{{transform:translateX({L}px)}}}}"
        f".head{{animation:head 24s linear infinite}}"
    )
    svg.raw(f'<line class="prog" x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="{t["accent"]}" stroke-width="3" stroke-linecap="round"/>')
    svg.raw(f'<circle class="head" cx="{x0}" cy="{y}" r="6" fill="{t["accent"]}"/>')


def iso_plate(cx, cy, a, b, th):
    top = f"{cx},{cy - b} {cx + a},{cy} {cx},{cy + b} {cx - a},{cy}"
    left = f"{cx - a},{cy} {cx},{cy + b} {cx},{cy + b + th} {cx - a},{cy + th}"
    right = f"{cx},{cy + b} {cx + a},{cy} {cx + a},{cy + th} {cx},{cy + b + th}"
    return top, left, right


def cover_pdr(svg, t, x, y, w, h):
    cover_base(svg, t, x, y, w, h, "pd", fade="left")
    glow_filter(svg, "pdg", 6)
    cx, cy = x + w / 2 - 30, y + 72
    svg.raw(f'<ellipse cx="{cx}" cy="{cy + 80}" rx="180" ry="100" fill="url(#rpd)"/>')
    a, b, th, gap = 96, 48, 12, 38
    names = ["services", "adapters", "application", "core"]
    for i in range(4):
        py = cy + i * gap
        top, left, right = iso_plate(cx, py, a, b, th)
        lx, ly = cx + a + 20, py + 6
        if i == 0:
            svg.style.append(
                "@keyframes fl{0%,100%{transform:translateY(-6px)}50%{transform:translateY(-14px)}}"
                ".fl{animation:fl 4s ease-in-out infinite}"
            )
            svg.raw(f'<g class="fl"><polygon points="{top}" fill="{t["accent"]}" fill-opacity=".07" stroke="{t["accent"]}" stroke-width="1.6" stroke-dasharray="6 5"/></g>')
            svg.text(lx, ly - 8, names[i], "mono", 12, t["accent"])
            continue
        svg.raw(f'<polygon points="{left}" fill="{t["face_l"]}" stroke="{t["border"]}"/>')
        svg.raw(f'<polygon points="{right}" fill="{t["face_r"]}" stroke="{t["border"]}"/>')
        svg.raw(f'<polygon points="{top}" fill="{t["panel2"]}" stroke="{t["border"]}"/>')
        svg.text(lx, ly, names[i], "mono", 12, t["dim"])
    core_top = iso_plate(cx, cy + 3 * gap, a, b, th)[0]
    svg.raw(f'<polygon points="{core_top}" fill="none" stroke="{t["accent"]}" stroke-width="1.4" opacity=".8"/>')


def card(t, p, side):
    W, H = 500, 392
    svg = Svg(W, H, f'{p["name"]}: {" ".join(p["desc"])}', **{"right" if side == "l" else "left": GAP})
    svg.defs.append(f'<clipPath id="cc"><rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="16"/></clipPath>')
    panel(svg, t)
    svg.raw('<g clip-path="url(#cc)">')
    p["cover"](svg, t)
    svg.raw("</g>")
    pad = 32
    status(svg, t, 24, 44, p["status"], p["live"])
    arrow(svg, W - pad - 14, 26, t["dim"])
    svg.text(pad - 2, 210, p["name"], "head", 30, t["text"])
    for i, line in enumerate(p["desc"]):
        svg.text(pad, 242 + i * 21, line, "mono", 13.5, t["dim"])
    svg.raw(f'<line x1="{pad}" y1="{H - 76}.5" x2="{W - pad}" y2="{H - 76}.5" stroke="{t["border"]}"/>')
    colw = (W - 2 * pad) / 3
    for i, (num, cap) in enumerate(p["metrics"]):
        mx = pad + i * colw
        svg.text(mx, H - 42, num, "head", 21, t["accent"])
        svg.text(mx, H - 22, cap, "mono", 12, t["dim"])
    return svg


def wide_card(t, p):
    W, H = 1000, 300
    svg = Svg(W, H, f'{p["name"]}: {" ".join(p["desc"])}')
    svg.defs.append(f'<clipPath id="cc"><rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="16"/></clipPath>')
    panel(svg, t)
    svg.raw('<g clip-path="url(#cc)">')
    cover_pdr(svg, t, 560, 0, 440, H)
    svg.raw("</g>")
    pad = 32
    status(svg, t, 24, 44, p["status"], p["live"])
    arrow(svg, W - pad - 14, 26, t["dim"])
    svg.text(pad - 2, 108, p["name"], "head", 30, t["text"])
    for i, line in enumerate(p["desc"]):
        svg.text(pad, 142 + i * 21, line, "mono", 13.5, t["dim"])
    svg.raw(f'<line x1="{pad}" y1="{H - 76}.5" x2="560" y2="{H - 76}.5" stroke="{t["border"]}"/>')
    xs = [pad, pad + 150, pad + 340]
    for i, (num, cap) in enumerate(p["metrics"]):
        svg.text(xs[i], H - 42, num, "head", 21, t["accent"])
        svg.text(xs[i], H - 22, cap, "mono", 12, t["dim"])
    return svg


def stack(t):
    rows = [
        ("языки", ["C++", "C", "Python", "SQL", "Bash"]),
        ("библиотеки", ["userver", "Qt / QML", "Boost", "STL", "gtest", "Flask"]),
        ("инфраструктура", ["PostgreSQL", "Docker", "CMake", "GitHub Actions", "GitLab CI", "Linux"]),
    ]
    H = 40 + len(rows) * 52
    svg = Svg(1000, H, "Стек: " + "; ".join(", ".join(r[1]) for r in rows))
    panel(svg, t)
    for i, (name, items) in enumerate(rows):
        y = 32 + i * 52
        svg.text(32, y + 23, name.upper(), "mono", 11.5, t["dim"], spacing=2)
        x = 210
        for j, item in enumerate(items):
            w = mono_w(item, 14) + 28
            first = i == 0 and j == 0
            fill = t["panel2"]
            stroke = t["accent"] if first else t["border"]
            svg.raw(f'<rect x="{x}" y="{y}.5" width="{w:.0f}" height="34" rx="9" fill="{fill}" stroke="{stroke}"/>')
            svg.text(x + 14, y + 22.5, item, "mono", 14, t["accent"] if first else t["text"])
            x += w + 10
    return svg


def button(t, name, handle, side):
    W, H = 500, 76
    svg = Svg(W, H, f"{name}: {handle}", **{"right" if side == "l" else "left": GAP})
    panel(svg, t, r=14)
    svg.text(32, 33, name.upper(), "mono", 12, t["dim"], spacing=2)
    svg.text(32, 56, handle, "mono", 17, t["text"])
    arrow(svg, W - 32 - 14, 31, t["accent"], 14)
    return svg


def footer(t):
    svg = Svg(1000, 64, "Это наполняет тебя решимостью")
    svg.text(500, 46, "* это наполняет тебя решимостью.", "mono", 13, t["faint"], anchor="middle")
    return svg


PROJECTS = {
    "sixfeat": dict(
        name="SixFeat",
        status="доделан",
        live=False,
        desc=[
            "Граф музыкальных коллабораций по Genius.",
            "Кто с кем записывался, кто спродюсировал",
            "и как дойти от одного артиста до другого.",
        ],
        metrics=[("5", "сервисов"), ("31", "джоба в CI"), ("15", "ADR")],
        cover=cover_sixfeat,
        stack=["C++", "userver", "PostgreSQL", "Docker", "JS canvas"],
    ),
    "morph": dict(
        name="morph",
        status="допиливаю",
        live=True,
        desc=[
            "Форк десктопного плеера Яндекс Музыки.",
            "Собрал под macOS, написал свои рекомендации",
            "и вернул треки, которые Яндекс удалил.",
        ],
        metrics=[("67", "моих коммитов"), ("25", "наборов тестов"), ("3", "площадки")],
        cover=cover_morph,
        stack=["C++23", "Qt 6", "QML", "SQLite", "Last.fm", "Subsonic"],
    ),
    "pdr": dict(
        name="pdr",
        status="строю",
        live=True,
        desc=[
            "Новый большой проект. Пока это фундамент: слои с",
            "проверкой границ на каждой сборке, изоляция данных",
            "через RLS в Postgres, фоновые задания на DistLock.",
            "Что из этого вырастет, покажу, когда будет что показать.",
        ],
        metrics=[("20", "решений в ADR"), ("4", "контекста первой фазы"), ("3", "уровня тестов")],
        stack=["C++20", "userver", "PostgreSQL", "CMake", "gtest", "pytest"],
    ),
}


def build():
    global F
    F = Fonts()
    OUT.mkdir(exist_ok=True)
    for name, t in THEMES.items():
        items = {
            "header": header(t),
            "label-projects": label(t, "проекты"),
            "label-stack": label(t, "стек"),
            "label-contacts": label(t, "связь"),
            "card-sixfeat": card(t, PROJECTS["sixfeat"], "l"),
            "card-morph": card(t, PROJECTS["morph"], "r"),
            "card-pdr": wide_card(t, PROJECTS["pdr"]),
            "stack": stack(t),
            "btn-telegram": button(t, "telegram", "@A_12_11_4_17", "l"),
            "btn-leetcode": button(t, "leetcode", "don_qu1jote", "r"),
            "footer": footer(t),
        }
        for key, svg in items.items():
            (OUT / f"{key}-{name}.svg").write_text(svg.render(), encoding="utf-8")


if __name__ == "__main__":
    build()
