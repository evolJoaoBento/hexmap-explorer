"""
Command-line Hex Map Generator Tool
Test version for generating hex maps without GUI
"""
import random
import json
import math
import sys
import os

# Add current directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from generation.minecraft_biomes import MinecraftBiomeGenerator
    from config.constants import TERRAIN_TYPES
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running this from the hexcrawl directory")
    sys.exit(1)


def generate_hex_map(width, height, seed=None):
    """Generate a hex map with given dimensions"""
    if seed is None:
        seed = random.randint(1, 1000000)
    
    print(f"Generating {width}x{height} hex map with seed {seed}...")
    
    # Create biome generator
    biome_generator = MinecraftBiomeGenerator(seed)
    
    # Generate hex map data using offset coordinates
    hex_map_data = {}
    biome_counts = {}
    
    for col in range(width):
        for row in range(height):
            # Convert offset coordinates to cube coordinates
            q = col - (row - (row & 1)) // 2
            r = row
            s = -q - r
            
            # Generate terrain for this hex
            terrain = biome_generator.select_biome(q, r, s)
            
            # Store hex data
            hex_map_data[(col, row)] = {
                'q': q, 'r': r, 's': s,
                'terrain': terrain,
                'col': col, 'row': row
            }
            
            # Count biomes
            biome_counts[terrain] = biome_counts.get(terrain, 0) + 1
    
    return hex_map_data, biome_counts, seed


def print_map_info(hex_map_data, biome_counts, seed):
    """Print information about the generated map"""
    width = max(data['col'] for data in hex_map_data.values()) + 1
    height = max(data['row'] for data in hex_map_data.values()) + 1
    
    print(f"\n=== HEX MAP GENERATION COMPLETE ===")
    print(f"Dimensions: {width} x {height}")
    print(f"Total Hexes: {len(hex_map_data)}")
    print(f"Seed: {seed}")
    print(f"\nTerrain Distribution:")
    print("-" * 40)
    
    total_hexes = len(hex_map_data)
    for terrain, count in sorted(biome_counts.items()):
        percentage = (count / total_hexes) * 100
        terrain_info = TERRAIN_TYPES.get(terrain, {"description": "Unknown"})
        print(f"{terrain.title():12} {count:3} ({percentage:5.1f}%) - {terrain_info['description']}")


def create_ascii_preview(hex_map_data, width, height):
    """Create ASCII preview of the map"""
    # For large maps, scale down the preview
    show_width = min(width, 80)
    show_height = min(height, 40)
    scale_x = width / show_width if show_width < width else 1
    scale_y = height / show_height if show_height < height else 1
    
    print(f"\nASCII Preview ({width}x{height})")
    if show_width < width or show_height < height:
        print(f"Scaled to {show_width}x{show_height} for display")
    print("-" * (show_width * 2 + 5))
    
    # Create terrain symbol mapping
    terrain_symbols = {
        'water': '~', 'forest': 'T', 'plains': '.', 'mountains': '^',
        'desert': 'S', 'swamp': 'M', 'tundra': 'I', 'hills': 'h'
    }
    
    for display_row in range(show_height):
        # Indent every other row for hex offset
        if display_row % 2 == 1:
            print(" ", end="")
        
        for display_col in range(show_width):
            # Map display coordinates to actual coordinates
            actual_col = int(display_col * scale_x)
            actual_row = int(display_row * scale_y)
            
            if (actual_col, actual_row) in hex_map_data:
                terrain = hex_map_data[(actual_col, actual_row)]['terrain']
                symbol = terrain_symbols.get(terrain, '?')
                print(symbol, end=" ")
            else:
                print("?", end=" ")
        print()  # New line


def save_map_json(hex_map_data, seed, filename):
    """Save map as JSON file"""
    width = max(data['col'] for data in hex_map_data.values()) + 1
    height = max(data['row'] for data in hex_map_data.values()) + 1
    
    export_data = {
        "seed": seed,
        "dimensions": {"width": width, "height": height},
        "hexes": {}
    }
    
    for (col, row), hex_data in hex_map_data.items():
        key = f"{hex_data['q']},{hex_data['r']},{hex_data['s']}"
        export_data["hexes"][key] = {
            "q": hex_data['q'],
            "r": hex_data['r'],
            "s": hex_data['s'],
            "terrain": hex_data['terrain'],
            "description": f"A {TERRAIN_TYPES[hex_data['terrain']]['description'].lower()}",
            "explored": False,
            "visible": False
        }
    
    with open(filename, 'w') as f:
        json.dump(export_data, f, indent=2)
    
    print(f"\nMap saved as: {filename}")


def main():
    """Main function for command-line interface"""
    print("=== HEX MAP TERRAIN GENERATOR ===")
    print("Command-line version for testing\n")
    
    # Get user input
    try:
        width = int(input("Enter map width (5-500): ") or "15")
        height = int(input("Enter map height (5-500): ") or "15")
        seed_input = input("Enter seed (or press Enter for random): ").strip()
        seed = int(seed_input) if seed_input else None
    except ValueError:
        print("Invalid input. Using defaults: 15x15 with random seed")
        width, height, seed = 15, 15, None
    
    # Validate dimensions
    width = max(5, min(500, width))
    height = max(5, min(500, height))
    
    # Warn about large maps
    if width > 100 or height > 100:
        confirm = input(f"Large map ({width}x{height}) may take time. Continue? (y/n): ")
        if not confirm.lower().startswith('y'):
            print("Cancelled.")
            return
    
    # Generate map
    hex_map_data, biome_counts, final_seed = generate_hex_map(width, height, seed)
    
    # Display results
    print_map_info(hex_map_data, biome_counts, final_seed)
    create_ascii_preview(hex_map_data, width, height)
    
    # Ask if user wants to save
    save_choice = input("\nSave this map to file? (y/n): ").lower().strip()
    if save_choice.startswith('y'):
        filename = f"generated_map_{final_seed}.json"
        # Create maps directory if it doesn't exist
        os.makedirs("maps", exist_ok=True)
        save_map_json(hex_map_data, final_seed, f"maps/{filename}")
        print(f"You can load this map in the game using 'Load Map'")
    
    print("\nThanks for using the Hex Map Generator!")


if __name__ == "__main__":
    main()