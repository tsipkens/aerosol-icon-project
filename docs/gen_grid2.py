import re
from pathlib import Path


def create_labeled_svg(svg_path: Path, output_path: Path):
    """Reads an original SVG, appends a text label at the bottom, and saves to an output path."""
    content = svg_path.read_text(encoding="utf-8")
    name = svg_path.stem.replace("-", " ").replace("_", " ").title().upper()

    # Find and parse the viewBox attribute
    vb_match = re.search(r'viewBox=["\']([\d\.\s,-]+)["\']', content)
    if vb_match:
        vb_vals = [float(v) for v in vb_match.group(1).replace(',', ' ').split()]
        if len(vb_vals) == 4:
            min_x, min_y, w, h = vb_vals
            extra_h = 22  # Extra canvas height allocated for the text label
            new_h = h + extra_h
            
            # Update viewBox with the expanded height
            new_vb = f'viewBox="{min_x} {min_y} {w} {new_h}"'
            content = content.replace(vb_match.group(0), new_vb)
            
            if len(name) > 15:
                name_label = name[0:12] + "..." + name[-1]
            else:
                name_label = name

            # Create the SVG text element centered at the bottom
            text_x = min_x + (w / 2)
            text_y = min_y + h + 15
            text_tag = (
                f'<text x="{text_x}" y="{text_y}" text-anchor="middle" '
                f'font-family="-apple-system, BlinkMacSystemFont, sans-serif" '
                f'font-size="14" fill="#666666" data-labeled="true">{name_label}</text>\n'
            )
            
            # Insert the text tag right before the closing </svg> tag
            content = re.sub(r'</\s*svg\s*>', text_tag + '</svg>', content, flags=re.IGNORECASE)

    # Save to the designated output folder
    output_path.write_text(content, encoding="utf-8")


def update_readme_with_svg_table(
    svg_folder: str = "./svg",
    output_folder: str = "docs//grid_svg",
    readme_path: str = "README.md",
    columns: int = 4,
    icon_size: int = 96,
):
    """Generates labeled SVGs in an output folder and updates README.md with an HTML table."""
    svg_dir = Path(svg_folder)
    output_dir = Path(output_folder)
    readme = Path(readme_path)

    if not svg_dir.is_dir():
        print(f"Error: Directory '{svg_folder}' does not exist.")
        return

    svg_files = sorted(list(svg_dir.glob("*.svg")))
    if not svg_files:
        print(f"No SVG files found in '{svg_folder}'.")
        return

    # Ensure the output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Build HTML Table without <thead> or <th> using the new labeled files
    html_lines = ["<!-- SVG_GRID_START -->", '<p align="left">']

    for i in range(0, len(svg_files)):
        svg_file = svg_files[i]
        
        # Define output path for the labeled SVG
        output_file = output_dir / svg_file.name
        
        # Generate and save the labeled SVG copy
        create_labeled_svg(svg_file, output_file)

        rel_path = output_file.as_posix()
        name = svg_file.stem.replace("-", " ").replace("_", " ").title()

        cell = (
            f'<a href="{rel_path}">'
            f'<img src="{rel_path}" width="{icon_size}" height="{icon_size}" alt="{name}" title="{svg_file.stem}" />'
            f"</a>"
        )
        html_lines.append(cell)

    html_lines.append("</p>")
    html_lines.append("<!-- SVG_GRID_END -->")
    gallery_html = "\n".join(html_lines)

    # 2. Read existing README.md or initialize if empty
    if readme.exists():
        content = readme.read_text(encoding="utf-8")
    else:
        content = "# Icon Library\n\n"

    # 3. Replace existing gallery block or append to the end
    pattern = r"<!-- SVG_GRID_START -->.*?<!-- SVG_GRID_END -->"
    if re.search(pattern, content, flags=re.DOTALL):
        updated_content = re.sub(
            pattern, gallery_html, content, flags=re.DOTALL
        )
    else:
        updated_content = content.rstrip() + "\n\n" + gallery_html + "\n"

    # 4. Save to README.md
    readme.write_text(updated_content, encoding="utf-8")
    print(
        f"Successfully generated {len(svg_files)} labeled SVGs in '{output_folder}' and updated '{readme_path}'!"
    )


if __name__ == "__main__":
    update_readme_with_svg_table(
        svg_folder="./svg",  # Path to your source SVG folder
        output_folder="docs//grid_svg",  # Path where labeled copies will be saved
        readme_path="./README.md",  # Path to your README file
        columns=4,  # Number of table columns
        icon_size=96,  # Preview size in pixels
    )