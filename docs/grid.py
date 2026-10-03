#!/usr/bin/env python3
"""
Generates a markdown-compatible HTML grid of SVGs and injects it directly
into the repository's main README.md between marker comments.
"""

from pathlib import Path
import xml.etree.ElementTree as ET
import html
import re
import sys

# Configuration
SVG_DIR = Path("../svg")  # Directory containing SVGs
README_FILE = Path("../README.md")  # Main README file

# Comment markers to target in README.md
START_MARKER = "<!-- SVG_GRID_START -->"
END_MARKER = "<!-- SVG_GRID_END -->"

# Grid styling
CSS_STYLES = """<style>
  .svg-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
    gap: 16px;
    padding: 12px 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  }
  .svg-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    border: 1px solid #d0d7de;
    border-radius: 8px;
    padding: 16px 12px;
    background-color: #ffffff;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
  }
  .svg-card:hover {
    border-color: #0969da;
    box-shadow: 0 2px 6px rgba(9, 105, 218, 0.15);
  }
  .svg-container {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 60px;
    height: 60px;
    overflow: visible;
  }
  .svg-container svg {
    width: 100%;
    height: 100%;
    max-width: 100%;
    max-height: 100%;
    overflow: visible !important;
    transform: scale(0.75);
    transform-origin: center center;
  }
  .svg-label {
    margin-top: 12px;
    font-size: 11px;
    font-weight: 500;
    color: #57606a;
    text-align: center;
    word-break: break-word;
  }
</style>"""


def sanitize_and_normalize_svg(filepath: Path) -> str:
    """Parses SVG to remove fixed dimensions and ensure a valid viewBox exists."""
    try:
        ET.register_namespace("", "http://www.w3.org/2000/svg")
        tree = ET.parse(filepath)
        root = tree.getroot()

        tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag
        if tag.lower() != "svg":
            return filepath.read_text(encoding="utf-8")

        width = root.attrib.get("width")
        height = root.attrib.get("height")
        viewbox = root.attrib.get("viewBox") or root.attrib.get("viewbox")

        if not viewbox and width and height:
            w_val = "".join(c for c in width if c.isdigit() or c == ".")
            h_val = "".join(c for c in height if c.isdigit() or c == ".")
            if w_val and h_val:
                root.attrib["viewBox"] = f"0 0 {w_val} {h_val}"

        root.attrib.pop("width", None)
        root.attrib.pop("height", None)

        return ET.tostring(root, encoding="unicode")
    except Exception:
        return filepath.read_text(encoding="utf-8")


def build_svg_grid(svg_directory: Path) -> str:
    svg_files = sorted(list(svg_directory.glob("*.svg")))

    if not svg_files:
        print(f"Warning: No SVG files found in {svg_directory}", file=sys.stderr)
        return ""

    cards = []
    for filepath in svg_files:
        svg_content = sanitize_and_normalize_svg(filepath)
        label = html.escape(filepath.stem)

        card_html = f"""  <div class="svg-card">
    <div class="svg-container">
      {svg_content}
    </div>
    <span class="svg-label">{label}</span>
  </div>"""
        cards.append(card_html)

    grid_body = "\n".join(cards)
    return f"{CSS_STYLES}\n<div class=\"svg-grid\">\n{grid_body}\n</div>"


def update_readme(grid_html: str):
    if not README_FILE.exists():
        print(f"Creating new {README_FILE}...")
        readme_content = f"# Icon Gallery\n\n{START_MARKER}\n{END_MARKER}\n"
    else:
        readme_content = README_FILE.read_text(encoding="utf-8")

    # Check for marker presence
    if START_MARKER not in readme_content or END_MARKER not in readme_content:
        print(
            f"Error: Could not find '{START_MARKER}' and '{END_MARKER}' in {README_FILE}.\n"
            f"Please add these marker comments to your README where you want the grid to appear.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Replace content between markers
    pattern = re.compile(
        f"{re.escape(START_MARKER)}.*?{re.escape(END_MARKER)}", re.DOTALL
    )
    replacement = f"{START_MARKER}\n{grid_html}\n{END_MARKER}"
    updated_content = pattern.sub(replacement, readme_content)

    README_FILE.write_text(updated_content, encoding="utf-8")
    print(f"Successfully updated {README_FILE} with the latest SVG grid.")


def main():
    if not SVG_DIR.exists():
        print(f"Error: Directory '{SVG_DIR}' does not exist.", file=sys.stderr)
        sys.exit(1)

    grid_html = build_svg_grid(SVG_DIR)
    if grid_html:
        update_readme(grid_html)


if __name__ == "__main__":
    main()