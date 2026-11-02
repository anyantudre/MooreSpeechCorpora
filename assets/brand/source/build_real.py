"""Round 3: balafon concepts drawn close to the real instrument (frame, slats, gourds, mallets)."""
import math
from pathlib import Path

OUT = Path(__file__).parent


def save(body, name, bg=None):
    rect = f'<rect width="256" height="256" fill="{bg}"/>\n' if bg else ""
    (OUT / name).write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">\n' + rect + body
                            + "\n</svg>\n", encoding="utf-8")


def poly(pts, fill):
    return f'<path fill="{fill}" d="M' + " L".join(f"{x:.2f},{y:.2f}" for x, y in pts) + ' Z"/>'


def rrect(x, y, w, h, r, fill):
    return f'<rect fill="{fill}" x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" rx="{r:.2f}"/>'


def circle(cx, cy, r, fill):
    return f'<circle fill="{fill}" cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}"/>'


def stick(p, q, w, fill):
    return (f'<line stroke="{fill}" stroke-width="{w}" stroke-linecap="round" x1="{p[0]:.2f}" y1="{p[1]:.2f}" '
            f'x2="{q[0]:.2f}" y2="{q[1]:.2f}"/>')


def band(p, q, h, fill):
    """Bar of thickness h hanging below the line p-q."""
    return poly([p, q, (q[0], q[1] + h), (p[0], p[1] + h)], fill)


def three_quarter(c, n=8, w=18, g=4, rise=9, L=(48, 82), lean=0.2679, ox=0, oy=0, gourds=None):
    """Instrument seen from the front-left and above, like the reference photo.
    The long axis rises to the right by `rise` degrees; slats lean back-right and get longer to the right.
    One gourd hangs under each slat, gourds grow with the slats. Returns (parts, bbox)."""
    t = math.tan(math.radians(rise))
    pitch = w + g
    span = n * pitch - g
    x0 = 128 - span / 2 - 8 + ox
    y0 = 118 + span * t / 2 + oy                      # front-left corner of the keyboard
    at = lambda x: (x, y0 - (x - x0) * t)              # point on the front edge
    parts = []
    for i in range(n):
        x = x0 + i * pitch
        li = L[0] + (L[1] - L[0]) * i / (n - 1)
        dx, dy = li * lean, -li
        p, q = at(x), at(x + w)
        parts.append(poly([p, q, (q[0] + dx, q[1] + dy), (p[0] + dx, p[1] + dy)], c["slat"]))
    rl, rr = at(x0 - 12), at(x0 + span + 12)
    rl, rr = (rl[0], rl[1] + 3), (rr[0], rr[1] + 3)
    k = gourds or n                                    # real balafons often have fewer gourds than keys
    gp = span / k
    rmax = gp / 2 - 1
    for i in range(k):                                 # gourds hang from the rail, bigger on the bass side
        cx = x0 + (i + 0.5) * gp
        r = rmax * (0.80 + 0.20 * i / (k - 1))
        parts.append(circle(cx, at(cx)[1] + 3 + 9 - 3 + r, r, c["gourd"]))
    parts.append(band(rl, rr, 9, c["wood"]))
    # posts at both ends of the front rail, and the ground rail
    drop = 9 + 2 * rmax + 1
    for x in (x0 - 12, x0 + span + 12 - 8):
        y = at(x)[1]
        parts.append(rrect(x, y - 12, 8, drop + 12 + 9, 3, c["wood"]))
    gl, gr = at(x0 - 12), at(x0 + span + 12)
    parts.append(band((gl[0], gl[1] + drop), (gr[0], gr[1] + drop), 8, c["wood"]))
    return parts


BLACK = dict(wood="#000", slat="#000", gourd="#000")
WOOD = dict(wood="#4A2E17", slat="#B0723A", gourd="#E2B45C")


def mallets(c, y, x=70, length=110, w=6, head=8.5):
    """Two mallets lying in front in a narrow V, heads on the left (as in the photo)."""
    m = c["wood"]
    a = (x, y)
    b = (x + 2, y + 22)
    tip = (x + length, y + 6)
    return [stick(tip, a, w, m), circle(*a, head, m), stick((tip[0] - 4, tip[1] + 4), b, w, m), circle(*b, head, m)]


def concept_g(c, name, bg=None):
    """G - The balafon: the whole instrument with its mallets."""
    parts = three_quarter(c, n=10, w=16, g=3.5, L=(34, 58), oy=4, gourds=6)
    parts += mallets(c, 194, x=60, length=132)
    save("\n".join(parts), name, bg)


def concept_h(c, name, disc, fg, bg=None):
    """H - Balafon seal: the instrument and mallets inside a disc (avatar, favicon)."""
    inner = "\n".join(three_quarter(fg, n=8, w=19, g=4, L=(36, 58), oy=4, gourds=5) + mallets(fg, 200, x=66, length=124))
    body = [circle(128, 128, 124, disc),
            f'<g transform="translate(128 126) scale(0.80) translate(-128 -128)">{inner}</g>']
    save("\n".join(body), name, bg)


def concept_i(c, name, bg=None):
    """I - Balafon front: seen by the audience; each key sits over its gourd, bass on the left."""
    radii = [19, 17.5, 16, 14.5, 13, 11.5, 10]
    gap = 2.5
    total = sum(2 * r for r in radii) + gap * (len(radii) - 1)
    left = 128 - total / 2
    parts = []
    rail_y, rail_h = 104, 10
    ground = rail_y + rail_h + 2 * radii[0] + 8
    x = left
    for i, r in enumerate(radii):                     # keys (seen slightly from above) and gourds
        kw = 2 * r - 3
        kh = 16 - 6 * i / (len(radii) - 1)
        parts.append(poly([(x + 1.5, rail_y - 3), (x + 1.5 + kw, rail_y - 3),
                           (x + kw - 1.5, rail_y - 3 - kh), (x + 4.5, rail_y - 3 - kh)], c["slat"]))
        parts.append(circle(x + r, rail_y + rail_h + 2 + r, r, c["gourd"]))
        x += 2 * r + gap
    parts.append(rrect(left - 14, rail_y, total + 28, rail_h, 3, c["wood"]))
    parts.append(rrect(left - 14, ground, total + 28, 9, 3, c["wood"]))
    for px in (left - 14, left + total + 6):
        parts.append(rrect(px, rail_y - 26, 8, ground + 9 - (rail_y - 26), 3, c["wood"]))
    # mallets crossed in front, below the instrument
    m = c["wood"]
    parts += [stick((92, 226), (168, 196), 6, m), circle(92, 226, 8.5, m),
              stick((164, 226), (88, 196), 6, m), circle(164, 226, 8.5, m)]
    save("\n".join(parts), name, bg)


LIGHT = dict(wood="#F3E3C3", slat="#E7B573", gourd="#E2B45C")

if __name__ == "__main__":
    concept_g(BLACK, "g-balafon-3q-v4.svg")
    concept_h(BLACK, "h-balafon-seal-v4.svg", "#000", dict(wood="#fff", slat="#fff", gourd="#fff"))
    concept_i(BLACK, "i-balafon-front-v4.svg")
    concept_g(WOOD, "g-balafon-3q-v4-colour.svg")
    concept_h(WOOD, "h-balafon-seal-v4-colour.svg", "#4A2E17", LIGHT)
    concept_i(WOOD, "i-balafon-front-v4-colour.svg")
