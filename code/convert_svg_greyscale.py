#!/usr/bin/env python3
import os
import re
import xml.etree.ElementTree as ET

# Configure your directories here
SRC_DIR = "svg"
DEST_DIR = "grey"

def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 3:
        hex_str = ''.join([c*2 for c in hex_str])
    return int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)

def rgb_to_grayscale_hex(r, g, b):
    # Standard luminance weights for grayscale conversion
    gray = int(0.299 * r + 0.587 * g + 0.114 * b)
    return f"#{gray:02x}{gray:02x}{gray:02x}"

def color_to_gray(color_str):
    color_str = color_str.strip()
    if color_str.startswith('#'):
        try:
            r, g, b = hex_to_rgb(color_str)
            return rgb_to_grayscale_hex(r, g, b)
        except ValueError:
            return color_str
    # Handles basic named colors if present (add more as needed)
    named_colors = {'white': '#ffffff', 'black': '#000000', 'red': '#ff0000', 'blue': '#0000ff', 'green': '#008000'}
    if color_str.lower() in named_colors:
        r, g, b = hex_to_rgb(named_colors[color_str.lower()])
        return rgb_to_grayscale_hex(r, g, b)
    return color_str

def convert_style_string(style_str):
    if not style_str:
        return ""
    rules = style_str.split(';')
    new_rules = []
    for rule in rules:
        if ':' in rule:
            prop, val = rule.split(':', 1)
            prop = prop.strip()
            val = val.strip()
            if prop in ['fill', 'stroke'] and val != 'none':
                val = color_to_gray(val)
            new_rules.append(f"{prop}:{val}")
        else:
            if rule.strip():
                new_rules.append(rule)
    return ';'.join(new_rules)

def process_svg(src_path, dest_path):
    # Register namespaces to prevent 'ns0:' prefixes on write
    ET.register_namespace('', "http://www.w3.org/2000/svg")
    
    try:
        tree = ET.parse(src_path)
        root = tree.getroot()
        
        # Traverse every single element in the SVG
        for elem in root.iter():
            # 1. Convert fill and stroke attributes
            for attr in ['fill', 'stroke']:
                if attr in elem.attrib and elem.attrib[attr] != 'none':
                    elem.attrib[attr] = color_to_gray(elem.attrib[attr])
            
            # 2. Convert inline style attributes
            if 'style' in elem.attrib:
                elem.attrib['style'] = convert_style_string(elem.attrib['style'])
        
        # Write out to the target directory
        tree.write(dest_path, encoding='utf-8', xml_declaration=True)
    except Exception as e:
        print(f"Error processing {src_path}: {e}")

def main():
    if not os.path.exists(DEST_DIR):
        os.makedirs(DEST_DIR)
        
    if not os.path.exists(SRC_DIR):
        print(f"Source directory '{SRC_DIR}' does not exist.")
        return

    svg_files = [f for f in os.listdir(SRC_DIR) if f.lower().endswith('.svg')]
    
    if not svg_files:
        return

    print(f"Converting {len(svg_files)} SVGs to grayscale...")
    for filename in svg_files:
        src_path = os.path.join(SRC_DIR, filename)
        dest_path = os.path.join(DEST_DIR, filename)
        process_svg(src_path, dest_path)
        
        # Stage the newly created/updated file automatically
        os.system(f'git add "{dest_path}"')

if __name__ == "__main__":
    main()
