"""FasoSpeechCorpora logo kit: symbol D (balafon), seal E, constructed wordmark, lockups, small cuts."""
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


DESC = 24                                # descender depth (p)
WORD = "FasoSpeechCorpora"
ACCENT = 4                               # the first 4 letters ("Faso") take the accent colour


def letters():
    r = (XH - S) / 2                     # o / a / e / p ring radius (centre line)
    c40, s40 = math.cos(math.radians(40)), math.sin(math.radians(40))

    def s_shape(height, rx):             # s and S: two stacked bowls, wider than tall
        R = (height - S) / 4
        sc = rx + H
        a1 = math.radians(28)
        return (2 * sc, f"M{sc + rx * math.cos(a1):.2f},{-height + H + R - R * math.sin(a1):.2f} "
                        f"A{rx:.2f},{R:.2f} 0 1 0 {sc:.2f},{-height / 2:.2f} "
                        f"A{rx:.2f},{R:.2f} 0 1 1 {sc - rx * math.cos(a1):.2f},{-H - R + R * math.sin(a1):.2f}")

    ring = f"M{H:.2f},{-XH / 2:.2f} a{r:.2f},{r:.2f} 0 1 0 {2 * r:.2f},0 a{r:.2f},{r:.2f} 0 1 0 {-2 * r:.2f},0"
    cx, cy = XH / 2, -XH / 2
    rc = (CH - S) / 2                    # C
    Cx, Cy = rc + H, -CH / 2
    ra = 20                              # h arch
    rr = 17                              # r shoulder
    return {
        "F": (50, f"M{H},{-H} V{-CH + H} H{50 - H} M{H},-44 H{44 - H}"),
        "a": (XH, ring + f" M{XH - H},{-XH + H} V{-H}"),
        "s": s_shape(XH, 15.5),
        "o": (XH, ring),
        "S": s_shape(CH, 21),
        "p": (XH, ring + f" M{H},{-XH + H} V{DESC - H}"),
        "e": (XH, f"M{H},{cy} H{XH - H} A{r},{r} 0 1 0 {cx + r * c40:.2f},{cy + r * s40:.2f}"),
        "c": (XH - 4, f"M{cx + r * c40:.2f},{cy - r * s40:.2f} A{r},{r} 0 1 0 {cx + r * c40:.2f},{cy + r * s40:.2f}"),
        "h": (2 * ra + S, f"M{H},{-CH + H} V{-H} M{H},{-XH + H + ra} A{ra},{ra} 0 0 1 {H + 2 * ra},{-XH + H + ra} V{-H}"),
        "C": (2 * rc + S - 6, f"M{Cx + rc * c40:.2f},{Cy - rc * s40:.2f} A{rc},{rc} 0 1 0 {Cx + rc * c40:.2f},{Cy + rc * s40:.2f}"),
        "r": (H + rr + 7 + H, f"M{H},{-XH + H} V{-H} M{H},{-XH + H + rr} A{rr},{rr} 0 0 1 {H + rr},{-XH + H} H{H + rr + 7}"),
    }


GAP = 9
KERN = {"F": -6, "r": -4, "C": -4, "c": -2}  # open right sides sit closer to the next letter


def layout():
    L, x, out = letters(), 0.0, []
    for ch in WORD:
        out.append((ch, x))
        x += L[ch][0] + GAP + KERN.get(ch, 0)
    return out, x - GAP - KERN.get(WORD[-1], 0)


LAYOUT, WORD_W = layout()


def wordmark(c_main, c_accent, x=0.0, y=0.0, k=1.0):
    """SVG for the name: "Faso" in c_accent, "SpeechCorpora" in c_main. Baseline at y, left at x, scale k."""
    L = letters()
    groups = {c_accent: [], c_main: []}
    for i, (ch, dx) in enumerate(LAYOUT):
        groups[c_accent if i < ACCENT else c_main].append(f'<path transform="translate({dx:.2f} 0)" d="{L[ch][1]}"/>')
    out = [f'<g fill="none" stroke="{col}" stroke-width="{S}" stroke-linecap="round" stroke-linejoin="round">'
           + "".join(p) + "</g>" for col, p in groups.items()]
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
    k = 0.82
    # baseline sits on the front rail's height so the name reads on the instrument's line
    word = wordmark(w1, w2, sw + gap, sh * 0.70, k)
    write_args = (sym + "\n" + word, sw + gap + WORD_W * k + 4, sh + 2)
    return write_args


def stacked(c, w1, w2):
    sh = 400
    k = 0.92
    ww = WORD_W * k
    width = max(ww, (SYM["x1"] - SYM["x0"]) * sh / (SYM["y1"] - SYM["y0"])) + 8
    sym, sw = placed_symbol(symbol(c), (width - (SYM["x1"] - SYM["x0"]) * sh / (SYM["y1"] - SYM["y0"])) / 2, 0, sh)
    word = wordmark(w1, w2, (width - ww) / 2, sh + 46 + CH * k, k)
    return sym + "\n" + word, width, sh + 30 + CH * k + 8


def build():
    write("fasospeechcorpora-symbol.svg", symbol(COLOUR))
    write("fasospeechcorpora-symbol-reversed.svg", symbol(REVERSED))
    write("fasospeechcorpora-symbol-black.svg", symbol(BLACK))
    write("fasospeechcorpora-symbol-white.svg", symbol(WHITE))
    write("fasospeechcorpora-symbol-small.svg", symbol_small(COLOUR))
    write("fasospeechcorpora-seal.svg", seal(FRAME, dict(wood=SHEA, slat=KEY_LIGHT, gourd=CALABASH)))
    write("fasospeechcorpora-seal-black.svg", seal("#000", WHITE).replace('fill="#fff"', 'fill="#fff"'))
    write("fasospeechcorpora-seal-small.svg", seal_small(FRAME, dict(wood=SHEA, slat=KEY_LIGHT, gourd=CALABASH)))
    write("fasospeechcorpora-wordmark.svg", wordmark(FRAME, KEY, 6.5, CH + 6.5), WORD_W + 13, CH + DESC + 13)
    write("fasospeechcorpora-wordmark-reversed.svg", wordmark(SHEA, KEY_LIGHT, 6.5, CH + 6.5), WORD_W + 13, CH + DESC + 13)
    for name, c, w1, w2 in [("", COLOUR, FRAME, KEY), ("-reversed", REVERSED, SHEA, KEY_LIGHT),
                            ("-black", BLACK, "#000", "#000"), ("-white", WHITE, "#fff", "#fff")]:
        write(f"fasospeechcorpora-horizontal{name}.svg", *horizontal(c, w1, w2))
        write(f"fasospeechcorpora-stacked{name}.svg", *stacked(c, w1, w2))


if __name__ == "__main__":
    build()
