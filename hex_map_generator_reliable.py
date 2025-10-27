"""
Ultra-Reliable Hex Map Generator
Basic prompt-based interface with no GUI crashes
"""
import random
import json
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def safe_import():
    """Safely import biome system"""
    try:
        from generation.minecraft_biomes import MinecraftBiomeGenerator
        from config.constants import TERRAIN_TYPES
        return MinecraftBiomeGenerator, TERRAIN_TYPES
    except ImportError:
        return None, None

def get_user_input():
    """Get user input safely"""
    print("=== HEX MAP GENERATOR ===")
    print()
    
    try:
        width = input("Map width (5-200, default 20): ").strip()
        width = int(width) if width else 20
        width = max(5, min(200, width))
        
        height = input("Map height (5-200, default 20): ").strip()
        height = int(height) if height else 20
        height = max(5, min(200, height))
        
        seed_input = input("Seed (or Enter for random): ").strip()
        seed = int(seed_input) if seed_input else random.randint(1, 1000000)
        
        return width, height, seed
        
    except (ValueError, KeyboardInterrupt):
        print("Using defaults: 20x20 with random seed")
        return 20, 20, random.randint(1, 1000000)

def generate_with_biome_system(width, height, seed):
    """Generate using Minecraft biome system"""
    MinecraftBiomeGenerator, TERRAIN_TYPES = safe_import()
    
    if not MinecraftBiomeGenerator:
        return generate_simple(width, height, seed)
    
    print(f"Generating {width}x{height} map with Minecraft biomes (seed: {seed})...")
    
    generator = MinecraftBiomeGenerator(seed)
    hex_data = {}
    biome_counts = {}
    
    for col in range(width):
        for row in range(height):
            # Show progress for large maps
            if width * height > 1000 and (col * height + row) % 500 == 0:
                progress = ((col * height + row) / (width * height)) * 100
                print(f"Progress: {progress:.0f}%")
            
            # Convert to cube coordinates
            q = col - (row - (row & 1)) // 2
            r = row
            s = -q - r
            
            # Generate terrain
            terrain = generator.select_biome(q, r, s)
            
            # Store data
            hex_data[(col, row)] = {
                'q': q, 'r': r, 's': s,
                'terrain': terrain
            }
            
            biome_counts[terrain] = biome_counts.get(terrain, 0) + 1
    
    return hex_data, biome_counts, seed

def generate_simple(width, height, seed):
    """Generate using simple random system"""
    print(f"Generating {width}x{height} map with simple terrains (seed: {seed})...")
    
    random.seed(seed)
    terrains = ["water", "forest", "plains", "mountains", "desert", "hills", "swamp", "tundra"]
    
    hex_data = {}
    biome_counts = {}
    
    for col in range(width):
        for row in range(height):
            q = col - (row - (row & 1)) // 2
            r = row
            s = -q - r
            
            # Simple neighbor-influenced generation
            terrain = random.choice(terrains)
            
            hex_data[(col, row)] = {
                'q': q, 'r': r, 's': s,
                'terrain': terrain
            }
            
            biome_counts[terrain] = biome_counts.get(terrain, 0) + 1
    
    return hex_data, biome_counts, seed

def display_results(hex_data, biome_counts, seed, width, height):
    """Display generation results"""
    print()
    print("=" * 40)
    print(f"MAP GENERATED SUCCESSFULLY")
    print("=" * 40)
    print(f"Dimensions: {width} x {height}")
    print(f"Total Hexes: {len(hex_data)}")
    print(f"Seed: {seed}")
    print()
    print("TERRAIN DISTRIBUTION:")
    print("-" * 30)
    
    total = len(hex_data)
    for terrain, count in sorted(biome_counts.items()):
        percent = (count / total) * 100
        print(f"{terrain.title():12} {count:4} ({percent:5.1f}%)")
    
    # Show small preview for small maps
    if width <= 40 and height <= 25:
        print()
        print("ASCII PREVIEW:")
        print("-" * 30)
        
        symbols = {
            'water': '~', 'forest': 'T', 'plains': '.', 'mountains': '^',
            'desert': 'S', 'hills': 'h', 'swamp': 'M', 'tundra': 'I'
        }
        
        for row in range(height):
            line = " " if row % 2 == 1 else ""
            for col in range(width):
                if (col, row) in hex_data:
                    terrain = hex_data[(col, row)]['terrain']
                    symbol = symbols.get(terrain, '?')
                    line += symbol + " "
                else:
                    line += "? "
            print(line)

def save_map(hex_data, seed, width, height):
    """Save map to JSON"""
    save_choice = input("\\nSave this map? (y/n): ").strip().lower()
    
    if not save_choice.startswith('y'):
        return
    
    try:
        # Create maps directory
        os.makedirs("maps", exist_ok=True)
        
        # Generate filename
        filename = f"maps/generated_reliable_{seed}.json"
        
        # Create export data
        export_data = {
            "seed": seed,
            "dimensions": {"width": width, "height": height},
            "hexes": {}
        }
        
        for (col, row), hex_data_item in hex_data.items():
            key = f"{hex_data_item['q']},{hex_data_item['r']},{hex_data_item['s']}"
            export_data["hexes"][key] = {
                "q": hex_data_item['q'],
                "r": hex_data_item['r'],
                "s": hex_data_item['s'],
                "terrain": hex_data_item['terrain'],
                "description": f"A generated {hex_data_item['terrain']}",
                "explored": False,
                "visible": False
            }
        
        # Save file
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"\\nMap saved: {filename}")
        print("Load this in your game using 'Load Map'!")
        
    except Exception as e:
        print(f"Save failed: {e}")

def main():
    """Main function"""
    try:
        # Get input
        width, height, seed = get_user_input()
        
        # Generate map
        hex_data, biome_counts, seed = generate_with_biome_system(width, height, seed)
        
        # Display results
        display_results(hex_data, biome_counts, seed, width, height)
        
        # Save option
        save_map(hex_data, seed, width, height)
        
        print("\\nThank you for using the Hex Map Generator!")
        
    except KeyboardInterrupt:
        print("\\nCancelled by user.")
    except Exception as e:
        print(f"\\nUnexpected error: {e}")

if __name__ == "__main__":
    main()