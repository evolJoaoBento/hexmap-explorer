#!/usr/bin/env python3
"""
Convert hex map JSON to text-mapper format.

Usage: python hex_to_textmapper.py input.json > output.txt
"""

import json
import sys
from pathlib import Path

# Terrain type mappings to text-mapper terrain codes
TERRAIN_MAP = {
    'forest': 'forest',
    'water': 'lake',
    'lake': 'lake',
    'river': 'lake',
    'ocean': 'lake',
    'sea': 'lake',
    'grass': 'grass',
    'grassland': 'grass',
    'plains': 'grass',
    'hill': 'hill',
    'hills': 'hill',
    'mountain': 'mountain',
    'mountains': 'mountains',
    'desert': 'desert',
    'swamp': 'swamp',
    'marsh': 'marsh',
    'bush': 'bush',
    'bushes': 'bushes',
    'brushland': 'brushland',
    'fields': 'fields',
    'tree': 'tree',
    'trees': 'trees',
    'fir': 'fir',
    'firs': 'firs',
    'sand': 'sand',
    'rock': 'rock',
    'soil': 'soil',
    'dust': 'dust',
    'town': 'town',
    'village': 'village',
    'city': 'city',
    'thorp': 'thorp',
    'castle': 'castle',
    'keep': 'keep',
    'tower': 'tower',
    'shrine': 'shrine'
}

def axial_to_offset(q, r):
    """Convert axial coordinates (q, r) to offset coordinates (col, row)."""
    col = q
    row = r + (q - (q & 1)) // 2
    return col, row

def offset_to_textmapper(col, row):
    """Convert offset coordinates to text-mapper format (0101, 0102, etc.)."""
    # Text-mapper uses 1-based indexing, format: XXYY where XX is column, YY is row
    # Shift to make coordinates positive and 1-based
    tm_col = col + 1
    tm_row = row + 1
    
    # Handle negative coordinates by shifting the entire map if needed
    if tm_col <= 0:
        tm_col = 1
    if tm_row <= 0:
        tm_row = 1
        
    return f"{tm_col:02d}{tm_row:02d}"

def convert_hex_to_textmapper(json_file):
    """Convert hex map JSON to text-mapper format."""
    
    # Load JSON
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    hexes = data.get('hexes', [])
    
    if not hexes:
        print("# No hexes found in JSON file", file=sys.stderr)
        return
    
    # Find the bounds to properly offset coordinates
    min_col = min_row = float('inf')
    max_col = max_row = float('-inf')
    
    for hex_data in hexes:
        q = hex_data['q']
        r = hex_data['r']
        col, row = axial_to_offset(q, r)
        min_col = min(min_col, col)
        min_row = min(min_row, row)
        max_col = max(max_col, col)
        max_row = max(max_row, row)
    
    # Calculate offset to make all coordinates positive
    col_offset = 1 - min_col if min_col < 0 else 0
    row_offset = 1 - min_row if min_row < 0 else 0
    
    # Convert each hex
    output_lines = []
    
    for hex_data in hexes:
        q = hex_data['q']
        r = hex_data['r']
        terrain = hex_data.get('terrain', 'grass').lower()
        description = hex_data.get('description', '')
        
        # Convert coordinates
        col, row = axial_to_offset(q, r)
        col += col_offset
        row += row_offset
        
        # Format as text-mapper coordinate
        coord = f"{col:02d}{row:02d}"
        
        # Map terrain type
        tm_terrain = TERRAIN_MAP.get(terrain, terrain)
        
        # Create the line
        # Format: XXYY terrain "description"
        if description:
            # Escape quotes in description
            description = description.replace('"', '\\"')
            # Truncate long descriptions
            if len(description) > 50:
                description = description[:47] + "..."
            line = f'{coord} {tm_terrain} "{description}"'
        else:
            line = f'{coord} {tm_terrain} "{tm_terrain}"'
        
        output_lines.append(line)
    
    # Sort by coordinates for better readability
    output_lines.sort()
    
    # Output
    print("# Generated from hex map JSON")
    print(f"# Original bounds: q:[{min(h['q'] for h in hexes)},{max(h['q'] for h in hexes)}] r:[{min(h['r'] for h in hexes)},{max(h['r'] for h in hexes)}]")
    print(f"# Offset applied: col+{col_offset}, row+{row_offset}")
    print()
    
    for line in output_lines:
        print(line)

def main():
    if len(sys.argv) != 2:
        print("Usage: python hex_to_textmapper.py input.json", file=sys.stderr)
        print("Output is written to stdout, redirect to save:", file=sys.stderr)
        print("  python hex_to_textmapper.py input.json > output.txt", file=sys.stderr)
        sys.exit(1)
    
    json_file = Path(sys.argv[1])
    
    if not json_file.exists():
        print(f"Error: File '{json_file}' not found", file=sys.stderr)
        sys.exit(1)
    
    try:
        convert_hex_to_textmapper(json_file)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{json_file}': {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()