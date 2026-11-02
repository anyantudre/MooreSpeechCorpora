"""VoxFaso logo kit: symbol D (balafon), seal E, constructed wordmark, lockups, small cuts."""
import math
from pathlib import Path

from build_real import three_quarter, mallets, circle

KIT = Path(__file__).parent / "kit"
KIT.mkdir(exist_ok=True)

FRAME, KEY, CALABASH, SHEA = "#4A2E17", "#B0723A", "#E2B45C", "#F3E3C3"
KEY_LIGHT = "#E7B573"
NIGHT = "#1E140C"                       # dark background used in the guide

COLOUR = dict(wood=FRAME, slat=KEY, gourd=CALABASH)
REVERSED = dict(wood=SHEA, slat=KEY_LIGHT, gourd=CALABASH)
BLACK = dict(wood="#000", slat="#000", gourd="#000")
WHITE = dict(wood="#fff", slat="#fff", gourd="#fff")


def write(name, body, w=256, h=256):
    (KIT / name).write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}">\n{body}\n</svg>\n',
                            encoding="utf-8")


# ---- symbol D -----------------------------------------------------------------------------------
def symbol(c):
    return '<g transform="translate(6.25 -10.8)">' + "\n".join(three_quarter(c, n=10, w=16, g=3.5, L=(34, 58), oy=4, gourds=6)
                     + mallets(c, 194, x=60, length=132)) + "</g>"


def symbol_small(c):
    """Small-size cut (24 to 48 px): fewer, wider slats, four gourds, no mallets."""
    return "\n".join(three_quarter(c, n=6, w=26, g=6, L=(40, 62), oy=14, gourds=4))


# ---- seal E --------------------------------------------------------------------------------------
def seal(disc, c):
    inner = "\n".join(three_quarter(c, n=8, w=19, g=4, L=(36, 58), oy=4, gourds=5) + mallets(c, 200, x=66, length=124))
    return circle(128, 128, 124, disc) + f'\n<g transform="translate(128 126) scale(0.80) translate(-128 -128)">{inner}</g>'


def seal_small(disc, c):
    """Favicon cut: five slats, three gourds, no mallets, drawn larger in the disc."""
    inner = "\n".join(three_quarter(c, n=5, w=28, g=7, L=(40, 60), oy=16, gourds=3))
    return circle(128, 128, 124, disc) + f'\n<g transform="translate(128 128) scale(0.86) translate(-128 -128)">{inner}</g>'


# ---- wordmark: monoline geometric letters with round ends, like the mallet handles ----------------
S = 13                                   # stroke
H = S / 2
XH, CH = 60, 84                          # x-height, cap height (outer)


def letters():
    r = (XH - S) / 2                     # o / a ring radius (centre line)
    R = (XH - S) / 4                     # s bowls: vertical radius
    RX = 15.5                            # s bowls: horizontal radius (wider than tall, less curly)
    sc = RX + H
    a1 = math.radians(28)
    s_path = (f"M{sc + RX * math.cos(a1):.2f},{-XH + H + R - R * math.sin(a1):.2f} "
              f"A{RX:.2f},{R:.2f} 0 1 0 {sc:.2f},{-XH / 2:.2f} "
              f"A{RX:.2f},{R:.2f} 0 1 1 {sc - RX * math.cos(a1):.2f},{-H - R + R * math.sin(a1):.2f}")
    ring = lambda: f"M{H:.2f},{-XH / 2:.2f} a{r:.2f},{r:.2f} 0 1 0 {2 * r:.2f},0 a{r:.2f},{r:.2f} 0 1 0 {-2 * r:.2f},0"
    return {
        "V": (66, f"M{H},{-CH + H} L33,{-H} L{66 - H},{-CH + H}"),
        "o": (XH, ring()),
        "x": (50, f"M{H},{-XH + H} L{50 - H},{-H} M{50 - H},{-XH + H} L{H},{-H}"),
        "F": (50, f"M{H},{-H} V{-CH + H} H{50 - H} M{H},-44 H{44 - H}"),
        "a": (XH, ring() + f" M{XH - H},{-XH + H} V{-H}"),
        "s": (2 * sc, s_path),
    }


