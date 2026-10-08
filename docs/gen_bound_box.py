import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Optional, Tuple

ET.register_namespace("", "http://www.w3.org/2000/svg")
NS = {"svg": "http://www.w3.org/2000/svg"}


def get_svg_dimensions(root: ET.Element) -> Optional[Tuple[float, float, float, float]]:
    """Extracts (x, y, width, height) from viewBox or width/height attributes."""
    viewbox_str = root.attrib.get("viewBox")
    if viewbox_str:
        try:
            parts = [float(p) for p in viewbox_str.replace(",", " ").split()]
            if len(parts) == 4 and parts[2] > 0 and parts[3] > 0:
                return parts[0], parts[1], parts[2], parts[3]
        except ValueError:
            pass

    # Fallback to width / height attributes
    try:
        w_str = root.attrib.get("width", "0").replace("px", "").strip()
        h_str = root.attrib.get("height", "0").replace("px", "").strip()
        w, h = float(w_str), float(h_str)
        if w > 0 and h > 0:
            return 0.0, 0.0, w, h
    except ValueError:
        pass

    return None


def standardize_svg_bounding_boxes(
    folder_path: str,
    target_path: str,
    target_size: Optional[Tuple[float, float]] = None,
    padding: float = 0.0,
):
    """Processes all SVGs in folder_path to give them a uniform bounding box.

    If target_size is None, automatically calculates max(width) and max(height)
    across all valid SVGs.

    padding: Uniform padding applied to all four sides of the final bounding box.
    """
    directory = Path(folder_path)
    if not directory.is_dir():
        print(f"Error: Directory '{folder_path}' does not exist.")
        return

    svg_files = list(directory.glob("*.svg"))
    if not svg_files:
        print(f"No SVG files found in '{folder_path}'.")
        return

    print(f"Found {len(svg_files)} SVG file(s). Starting Pass 1 (Inspection)...")

    # Pass 1: Parse all SVGs and calculate global maximum dimensions
    svg_data: Dict[Path, Tuple[ET.ElementTree, float, float, float, float]] = {}
    max_w, max_h = 0.0, 0.0

    for svg_path in svg_files:
        try:
            tree = ET.parse(svg_path)
            root = tree.getroot()
            dims = get_svg_dimensions(root)
            if dims:
                svg_data[svg_path] = (tree, *dims)
                _, _, w, h = dims
                max_w = max(max_w, w)
                max_h = max(max_h, h)
            else:
                print(f"⚠️  Skipping {svg_path.name}: Could not determine dimensions.")
        except ET.ParseError:
            print(f"⚠️  Skipping invalid SVG/XML file: {svg_path.name}")

    if not svg_data:
        print("No valid SVGs found to process.")
        return

    # Use explicit target_size if passed, otherwise use maximum bounds
    content_width = target_size[0] if target_size else max_w
    content_height = target_size[1] if target_size else max_h

    # Add uniform padding to both sides (left/right and top/bottom)
    total_width = content_width + (2 * padding)
    total_height = content_height + (2 * padding)

    print(
        f"\nPass 1 Complete. Base Size: {content_width:.2f} x {content_height:.2f} | "
        f"Padding: {padding:.2f} | Final Bounding Box Size: {total_width:.2f} x {total_height:.2f}"
    )
    print("Starting Pass 2 (Applying uniform bounding boxes and centering content)...")

    # Pass 2: Adjust viewBox to center artwork inside uniform bounding box and add <rect>
    modified_count = 0
    for svg_path, (tree, orig_x, orig_y, orig_w, orig_h) in svg_data.items():
        root = tree.getroot()

        # Calculate offset padding required to center the original content + user padding
        pad_x = ((content_width - orig_w) / 2.0) + padding
        pad_y = ((content_height - orig_h) / 2.0) + padding

        new_x = orig_x - pad_x
        new_y = orig_y - pad_y

        # Update root viewBox to represent uniform bounding dimensions
        root.attrib["viewBox"] = f"{new_x} {new_y} {total_width} {total_height}"

        # Sync explicit width/height attributes if present
        if "width" in root.attrib:
            root.attrib["width"] = f"{total_width}px"
        if "height" in root.attrib:
            root.attrib["height"] = f"{total_height}px"

        # Remove existing full-canvas bounding box rects to prevent duplicates
        for rect in list(root.findall(".//svg:rect", NS)) + list(
            root.findall(".//rect")
        ):
            if rect.attrib.get("id") == "bounding-box":
                root.remove(rect)

        # Insert uniform invisible bounding box rect at the back (first child)
        bbox_rect = ET.Element(
            "{http://www.w3.org/2000/svg}rect",
            {
                "id": "bounding-box",
                "x": str(new_x),
                "y": str(new_y),
                "width": str(total_width),
                "height": str(total_height),
                "fill": "none",
                "pointer-events": "all",
            },
        )
        root.insert(0, bbox_rect)

        # Save back to file
        out_path = Path(target_path) / svg_path.name
        tree.write(out_path, encoding="utf-8", xml_declaration=True)
        print(f"✔ Standardized: {svg_path.name}")
        modified_count += 1

    print(
        f"\nDone! Successfully updated {modified_count} SVGs to {total_width:.1f}x{total_height:.1f} (including {padding}px padding)."
    )


if __name__ == "__main__":
    folder_to_clean = "./raw"
    folder_to_output = './svg'

    # Example 1: Automatic bounds + 10px uniform padding
    standardize_svg_bounding_boxes(folder_to_clean, folder_to_output, padding=10)

    # Example 2: Forced target size (64x64) + 8px uniform padding (Canvas becomes 80x80)
    # standardize_svg_bounding_boxes(folder_to_clean, target_size=(64.0, 64.0), padding=8.0)