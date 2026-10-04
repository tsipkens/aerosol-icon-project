import re
from pathlib import Path


def update_readme_with_svg_table(
    svg_folder: str = "./icons",
    readme_path: str = "README.md",
    columns: int = 4,
    icon_size: int = 48,
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
    html_lines = ["<!-- SVG_GRID_START -->", "<table>"]

    for i in range(0, len(svg_files), columns):
        html_lines.append("  <tr>")
        row_files = svg_files[i : i + columns]

        for svg_file in row_files:
            rel_path = svg_file.as_posix()
            name = svg_file.stem.replace("-", " ").replace("_", " ").title()

            cell = (
                f'    <td align="center" valign="middle">\n'
                f'      <a href="{rel_path}">\n'
                f'        <img src="{rel_path}" width="{icon_size}" height="{icon_size}" alt="{name}" /><br />\n'
                # f"        <sub><b>{name}</b></sub>\n"
                f"      </a>\n"
                f"    </td>"
            )
            html_lines.append(cell)

        # Fill remaining empty cells in the last row to maintain grid shape
        empty_cells_needed = columns - len(row_files)
        for _ in range(empty_cells_needed):
            html_lines.append('    <td align="center"></td>')

        html_lines.append("  </tr>")

    html_lines.append("</table>")
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
        readme_path="README.md",  # Path to your README file
        columns=4,  # Number of table columns
        icon_size=96,  # Preview size in pixels
    )