# advance positions (optical spacing set by eye; V-o and F-a pairs tightened)
LAYOUT = [("V", 0), ("o", 58), ("x", 128), ("F", 194), ("a", 242), ("s", 312), ("o", 366)]
WORD_W = 366 + XH


def wordmark(c1, c2, x=0.0, y=0.0, k=1.0):
    """Returns SVG for "VoxFaso": Vox in c1, Faso in c2. Baseline at y, left at x, scale k."""
    L = letters()
    groups = {c1: [], c2: []}
    for i, (ch, dx) in enumerate(LAYOUT):
        groups[c1 if i < 3 else c2].append(f'<path transform="translate({dx} 0)" d="{L[ch][1]}"/>')
    out = []
    for col, paths in groups.items():
        out.append(f'<g fill="none" stroke="{col}" stroke-width="{S}" stroke-linecap="round" '
                   f'stroke-linejoin="round">' + "".join(paths) + "</g>")
    return f'<g transform="translate({x:.2f} {y:.2f}) scale({k})">' + "".join(out) + "</g>"


# symbol D's drawn area inside its 256 box (measured from a render)
SYM = dict(x0=18.2, y0=38, x1=237.8, y1=213.7)


def placed_symbol(body, x, y, height):
    k = height / (SYM["y1"] - SYM["y0"])
    return (f'<g transform="translate({x:.2f} {y:.2f}) scale({k:.4f}) translate({-SYM["x0"]} {-SYM["y0"]})">'
            f'{body}</g>', (SYM["x1"] - SYM["x0"]) * k)


def horizontal(c, w1, w2):
    sh = 150
    sym, sw = placed_symbol(symbol(c), 0, 0, sh)
    gap = 34
    k = 0.92
    # baseline sits on the front rail's height so the name reads on the instrument's line
    word = wordmark(w1, w2, sw + gap, sh * 0.70, k)
    write_args = (sym + "\n" + word, sw + gap + WORD_W * k + 4, sh + 2)
    return write_args


def stacked(c, w1, w2):
    sh = 190
    k = 0.92
    ww = WORD_W * k
    width = max(ww, (SYM["x1"] - SYM["x0"]) * sh / (SYM["y1"] - SYM["y0"])) + 8
    sym, sw = placed_symbol(symbol(c), (width - (SYM["x1"] - SYM["x0"]) * sh / (SYM["y1"] - SYM["y0"])) / 2, 0, sh)
    word = wordmark(w1, w2, (width - ww) / 2, sh + 30 + CH * k, k)
    return sym + "\n" + word, width, sh + 30 + CH * k + 8


def build():
    write("voxfaso-symbol.svg", symbol(COLOUR))
    write("voxfaso-symbol-reversed.svg", symbol(REVERSED))
    write("voxfaso-symbol-black.svg", symbol(BLACK))
    write("voxfaso-symbol-white.svg", symbol(WHITE))
    write("voxfaso-symbol-small.svg", symbol_small(COLOUR))
    write("voxfaso-seal.svg", seal(FRAME, dict(wood=SHEA, slat=KEY_LIGHT, gourd=CALABASH)))
    write("voxfaso-seal-black.svg", seal("#000", WHITE).replace('fill="#fff"', 'fill="#fff"'))
    write("voxfaso-seal-small.svg", seal_small(FRAME, dict(wood=SHEA, slat=KEY_LIGHT, gourd=CALABASH)))
    write("voxfaso-wordmark.svg", wordmark(FRAME, KEY, 6.5, CH + 6.5), WORD_W + 13, CH + 13)
    write("voxfaso-wordmark-reversed.svg", wordmark(SHEA, KEY_LIGHT, 6.5, CH + 6.5), WORD_W + 13, CH + 13)
    for name, c, w1, w2 in [("", COLOUR, FRAME, KEY), ("-reversed", REVERSED, SHEA, KEY_LIGHT),
                            ("-black", BLACK, "#000", "#000"), ("-white", WHITE, "#fff", "#fff")]:
        write(f"voxfaso-horizontal{name}.svg", *horizontal(c, w1, w2))
        write(f"voxfaso-stacked{name}.svg", *stacked(c, w1, w2))


if __name__ == "__main__":
    build()
