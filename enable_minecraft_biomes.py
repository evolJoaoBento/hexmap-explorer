"""
Enable Minecraft-style biome generation in your hex map explorer
"""
from core.map import HexMap
from generation.manager import GenerationManager
from generation.minecraft_biomes import MinecraftBiomeGenerator

def demo_minecraft_biomes():
    """Demo the Minecraft biome system"""
    print("=== Minecraft-Style Biome Generation Demo ===\n")
    
    # Create a generation manager (mock for demo)
    class MockGenManager:
        def start_generation(self, hexes, gen_type):
            pass
    
    gen_manager = MockGenManager()
    
    # Create hex map with Minecraft biomes enabled
    hex_map = HexMap(
        generation_manager=gen_manager, 
        seed=12345, 
        use_minecraft_biomes=True
    )
    
    print("Creating hexes with Minecraft-style biome generation...")
    
    # Generate a small area of hexes
    for r in range(-3, 4):
        for q in range(-3, 4):
            s = -q - r
            hex_obj = hex_map.create_hex(q, r, s)
            print(f"Hex ({q:2},{r:2},{s:2}): {hex_obj.terrain}")
    
    print(f"\nTo enable this in your application:")
    print("1. Modify the HexMap constructor call in your main application")
    print("2. Add parameter: use_minecraft_biomes=True")
    print("3. Example:")
    print("   hex_map = HexMap(gen_manager, seed=12345, use_minecraft_biomes=True)")

if __name__ == "__main__":
    demo_minecraft_biomes()