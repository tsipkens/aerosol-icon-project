#!/usr/bin/env python3
"""
Generates a static icon-grid preview for the README.

    python3 docs/generate_preview.py [svg_dir] [out_dir]

Defaults: svg_dir = "svg", out_dir = "docs"
Writes:   <out_dir>/icons-light.svg  and  <out_dir>/icons-dark.svg

Standard library only; needs Python 3.8+. A minimal grid: just the icons,
sorted by name, with no tiles or labels.
"""
import math
import re
import sys
from pathlib import Path

# ---------- settings ----------
SVG_DIR = Path(sys.argv[1] if len(sys.argv) > 1 else "svg")
OUT_DIR = Path(sys.argv[2] if len(sys.argv) > 2 else "docs")

N = None             # show only the first N icons (sorted by name); None = show all
COLS = 10            # icons per row
ICON = 64            # icon size in px
GAP_X = 24           # horizontal gap between icons
GAP_Y = 24           # vertical gap between rows

THEMES = {
    "light": "#15171c",   # icon color on light READMEs
    "dark": "#eceef3",    # icon color on dark READMEs
}

# ---------- helpers ----------
ATTR_RE = re.compile(r"""([\w:.-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')""")
COLOR_RE = re.compile(r"""\b(fill|stroke)(\s*=\s*)(?:"([^"]*)"|'([^']*)')""")
NEUTRAL_RE = re.compile(r"^(none|currentcolor|url\()", re.I)
DROP_ROOT = {"width", "height", "class", "style", "x", "y", "id", "version", "xmlns"}


def fmt(n):
    """Print 24.0 as 24, keep 24.5 as 24.5."""
    return str(int(n)) if float(n).is_integer() else repr(float(n))


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def natural_key(name):
    return [int(p) if p.isdigit() else p.casefold() for p in re.split(r"(\d+)", name)]


def attr_value(m, d=2, s=3):
    return m.group(d) if m.group(d) is not None else m.group(s)


def normalize(text, uid):
    """Return (viewBox, root_attrs, body) for one icon, or None if it isn't a usable svg."""
    m = re.search(r"<svg\b([^>]*)>([\s\S]*)</svg\s*>", text, re.I)
    if not m:
        return None
    root_attrs, inner = m.group(1), m.group(2)
    root_attrs = re.sub(r"/\s*$", "", root_attrs)

    attrs = {a.group(1): attr_value(a) for a in ATTR_RE.finditer(root_attrs)}

    # viewBox: use the given one, or build it from width/height
    view_box = attrs.get("viewBox")
    if not view_box:
        try:
            w, h = float(attrs["width"]), float(attrs["height"])
        except (KeyError, ValueError):
            return None
        if not (w > 0 and h > 0):
            return None
        view_box = f"0 0 {fmt(w)} {fmt(h)}"

    # drop things that don't belong in a preview
    inner = re.sub(r"<!--[\s\S]*?-->", "", inner)
    inner = re.sub(r"<(script|metadata|title|desc|style|foreignObject)\b[\s\S]*?</\1\s*>", "", inner, flags=re.I)
    inner = re.sub(r"<(script|metadata|title|desc|style)\b[^>]*/>", "", inner, flags=re.I)
    inner = re.sub(r"""\son\w+\s*=\s*(?:"[^"]*"|'[^']*')""", "", inner, flags=re.I)

    # single-colour icons inherit currentColor so they follow the theme
    colors = set()
    for chunk in (root_attrs, inner):
        for a in COLOR_RE.finditer(chunk):
            v = attr_value(a, 3, 4).strip()
            if not NEUTRAL_RE.match(v):
                colors.add(v.lower())
    single = len(colors) <= 1

    def recolor(s):
        def sub(a):
            v = attr_value(a, 3, 4).strip()
            return a.group(0) if NEUTRAL_RE.match(v) else f'{a.group(1)}{a.group(2)}"currentColor"'
        return COLOR_RE.sub(sub, s)

    # keep the remaining root attributes (fill, stroke-width, ...) on the nested <svg>
    kept = " ".join(
        f'{k}="{esc(v)}"'
        for k, v in attrs.items()
        if k not in DROP_ROOT and not k.startswith("xmlns") and k != "viewBox"
    )
    kept_attrs = recolor(kept) if single else kept
    body = recolor(inner) if single else inner

    # make ids unique across the whole sheet (gradients, clipPaths, ...)
    for id_ in dict.fromkeys(re.findall(r'\bid\s*=\s*"([^"]+)"', body)):
        e = re.escape(id_)
        new = f"{uid}-{id_}"
        body = re.sub(rf'\bid\s*=\s*"{e}"', lambda _: f'id="{new}"', body)
        body = re.sub(rf"""url\(\s*['"]?#{e}['"]?\s*\)""", lambda _: f"url(#{new})", body)
        body = re.sub(rf'((?:xlink:)?href\s*=\s*")#{e}"', lambda a: f'{a.group(1)}#{new}"', body)

    return view_box, kept_attrs, body


# ---------- load ----------
if not SVG_DIR.is_dir():
    sys.exit(f"[docs] folder not found: {SVG_DIR}")

files = sorted(p for p in SVG_DIR.rglob("*") if p.is_file() and p.suffix.lower() == ".svg")
icons, skipped = [], 0
for i, path in enumerate(files):
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as err:
        text = ""
        print(f"[docs] could not read {path}: {err}", file=sys.stderr)
    svg = normalize(text, f"i{i}")
    if svg:
        icons.append({"name": path.stem, "svg": svg})
    else:
        skipped += 1
        print(f"[docs] skipped (not a valid svg): {path}", file=sys.stderr)

icons.sort(key=lambda ic: natural_key(ic["name"]))
if not icons:
    sys.exit(f"[docs] no SVGs found in {SVG_DIR}")
total = len(icons)
if N is not None:
    if N < 1:
        sys.exit("[docs] N must be a positive number, or None to show all icons")
    icons = icons[:N]

# ---------- layout + render ----------
rows = math.ceil(len(icons) / COLS)
W = COLS * ICON + (COLS - 1) * GAP_X
H = rows * (ICON + GAP_Y) - GAP_Y


def render(color):
    cells = []
    for i, ic in enumerate(icons):
        x = (i % COLS) * (ICON + GAP_X)
        y = (i // COLS) * (ICON + GAP_Y)
        view_box, attrs, body = ic["svg"]
        cells.append(
            f'<svg x="{x}" y="{y}" width="{ICON}" height="{ICON}" viewBox="{view_box}"'
            f'{" " + attrs if attrs else ""}>{body}</svg>'
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{W}" height="{H}" viewBox="0 0 {W} {H}" color="{color}" '
        f'role="img" aria-label="Preview of {len(icons)} icons">\n'
        + "\n".join(cells)
        + "\n</svg>\n"
    )


OUT_DIR.mkdir(parents=True, exist_ok=True)
for theme, color in THEMES.items():
    out = OUT_DIR / f"icons-{theme}.svg"
    text = render(color)
    out.write_text(text, encoding="utf-8", newline="\n")
    kb = round(len(text.encode("utf-8")) / 1024)
    print(f"[docs] {out}  {len(icons)} of {total} icons, {kb} KB")
    if kb > 1500:
        print(f"[docs] warning: {out} is large; GitHub may be slow to render it.", file=sys.stderr)
if skipped:
    print(f"[docs] {skipped} file(s) skipped")