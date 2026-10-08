import re
from pathlib import Path


def update_readme_with_svg_table(
    svg_folder: str = "./icons",
    readme_path: str = "README.md",
    columns: int = 4,
    icon_size: int = 96,
):
    """Generates an HTML table (without headers) with linked SVGs and inserts it into README.md."""
    svg_dir = Path(svg_folder)
    readme = Path(readme_path)

    if not svg_dir.is_dir():
        print(f"Error: Directory '{svg_folder}' does not exist.")
        return

    svg_files = sorted(list(svg_dir.glob("*.svg")))
    if not svg_files:
        print(f"No SVG files found in '{svg_folder}'.")
        return

    # 1. Build HTML Table without <thead> or <th>
    html_lines = ["<!-- SVG_GRID_START -->", '<p align="left">']

    for i in range(0, len(svg_files)):
        svg_file = svg_files[i]

        rel_path = svg_file.as_posix()
        name = svg_file.stem.replace("-", " ").replace("_", " ").title()

        cell = (
            f'<a href="{rel_path}">'
            f'<img src="{rel_path}" width="{icon_size}" height="{icon_size}" alt="{name}" title="{svg_file.stem}" />'
            # f"        <sub><b>{name}</b></sub>\n"
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
        f"✔ Successfully updated '{readme_path}' with {len(svg_files)} clickable SVGs (HTML table, no headers)!"
    )


if __name__ == "__main__":
    update_readme_with_svg_table(
        svg_folder="./svg",  # Path to your SVG folder
        readme_path="./README.md",  # Path to your README file
        columns=4,  # Number of table columns
        icon_size=96,  # Preview size in pixels
    )