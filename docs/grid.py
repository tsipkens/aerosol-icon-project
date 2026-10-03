#!/usr/bin/env python3
"""
Generates a GitHub-compatible HTML grid of SVGs using native <table> elements
and injects it directly into README.md between marker comments.
Calculates width based on aspect ratios so all SVGs scale uniformly without stretching.
"""

from pathlib import Path
import xml.etree.ElementTree as ET
import re
import sys

# Configuration
SVG_DIR = Path("../svg")  # Directory containing SVGs
README_FILE = Path("../README.md")  # Main README file

# Comment markers in README.md
START_MARKER = "<!-- SVG_GRID_START -->"
END_MARKER = "<!-- SVG_GRID_END -->"

# Grid formatting configuration
COLUMNS_PER_ROW = 5  # Number of columns in the HTML table
TARGET_HEIGHT = 48   # Target visual height (in px) for all icons
MAX_CELL_WIDTH = 90  # Maximum bounding width (in px) to fit inside table cells


def get_svg_aspect_ratio(filepath: Path) -> float:
    """
    Extracts (width / height) aspect ratio from an SVG's viewBox or dimensions.
    Defaults to 1.0 (square) if unparseable.
    """
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()

        # Parse viewBox if available ("min-x min-y width height")
        viewbox = root.attrib.get("viewBox") or root.attrib.get("viewbox")
        if viewbox:
            parts = [float(p) for p in re.split(r"[\s,]+", viewbox.strip()) if p]
            if len(parts) == 4 and parts[2] > 0 and parts[3] > 0:
                return parts[2] / parts[3]

        # Fallback to width/height attributes
        w_attr = root.attrib.get("width", "")
        h_attr = root.attrib.get("height", "")
        w_val = "".join(c for c in w_attr if c.isdigit() or c == ".")
        h_val = "".join(c for c in h_attr if c.isdigit() or c == ".")

        if w_val and h_val and float(h_val) > 0:
            return float(w_val) / float(h_val)
    except Exception:
        pass

    return 1.0


def build_svg_grid(svg_directory: Path) -> str:
    svg_files = sorted(list(svg_directory.glob("*.svg")))

    if not svg_files:
        print(f"Warning: No SVG files found in {svg_directory}", file=sys.stderr)
        return ""

    rows = []
    current_row = []

    for filepath in svg_files:
        # Determine relative path from README location to SVG
        try:
            rel_path = filepath.relative_to(README_FILE.parent).as_posix()
        except ValueError:
            rel_path = filepath.as_posix()

        # Calculate width based on aspect ratio targeting ~48px height
        aspect_ratio = get_svg_aspect_ratio(filepath)
        display_w = round(min(TARGET_HEIGHT * aspect_ratio, MAX_CELL_WIDTH))

        # Specifying ONLY width allows the browser engine to automatically compute 
        # height based on the SVG's viewBox, preventing stretching/distortion entirely.
        cell_html = (
            f'<td align="center" width="120" height="80" valign="middle">\n'
            f'  <img src="{rel_path}" width="{display_w}" alt="{filepath.stem}" />\n'
            f'</td>'
        )
        current_row.append(cell_html)

        if len(current_row) == COLUMNS_PER_ROW:
            rows.append("  <tr>\n" + "\n".join(current_row) + "\n  </tr>")
            current_row = []

    # Fill remaining cells in incomplete final row
    if current_row:
        while len(current_row) < COLUMNS_PER_ROW:
            current_row.append('<td align="center" width="120"></td>')
        rows.append("  <tr>\n" + "\n".join(current_row) + "\n  </tr>")

    table_body = "\n".join(rows)
    return f"<table>\n{table_body}\n</table>"


def update_readme(grid_html: str):
    if not README_FILE.exists():
        print(f"Creating new {README_FILE}...")
        readme_content = f"# Icon Gallery\n\n{START_MARKER}\n{END_MARKER}\n"
    else:
        readme_content = README_FILE.read_text(encoding="utf-8")

    if START_MARKER not in readme_content or END_MARKER not in readme_content:
        print(
            f"Error: Could not find '{START_MARKER}' and '{END_MARKER}' in {README_FILE}.\n"
            f"Please add these marker comments to your README where you want the grid to appear.",
            file=sys.stderr,
        )
        sys.exit(1)

    pattern = re.compile(
        f"{re.escape(START_MARKER)}.*?{re.escape(END_MARKER)}", re.DOTALL
    )
    replacement = f"{START_MARKER}\n{grid_html}\n{END_MARKER}"
    updated_content = pattern.sub(replacement, readme_content)

    README_FILE.write_text(updated_content, encoding="utf-8")
    print(f"Successfully updated {README_FILE} with non-distorted SVG grid.")


def main():
    if not SVG_DIR.exists():
        print(f"Error: Directory '{SVG_DIR}' does not exist.", file=sys.stderr)
        sys.exit(1)

    grid_html = build_svg_grid(SVG_DIR)
    if grid_html:
        update_readme(grid_html)


if __name__ == "__main__":
    main()